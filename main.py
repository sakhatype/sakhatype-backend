from contextlib import asynccontextmanager
import logging
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from app.db.mongodb import connect_db, disconnect_db
from app.api.routes import auth, typing, leaderboard, profile, arena

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    await connect_db()
    yield
    await disconnect_db()


app = FastAPI(
    title="SAKHATYPE API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def legacy_api_prefix_compat(request: Request, call_next):
    path = request.scope.get("path", "")
    legacy_prefixes = ("/typing", "/auth", "/leaderboard", "/profile", "/arena")

    # Backward compatibility for clients calling old routes without "/api".
    if not path.startswith("/api") and path.startswith(legacy_prefixes):
        request.scope["path"] = f"/api{path}"

    try:
        return await call_next(request)
    except Exception:
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

# Routes
app.include_router(auth.router)
app.include_router(typing.router)
app.include_router(leaderboard.router)
app.include_router(profile.router)
app.include_router(arena.router)


@app.get("/")
async def root():
    return {"message": "SAKHATYPE API v1.0", "status": "online"}


@app.get("/api/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
