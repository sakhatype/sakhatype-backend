from sqlalchemy.orm import Session

from ..auth.models import User

class UserService:
    @staticmethod
    def get_user_profile(db: Session, username: str) -> User | None:
        return db.query(User).filter(User.username == username).first()
