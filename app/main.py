import re
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
from .crud import authenticate_user, get_user_by_username
from .database import engine, get_db, SessionLocal
from .auth import create_access_token, get_current_username

models.Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        db = SessionLocal()
        db.execute(text('SELECT 1'))
        db.close()
        print('Database is connected.')
    except Exception as error:
        print('Could not connect to database.')
        print(error)
    yield
    print('App is stopped.')

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
    print(f'Critical database error: {exception}')
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

@app.post('/api/auth/register', status_code=status.HTTP_201_CREATED)
def register(user: schemas.User, db: Session = Depends(get_db)):
    user.username = user.username.lower()
    if not re.match(r'^[a-z0-9]+$', user.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Username format is invalid. Only a-z, A-Z and 0-9 allowed.'
        )
    db_user = crud.get_user_by_username(db, user.username)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'User with username {user.username} already exists.'
        )
    crud.create_user(db, user)
    return {'login': user.username, 'message': 'User registered successfully.'}

@app.post('/api/auth/login')
def login(user: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user.username = user.username.lower()
    if not re.match(r'^[a-z0-9]+$', user.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Username format is invalid. Only a-z, A-Z and 0-9 allowed.'
        )
    db_user = authenticate_user(db, user.username, user.password)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect username or password.',
            headers={'WWW-Authenticate': 'Bearer'}
        )
    access_token = create_access_token(user.username)
    return {'access_token': access_token, 'token_type': 'bearer', 'username': user.username}

@app.get('/api/users/me')
def get_current_user_info(username: str = Depends(get_current_username), db: Session = Depends(get_db)):
    user = get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=404, detail='User not found.')
    return user

@app.get('/api/words')
def get_words(limit: int = 200, db: Session = Depends(get_db)):
    return [word[0] for word in crud.get_words(db, limit)]