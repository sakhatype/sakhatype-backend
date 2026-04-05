import io

from PIL import Image

from app.core.paths import AVATAR_UPLOAD_DIR

AVATAR_SIZE = 128


def _to_rgb_or_rgba(img: Image.Image) -> Image.Image:
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        return img.convert("RGBA")
    return img.convert("RGB")


def process_avatar_image(content: bytes) -> bytes:
    """
    Decode image, require min 128×128, square-crop, resize to 128×128, encode WebP.
    """
    try:
        img = Image.open(io.BytesIO(content))
        img.load()
    except Exception as exc:
        raise ValueError("Не удалось прочитать изображение") from exc

    if img.width < AVATAR_SIZE or img.height < AVATAR_SIZE:
        raise ValueError("Изображение должно быть не меньше 128×128 пикселей")

    img = _to_rgb_or_rgba(img)
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    img = img.crop((left, top, left + side, top + side))
    try:
        resample = Image.Resampling.LANCZOS
    except AttributeError:
        resample = Image.LANCZOS  # type: ignore[attr-defined]
    img = img.resize((AVATAR_SIZE, AVATAR_SIZE), resample)

    buf = io.BytesIO()
    img.save(buf, "WEBP", quality=85, method=6)
    return buf.getvalue()


def save_avatar_for_user(user_id: str, webp_bytes: bytes) -> str:
    AVATAR_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = AVATAR_UPLOAD_DIR / f"{user_id}.webp"
    path.write_bytes(webp_bytes)
    return f"/api/uploads/avatars/{user_id}.webp"
