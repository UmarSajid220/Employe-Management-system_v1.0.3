"""
Messages Router for A Square Skills Academy EMS
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from slowapi import limiter
from bson import ObjectId

from models import (
    Message, MessageCreate, MessageResponse,
    PaginatedResponse, ApiResponse
)
from dependencies import (
    get_database, get_current_user,
    serialize_mongo_doc, serialize_mongo_docs, paginate_query
)
from logging_config import setup_logging, log_database_operation

router = APIRouter()
logger = setup_logging()


class ChatMessage(BaseModel):
    """Chat message model"""
    receiver_id: str
    message: str
    attachments: Optional[List[str]] = []


class ConversationResponse(BaseModel):
    """Conversation response model"""
    user_id: str
    user_name: str
    last_message: str
    last_message_time: datetime
    unread_count: int


@router.get("/conversations")
@limiter.limit("10/minute")
async def get_conversations(
    request,
    current_user=Depends(get_current_user)
):
    """Get user's conversations"""
    try:
        db = get_database()
        
        # Get conversations where user is either sender or receiver
        pipeline = [
            {
                "$match": {
                    "$or": [
                        {"sender_id": ObjectId(current_user.id)},
                        {"receiver_id": ObjectId(current_user.id)}
                    ]
                }
            },
            {
                "$sort": {"created_at": -1}
            },
            {
                "$group": {
                    "_id": {
                        "$cond": [
                            {"$eq": ["$sender_id", ObjectId(current_user.id)]},
                            "$receiver_id",
                            "$sender_id"
                        ]
                    },
                    "last_message": {"$first": "$message"},
                    "last_message_time": {"$first": "$created_at"},
                    "unread_count": {
                        "$sum": {
                            "$cond": [
                                {
                                    "$and": [
                                        {"$ne": ["$sender_id", ObjectId(current_user.id)]},
                                        {"$eq": ["$is_read", False]}
                                    ]
                                },
                                1,
                                0
                            ]
                        }
                    }
                }
            },
            {
                "$lookup": {
                    "from": "users",
                    "localField": "_id",
                    "foreignField": "_id",
                    "as": "user"
                }
            },
            {
                "$project": {
                    "user_id": {"$arrayElemAt": ["$user._id", 0]},
                    "user_name": {"$arrayElemAt": ["$user.name", 0]},
                    "last_message": 1,
                    "last_message_time": 1,
                    "unread_count": 1
                }
            },
            {
                "$sort": {"last_message_time": -1}
            }
        ]
        
        conversations = await db.messages.aggregate(pipeline).to_list(length=None)
        conversations = serialize_mongo_docs(conversations)
        
        # Convert user_id to string
        for conv in conversations:
            if conv.get("user_id"):
                conv["user_id"] = str(conv["user_id"])
        
        return ApiResponse(
            success=True,
            message="Conversations retrieved",
            data={"conversations": conversations}
        )
        
    except Exception as e:
        logger.error(f"Get conversations error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch conversations"
        )


@router.get("/{user_id}")
@limiter.limit("10/minute")
async def get_messages(
    request,
    user_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user)
):
    """Get messages with a specific user"""
    try:
        db = get_database()
        
        # Build query
        query = {
            "$or": [
                {
                    "sender_id": ObjectId(current_user.id),
                    "receiver_id": ObjectId(user_id)
                },
                {
                    "sender_id": ObjectId(user_id),
                    "receiver_id": ObjectId(current_user.id)
                }
            ]
        }
        
        # Get total count
        total = await db.messages.count_documents(query)
        
        # Get paginated results with user details
        pipeline = [
            {"$match": query},
            {"$sort": {"created_at": -1}},
            {"$skip": (page - 1) * limit},
            {"$limit": limit},
            {
                "$lookup": {
                    "from": "users",
                    "localField": "sender_id",
                    "foreignField": "_id",
                    "as": "sender"
                }
            },
            {
                "$lookup": {
                    "from": "users",
                    "localField": "receiver_id",
                    "foreignField": "_id",
                    "as": "receiver"
                }
            },
            {
                "$project": {
                    "message": 1,
                    "is_read": 1,
                    "read_at": 1,
                    "attachments": 1,
                    "created_at": 1,
                    "sender": {"$arrayElemAt": ["$sender", 0]},
                    "receiver": {"$arrayElemAt": ["$receiver", 0]}
                }
            }
        ]
        
        messages = await db.messages.aggregate(pipeline).to_list(length=limit)
        messages = serialize_mongo_docs(messages)
        
        # Clean up user data and reverse to show oldest first
        messages.reverse()
        for msg in messages:
            if msg.get("sender"):
                msg["sender"].pop("password", None)
                msg["sender"]["id"] = str(msg["sender"].pop("_id"))
            if msg.get("receiver"):
                msg["receiver"].pop("password", None)
                msg["receiver"]["id"] = str(msg["receiver"].pop("_id"))
        
        # Mark messages as read
        await db.messages.update_many(
            {
                "sender_id": ObjectId(user_id),
                "receiver_id": ObjectId(current_user.id),
                "is_read": False
            },
            {
                "$set": {
                    "is_read": True,
                    "read_at": datetime.utcnow()
                }
            }
        )
        
        total_pages = (total + limit - 1) // limit
        
        log_database_operation(
            logger, "read", "messages",
            user_id=current_user.id,
            duration=0.1
        )
        
        return PaginatedResponse(
            items=messages,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )
        
    except Exception as e:
        logger.error(f"Get messages error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch messages"
        )


