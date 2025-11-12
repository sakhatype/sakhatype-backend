from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from .schemas import LeaderboardEntry
from .service import LeaderboardService
from ...shared.dependencies import get_db

router = APIRouter(prefix='/api/leaderboard', tags=['Leaderboard'])

@router.get('/wpm', response_model=List[LeaderboardEntry])
def get_leaderboard_wpm(limit: int = 100, db: Session = Depends(get_db)):
    return LeaderboardService.get_leaderboard_wpm(db, limit)

@router.get('/accuracy', response_model=List[LeaderboardEntry])
def get_leaderboard_accuracy(limit: int = 100, db: Session = Depends(get_db)):
    return LeaderboardService.get_leaderboard_accuracy(db, limit)
