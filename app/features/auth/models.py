from sqlalchemy import Column, String, Integer, Float, DateTime
from datetime import datetime

from ...core.database import Base

class User(Base):
    __tablename__ = 'users'

    username = Column(String, primary_key=True)
    password = Column(String)
    total_tests = Column(Integer, default=0)
    total_time_seconds = Column(Integer, default=0)
    best_wpm = Column(Float, default=0.0)
    best_accuracy = Column(Float, default=0.0)
    total_experience = Column(Integer, default=0)
    level = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
