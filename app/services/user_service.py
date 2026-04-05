from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from app.core.security import get_password_hash, verify_password
from app.db.postgres import get_pool
from app.services.avatar_storage import process_avatar_image, save_avatar_for_user

_AVATAR_UPLOAD_MAX_BYTES = 8 * 1024 * 1024


ACHIEVEMENTS = {
    "first_test": {"name": "Бастакы хардыы", "desc": "Бастакы тэстиҥи толор"},
    "sakha_god": {"name": "Саха Тойоно", "desc": "Саха тылынан 120+ WPM ситис"},
    "speed_demon": {"name": "Түргэн Абааһы", "desc": "150+ WPM ситис"},
    "accuracy_king": {"name": "Сөпкө Хааны", "desc": "100% сөпкөлүктээх тэст толор"},
    "centurion": {"name": "Сүүстээх", "desc": "100 тэст толор"},
    "marathon": {"name": "Марафонсук", "desc": "60 сөкүүндэлээх тэскэ 80+ WPM ситис"},
    "perfectionist": {"name": "Чыычаах Харах", "desc": "10 тэһиэктэн 99%+ сөпкөлүк тут"},
    "level_10": {"name": "Кыһаммыт Суруйааччы", "desc": "10 таһымҥа тиий"},
    "level_25": {"name": "Мастар Суруйааччы", "desc": "25 таһымҥа тиий"},
    "level_50": {"name": "Легендарнай Суруйааччы", "desc": "50 таһымҥа тиий"},
}


def _row_to_dict(row) -> dict:
    """Convert asyncpg.Record to dict."""
    if row is None:
        return None
    return dict(row)


def calculate_xp(wpm: float, accuracy: float, difficulty: str, mode: str, mode_value: int) -> int:
    base_xp = wpm * (accuracy / 100)
    difficulty_mult = 1.5 if difficulty == "expert" else 1.0
    if mode == "time":
        time_mult = mode_value / 30
    else:
        time_mult = mode_value / 25
    return int(base_xp * difficulty_mult * time_mult)


def xp_for_next_level(level: int) -> int:
    # 100 XP/ур. для 1–5, 200 для 6–10, далее +100 каждые 5 уровней
    if level < 1:
        level = 1
    bracket = (level - 1) // 5 + 1
    return 100 * bracket


