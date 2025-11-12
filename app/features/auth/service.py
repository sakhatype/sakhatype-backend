from sqlalchemy.orm import Session
from datetime import datetime

from .models import User
from .schemas import UserCreate
from ...core.security import get_password_hash, verify_password

class AuthService:
    @staticmethod
    def get_user_by_username(db: Session, username: str) -> User | None:
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def create_user(db: Session, user: UserCreate) -> User:
        db_user = User(
            username=user.username,
            password=get_password_hash(user.password),
            created_at=datetime.utcnow()
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    def authenticate_user(db: Session, username: str, password: str) -> User | None:
        user = AuthService.get_user_by_username(db, username)
        if not user or not verify_password(password, user.password):
            return None
        return user
