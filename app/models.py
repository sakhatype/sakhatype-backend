from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    username = Column(String, primary_key=True)
    password = Column(String)

class Word(Base):
    __tablename__ = 'words'

    id = Column(Integer, primary_key=True)
    word = Column(String)