from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from app.schemas.schemas import UserUpdate
from app.services.user_service import (
    apply_avatar_upload,
    get_user_by_id,
    get_user_by_username,
    get_user_by_username_ci,
    get_user_contribution_results,
    get_user_tests_paginated,
    xp_for_next_level,
    ACHIEVEMENTS,
    update_user_profile,
)
from app.core.security import get_current_user
from app.api.routes.auth import user_to_public

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("/achievements")
async def get_all_achievements():
    """Get all possible achievements."""
    return ACHIEVEMENTS


@router.post("/me/avatar")
async def upload_my_avatar(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
):
    """
    Загрузка аватара текущего пользователя. Путь не пересекается с GET /{username}.
    Основной URL для фронта, если на проде 404 на /api/auth/avatar (прокси / nginx).
    """
    content = await file.read()
    try:
        data = await apply_avatar_upload(user_id, content)
    except ValueError as e:
        msg = str(e)
        if msg == "Пользователь не найден":
            raise HTTPException(status_code=404, detail=msg) from e
        raise HTTPException(status_code=400, detail=msg) from e
    return {"avatar_url": data["avatar_url"], "user": user_to_public(data["user"])}


@router.put("/update")
async def update_profile(data: UserUpdate, user_id: str = Depends(get_current_user)):
    raw = data.model_dump(exclude_unset=True)
    new_password = raw.pop("new_password", None)
    current_password = raw.pop("current_password", None)
    if not raw and not new_password:
        user = await get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        return {"user": user_to_public(user)}
    try:
        user = await update_user_profile(
            user_id, raw, new_password=new_password, current_password=current_password
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"user": user_to_public(user)}


def _result_row_to_history_item(r: dict) -> dict:
    return {
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


@router.get("/{username}/tests")
async def get_profile_tests(
    username: str,
    period: str = Query("all", description="all | 7d | 30d | 365d"),
    mode: str = Query("all", description="all | time | words"),
    page: int = Query(1, ge=1),
    page_size: int = Query(40, description="40 | 60 | 120"),
):
    user = await get_user_by_username_ci(username)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    ps = page_size if page_size in (40, 60, 120) else 40
    results, total = await get_user_tests_paginated(
        str(user["id"]),
        period=period,
        mode=mode,
        page=page,
        page_size=ps,
    )
    return {
        "tests": [_result_row_to_history_item(r) for r in results],
        "total": total,
        "page": page,
        "page_size": ps,
    }


@router.get("/{username}")
async def get_profile(
    username: str,
    tests_page: Optional[int] = Query(
        None,
        ge=1,
        description="Если задан — в ответе будет блок tests (пагинация без отдельного URL /tests).",
    ),
    tests_page_size: int = Query(40, description="40 | 60 | 120"),
    period: str = Query("all", description="all | 7d | 30d | 365d"),
    mode: str = Query("all", description="all | time | words"),
):
    user = await get_user_by_username_ci(username)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    contrib = await get_user_contribution_results(str(user["id"]), days=320)
    wpm_history = [
        {
            "wpm": r["wpm"],
            "created_at": r["created_at"].isoformat(),
            "timestamp": r["created_at"].isoformat(),
        }
        for r in contrib
    ]

    payload = {
        "user": {
            "id": str(user["id"]),
            "username": user["username"],
            "avatar_url": user.get("avatar_url"),
            "level": user.get("level", 1),
            "xp": user.get("xp", 0),
            "xp_to_next": xp_for_next_level(user.get("level", 1)),
            "total_tests": user.get("total_tests", 0),
            "best_wpm": user.get("best_wpm", 0),
            "avg_wpm": user.get("avg_wpm", 0),
            "avg_accuracy": user.get("avg_accuracy", 0),
            "achievements": user.get("achievements") or [],
            "created_at": user["created_at"].isoformat() if user.get("created_at") else None,
        },
        "history": wpm_history,
    }

    if tests_page is not None:
        ps = tests_page_size if tests_page_size in (40, 60, 120) else 40
        results, total = await get_user_tests_paginated(
            str(user["id"]),
            period=period,
            mode=mode,
            page=tests_page,
            page_size=ps,
        )
        payload["tests"] = [_result_row_to_history_item(r) for r in results]
        payload["total"] = total
        payload["page"] = tests_page
        payload["page_size"] = ps

    return payload
