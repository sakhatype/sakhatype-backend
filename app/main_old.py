from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from typing import List

from . import models, schemas, crud
from .crud import authenticate_user
from .database import engine, get_db
from .auth import create_access_token, get_current_username

models.Base.metadata.create_all(bind=engine)
app = FastAPI(
    title='Sakhatype API',
    version='1.0',
    swagger_ui_parameters={
        "persistAuthorization": True
    }
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def hello():
    return {"message": "Sakhatype API үлэлии турар"}

# Auth endpoints
@app.post('/api/auth/register')
def register(user: schemas.User, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_username(db, user.username)
    if db_user:
        raise HTTPException(
            status_code=400,
            detail=f'User with username {user.username} already exists'
        )
    return crud.create_user(db, user)

@app.post('/api/auth/login')
def login(user: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    db_user = authenticate_user(db, user.username, user.password)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect username or password',
            headers={'WWW-Authenticate': 'Bearer'}
        )
    access_token = create_access_token(user.username)
    return {'access_token': access_token, 'token_type': 'bearer', 'username': user.username}

@app.get('/api/users/me')
def get_current_user_info(username: str = Depends(get_current_username), db: Session = Depends(get_db)):
    user = crud.get_user_profile(db, username)
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    return user

# Words endpoint
@app.get('/api/words')
def get_words(limit: int = 100, db: Session = Depends(get_db)):
    return [word[0] for word in crud.get_words(db, limit)]

# Test results endpoints
@app.post('/api/results', response_model=schemas.TestResultResponse)
def save_test_result(
    result: schemas.TestResultCreate, 
    username: str = Depends(get_current_username),
    db: Session = Depends(get_db)
):
    return crud.create_test_result(db, username, result)

@app.get('/api/results/user/{username}', response_model=List[schemas.TestResultResponse])
def get_user_results(username: str, limit: int = 50, db: Session = Depends(get_db)):
    return crud.get_user_results(db, username, limit)

@app.get('/api/profile/{username}', response_model=schemas.UserProfile)
def get_user_profile(username: str, db: Session = Depends(get_db)):
    user = crud.get_user_profile(db, username)
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    return user

# Leaderboard endpoints
@app.get('/api/leaderboard/wpm', response_model=List[schemas.LeaderboardEntry])
def get_leaderboard_wpm(limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_leaderboard_wpm(db, limit)

@app.get('/api/leaderboard/accuracy', response_model=List[schemas.LeaderboardEntry])
def get_leaderboard_accuracy(limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_leaderboard_accuracy(db, limit)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8001)