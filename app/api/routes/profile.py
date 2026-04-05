from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from app.schemas.schemas import UserUpdate
from app.services.user_service import (
    ACHIEVEMENTS,
    apply_avatar_upload,
    get_profile_tests_payload_by_username,
    get_user_by_id,
    get_user_by_username_ci,
    get_user_contribution_results,
    get_user_tests_paginated,
    result_row_to_profile_history_item,
    update_user_profile,
    xp_for_next_level,
)
from app.core.security import get_current_user
from app.api.routes.auth import user_to_public

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("/achievements")
async def get_all_achievements():
    """Get all possible achievements."""
    return ACHIEVEMENTS


async def _do_avatar_upload(file: UploadFile, user_id: str) -> dict:
    content = await file.read()
    try:
        data = await apply_avatar_upload(user_id, content)
    except ValueError as e:
        msg = str(e)
        if msg == "Пользователь не найден":
            raise HTTPException(status_code=404, detail=msg) from e
        raise HTTPException(status_code=400, detail=msg) from e
    return {"avatar_url": data["avatar_url"], "user": user_to_public(data["user"])}


@router.post("/me/avatar")
async def upload_my_avatar(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
):
    """
    Загрузка аватара. Дубликат без вложенного пути: POST /api/profile/upload-avatar
    (не /avatar — иначе при отсутствии POST на проде Starlette отдаёт 405 из-за GET /{username}).
    """
    return await _do_avatar_upload(file, user_id)


@router.post("/upload-avatar")
async def upload_my_avatar_one_segment(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
):
    """Один сегмент после /profile/, без конфликта с GET /api/profile/{username}."""
    return await _do_avatar_upload(file, user_id)


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


async def _profile_tests_payload(
    username: str,
    period: str,
    mode: str,
    page: int,
    page_size: int,
) -> dict:
    out = await get_profile_tests_payload_by_username(username, period, mode, page, page_size)
    if not out:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return out


@router.get("/{username}/tests")
async def get_profile_tests(
    username: str,
    period: str = Query("all", description="all | 7d | 30d | 365d"),
    mode: str = Query("all", description="all | time | words"),
    page: int = Query(1, ge=1),
    page_size: int = Query(40, description="40 | 60 | 120"),
):
    return await _profile_tests_payload(username, period, mode, page, page_size)


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
        payload["tests"] = [result_row_to_profile_history_item(r) for r in results]
        payload["total"] = total
        payload["page"] = tests_page
        payload["page_size"] = ps

    return payload
