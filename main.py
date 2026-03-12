from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.db.mongodb import connect_db, disconnect_db
from app.api.routes import auth, typing, leaderboard, profile, arena

settings = get_settings()

app = FastAPI(
    title="DOTX TYPE API",
    description="Sakha Language Typing Terminal - Backend API",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "https://sakhatype.ru",
        "http://sakhatype.ru",
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth.router)
app.include_router(typing.router)
app.include_router(leaderboard.router)
app.include_router(profile.router)
app.include_router(arena.router)


@app.on_event("startup")
async def startup():
    await connect_db()


@app.on_event("shutdown")
async def shutdown():
    await disconnect_db()


@app.get("/")
async def root():
    return {"message": "DOTX TYPE API v1.0", "status": "online"}


@app.get("/api/health")
async def health():
    return {"status": "ok"}
