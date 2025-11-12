from pydantic import BaseModel
from datetime import datetime

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
