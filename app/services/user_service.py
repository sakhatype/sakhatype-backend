from datetime import datetime, timezone
from typing import Optional, List
from bson import ObjectId
from app.db.mongodb import get_db
from app.core.security import get_password_hash, verify_password


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


def calculate_xp(wpm: float, accuracy: float, difficulty: str, mode: str, mode_value: int) -> int:
    """Calculate XP earned from a test."""
    base_xp = wpm * (accuracy / 100)
    difficulty_mult = 1.5 if difficulty == "expert" else 1.0
    # Longer tests give more XP
    if mode == "time":
        time_mult = mode_value / 30  # 30s is baseline
    else:
        time_mult = mode_value / 25  # 25 words is baseline
    return int(base_xp * difficulty_mult * time_mult)


def xp_for_next_level(level: int) -> int:
    """XP needed to reach next level."""
    return level * 500


async def create_user(username: str, email: str, password: str) -> dict:
    db = get_db()
    user_doc = {
        "username": username,
        "email": email,
        "password_hash": get_password_hash(password),
        "level": 1,
        "xp": 0,
        "total_tests": 0,
        "best_wpm": 0,
        "avg_wpm": 0,
        "avg_accuracy": 0,
        "achievements": [],
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.users.insert_one(user_doc)
    user_doc["_id"] = result.inserted_id
    return user_doc


async def authenticate_user(username: str, password: str) -> Optional[dict]:
    db = get_db()
    user = await db.users.find_one({"username": username})
    if not user or not verify_password(password, user["password_hash"]):
        return None
    return user


async def get_user_by_id(user_id: str) -> Optional[dict]:
    db = get_db()
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        return user
    except Exception:
        return None


async def get_user_by_username(username: str) -> Optional[dict]:
    db = get_db()
    return await db.users.find_one({"username": username})


async def save_test_result(user_id: Optional[str], result_data: dict) -> dict:
    db = get_db()
    doc = {
        **result_data,
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
    }
    insert_result = await db.results.insert_one(doc)
    doc["_id"] = insert_result.inserted_id

    xp_earned = 0
    level_up = False
    new_level = 1
    new_xp = 0
    new_achievements = []

    if user_id:
        user = await get_user_by_id(user_id)
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

            # Update stats
            total_tests = user["total_tests"] + 1
            best_wpm = max(user["best_wpm"], result_data["wpm"])
            avg_wpm = (
                (user["avg_wpm"] * user["total_tests"] + result_data["wpm"])
                / total_tests
            )
            avg_accuracy = (
                (user["avg_accuracy"] * user["total_tests"] + result_data["accuracy"])
                / total_tests
            )

            # Check achievements
            current_achievements = set(user.get("achievements", []))

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

            await db.users.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "level": new_level,
                        "xp": new_xp,
                        "total_tests": total_tests,
                        "best_wpm": best_wpm,
                        "avg_wpm": round(avg_wpm, 2),
                        "avg_accuracy": round(avg_accuracy, 2),
                        "achievements": list(current_achievements),
                    }
                },
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
    db = get_db()
    cursor = db.results.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def get_leaderboard(mode: str = "time", mode_value: int = 30, limit: int = 50) -> List[dict]:
    db = get_db()
    pipeline = [
        {
            "$match": {
                "user_id": {"$ne": None},
                "mode": mode,
                "mode_value": mode_value,
            }
        },
        {"$sort": {"wpm": -1}},
        {
            "$group": {
                "_id": "$user_id",
                "best_wpm": {"$max": "$wpm"},
                "best_accuracy": {"$first": "$accuracy"},
            }
        },
        {"$sort": {"best_wpm": -1}},
        {"$limit": limit},
    ]

    results = await db.results.aggregate(pipeline).to_list(length=limit)

    leaderboard = []
    for rank, entry in enumerate(results, 1):
        user = await get_user_by_id(entry["_id"])
        if user:
            leaderboard.append({
                "rank": rank,
                "user_id": entry["_id"],
                "username": user["username"],
                "wpm": entry["best_wpm"],
                "accuracy": entry["best_accuracy"],
                "language": "sakha",
                "level": user.get("level", 1),
            })

    return leaderboard
