from fastapi import APIRouter, Depends, HTTPException
from app.schemas.schemas import UserPublic
from app.services.user_service import get_user_by_id, get_user_by_username, get_user_results, xp_for_next_level, ACHIEVEMENTS
from app.core.security import get_current_user

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("/achievements")
async def get_all_achievements():
    """Get all possible achievements."""
    return ACHIEVEMENTS


@router.get("/{username}")
async def get_profile(username: str):
    user = await get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    results = await get_user_results(str(user["_id"]), limit=100)

    # Build WPM history for graph
    wpm_history = [
        {
            "wpm": r["wpm"],
            "raw_wpm": r.get("raw_wpm", r["wpm"]),
            "accuracy": r["accuracy"],
            "created_at": r["created_at"].isoformat(),
            "timestamp": r["created_at"].isoformat(),
            "mode": r["mode"],
            "mode_value": r["mode_value"],
            "language": r["language"],
            "difficulty": r.get("difficulty", "normal"),
            "chars_correct": r.get("chars_correct", 0),
            "chars_incorrect": r.get("chars_incorrect", 0),
            "chars_extra": r.get("chars_extra", 0),
            "chars_missed": r.get("chars_missed", 0),
        }
        for r in results
    ]

    return {
        "user": {
            "id": str(user["_id"]),
            "username": user["username"],
            "level": user.get("level", 1),
            "xp": user.get("xp", 0),
            "xp_to_next": xp_for_next_level(user.get("level", 1)),
            "total_tests": user.get("total_tests", 0),
            "best_wpm": user.get("best_wpm", 0),
            "avg_wpm": user.get("avg_wpm", 0),
            "avg_accuracy": user.get("avg_accuracy", 0),
            "achievements": user.get("achievements", []),
            "created_at": user.get("created_at", "").isoformat() if user.get("created_at") else None,
        },
        "history": wpm_history,
    }
