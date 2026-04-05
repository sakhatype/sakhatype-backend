from typing import List

from fastapi import APIRouter, HTTPException, Query

from app.schemas.schemas import LeaderboardEntry
from app.services.user_service import get_leaderboard, get_profile_tests_payload_by_username

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


@router.get("/user-tests")
async def leaderboard_user_tests(
    username: str = Query(..., description="Имя пользователя"),
    period: str = Query("all", description="all | 7d | 30d | 365d"),
    mode: str = Query("all", description="all | time | words"),
    page: int = Query(1, ge=1),
    page_size: int = Query(40, description="40 | 60 | 120"),
):
    """Дубликат GET /api/typing/user-tests — другой префикс на случай фильтра прокси."""
    out = await get_profile_tests_payload_by_username(username, period, mode, page, page_size)
    if not out:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return out
