import http
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, IntegrityError
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from . import schemas, crud, enums
from .auth import create_access_token, get_current_id
from .config import settings
from .database import get_db, SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CustomLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith("/api/"):
            return await call_next(request)

        start_time = time.time()
        username = "Guest"
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1] if len(auth_header.split(" ")) == 2 else ""
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                username = payload.get("username", "Unknown")
            except Exception:
                username = "Invalid-Token"

        response = await call_next(request)
        try:
            phrase = http.HTTPStatus(response.status_code).phrase
        except ValueError:
            phrase = ""
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time))
        logger.info(f"| {ts} | {username} | {request.method} {path} | {response.status_code} {phrase}")
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.getLogger('uvicorn.access').disabled = True
    try:
        db = SessionLocal()
        db.execute(text('SELECT 1'))
        db.close()
        logger.info('БД подключена.')
    except Exception as e:
        logger.error(f'БД недоступна: {e}')
    yield
    logger.info('Остановлено.')


app = FastAPI(title='Sakhatype', version='1.1', lifespan=lifespan)
app.add_middleware(CustomLogMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(','),
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)


@app.exception_handler(OperationalError)
async def db_error(request: Request, exc: OperationalError):
    logger.critical(f'DB error: {exc}')
    return JSONResponse(status_code=503, content={'message': 'БД временно недоступна.'})


@app.exception_handler(IntegrityError)
async def integrity_error(request: Request, exc: IntegrityError):
    return JSONResponse(status_code=409, content={'message': 'Этот пользователь уже существует.'})


# ==================== AUTH ====================

@app.post('/api/auth/register', status_code=201, response_model=schemas.UserRegisterResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if crud.get_user_by_username(db, user.username):
        raise HTTPException(409, f'Пользователь {user.username} уже существует.')
    return crud.create_user(db, user)


@app.post('/api/auth/login', response_model=schemas.Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = crud.authenticate_user(db, form.username.lower(), form.password)
    if not user:
        raise HTTPException(401, 'Неправильное имя или пароль.', headers={'WWW-Authenticate': 'Bearer'})
    token = create_access_token(user.id, user.username)
    return {'access_token': token, 'token_type': 'bearer', 'username': user.username}


# ==================== USERS ====================

@app.get('/api/users/me', response_model=schemas.UserResponse)
def me(user_id: int = Depends(get_current_id), db: Session = Depends(get_db)):
    user = crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(404, 'Не найден.')
    return user


@app.get('/api/profile/{username}', response_model=schemas.UserResponse)
def profile(username: str, db: Session = Depends(get_db)):
    user = crud.get_user_by_username(db, username)
    if not user:
        raise HTTPException(404, 'Не найден.')
    return user


# ==================== RESULTS ====================

@app.post('/api/results', response_model=schemas.TestResultResponse)
def save_result(result: schemas.TestResultCreate, user_id: int = Depends(get_current_id), db: Session = Depends(get_db)):
    return crud.create_test_result(db, user_id, result)


@app.get('/api/results/user/{username}', response_model=list[schemas.TestResultResponse])
def user_results(username: str, limit: int = 25, db: Session = Depends(get_db)):
    user = crud.get_user_by_username(db, username)
    if not user:
        raise HTTPException(404, 'Не найден.')
    return crud.get_user_results(db, user.id, limit)


# ==================== WORDS ====================

@app.get('/api/words/{difficulty}', response_model=list[str])
def words(difficulty: enums.Difficulty, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_words(db, difficulty, limit)


# ==================== LEADERBOARD ====================

@app.get('/api/leaderboard/{difficulty}/{time_mode}', response_model=list[schemas.UserStatResponse])
def leaderboard(difficulty: enums.Difficulty, time_mode: enums.TimeMode, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_leaderboard(db, difficulty, time_mode, limit)
