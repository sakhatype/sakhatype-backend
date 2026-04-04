from fastapi import APIRouter
from typing import List
from app.schemas.schemas import LeaderboardEntry
from app.services.user_service import get_leaderboard

router = APIRouter(prefix="/api/leaderboard", tags=["leaderboard"])


@router.get("/", response_model=List[LeaderboardEntry])
async def leaderboard(
    mode: str = "time",
    mode_value: int = 30,
    limit: int = 50,
    difficulty: str = "normal",
):
    return await get_leaderboard(
        mode=mode, mode_value=mode_value, limit=limit, difficulty=difficulty
    )
