import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, IntegrityError
from sqlalchemy.orm import Session
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from . import models, schemas, crud
from .auth import create_access_token, get_current_id
from .database import engine, get_db, SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

models.Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        db = SessionLocal()
        db.execute(text('SELECT 1'))
        db.close()
        logger.info('Database is connected.')
    except Exception as error:
        logger.error(f'Could not connect to database: {error}')
    yield
    logger.info('App is stopped.')

app = FastAPI(
    title='Sakhatype',
    version='1.0',
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['https://sakhatype-sakhatype-frontend-0564.twc1.net'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

@app.exception_handler(OperationalError)
async def db_connection_error_handler(request: Request, exception: OperationalError):
    logger.critical(f'Critical database error: {exception}')
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={'message': 'Service is temporarily unavailable.'}
    )

@app.exception_handler(IntegrityError)
async def db_integrity_error_handler(request: Request, exception: IntegrityError):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={'message': 'Data error. Maybe this user already exists.'}
    )

@app.post('/api/auth/register', status_code=status.HTTP_201_CREATED, response_model=schemas.UserRegisterResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_username(db, user.username)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'User with username {user.username} already exists.'
        )
    crud.create_user(db, user)
    return {'username': user.username}

@app.post('/api/auth/login', response_model=schemas.Token)
def login(user: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user.username = user.username.lower()
    db_user = crud.authenticate_user(db, user.username, user.password)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect username or password.',
            headers={'WWW-Authenticate': 'Bearer'}
        )
    access_token = create_access_token(db_user.id)
    return {'access_token': access_token, 'token_type': 'bearer', 'username': user.username}

@app.get('/api/users/me', response_model=schemas.UserResponse)
def get_current_user_info(id: int = Depends(get_current_id), db: Session = Depends(get_db)):
    user = crud.get_user_by_id(db, id)
    if not user:
        raise HTTPException(status_code=404, detail='User not found.')
    return user

@app.get('/api/profile/{username}', response_model=schemas.UserResponse)
def get_user_info(username: str, db: Session = Depends(get_db)):
    user = crud.get_user_by_id(db, id)
    if not user:
        raise HTTPException(status_code=404, detail='User not found.')
    return user

@app.get('/api/words', response_model=list[str])
def get_words(limit: int = 200, db: Session = Depends(get_db)):
    return crud.get_words(db, limit)