from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List
from datetime import datetime


def _normalize_optional_email(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip().lower()
    return s if s else None


def _validate_email_if_set(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    if "@" not in v or "." not in v.split("@", 1)[-1]:
        raise ValueError("Invalid email format")
    return v


# ── Auth ──
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=20)
    email: Optional[str] = None
    password: str = Field(..., min_length=6)

    @field_validator("email", mode="before")
    @classmethod
    def register_email_blank(cls, v):
        return _normalize_optional_email(v if isinstance(v, str) or v is None else str(v))

    @field_validator("email")
    @classmethod
    def register_email_format(cls, v: Optional[str]) -> Optional[str]:
        return _validate_email_if_set(v)


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserPublic"


# ── User ──
class UserPublic(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    level: int = 1
    xp: int = 0
    xp_to_next: int = 500
    total_tests: int = 0
    best_wpm: float = 0
    avg_wpm: float = 0
    avg_accuracy: float = 0
    achievements: List[str] = []
    created_at: Optional[datetime] = None


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=30)
    email: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = Field(None, min_length=6)

    @field_validator("email", mode="before")
    @classmethod
    def update_email_blank(cls, v):
        if v is None:
            return None
        return _normalize_optional_email(v if isinstance(v, str) else str(v))

    @field_validator("email")
    @classmethod
    def update_email_format(cls, v: Optional[str]) -> Optional[str]:
        return _validate_email_if_set(v)

    @model_validator(mode="after")
    def new_password_needs_current(self):
        if self.new_password and not (self.current_password or "").strip():
            raise ValueError("Current password is required to set a new password")
        return self


# ── Test Result ──
class TestResultCreate(BaseModel):
    wpm: float
    raw_wpm: float
    accuracy: float
    mode: str  # "time" or "words"
    mode_value: int  # 15,30,60 or 10,25,50
    language: str = "sakha"  # Саха тыла гына
    difficulty: str = "normal"  # "normal" or "expert"
    chars_correct: int = 0
    chars_incorrect: int = 0
    chars_extra: int = 0
    chars_missed: int = 0


class TestResultResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    wpm: float
    raw_wpm: float
    accuracy: float
    mode: str
    mode_value: int
    language: str
    difficulty: str
    chars_correct: int = 0
    chars_incorrect: int = 0
    chars_extra: int = 0
    chars_missed: int = 0
    xp_earned: int = 0
    created_at: datetime


class TestResultWithXP(BaseModel):
    result: TestResultResponse
    xp_earned: int
    level_up: bool = False
    new_level: int = 1
    new_xp: int = 0
    xp_to_next: int = 500
    new_achievements: List[str] = []


# ── Leaderboard ──
class LeaderboardEntry(BaseModel):
    rank: int
    user_id: str
    username: str
    wpm: float
    accuracy: float
    language: str
    level: int = 1
    difficulty: str = "normal"  # "normal" | "expert" — на какой сложности записан результат


# ── Arena ──
class ArenaRoom(BaseModel):
    room_id: str
    host: str
    players: List[str]
    status: str  # "waiting", "in_progress", "finished"
    mode: str = "time"
    mode_value: int = 30
    language: str = "sakha"


# ── Words ──
class WordsRequest(BaseModel):
    language: str = "sakha"
    count: int = 50
    difficulty: str = "normal"  # "normal" or "expert"


class WordsResponse(BaseModel):
    words: List[str]
    language: str


# Forward ref update
Token.model_rebuild()
