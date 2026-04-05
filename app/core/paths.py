import os
from pathlib import Path

# Корень проекта backend/ (в Docker: /app)
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
_default_avatar_dir = BACKEND_ROOT / "uploads" / "avatars"
# Переопределение для Docker/K8s: том на хосте, например /data/avatars
AVATAR_UPLOAD_DIR = Path(os.environ.get("AVATAR_UPLOAD_DIR", str(_default_avatar_dir))).resolve()
