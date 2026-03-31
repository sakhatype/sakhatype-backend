from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ── Auth ──
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=20)
    email: str
    password: str = Field(..., min_length=6)


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
    email: str
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
    username: Optional[str] = None
    email: Optional[str] = None


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
