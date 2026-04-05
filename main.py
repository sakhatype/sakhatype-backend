from contextlib import asynccontextmanager
import logging
import os
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from app.core.validation_errors_ru import format_validation_errors_detail
import uvicorn
from app.db.postgres import connect_db, disconnect_db
from app.api.routes import auth, typing, leaderboard, profile, arena, friends
from app.core.paths import AVATAR_UPLOAD_DIR

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    AVATAR_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    await connect_db()
    yield
    await disconnect_db()


app = FastAPI(
    title="SAKHATYPE API",
    version="2.0.0",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    message = format_validation_errors_detail(exc.errors())
    return JSONResponse(status_code=422, content={"detail": message})


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
    legacy_prefixes = ("/typing", "/auth", "/leaderboard", "/profile", "/arena", "/friends")

    if not path.startswith("/api") and path.startswith(legacy_prefixes):
        request.scope["path"] = f"/api{path}"

    try:
        return await call_next(request)
    except Exception:
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "Внутренняя ошибка сервера"},
        )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Внутренняя ошибка сервера"},
    )

# Routes
app.include_router(auth.router)
app.include_router(typing.router)
app.include_router(leaderboard.router)
app.include_router(profile.router)
app.include_router(arena.router)
app.include_router(arena.legacy_ws_router)
app.include_router(friends.router)

# До lifespan: StaticFiles падает при импорте, если каталога нет (Docker / чистый деплой).
AVATAR_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount(
    "/api/uploads/avatars",
    StaticFiles(directory=str(AVATAR_UPLOAD_DIR)),
    name="avatar_uploads",
)


@app.get("/")
async def root():
    return {"message": "SAKHATYPE API v2.0 (PostgreSQL)", "status": "online"}


@app.get("/api/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