@router.post("/")
@limiter.limit("10/minute")
async def send_message(
    request,
    message_data: MessageCreate,
    current_user=Depends(get_current_user)
):
    """Send message"""
    try:
        db = get_database()
        
        # Check if receiver exists
        receiver = await db.users.find_one({"_id": ObjectId(message_data.receiver_id)})
        if not receiver:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Receiver not found"
            )
        
        # Prepare message data
        message_dict = message_data.dict()
        message_dict["sender_id"] = ObjectId(current_user.id)
        message_dict["receiver_id"] = ObjectId(message_data.receiver_id)
        message_dict["created_at"] = datetime.utcnow()
        message_dict["updated_at"] = datetime.utcnow()
        
        # Insert message
        result = await db.messages.insert_one(message_dict)
        message_id = str(result.inserted_id)
        
        log_database_operation(
            logger, "create", "messages", message_id,
            user_id=current_user.id,
            duration=0.1
        )
        
        # Get created message with user details
        created_message = await db.messages.find_one({"_id": result.inserted_id})
        created_message = serialize_mongo_doc(created_message)
        
        # Add sender info
        created_message["sender"] = {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email
        }
        
        return ApiResponse(
            success=True,
            message="Message sent successfully",
            data={"message": created_message}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Send message error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send message"
        )


@router.put("/{message_id}/read")
@limiter.limit("10/minute")
async def mark_message_read(
    request,
    message_id: str,
    current_user=Depends(get_current_user)
):
    """Mark message as read"""
    try:
        db = get_database()
        
        # Check if message exists and belongs to user
        message = await db.messages.find_one({
            "_id": ObjectId(message_id),
            "receiver_id": ObjectId(current_user.id)
        })
        
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )
        
        # Update message
        result = await db.messages.update_one(
            {"_id": ObjectId(message_id)},
            {
                "$set": {
                    "is_read": True,
                    "read_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to mark message as read"
            )
        
        log_database_operation(
            logger, "update", "messages", message_id,
            user_id=current_user.id,
            duration=0.1
        )
        
        return ApiResponse(
            success=True,
            message="Message marked as read",
            data={}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Mark message read error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark message as read"
        )


@router.get("/unread/count")
@limiter.limit("10/minute")
async def get_unread_count(
    request,
    current_user=Depends(get_current_user)
):
    """Get unread message count"""
    try:
        db = get_database()
        
        count = await db.messages.count_documents({
            "receiver_id": ObjectId(current_user.id),
            "is_read": False
        })
        
        return ApiResponse(
            success=True,
            message="Unread count retrieved",
            data={"unread_count": count}
        )
        
    except Exception as e:
        logger.error(f"Get unread count error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get unread count"
        )


@router.delete("/{message_id}")
@limiter.limit("5/minute")
async def delete_message(
    request,
    message_id: str,
    current_user=Depends(get_current_user)
):
    """Delete message (only if sender)"""
    try:
        db = get_database()
        
        # Check if message exists and belongs to user
        message = await db.messages.find_one({
            "_id": ObjectId(message_id),
            "sender_id": ObjectId(current_user.id)
        })
        
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found or access denied"
            )
        
        # Delete message
        result = await db.messages.delete_one({"_id": ObjectId(message_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete message"
            )
        
        log_database_operation(
            logger, "delete", "messages", message_id,
            user_id=current_user.id,
            duration=0.1
        )
        
        return ApiResponse(
            success=True,
            message="Message deleted successfully",
            data={}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete message error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete message"
        )


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict = {}
    
    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
    
    def disconnect(self, user_id: str, websocket: WebSocket):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
    
    async def broadcast_to_user(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except:
                    pass


manager = ConnectionManager()


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time messaging"""
    await manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            
            # Handle different message types
            if data.get("type") == "message":
                # Broadcast message to receiver
                await manager.broadcast_to_user(data["receiver_id"], data)
                
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)