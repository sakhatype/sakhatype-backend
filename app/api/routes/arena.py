import json
import uuid
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(prefix="/api/arena", tags=["arena"])
legacy_ws_router = APIRouter(prefix="/arena", tags=["arena"])

# In-memory arena state
rooms: Dict[str, dict] = {}
connections: Dict[str, Dict[str, WebSocket]] = {}  # room_id -> {user_id: ws}


@router.post("/create")
async def create_room(mode: str = "time", mode_value: int = 30, language: str = "sakha"):
    room_id = str(uuid.uuid4())[:8]
    rooms[room_id] = {
        "room_id": room_id,
        "players": {},
        "status": "waiting",
        "mode": mode,
        "mode_value": mode_value,
        "language": language,
        "words": [],
    }
    connections[room_id] = {}
    return {"room_id": room_id}


@router.get("/rooms")
async def list_rooms():
    return [
        {
            "room_id": r["room_id"],
            "player_count": len(r["players"]),
            "status": r["status"],
            "mode": r["mode"],
            "mode_value": r["mode_value"],
            "language": r["language"],
        }
        for r in rooms.values()
        if r["status"] == "waiting"
    ]


@router.websocket("/ws/{room_id}/{username}")
@legacy_ws_router.websocket("/ws/{room_id}/{username}")
async def arena_ws(websocket: WebSocket, room_id: str, username: str):
    if room_id not in rooms:
        await websocket.close(code=4004, reason="Room not found")
        return

    await websocket.accept()
    connections[room_id][username] = websocket
    rooms[room_id]["players"][username] = {
        "username": username,
        "progress": 0,
        "wpm": 0,
        "accuracy": 100,
        "finished": False,
    }

    # Broadcast join
    await broadcast(room_id, {
        "type": "player_joined",
        "player": username,
        "players": rooms[room_id]["players"],
    })

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg["type"] == "start":
                rooms[room_id]["status"] = "in_progress"
                from app.services.word_service import get_words
                words = get_words(
                    language=rooms[room_id]["language"],
                    count=100,
                )
                rooms[room_id]["words"] = words
                await broadcast(room_id, {
                    "type": "game_start",
                    "words": words,
                    "mode": rooms[room_id]["mode"],
                    "mode_value": rooms[room_id]["mode_value"],
                })

            elif msg["type"] == "progress":
                rooms[room_id]["players"][username]["progress"] = msg.get("progress", 0)
                rooms[room_id]["players"][username]["wpm"] = msg.get("wpm", 0)
                rooms[room_id]["players"][username]["accuracy"] = msg.get("accuracy", 100)
                await broadcast(room_id, {
                    "type": "player_progress",
                    "player": username,
                    "progress": msg.get("progress", 0),
                    "wpm": msg.get("wpm", 0),
                    "accuracy": msg.get("accuracy", 100),
                })

            elif msg["type"] == "finish":
                rooms[room_id]["players"][username]["finished"] = True
                rooms[room_id]["players"][username]["wpm"] = msg.get("wpm", 0)
                rooms[room_id]["players"][username]["accuracy"] = msg.get("accuracy", 100)

                all_finished = all(
                    p["finished"] for p in rooms[room_id]["players"].values()
                )
                if all_finished:
                    rooms[room_id]["status"] = "finished"
                    # Determine winner
                    winner = max(
                        rooms[room_id]["players"].values(),
                        key=lambda p: p["wpm"],
                    )
                    await broadcast(room_id, {
                        "type": "game_end",
                        "winner": winner["username"],
                        "results": rooms[room_id]["players"],
                    })
                else:
                    await broadcast(room_id, {
                        "type": "player_finished",
                        "player": username,
                        "wpm": msg.get("wpm", 0),
                        "accuracy": msg.get("accuracy", 100),
                    })

    except WebSocketDisconnect:
        if room_id in connections and username in connections[room_id]:
            del connections[room_id][username]
        if room_id in rooms and username in rooms[room_id]["players"]:
            del rooms[room_id]["players"][username]

        if not rooms[room_id]["players"]:
            del rooms[room_id]
            if room_id in connections:
                del connections[room_id]
        else:
            await broadcast(room_id, {
                "type": "player_left",
                "player": username,
                "players": rooms[room_id]["players"],
            })


async def broadcast(room_id: str, message: dict):
    if room_id not in connections:
        return
    dead = []
    for uname, ws in connections[room_id].items():
        try:
            await ws.send_text(json.dumps(message, default=str))
        except Exception:
            dead.append(uname)
    for uname in dead:
        del connections[room_id][uname]
