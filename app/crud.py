from sqlalchemy.orm import Session
from sqlalchemy import func, select

from . import models, schemas
from .auth import get_password_hash, verify_password

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

def get_user_by_id(db: Session, id: int):
    stmt = select(models.User).where(models.User.id == id)
    return db.scalar(stmt)

def get_words(db: Session, limit: int = 30):
    stmt = select(models.Word.word).order_by(func.random()).limit(limit)
    return db.scalars(stmt).all()