import re

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from starlette.middleware.cors import CORSMiddleware

from . import models, schemas, crud
from .crud import authenticate_user
from .database import engine, get_db
from .auth import create_access_token, get_current_login

models.Base.metadata.create_all(bind=engine)
app = FastAPI(
    title='Sakhatype',
    version='1.0'
)
origins = [
    # пока что хз
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.post('/auth/register')
def register(user: schemas.User, db: Session = Depends(get_db)):
    user.login = user.login.lower()
    if not re.match(r'^[a-z0-9]+$', user.login) or not re.match(r'^[a-zA-Z0-9]+$', user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Username format is invalid. Only a-z, A-Z and 0-9 allowed.'
        )
    db_user = crud.get_user_by_login(db, user.login)
    if db_user:
        raise HTTPException(
            status_code=400,
            detail=f'User with login {user.login} already exists.'
        )
    crud.create_user(db, user)
    return user.login

@app.post('/auth/login')
def login(user: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user.username = user.username.lower()
    if not re.match(r'^[a-z0-9]+$', user.username) or not re.match(r'^[a-zA-Z0-9]+$', user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Username or password format is invalid. Only a-z, A-Z and 0-9 allowed.'
        )
    db_user = authenticate_user(db, user.username, user.password)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect login or password.',
            headers={'WWW-Authenticate': 'Bearer'}
        )
    access_token = create_access_token(user.username)
    return {'access_token': access_token, 'token_type': 'bearer'}

@app.get('/users/me')
def get_current_user_info(login: str = Depends(get_current_login)):
    return {'login': login}

@app.get('/words')
def get_words(limit: int = 30, db: Session = Depends(get_db)):
    return [word[0] for word in crud.get_words(db, 30)]