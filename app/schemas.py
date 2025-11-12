from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class User(BaseModel):
    username: str
    password: str

class UserProfile(BaseModel):
    username: str
    total_tests: int
    total_time_seconds: int
    best_wpm: float
    best_accuracy: float
    total_experience: int
    level: int
    created_at: datetime

    class Config:
        from_attributes = True

class TestResultCreate(BaseModel):
    wpm: float
    raw_wpm: float
    accuracy: float
    burst_wpm: float
    total_errors: int
    time_mode: int
    test_duration: int
    consistency: float = 0.0

class TestResultResponse(BaseModel):
    id: int
    username: str
    wpm: float
    raw_wpm: float
    accuracy: float
    burst_wpm: float
    total_errors: int
    time_mode: int
    test_duration: int
    consistency: float
    created_at: datetime

    class Config:
        from_attributes = True

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