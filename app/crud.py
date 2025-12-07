from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, select

from . import models, schemas
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
    stmt = select(models.User).where(models.User.id == id)
    user = db.scalar(stmt)
    if user:
        user.update_stats(result)

    db_test_result = models.TestResult(
        user_id=id,
        time_mode=result.time_mode,
        test_duration=result.test_duration,
        wpm=result.wpm,
        accuracy=result.accuracy,
        raw_wpm=result.raw_wpm,
        burst_wpm=result.burst_wpm,
        consistency=result.consistency,
        total_errors=result.total_errors
    )

    db.add(db_test_result)
    db.commit()
    db.refresh(db_test_result)
    return db_test_result

def get_user_results(db: Session, id: int, limit: int = 50):
    stmt = (
        select(models.TestResult)
        .options(joinedload(models.TestResult.user))
        .where(models.TestResult.user_id == id)
        .order_by(models.TestResult.created_at.desc())
        .limit(limit)
    )
    return db.scalars(stmt).all()

def get_words(db: Session, limit: int = 30):
    stmt = select(models.Word.word).order_by(func.random()).limit(limit)
    return db.scalars(stmt).all()

def get_leaderboard_wpm(db: Session, limit: int = 100):
    stmt = (
        select(models.User)
        .where(models.User.total_tests > 0)
        .order_by(models.User.best_wpm.desc())
        .limit(limit)
    )
    return db.scalars(stmt).all()

def get_leaderboard_accuracy(db: Session, limit: int = 100):
    stmt = (
        select(models.User)
        .where(models.User.total_tests > 0)
        .order_by(models.User.best_accuracy.desc())
        .limit(limit)
    )
    return db.scalars(stmt).all()