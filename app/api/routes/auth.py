from fastapi import APIRouter, HTTPException, status
from app.schemas.schemas import UserRegister, UserLogin, Token, UserPublic
from app.services.user_service import create_user, authenticate_user, get_user_by_id, get_user_by_username, get_user_by_email, xp_for_next_level
from app.core.security import create_access_token, get_current_user
from fastapi import Depends
from pymongo.errors import DuplicateKeyError

router = APIRouter(prefix="/api/auth", tags=["auth"])


def user_to_public(user: dict) -> UserPublic:
    return UserPublic(
        id=str(user["_id"]),
        username=user["username"],
        email=user["email"],
        level=user.get("level", 1),
        xp=user.get("xp", 0),
        xp_to_next=xp_for_next_level(user.get("level", 1)),
        total_tests=user.get("total_tests", 0),
        best_wpm=user.get("best_wpm", 0),
        avg_wpm=user.get("avg_wpm", 0),
        avg_accuracy=user.get("avg_accuracy", 0),
        achievements=user.get("achievements", []),
        created_at=user.get("created_at"),
    )


@router.post("/register", response_model=Token)
async def register(data: UserRegister):
    existing = await get_user_by_username(data.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    existing_email = await get_user_by_email(data.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    try:
        user = await create_user(data.username, data.email, data.password)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already exists",
        )
    token = create_access_token(data={"sub": str(user["_id"])})
    return Token(access_token=token, user=user_to_public(user))


@router.post("/login", response_model=Token)
async def login(data: UserLogin):
    user = await authenticate_user(data.username, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    token = create_access_token(data={"sub": str(user["_id"])})
    return Token(access_token=token, user=user_to_public(user))


@router.get("/me", response_model=UserPublic)
async def get_me(user_id: str = Depends(get_current_user)):
    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user_to_public(user)
