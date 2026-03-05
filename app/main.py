import http
import logging
import time
from contextlib import asynccontextmanager
from typing import Optional

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
            parts = auth_header.split(" ")

            if len(parts) == 2:
                token = parts[1]

                try:
                    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                    username = payload.get("username", "Unknown")
                except Exception:
                    username = "Invalid-Token"

        response = await call_next(request)

        try:
            status_phrase = http.HTTPStatus(response.status_code).phrase
        except ValueError:
            status_phrase = ""

        log_timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time))

        logger.info(
            f"| {log_timestamp} | User: {username} | {request.method} {path} | "
            f"{response.status_code} {status_phrase}"
        )

        return response

@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.getLogger('uvicorn.access').disabled = True

    try:
        db = SessionLocal()
        db.execute(text('SELECT 1'))
        db.close()
        logger.info('База данных подключена.')
    except Exception as error:
        logger.error(f'Не получилось подключиться к базе данных: {error}')

    yield
    logger.info('Приложение остановлено.')

app = FastAPI(
    title='Sakhatype',
    version='1.1',
    lifespan=lifespan
)

app.add_middleware(CustomLogMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(','),
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

@app.exception_handler(OperationalError)
async def db_connection_error_handler(request: Request, exception: OperationalError):
    logger.critical(f'Critical database error: {exception}')

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={'message': 'База данных временно недоступна.'}
    )

@app.exception_handler(IntegrityError)
async def db_integrity_error_handler(request: Request, exception: IntegrityError):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={'message': 'Возможно этот пользователь уже существует.'}
    )

# ===================== AUTH =====================

@app.post('/api/auth/register', status_code=status.HTTP_201_CREATED, response_model=schemas.UserRegisterResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_username(db, user.username)

    if db_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'Пользователь с именем {user.username} уже существует.'
        )

    return crud.create_user(db, user)

@app.post('/api/auth/login', response_model=schemas.Token)
def login(user: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user.username = user.username.lower()
    db_user = crud.authenticate_user(db, user.username, user.password)

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Неправильное имя или пароль.',
            headers={'WWW-Authenticate': 'Bearer'}
        )

    access_token = create_access_token(db_user.id, db_user.username)
    return {'access_token': access_token, 'token_type': 'bearer', 'username': user.username}

# ===================== USERS =====================

@app.get('/api/users/me', response_model=schemas.UserResponse)
def get_current_user(id: int = Depends(get_current_id), db: Session = Depends(get_db)):
    user = crud.get_user_by_id(db, id)

    if not user:
        raise HTTPException(status_code=404, detail='Пользователь не найден.')

    return user

@app.get('/api/profile/{username}', response_model=schemas.UserResponse)
def get_user_by_username(username: str, db: Session = Depends(get_db)):
    user = crud.get_user_by_username(db, username)

    if not user:
        raise HTTPException(status_code=404, detail='Пользователь не найден.')

    return user

# ===================== RESULTS =====================

@app.post('/api/results', response_model=schemas.TestResultResponse)
def save_test_result(result: schemas.TestResultCreate, id: int = Depends(get_current_id), db: Session = Depends(get_db)):
    return crud.create_test_result(db, id, result)

@app.get('/api/results/user/{username}', response_model=list[schemas.TestResultResponse])
def get_user_results(username: str, limit: int = 25, db: Session = Depends(get_db)):
    user = crud.get_user_by_username(db, username)

    if not user:
        raise HTTPException(status_code=404, detail='Пользователь не найден.')

    return crud.get_user_results(db, user.id, limit)

# ===================== WORDS =====================

@app.get('/api/words/{difficulty}', response_model=list[str])
def get_words(difficulty: enums.Difficulty, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_words(db, difficulty, limit)

# ===================== LEADERBOARD =====================
# ВАЖНО: статические маршруты ПЕРЕД параметризованными!
# Иначе FastAPI пытается разобрать "global" как значение {difficulty}

# 1. Глобальный лидерборд (без фильтров)
@app.get('/api/leaderboard/global', response_model=list[schemas.GlobalLeaderboardEntry])
def get_global_leaderboard(limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_global_leaderboard(db, limit)

# 2. Глобальный ранг текущего пользователя
@app.get('/api/leaderboard/rank/global', response_model=Optional[schemas.UserRank])
def get_my_global_rank(id: int = Depends(get_current_id), db: Session = Depends(get_db)):
    result = crud.get_user_global_rank(db, id)
    if not result:
        raise HTTPException(status_code=404, detail='Нет данных.')
    return result

# 3. Ранг текущего пользователя в конкретном режиме
@app.get('/api/leaderboard/rank/{difficulty}/{time_mode}', response_model=Optional[schemas.UserRank])
def get_my_rank(difficulty: enums.Difficulty, time_mode: enums.TimeMode, id: int = Depends(get_current_id), db: Session = Depends(get_db)):
    result = crud.get_user_rank(db, id, difficulty, time_mode)
    if not result:
        raise HTTPException(status_code=404, detail='Нет данных для этого режима.')
    return result

# 4. Лидерборд по режиму (параметризованный — ПОСЛЕДНИЙ!)
@app.get('/api/leaderboard/{difficulty}/{time_mode}', response_model=list[schemas.UserStat])
def get_leaderboard(difficulty: enums.Difficulty, time_mode: enums.TimeMode, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_leaderboard(db, difficulty, time_mode, limit)
