import re
from datetime import datetime

from fastapi import HTTPException
from pydantic import BaseModel, field_validator, ConfigDict
from starlette import status

from . import enums

class Token(BaseModel):
    access_token: str
    token_type: str
    username: str

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

    @field_validator('username')
    @classmethod
    def validate_username(cls, value: str):
        value = value.lower()

        if not re.match(r'^[a-z0-9]+$', value):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Разрешаются только цифры и латинские буквы.'
            )

        return value

class UserRegisterResponse(UserBase):
    pass

class TestResultCreate(BaseModel):
    difficulty: enums.Difficulty
    time_mode: enums.TimeMode
    test_duration: int

    wpm: float
    raw_wpm: float
    burst_wpm: float

    accuracy: float
    consistency: float
    total_errors: int

class TestResultResponse(BaseModel):
    difficulty: enums.Difficulty
    time_mode: enums.TimeMode
    test_duration: int

    wpm: float
    raw_wpm: float
    burst_wpm: float

    accuracy: float
    consistency: float
    total_errors: int

    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class UserStat(BaseModel):
    username: str

    difficulty: enums.Difficulty
    time_mode: enums.TimeMode

    total_tests: int
    best_wpm: float

    model_config = ConfigDict(from_attributes=True)

class UserResponse(UserBase):
    username: str

    total_tests: int
    total_time_seconds: int
    total_experience: int
    level: int

    best_wpm: float
    best_accuracy: float

    created_at: datetime

    stats: list[UserStat]

    model_config = ConfigDict(from_attributes=True)

class LeaderboardEntry(BaseModel):
    username: str
    level: int

    total_tests: int
    best_wpm: float

    model_config = ConfigDict(from_attributes=True)

# Глобальный лидерборд (без фильтров difficulty/time_mode)
class GlobalLeaderboardEntry(BaseModel):
    username: str
    level: int
    total_tests: int
    best_wpm: float
    best_accuracy: float

    model_config = ConfigDict(from_attributes=True)

# Ранг пользователя в лидерборде
class UserRank(BaseModel):
    rank: int
    username: str
    best_wpm: float
    total_tests: int
    level: int

    model_config = ConfigDict(from_attributes=True)
