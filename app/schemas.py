import re
from datetime import datetime

from pydantic import BaseModel, field_validator

class UserCreate(BaseModel):
    username: str
    password: str

    @field_validator('username')
    def validate_username(cls, value):
        value = value.lower()
        if not re.match(r'^[a-z0-9]+$', value):
            raise ValueError('Username format is invalid. Only a-z and 0-9 allowed.')
        return value

class UserRegisterResponse(BaseModel):
    username: str
    message: str

class Token(BaseModel):
    access_token: str
    token_type: str
    username: str

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