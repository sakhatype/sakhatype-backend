from datetime import datetime

from sqlalchemy import String, DateTime, func, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session

from . import schemas

class Base(DeclarativeBase):
    pass

class Word(Base):
    __tablename__ = 'words'

    id: Mapped[int] = mapped_column(primary_key=True)
    word: Mapped[str] = mapped_column(String(100), unique=True, index=True)

class TestResult(Base):
    __tablename__ = 'test_results'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))

    difficulty: Mapped[str]
    time_mode: Mapped[int]
    test_duration: Mapped[int]

    wpm: Mapped[float]
    raw_wpm: Mapped[float]
    burst_wpm: Mapped[float]

    accuracy: Mapped[float]
    consistency: Mapped[float]
    total_errors: Mapped[int]

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped['User'] = relationship(back_populates='test_results')

    # бэкенд Айтала возвращает username, поэтому возвращаем username
    @property
    def username(self) -> str:
        return self.user.username if self.user else ''

class UserStat(Base):
    __tablename__ = 'user_stats'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)

    difficulty: Mapped[str]
    time_mode: Mapped[int]

    total_tests: Mapped[int] = mapped_column(default=0, server_default='0')
    best_wpm: Mapped[float] = mapped_column(default=0.0, server_default='0.0')

    user: Mapped['User'] = relationship(back_populates='stats')

    @property
    def username(self) -> str:
        return self.user.username if self.user else ''

class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))

    total_tests: Mapped[int] = mapped_column(default=0, server_default='0')
    total_time_seconds: Mapped[int] = mapped_column(default=0, server_default='0')
    total_experience: Mapped[int] = mapped_column(default=0, server_default='0')
    level: Mapped[int] = mapped_column(default=1, server_default='1')

    best_wpm: Mapped[float] = mapped_column(default=0.0, server_default='0.0')
    best_accuracy: Mapped[float] = mapped_column(default=0.0, server_default='0.0')

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    test_results: Mapped[list['TestResult']] = relationship(back_populates='user')
    stats: Mapped[list['UserStat']] = relationship(back_populates='user')

    def update_stats(self, db: Session, result: schemas.TestResultCreate):
        self.total_tests += 1
        self.total_time_seconds += result.test_duration
        self.total_experience += int(result.wpm + result.accuracy)
        self.level = 1 + (self.total_experience // 1000)

        self.best_wpm = max(self.best_wpm, result.wpm)
        self.best_accuracy = max(self.best_accuracy, result.accuracy)

        stat = next((s for s in self.stats if s.time_mode == result.time_mode and s.difficulty == result.difficulty), None)

        if not stat:
            stat = UserStat(
                user_id=self.id,
                difficulty="normal",
                # difficulty=result.difficulty,
                time_mode=result.time_mode
            )
            db.add(stat)
            self.stats.append(stat)

        stat.total_tests += 1
        stat.best_wpm = max(stat.best_wpm, result.wpm)