from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import get_settings
from app.db.mongodb import connect_db, disconnect_db
from app.api.routes import auth, typing, leaderboard, profile, arena

settings = get_settings()
logger = logging.getLogger(__name__)
allowed_origins = set(settings.cors_origins())


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
    origin = request.headers.get("origin")
    is_allowed_origin = bool(origin and origin in allowed_origins)

    def apply_cors_headers(response: JSONResponse):
        if is_allowed_origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Vary"] = "Origin"
        return response

    # Explicit preflight fallback in case upstream middleware chain changes.
    if request.method == "OPTIONS":
        preflight = JSONResponse(status_code=204, content=None)
        if is_allowed_origin:
            preflight.headers["Access-Control-Allow-Origin"] = origin
            preflight.headers["Access-Control-Allow-Credentials"] = "true"
            preflight.headers["Access-Control-Allow-Methods"] = "*"
            requested_headers = request.headers.get("access-control-request-headers", "*")
            preflight.headers["Access-Control-Allow-Headers"] = requested_headers
            preflight.headers["Vary"] = "Origin"
        return preflight

    path = request.scope.get("path", "")
    legacy_prefixes = ("/typing", "/auth", "/leaderboard", "/profile", "/arena")

    # Backward compatibility for clients calling old routes without "/api".
    if not path.startswith("/api") and path.startswith(legacy_prefixes):
        request.scope["path"] = f"/api{path}"

    try:
        response = await call_next(request)
        return apply_cors_headers(response)
    except Exception:
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        response = JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )
        return apply_cors_headers(response)


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
