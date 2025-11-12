from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from datetime import datetime

from ...core.database import Base

class Word(Base):
    __tablename__ = 'words'

    id = Column(Integer, primary_key=True)
    word = Column(String)

class TestResult(Base):
    __tablename__ = 'test_results'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, ForeignKey('users.username'))
    wpm = Column(Float)
    raw_wpm = Column(Float)
    accuracy = Column(Float)
    burst_wpm = Column(Float)
    total_errors = Column(Integer)
    time_mode = Column(Integer)  # 15, 30, 60 seconds
    test_duration = Column(Integer)  # actual duration
    consistency = Column(Float, default=0.0)  # typing consistency
    created_at = Column(DateTime, default=datetime.utcnow)
