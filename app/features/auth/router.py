from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .schemas import UserCreate, UserResponse, TokenResponse
from .service import AuthService
from ...shared.dependencies import get_db, get_current_username
from ...core.security import create_access_token

router = APIRouter(prefix='/api/auth', tags=['Authentication'])

@router.post('/register', response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = AuthService.get_user_by_username(db, user.username)
    if db_user:
        raise HTTPException(
            status_code=400,
            detail=f'User with username {user.username} already exists'
        )
    return AuthService.create_user(db, user)

@router.post('/login', response_model=TokenResponse)
def login(user: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    db_user = AuthService.authenticate_user(db, user.username, user.password)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect username or password',
            headers={'WWW-Authenticate': 'Bearer'}
        )
    access_token = create_access_token(user.username)
    return {'access_token': access_token, 'token_type': 'bearer', 'username': user.username}

@router.get('/me', response_model=UserResponse)
def get_current_user_info(username: str = Depends(get_current_username), db: Session = Depends(get_db)):
    user = AuthService.get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    return user
