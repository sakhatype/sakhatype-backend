from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from .schemas import TestResultCreate, TestResultResponse
from .service import TypingService
from ...shared.dependencies import get_db, get_current_username

router = APIRouter(prefix='/api', tags=['Typing'])

@router.get('/words')
def get_words(limit: int = 100, db: Session = Depends(get_db)):
    return TypingService.get_words(db, limit)

@router.post('/results', response_model=TestResultResponse)
def save_test_result(
    result: TestResultCreate,
    username: str = Depends(get_current_username),
    db: Session = Depends(get_db)
):
    return TypingService.create_test_result(db, username, result)

@router.get('/results/user/{username}', response_model=List[TestResultResponse])
def get_user_results(username: str, limit: int = 50, db: Session = Depends(get_db)):
    return TypingService.get_user_results(db, username, limit)
