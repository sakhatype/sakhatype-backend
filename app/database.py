import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from fastapi import HTTPException

from config import settings

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

engine = create_engine(settings.DATABASE_URL, connect_args={'check_same_thread': False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        try:
            db.execute(text("SELECT 1"))
        except OperationalError:
            logger.error('Database session is invalid')
            db.rollback()
            db.close()
            raise HTTPException(
                status_code=503,
                detail='Database unavailable'
            )
        yield db
    except SQLAlchemyError as error:
        logger.error(f'Database error: {error}')
        db.rollback()
        raise
    finally:
        db.close()
