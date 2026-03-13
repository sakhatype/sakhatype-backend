from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.db.mongodb import connect_db, disconnect_db
from app.api.routes import auth, typing, leaderboard, profile, arena

settings = get_settings()


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
    allow_origins=settings.cors_origins(),
    allow_credentials=True,
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

    return await call_next(request)

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
