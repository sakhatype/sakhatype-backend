from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime

from . import models, schemas
from .auth import get_password_hash, verify_password

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def create_user(db: Session, user: schemas.User):
    db_user = models.User(
        username=user.username, 
        password=get_password_hash(user.password),
        created_at=datetime.utcnow()
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def authenticate_user(db: Session, username: str, password: str):
    user = get_user_by_username(db, username)
    if not user or not verify_password(password, user.password):
        return False
    return user

def get_words(db: Session, limit: int = 30):
    return db.query(models.Word.word).order_by(func.random()).limit(limit).all()

# Новые CRUD функции для результатов и статистики

def create_test_result(db: Session, username: str, result: schemas.TestResultCreate):
    # Создаем запись о результате теста
    db_result = models.TestResult(
        username=username,
        wpm=result.wpm,
        raw_wpm=result.raw_wpm,
        accuracy=result.accuracy,
        burst_wpm=result.burst_wpm,
        total_errors=result.total_errors,
        time_mode=result.time_mode,
        test_duration=result.test_duration,
        consistency=result.consistency,
        created_at=datetime.utcnow()
    )
    db.add(db_result)
    
    # Обновляем статистику пользователя
    user = get_user_by_username(db, username)
    if user:
        user.total_tests += 1
        user.total_time_seconds += result.test_duration
        
        # Обновляем лучшие результаты
        if result.wpm > user.best_wpm:
            user.best_wpm = result.wpm
        if result.accuracy > user.best_accuracy:
            user.best_accuracy = result.accuracy
            
        # Добавляем опыт (WPM + точность)
        experience_gained = int(result.wpm + result.accuracy)
        user.total_experience += experience_gained
        
        # Расчет уровня (каждые 1000 опыта = 1 уровень)
        user.level = 1 + (user.total_experience // 1000)
    
    db.commit()
    db.refresh(db_result)
    return db_result

def get_user_results(db: Session, username: str, limit: int = 50):
    return db.query(models.TestResult)\
        .filter(models.TestResult.username == username)\
        .order_by(desc(models.TestResult.created_at))\
        .limit(limit)\
        .all()

def get_user_profile(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def get_leaderboard_wpm(db: Session, limit: int = 100):
    return db.query(models.User)\
        .filter(models.User.total_tests > 0)\
        .order_by(desc(models.User.best_wpm))\
        .limit(limit)\
        .all()

def get_leaderboard_accuracy(db: Session, limit: int = 100):
    return db.query(models.User)\
        .filter(models.User.total_tests > 0)\
        .order_by(desc(models.User.best_accuracy))\
        .limit(limit)\
        .all()