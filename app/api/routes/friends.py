from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.core.security import get_current_user
from app.services.user_service import (
    get_user_by_id,
    get_user_by_username,
    send_friend_request,
    accept_friend_request,
    reject_friend_request,
    remove_friend,
    get_friends_list,
    get_friend_requests,
    get_friends_leaderboard,
)

router = APIRouter(prefix="/api/friends", tags=["friends"])


@router.post("/request/{username}")
async def request_friend(username: str, user_id: str = Depends(get_current_user)):
    """Send a friend request to a user by username."""
    target = await get_user_by_username(username)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    target_id = str(target["_id"])
    if target_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot friend yourself")

    result = await send_friend_request(user_id, target_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return {"status": "ok", "message": result["message"]}


@router.post("/accept/{username}")
async def accept_request(username: str, user_id: str = Depends(get_current_user)):
    """Accept a friend request from a user."""
    sender = await get_user_by_username(username)
    if not sender:
        raise HTTPException(status_code=404, detail="User not found")

    result = await accept_friend_request(str(sender["_id"]), user_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return {"status": "ok"}


@router.post("/reject/{username}")
async def reject_request(username: str, user_id: str = Depends(get_current_user)):
    """Reject a friend request from a user."""
    sender = await get_user_by_username(username)
    if not sender:
        raise HTTPException(status_code=404, detail="User not found")

    result = await reject_friend_request(str(sender["_id"]), user_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return {"status": "ok"}


@router.delete("/{username}")
async def delete_friend(username: str, user_id: str = Depends(get_current_user)):
    """Remove a friend."""
    target = await get_user_by_username(username)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    result = await remove_friend(user_id, str(target["_id"]))
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return {"status": "ok"}


@router.get("/list")
async def list_friends(user_id: str = Depends(get_current_user)):
    """Get current user's friends list."""
    friends = await get_friends_list(user_id)
    return friends


@router.get("/requests")
async def list_requests(user_id: str = Depends(get_current_user)):
    """Get pending friend requests (incoming and outgoing)."""
    requests = await get_friend_requests(user_id)
    return requests


@router.get("/leaderboard")
async def friends_leaderboard(
    mode: str = "time",
    mode_value: int = 30,
    user_id: str = Depends(get_current_user),
):
    """Get leaderboard filtered to friends only."""
    return await get_friends_leaderboard(user_id, mode, mode_value)


@router.get("/status/{username}")
async def friendship_status(username: str, user_id: str = Depends(get_current_user)):
    """Check friendship status with a user."""
    target = await get_user_by_username(username)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    target_id = str(target["_id"])
    if target_id == user_id:
        return {"status": "self"}

    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Current user not found")

    friends = user.get("friends", [])
    if target_id in friends:
        return {"status": "friends"}

    outgoing = user.get("friend_requests_sent", [])
    if target_id in outgoing:
        return {"status": "request_sent"}

    incoming = user.get("friend_requests_received", [])
    if target_id in incoming:
        return {"status": "request_received"}

    return {"status": "none"}
