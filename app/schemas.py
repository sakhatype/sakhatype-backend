from datetime import datetime

from pydantic import BaseModel

class User(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
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