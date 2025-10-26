from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

import models, schemas, crud
from crud import authenticate_user
from database import engine, get_db
from auth import create_access_token, get_current_username

models.Base.metadata.create_all(bind=engine)
app = FastAPI(
    title='Sakhatype',
    version='1.0',
    swagger_ui_parameters={
        "persistAuthorization": True
    }
)


@app.get("/")
async def hello():
    return {"message": "Sakhatype API үлэлии турар"}

@app.post('/auth/register')
def register(user: schemas.User, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_username(db, user.username)
    if db_user:
        raise HTTPException(
            status_code=400,
            detail=f'User with username {user.username} already exists'
        )
    return crud.create_user(db, user)

@app.post('/auth/login')
def login(user: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    db_user = authenticate_user(db, user.username, user.password)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect username or password',
            headers={'WWW-Authenticate': 'Bearer'}
        )
    access_token = create_access_token(user.username)
    return {'access_token': access_token, 'token_type': 'bearer'}

@app.get('/users/me')
def get_current_user_info(username: str = Depends(get_current_username)):
    return {'username': username}

@app.get('/words')
def get_words(limit: int = 30, db: Session = Depends(get_db)):
    return [word[0] for word in crud.get_words(db, 30)]

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8080)