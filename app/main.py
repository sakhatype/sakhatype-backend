from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.database import Base, engine
from .features.auth.router import router as auth_router
from .features.typing.router import router as typing_router
from .features.user.router import router as user_router
from .features.leaderboard.router import router as leaderboard_router

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title='Sakhatype API',
    version='2.0',
    swagger_ui_parameters={
        "persistAuthorization": True
    }
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def hello():
    return {"message": "Sakhatype API үлэлии турар"}

# Include routers
app.include_router(auth_router)
app.include_router(typing_router)
app.include_router(user_router)
app.include_router(leaderboard_router)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8001)
