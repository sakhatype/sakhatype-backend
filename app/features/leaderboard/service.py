from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..auth.models import User

class LeaderboardService:
    @staticmethod
    def get_leaderboard_wpm(db: Session, limit: int = 100) -> list[User]:
        return db.query(User)\
            .filter(User.total_tests > 0)\
            .order_by(desc(User.best_wpm))\
            .limit(limit)\
            .all()

    @staticmethod
    def get_leaderboard_accuracy(db: Session, limit: int = 100) -> list[User]:
        return db.query(User)\
            .filter(User.total_tests > 0)\
            .order_by(desc(User.best_accuracy))\
            .limit(limit)\
            .all()
