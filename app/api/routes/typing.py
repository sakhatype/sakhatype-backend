from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from app.schemas.schemas import (
    TestResultCreate,
    TestResultResponse,
    TestResultWithXP,
    WordsRequest,
    WordsResponse,
)
from app.services.user_service import (
    get_profile_tests_payload_by_username,
    get_user_results,
    save_test_result,
    xp_for_next_level,
)
from app.services.word_service import get_words
from app.core.security import get_current_user_optional

router = APIRouter(prefix="/api/typing", tags=["typing"])


@router.post("/words", response_model=WordsResponse)
async def fetch_words(req: WordsRequest):
    words = get_words(language=req.language, count=req.count, difficulty=req.difficulty)
    return WordsResponse(words=words, language=req.language)


@router.post("/result", response_model=TestResultWithXP)
async def submit_result(
    data: TestResultCreate,
    user_id: Optional[str] = Depends(get_current_user_optional),
):
    result_data = data.model_dump()
    saved = await save_test_result(user_id, result_data)

    result_doc = saved["result"]
    return TestResultWithXP(
        result=TestResultResponse(
            id=str(result_doc["id"]),
            user_id=str(result_doc["user_id"]) if result_doc.get("user_id") else None,
            wpm=result_doc["wpm"],
            raw_wpm=result_doc["raw_wpm"],
            accuracy=result_doc["accuracy"],
            mode=result_doc["mode"],
            mode_value=result_doc["mode_value"],
            language=result_doc["language"],
            difficulty=result_doc.get("difficulty", "normal"),
            chars_correct=result_doc.get("chars_correct", 0),
            chars_incorrect=result_doc.get("chars_incorrect", 0),
            chars_extra=result_doc.get("chars_extra", 0),
            chars_missed=result_doc.get("chars_missed", 0),
            xp_earned=saved["xp_earned"],
            created_at=result_doc["created_at"],
        ),
        xp_earned=saved["xp_earned"],
        level_up=saved["level_up"],
        new_level=saved["new_level"],
        new_xp=saved["new_xp"],
        xp_to_next=saved["xp_to_next"],
        new_achievements=saved["new_achievements"],
    )


@router.get("/user-tests")
async def get_public_user_tests(
    username: str = Query(..., description="Имя пользователя (как в URL профиля)"),
    period: str = Query("all", description="all | 7d | 30d | 365d"),
    mode: str = Query("all", description="all | time | words"),
    page: int = Query(1, ge=1),
    page_size: int = Query(40, description="40 | 60 | 120"),
):
    """
    Публичный список тестов по нику. Один сегмент пути (/api/typing/user-tests), без вложенности
    /profile/{user}/tests — удобно, если ingress режет глубокие пути под /api/profile/.
    """
    out = await get_profile_tests_payload_by_username(username, period, mode, page, page_size)
    if not out:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return out


@router.get("/history")
async def get_history(
    limit: int = 50,
    user_id: str = Depends(get_current_user_optional),
):
    if not user_id:
        return []
    results = await get_user_results(user_id, limit)
    return [
        {
            "id": str(r["id"]),
            "wpm": r["wpm"],
            "raw_wpm": r.get("raw_wpm", 0),
            "accuracy": r["accuracy"],
            "mode": r["mode"],
            "mode_value": r["mode_value"],
            "language": r["language"],
            "difficulty": r.get("difficulty", "normal"),
            "chars_correct": r.get("chars_correct", 0),
            "chars_incorrect": r.get("chars_incorrect", 0),
            "chars_extra": r.get("chars_extra", 0),
            "chars_missed": r.get("chars_missed", 0),
            "created_at": r["created_at"].isoformat(),
            "timestamp": r["created_at"].isoformat(),
        }
        for r in results
    ]
