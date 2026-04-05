from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.schemas.schemas import UserRegister, UserLogin, Token, UserPublic
from app.services.user_service import (
    apply_avatar_upload,
    authenticate_user,
    create_user,
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
    xp_for_next_level,
)
from app.core.security import create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


def user_to_public(user: dict) -> UserPublic:
    return UserPublic(
        id=str(user["id"]),
        username=user["username"],
        email=user.get("email"),
        avatar_url=user.get("avatar_url"),
        level=user.get("level", 1),
        xp=user.get("xp", 0),
        xp_to_next=xp_for_next_level(user.get("level", 1)),
        total_tests=user.get("total_tests", 0),
        best_wpm=user.get("best_wpm", 0),
        avg_wpm=user.get("avg_wpm", 0),
        avg_accuracy=user.get("avg_accuracy", 0),
        achievements=user.get("achievements") or [],
        created_at=user.get("created_at"),
    )


@router.post("/register", response_model=Token)
async def register(data: UserRegister):
    try:
        existing = await get_user_by_username(data.username)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Это имя пользователя уже занято",
            )

        if data.email:
            existing_email = await get_user_by_email(data.email)
            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Этот email уже зарегистрирован",
                )

        user = await create_user(data.username, data.email, data.password)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="База данных временно недоступна",
        )
    token = create_access_token(data={"sub": str(user["id"])})
    return Token(access_token=token, user=user_to_public(user))


@router.post("/login", response_model=Token)
async def login(data: UserLogin):
    try:
        user = await authenticate_user(data.username, data.password)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="База данных временно недоступна",
        )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )
    token = create_access_token(data={"sub": str(user["id"])})
    return Token(access_token=token, user=user_to_public(user))


@router.get("/me", response_model=UserPublic)
async def get_me(user_id: str = Depends(get_current_user)):
    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user_to_public(user)


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
):
    """
    Аватар (дубликат логики с POST /api/profile/me/avatar).
    Удобно для клиентов; если прокси режет /api/auth/*, используйте /api/profile/me/avatar.
    """
    content = await file.read()
    try:
        data = await apply_avatar_upload(user_id, content)
    except ValueError as e:
        msg = str(e)
        if msg == "Пользователь не найден":
            raise HTTPException(status_code=404, detail=msg) from e
        raise HTTPException(status_code=400, detail=msg) from e
    return {"avatar_url": data["avatar_url"], "user": user_to_public(data["user"])}
