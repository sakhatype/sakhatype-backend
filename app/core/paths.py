from pathlib import Path

# backend/
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
AVATAR_UPLOAD_DIR = BACKEND_ROOT / "uploads" / "avatars"
