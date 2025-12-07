import re
from datetime import datetime

from pydantic import BaseModel, field_validator, ConfigDict

class Token(BaseModel):
    access_token: str
    token_type: str
    username: str

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

    @field_validator('username')
    def validate_username(cls, value):
        value = value.lower()
        if not re.match(r'^[a-z0-9]+$', value):
            raise ValueError('Username format is invalid. Only a-z and 0-9 allowed.')
        return value

class UserRegisterResponse(UserBase):
    pass

class UserResponse(UserBase):
    total_tests: int
    total_time_seconds: int
    best_wpm: float
    best_accuracy: float
    total_experience: int
    level: int

    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TestResultCreate(BaseModel):
    time_mode: int
    test_duration: int
    wpm: float
    accuracy: float
    raw_wpm: float
    burst_wpm: float
    consistency: float
    total_errors: int

class TestResultResponse(BaseModel):
    id: int
    user_id: int
    username: str

    time_mode: int
    test_duration: int
    wpm: float
    accuracy: float
    raw_wpm: float
    burst_wpm: float
    consistency: float
    total_errors: int

    created_at: datetime

    model_config = ConfigDict(from_attributes=True)