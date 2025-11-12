from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .schemas import UserProfile
from .service import UserService
from ...shared.dependencies import get_db

router = APIRouter(prefix='/api/profile', tags=['User Profile'])

@router.get('/{username}', response_model=UserProfile)
def get_user_profile(username: str, db: Session = Depends(get_db)):
    user = UserService.get_user_profile(db, username)
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    return user
