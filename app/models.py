from datetime import datetime

from sqlalchemy import String, DateTime, func, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))

    total_tests: Mapped[int] = mapped_column(default=0, server_default="0")
    total_time_seconds: Mapped[int] = mapped_column(default=0, server_default="0")
    best_wpm: Mapped[float] = mapped_column(default=0.0, server_default="0.0")
    best_accuracy: Mapped[float] = mapped_column(default=0.0, server_default="0.0")
    total_experience: Mapped[int] = mapped_column(default=0, server_default="0")
    level: Mapped[int] = mapped_column(default=1, server_default="1")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    test_results: Mapped[list["TestResult"]] = relationship(back_populates="user")

class Word(Base):
    __tablename__ = 'words'

    id: Mapped[int] = mapped_column(primary_key=True)
    word: Mapped[str] = mapped_column(String(100), unique=True, index=True)

class TestResult(Base):
    __tablename__ = 'test_results'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    time_mode: Mapped[int]
    test_duration: Mapped[int]
    wpm: Mapped[float]
    accuracy: Mapped[float]
    raw_wpm: Mapped[float]
    burst_wpm: Mapped[float]
    consistency: Mapped[float]
    total_errors: Mapped[int]

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="test_results")

    # бэкенд Айтала возвращает username, поэтому возвращаем username
    @property
    def username(self) -> str:
        return self.user.username if self.user else ""