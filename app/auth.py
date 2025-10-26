from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from fastapi import HTTPException, status, Depends
from jose import jwt, JWTError
from datetime import datetime, timedelta

from config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(username: str):
    return jwt.encode(
        {'sub': username, 'exp': datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

def get_current_username(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Could not validate credentials',
        headers={'WWW-Authenticate': 'Bearer'}
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get('sub')
        if username is None:
            raise credentials_exception
        return username
    except JWTError:
        raise credentials_exception
