import os
from pathlib import Path

# Корень проекта backend/ (в Docker: обычно /app)
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
_default_avatar_dir = (BACKEND_ROOT / "uploads" / "avatars").resolve()

# Docker/K8s: только непустое значение; пустая строка в .env не должна ломать путь (Path("").resolve() → cwd).
_env_raw = (os.environ.get("AVATAR_UPLOAD_DIR") or "").strip()
if _env_raw:
    AVATAR_UPLOAD_DIR = Path(_env_raw).expanduser().resolve()
else:
    AVATAR_UPLOAD_DIR = _default_avatar_dir
