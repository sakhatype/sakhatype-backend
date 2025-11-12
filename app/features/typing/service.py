from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime

from .models import Word, TestResult
from .schemas import TestResultCreate
from ..auth.models import User

class TypingService:
    @staticmethod
    def get_words(db: Session, limit: int = 100) -> list[str]:
        words = db.query(Word.word).order_by(func.random()).limit(limit).all()
        return [word[0] for word in words]

    @staticmethod
    def create_test_result(db: Session, username: str, result: TestResultCreate) -> TestResult:
        # Create test result record
        db_result = TestResult(
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
        
        # Update user statistics
        user = db.query(User).filter(User.username == username).first()
        if user:
            user.total_tests += 1
            user.total_time_seconds += result.test_duration
            
            # Update best results
            if result.wpm > user.best_wpm:
                user.best_wpm = result.wpm
            if result.accuracy > user.best_accuracy:
                user.best_accuracy = result.accuracy
                
            # Add experience (WPM + accuracy)
            experience_gained = int(result.wpm + result.accuracy)
            user.total_experience += experience_gained
            
            # Calculate level (every 1000 experience = 1 level)
            user.level = 1 + (user.total_experience // 1000)
        
        db.commit()
        db.refresh(db_result)
        return db_result

    @staticmethod
    def get_user_results(db: Session, username: str, limit: int = 50) -> list[TestResult]:
        return db.query(TestResult)\
            .filter(TestResult.username == username)\
            .order_by(desc(TestResult.created_at))\
            .limit(limit)\
            .all()
