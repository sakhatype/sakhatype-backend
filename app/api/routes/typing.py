from fastapi import APIRouter, Depends
from typing import Optional
from app.schemas.schemas import (
    TestResultCreate,
    TestResultResponse,
    TestResultWithXP,
    WordsRequest,
    WordsResponse,
)
from app.services.user_service import save_test_result, get_user_results, xp_for_next_level
from app.services.word_service import get_words
from app.core.security import get_current_user_optional

router = APIRouter(prefix="/api/typing", tags=["typing"])


@router.post("/words", response_model=WordsResponse)
async def fetch_words(req: WordsRequest):
    words = get_words(language=req.language, count=req.count)
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
            id=str(result_doc["_id"]),
            user_id=result_doc.get("user_id"),
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
            "id": str(r["_id"]),
            "wpm": r["wpm"],
            "raw_wpm": r.get("raw_wpm", 0),
            "accuracy": r["accuracy"],
            "mode": r["mode"],
            "mode_value": r["mode_value"],
            "language": r["language"],
            "difficulty": r.get("difficulty", "normal"),
            "created_at": r["created_at"].isoformat(),
        }
        for r in results
    ]
