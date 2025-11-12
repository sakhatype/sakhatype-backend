from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

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
    time_mode = Column(Integer)  # 15, 30, 60 секунд
    test_duration = Column(Integer)  # фактическая длительность
    consistency = Column(Float, default=0.0)  # консистентность печати
    created_at = Column(DateTime, default=datetime.utcnow)