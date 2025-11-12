from pydantic import BaseModel
from typing import Optional

class LeaderboardEntry(BaseModel):
    username: str
    wpm: Optional[float] = None
    accuracy: Optional[float] = None
    total_tests: int
    best_wpm: float
    best_accuracy: float
    level: int

    class Config:
        from_attributes = True
