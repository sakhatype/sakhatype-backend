from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, union_all, func

from . import models, enums, schemas
from .auth import get_password_hash, verify_password


# ============ Users ============

def get_user_by_id(db: Session, id: int):
    return db.scalar(select(models.User).where(models.User.id == id))


def get_user_by_username(db: Session, username: str):
    return db.scalar(select(models.User).where(models.User.username == username))


def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(
        username=user.username,
        password_hash=get_password_hash(user.password)
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


# ============ Test Results ============

def create_test_result(db: Session, user_id: int, result: schemas.TestResultCreate):
    # Загружаем юзера со stats для update_stats
    user = db.scalar(
        select(models.User)
        .where(models.User.id == user_id)
        .options(joinedload(models.User.stats))
    )

    if user:
        user.update_stats(db, result)

    db_result = models.TestResult(
        user_id=user_id,
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
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    return db_result


def get_user_results(db: Session, user_id: int, limit: int = 25):
    stmt = (
        select(models.TestResult)
        .where(models.TestResult.user_id == user_id)
        .order_by(models.TestResult.created_at.desc())
        .limit(limit)
    )
    return db.scalars(stmt).all()


# ============ Words ============

def get_words(db: Session, difficulty: enums.Difficulty, limit: int = 100):
    """
    normal: 75% обычных + 25% с якутскими буквами
    high:   25% обычных + 75% с якутскими буквами
    Рандомный порядок.
    """
    if difficulty == enums.Difficulty.normal:
        normal_count = int(limit * 0.75)
        hard_count = limit - normal_count
    else:
        hard_count = int(limit * 0.75)
        normal_count = limit - hard_count

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


# ============ Leaderboard ============

def get_leaderboard(
    db: Session,
    difficulty: enums.Difficulty,
    time_mode: enums.TimeMode,
    limit: int = 100
):
    stmt = (
        select(models.UserStat)
        .where(
            models.UserStat.difficulty == difficulty,
            models.UserStat.time_mode == time_mode,
            models.UserStat.total_tests > 0
        )
        .options(joinedload(models.UserStat.user))
        .order_by(models.UserStat.best_wpm.desc())
        .limit(limit)
    )
    return db.scalars(stmt).all()