async def create_user(username: str, email: Optional[str], password: str) -> dict:
    pool = get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO users (username, email, password_hash)
        VALUES ($1, $2, $3)
        RETURNING *
        """,
        username, email, get_password_hash(password),
    )
    return _row_to_dict(row)


async def authenticate_user(username: str, password: str) -> Optional[dict]:
    pool = get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM users WHERE username = $1", username
    )
    if not row or not verify_password(password, row["password_hash"]):
        return None
    return _row_to_dict(row)


async def get_user_by_id(user_id: str) -> Optional[dict]:
    pool = get_pool()
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return None
    row = await pool.fetchrow("SELECT * FROM users WHERE id = $1", uid)
    return _row_to_dict(row)


async def get_user_by_username(username: str) -> Optional[dict]:
    pool = get_pool()
    row = await pool.fetchrow("SELECT * FROM users WHERE username = $1", username)
    return _row_to_dict(row)


async def get_user_by_username_ci(username: str) -> Optional[dict]:
    """Как get_user_by_username, но без учёта регистра (для публичных URL профиля)."""
    pool = get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM users WHERE lower(username) = lower($1)",
        (username or "").strip(),
    )
    return _row_to_dict(row)


async def get_user_by_email(email: str) -> Optional[dict]:
    if not email or not str(email).strip():
        return None
    pool = get_pool()
    row = await pool.fetchrow("SELECT * FROM users WHERE email = $1", email.strip().lower())
    return _row_to_dict(row)


async def update_user_profile(
    user_id: str,
    fields: dict,
    new_password: Optional[str] = None,
    current_password: Optional[str] = None,
) -> dict:
    """
    Apply profile updates. ``fields`` is UserUpdate.model_dump(exclude_unset=True) without password keys.
    Raises ValueError with a user-facing message on conflict or bad password.
    """
    user = await get_user_by_id(user_id)
    if not user:
        raise ValueError("Пользователь не найден")

    uid = int(user_id)
    pool = get_pool()

    if "username" in fields:
        new_username = fields["username"].strip()
        if new_username != user["username"]:
            taken = await get_user_by_username(new_username)
            if taken and taken["id"] != uid:
                raise ValueError("Это имя пользователя уже занято")
            await pool.execute(
                "UPDATE users SET username = $1 WHERE id = $2", new_username, uid
            )

    if "email" in fields:
        email = fields["email"]
        if email != user.get("email"):
            if email:
                other = await get_user_by_email(email)
                if other and other["id"] != uid:
                    raise ValueError("Этот email уже зарегистрирован")
            await pool.execute("UPDATE users SET email = $1 WHERE id = $2", email, uid)

    if new_password:
        if not verify_password(current_password or "", user["password_hash"]):
            raise ValueError("Неверный текущий пароль")
        await pool.execute(
            "UPDATE users SET password_hash = $1 WHERE id = $2",
            get_password_hash(new_password),
            uid,
        )

    return await get_user_by_id(user_id)


async def update_user_avatar_url(user_id: str, avatar_url: str) -> None:
    pool = get_pool()
    await pool.execute(
        "UPDATE users SET avatar_url = $1 WHERE id = $2",
        avatar_url,
        int(user_id),
    )


async def apply_avatar_upload(user_id: str, content: bytes) -> Dict[str, Any]:
    """
    Обработка файла аватара: WebP 128×128, запись на диск, UPDATE users.
    ValueError — текст для HTTP 400; «Пользователь не найден» — отдать как 404 в роуте.
    """
    if len(content) > _AVATAR_UPLOAD_MAX_BYTES:
        raise ValueError("Файл слишком большой (макс. 8 МБ)")
    webp_bytes = process_avatar_image(content)
    url = save_avatar_for_user(user_id, webp_bytes)
    await update_user_avatar_url(user_id, url)
    user = await get_user_by_id(user_id)
    if not user:
        raise ValueError("Пользователь не найден")
    return {"avatar_url": url, "user": user}


async def save_test_result(user_id: Optional[str], result_data: dict) -> dict:
    pool = get_pool()
    uid = int(user_id) if user_id else None

    row = await pool.fetchrow(
        """
        INSERT INTO results (user_id, wpm, raw_wpm, accuracy, mode, mode_value,
                             language, difficulty, chars_correct, chars_incorrect,
                             chars_extra, chars_missed)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
        RETURNING *
        """,
        uid,
        result_data["wpm"],
        result_data["raw_wpm"],
        result_data["accuracy"],
        result_data["mode"],
        result_data["mode_value"],
        result_data.get("language", "sakha"),
        result_data.get("difficulty", "normal"),
        result_data.get("chars_correct", 0),
        result_data.get("chars_incorrect", 0),
        result_data.get("chars_extra", 0),
        result_data.get("chars_missed", 0),
    )
    doc = _row_to_dict(row)

    xp_earned = 0
    level_up = False
    new_level = 1
    new_xp = 0
    new_achievements = []

    if uid:
        user = await get_user_by_id(str(uid))
        if user:
            xp_earned = calculate_xp(
                result_data["wpm"],
                result_data["accuracy"],
                result_data.get("difficulty", "normal"),
                result_data["mode"],
                result_data["mode_value"],
            )

            new_xp = user["xp"] + xp_earned
            new_level = user["level"]
            needed = xp_for_next_level(new_level)

            while new_xp >= needed:
                new_xp -= needed
                new_level += 1
                level_up = True
                needed = xp_for_next_level(new_level)

            total_tests = user["total_tests"] + 1
            best_wpm = max(user["best_wpm"], result_data["wpm"])
            avg_wpm = (user["avg_wpm"] * user["total_tests"] + result_data["wpm"]) / total_tests
            avg_accuracy = (user["avg_accuracy"] * user["total_tests"] + result_data["accuracy"]) / total_tests

            current_achievements = set(user.get("achievements") or [])

            if total_tests == 1:
                current_achievements.add("first_test")
                new_achievements.append("first_test")

            if result_data["wpm"] >= 120 and result_data.get("language") == "sakha":
                if "sakha_god" not in current_achievements:
                    current_achievements.add("sakha_god")
                    new_achievements.append("sakha_god")

            if result_data["wpm"] >= 150:
                if "speed_demon" not in current_achievements:
                    current_achievements.add("speed_demon")
                    new_achievements.append("speed_demon")

            if result_data["accuracy"] >= 100:
                if "accuracy_king" not in current_achievements:
                    current_achievements.add("accuracy_king")
                    new_achievements.append("accuracy_king")

            if total_tests >= 100:
                if "centurion" not in current_achievements:
                    current_achievements.add("centurion")
                    new_achievements.append("centurion")

            if (
                result_data["mode"] == "time"
                and result_data["mode_value"] == 60
                and result_data["wpm"] >= 80
            ):
                if "marathon" not in current_achievements:
                    current_achievements.add("marathon")
                    new_achievements.append("marathon")

            if new_level >= 10 and "level_10" not in current_achievements:
                current_achievements.add("level_10")
                new_achievements.append("level_10")
            if new_level >= 25 and "level_25" not in current_achievements:
                current_achievements.add("level_25")
                new_achievements.append("level_25")
            if new_level >= 50 and "level_50" not in current_achievements:
                current_achievements.add("level_50")
                new_achievements.append("level_50")

            await pool.execute(
                """
                UPDATE users
                SET level = $1, xp = $2, total_tests = $3, best_wpm = $4,
                    avg_wpm = $5, avg_accuracy = $6, achievements = $7
                WHERE id = $8
                """,
                new_level, new_xp, total_tests, best_wpm,
                round(avg_wpm, 2), round(avg_accuracy, 2),
                list(current_achievements), uid,
            )

    return {
        "result": doc,
        "xp_earned": xp_earned,
        "level_up": level_up,
        "new_level": new_level,
        "new_xp": new_xp,
        "xp_to_next": xp_for_next_level(new_level),
        "new_achievements": new_achievements,
    }


async def get_user_results(user_id: str, limit: int = 50) -> List[dict]:
    pool = get_pool()
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return []
    rows = await pool.fetch(
        "SELECT * FROM results WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2",
        uid, limit,
    )
    return [_row_to_dict(r) for r in rows]


async def get_user_contribution_results(user_id: str, days: int = 320) -> List[dict]:
    """Лёгкая выборка WPM по дням для тепловой карты (последние ``days`` дней)."""
    pool = get_pool()
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return []
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = await pool.fetch(
        """
        SELECT wpm, created_at FROM results
        WHERE user_id = $1 AND created_at >= $2
        ORDER BY created_at DESC
        LIMIT 20000
        """,
        uid,
        since,
    )
    return [_row_to_dict(r) for r in rows]


def _profile_period_to_since(period: str) -> Optional[datetime]:
    p = (period or "all").strip().lower()
    if p in ("", "all"):
        return None
    now = datetime.now(timezone.utc)
    if p == "7d":
        return now - timedelta(days=7)
    if p in ("30d", "1m", "month"):
        return now - timedelta(days=30)
    if p in ("365d", "1y", "year"):
        return now - timedelta(days=365)
    return None


async def get_user_tests_paginated(
    user_id: str,
    *,
    period: str = "all",
    mode: str = "all",
    page: int = 1,
    page_size: int = 40,
) -> tuple[List[dict], int]:
    """
    Полные записи тестов с фильтрами и пагинацией.
    ``page_size``: 40, 60 или 120.
    """
    pool = get_pool()
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return [], 0

    if page_size not in (40, 60, 120):
        page_size = 40
    page = max(1, int(page))

    m = (mode or "all").strip().lower()
    if m not in ("all", "time", "words"):
        m = "all"

    since = _profile_period_to_since(period)

    conds = ["user_id = $1"]
    args: list = [uid]
    n = 2

    if since is not None:
        conds.append(f"created_at >= ${n}")
        args.append(since)
        n += 1

    if m != "all":
        conds.append(f"mode = ${n}")
        args.append(m)
        n += 1

    where_sql = " AND ".join(conds)
    count_row = await pool.fetchrow(
        f"SELECT COUNT(*) AS c FROM results WHERE {where_sql}", *args
    )
    total = int(count_row["c"]) if count_row else 0

    offset = (page - 1) * page_size
    args_with_page = list(args) + [page_size, offset]
    lim_idx = n
    off_idx = n + 1
    rows = await pool.fetch(
        f"""
        SELECT * FROM results
        WHERE {where_sql}
        ORDER BY created_at DESC
        LIMIT ${lim_idx} OFFSET ${off_idx}
        """,
        *args_with_page,
    )
    return [_row_to_dict(r) for r in rows], total


async def get_leaderboard(
    mode: str = "time",
    mode_value: int = 30,
    limit: int = 50,
    difficulty: str = "normal",
) -> List[dict]:
    m = (mode or "time").strip().lower()
    if m not in ("time", "words"):
        m = "time"
    if difficulty not in ("normal", "expert"):
        difficulty = "normal"
    pool = get_pool()
    rows = await pool.fetch(
        """
        SELECT DISTINCT ON (r.user_id)
               r.user_id, r.wpm AS best_wpm, r.accuracy AS best_accuracy,
               u.username, u.level, u.avatar_url,
               COALESCE(r.difficulty, 'normal') AS result_difficulty
        FROM results r
        JOIN users u ON u.id = r.user_id
        WHERE r.user_id IS NOT NULL
          AND r.mode = $1
          AND r.mode_value = $2
          AND COALESCE(r.difficulty, 'normal') = $3
        ORDER BY r.user_id, r.wpm DESC
        """,
        m, mode_value, difficulty,
    )

    # Sort by best_wpm descending and limit
    sorted_rows = sorted(rows, key=lambda r: r["best_wpm"], reverse=True)[:limit]

    leaderboard = []
    for rank, entry in enumerate(sorted_rows, 1):
        leaderboard.append({
            "rank": rank,
            "user_id": str(entry["user_id"]),
            "username": entry["username"],
            "wpm": entry["best_wpm"],
            "accuracy": entry["best_accuracy"],
            "language": "sakha",
            "level": entry.get("level", 1),
            "difficulty": entry.get("result_difficulty") or difficulty,
            "avatar_url": entry.get("avatar_url"),
        })

    return leaderboard


# ── Friends ──────────────────────────────────────────────────────

async def send_friend_request(from_id: str, to_id: str) -> dict:
    pool = get_pool()
    from_uid, to_uid = int(from_id), int(to_id)

    sender = await get_user_by_id(from_id)
    receiver = await get_user_by_id(to_id)
    if not sender or not receiver:
        return {"success": False, "error": "Пользователь не найден"}

    friends = sender.get("friends") or []
    sent = sender.get("friend_requests_sent") or []
    received_by_target = receiver.get("friend_requests_received") or []

    if to_id in friends:
        return {"success": False, "error": "Уже в друзьях"}
    if to_id in sent:
        return {"success": False, "error": "Запрос уже отправлен"}

    # Check if target already sent us a request → auto-accept
    incoming = sender.get("friend_requests_received") or []
    if to_id in incoming:
        return await accept_friend_request(to_id, from_id)

    await pool.execute(
        "UPDATE users SET friend_requests_sent = array_append(friend_requests_sent, $1) WHERE id = $2",
        to_id, from_uid,
    )
    await pool.execute(
        "UPDATE users SET friend_requests_received = array_append(friend_requests_received, $1) WHERE id = $2",
        from_id, to_uid,
    )
    return {"success": True, "message": "Friend request sent"}


async def accept_friend_request(from_id: str, to_id: str) -> dict:
    pool = get_pool()
    from_uid, to_uid = int(from_id), int(to_id)

    receiver = await get_user_by_id(to_id)
    if not receiver:
        return {"success": False, "error": "Пользователь не найден"}

    incoming = receiver.get("friend_requests_received") or []
    if from_id not in incoming:
        return {"success": False, "error": "Нет входящего запроса от этого пользователя"}

    # Add to friends lists
    await pool.execute(
        """
        UPDATE users SET
            friends = array_append(friends, $1),
            friend_requests_received = array_remove(friend_requests_received, $1)
        WHERE id = $2
        """,
        from_id, to_uid,
    )
    await pool.execute(
        """
        UPDATE users SET
            friends = array_append(friends, $1),
            friend_requests_sent = array_remove(friend_requests_sent, $1)
        WHERE id = $2
        """,
        to_id, from_uid,
    )
    return {"success": True, "message": "Friend request accepted"}


async def reject_friend_request(from_id: str, to_id: str) -> dict:
    pool = get_pool()
    from_uid, to_uid = int(from_id), int(to_id)

    await pool.execute(
        "UPDATE users SET friend_requests_received = array_remove(friend_requests_received, $1) WHERE id = $2",
        from_id, to_uid,
    )
    await pool.execute(
        "UPDATE users SET friend_requests_sent = array_remove(friend_requests_sent, $1) WHERE id = $2",
        to_id, from_uid,
    )
    return {"success": True, "message": "Friend request rejected"}


async def remove_friend(user_id: str, friend_id: str) -> dict:
    pool = get_pool()
    uid, fid = int(user_id), int(friend_id)

    await pool.execute(
        "UPDATE users SET friends = array_remove(friends, $1) WHERE id = $2",
        friend_id, uid,
    )
    await pool.execute(
        "UPDATE users SET friends = array_remove(friends, $1) WHERE id = $2",
        user_id, fid,
    )
    return {"success": True, "message": "Friend removed"}


async def get_friends_list(user_id: str) -> List[dict]:
    user = await get_user_by_id(user_id)
    if not user:
        return []

    friend_ids = user.get("friends") or []
    friends = []
    for fid in friend_ids:
        friend = await get_user_by_id(fid)
        if friend:
            friends.append({
                "id": str(friend["id"]),
                "username": friend["username"],
                "level": friend.get("level", 1),
                "best_wpm": friend.get("best_wpm", 0),
                "avg_wpm": friend.get("avg_wpm", 0),
                "avatar_url": friend.get("avatar_url"),
            })
    return friends


async def get_friend_requests(user_id: str) -> dict:
    user = await get_user_by_id(user_id)
    if not user:
        return {"incoming": [], "outgoing": []}

    incoming = []
    for fid in (user.get("friend_requests_received") or []):
        u = await get_user_by_id(fid)
        if u:
            incoming.append({
                "id": str(u["id"]),
                "username": u["username"],
                "level": u.get("level", 1),
                "avatar_url": u.get("avatar_url"),
            })

    outgoing = []
    for fid in (user.get("friend_requests_sent") or []):
        u = await get_user_by_id(fid)
        if u:
            outgoing.append({
                "id": str(u["id"]),
                "username": u["username"],
                "level": u.get("level", 1),
                "avatar_url": u.get("avatar_url"),
            })

    return {"incoming": incoming, "outgoing": outgoing}


async def get_friends_leaderboard(
    user_id: str,
    mode: str = "time",
    mode_value: int = 30,
    difficulty: str = "normal",
) -> List[dict]:
    user = await get_user_by_id(user_id)
    if not user:
        return []

    friend_ids = user.get("friends") or []
    all_ids = [user_id] + friend_ids

    pool = get_pool()
    int_ids = []
    for i in all_ids:
        try:
            int_ids.append(int(i))
        except (ValueError, TypeError):
            pass

    if not int_ids:
        return []

    if difficulty not in ("normal", "expert"):
        difficulty = "normal"

    rows = await pool.fetch(
        """
        SELECT DISTINCT ON (r.user_id)
               r.user_id, r.wpm AS best_wpm, r.accuracy AS best_accuracy,
               u.username, u.level, u.avatar_url,
               COALESCE(r.difficulty, 'normal') AS result_difficulty
        FROM results r
        JOIN users u ON u.id = r.user_id
        WHERE r.user_id = ANY($1)
          AND r.mode = $2
          AND r.mode_value = $3
          AND COALESCE(r.difficulty, 'normal') = $4
        ORDER BY r.user_id, r.wpm DESC
        """,
        int_ids, mode, mode_value, difficulty,
    )

    sorted_rows = sorted(rows, key=lambda r: r["best_wpm"], reverse=True)

    leaderboard = []
    for rank, entry in enumerate(sorted_rows, 1):
        leaderboard.append({
            "rank": rank,
            "user_id": str(entry["user_id"]),
            "username": entry["username"],
            "wpm": entry["best_wpm"],
            "accuracy": entry["best_accuracy"],
            "language": "sakha",
            "level": entry.get("level", 1),
            "difficulty": entry.get("result_difficulty") or difficulty,
            "avatar_url": entry.get("avatar_url"),
        })

    return leaderboard
