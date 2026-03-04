from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, union_all, func, text

from . import models, enums, schemas
from .auth import get_password_hash, verify_password

def get_user_by_id(db: Session, id: int):
    stmt = select(models.User).where(models.User.id == id)
    return db.scalar(stmt)

def get_user_by_username(db: Session, username: str):
    stmt = select(models.User).where(models.User.username == username)
    return db.scalar(stmt)

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = get_password_hash(user.password)

    db_user = models.User(
        username=user.username,
        password_hash=hashed_password
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def authenticate_user(db: Session, username: str, password: str):
    user = get_user_by_username(db, username)
    if not user or not verify_password(password, user.password_hash):
        return False
    return user

def create_test_result(db: Session, id: int, result: schemas.TestResultCreate):
    stmt = select(models.User).where(models.User.id == id).options(joinedload(models.User.stats))
    user = db.scalar(stmt)

    if user:
        user.update_stats(db, result)

    db_test_result = models.TestResult(
        user_id=id,
        difficulty=result.difficulty,
        time_mode=result.time_mode,
        test_duration=result.test_duration,
        wpm=result.wpm,
        raw_wpm=result.raw_wpm,
        burst_wpm=result.burst_wpm,
        accuracy=result.accuracy,
        consistency=result.consistency,
        total_errors=result.total_errors
    )

    db.add(db_test_result)
    db.commit()
    db.refresh(db_test_result)
    return db_test_result

def get_user_results(db: Session, id: int, limit: int = 25):
    stmt = (
        select(models.TestResult)
        .where(models.TestResult.user_id == id)
        .order_by(models.TestResult.created_at.desc())
        .limit(limit)
    )
    return db.scalars(stmt).all()

def get_words(db: Session, difficulty: enums.Difficulty, limit: int = 100):
    """
    Получить слова по сложности с рандомным порядком.
    normal: 75% обычных слов + 25% с якутскими буквами
    high: 25% обычных слов + 75% с якутскими буквами
    """
    normal_count = int(limit * 0.75) if difficulty == 'normal' else int(limit * 0.25)
    hard_count = int(limit * 0.25) if difficulty == 'normal' else int(limit * 0.75)

    normal_words = (
        select(models.Word.word)
        .where(models.Word.yakut_letters == 0)
        .order_by(func.random())
        .limit(normal_count)
    )

    hard_words = (
        select(models.Word.word)
        .where(models.Word.yakut_letters > 0)
        .order_by(func.random())
        .limit(hard_count)
    )

    stmt = union_all(normal_words, hard_words)
    return db.scalars(stmt).all()

def get_leaderboard(db: Session, difficulty: enums.Difficulty, time_mode: enums.TimeMode, limit: int = 100):
    stmt = (
        select(models.UserStat)
        .where(models.UserStat.difficulty == difficulty,
               models.UserStat.time_mode == time_mode,
               models.UserStat.total_tests > 0)
        .options(joinedload(models.UserStat.user))
        .order_by(models.UserStat.best_wpm.desc())
        .limit(limit)
    )

    return db.scalars(stmt).all()

def get_global_leaderboard(db: Session, limit: int = 100):
    """Глобальный лидерборд по best_wpm пользователя (без фильтров)."""
    stmt = (
        select(models.User)
        .where(models.User.total_tests > 0)
        .order_by(models.User.best_wpm.desc())
        .limit(limit)
    )
    return db.scalars(stmt).all()

def get_user_rank(db: Session, user_id: int, difficulty: enums.Difficulty, time_mode: enums.TimeMode):
    """Получить ранг пользователя в конкретном лидерборде."""
    # Получаем stat пользователя
    user_stat = db.scalar(
        select(models.UserStat)
        .where(
            models.UserStat.user_id == user_id,
            models.UserStat.difficulty == difficulty,
            models.UserStat.time_mode == time_mode
        )
        .options(joinedload(models.UserStat.user))
    )

    if not user_stat or user_stat.total_tests == 0:
        return None

    # Считаем сколько пользователей имеют лучший WPM
    count_better = db.scalar(
        select(func.count())
        .select_from(models.UserStat)
        .where(
            models.UserStat.difficulty == difficulty,
            models.UserStat.time_mode == time_mode,
            models.UserStat.total_tests > 0,
            models.UserStat.best_wpm > user_stat.best_wpm
        )
    )

    return {
        'rank': (count_better or 0) + 1,
        'username': user_stat.user.username,
        'best_wpm': user_stat.best_wpm,
        'total_tests': user_stat.total_tests,
        'level': user_stat.user.level
    }

def get_user_global_rank(db: Session, user_id: int):
    """Получить глобальный ранг пользователя."""
    user = get_user_by_id(db, user_id)
    if not user or user.total_tests == 0:
        return None

    count_better = db.scalar(
        select(func.count())
        .select_from(models.User)
        .where(
            models.User.total_tests > 0,
            models.User.best_wpm > user.best_wpm
        )
    )

    return {
        'rank': (count_better or 0) + 1,
        'username': user.username,
        'best_wpm': user.best_wpm,
        'total_tests': user.total_tests,
        'level': user.level
    }
