"""
Tasks Router for A Square Skills Academy EMS
"""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from slowapi import limiter
from bson import ObjectId

from models import (
    Task, TaskCreate, TaskUpdate, TaskStatus,
    PaginatedResponse, ApiResponse
)
from dependencies import (
    get_database, get_current_user, get_admin_user,
    serialize_mongo_doc, serialize_mongo_docs, paginate_query
)
from logging_config import setup_logging, log_database_operation

router = APIRouter()
logger = setup_logging()


class TaskResponseWithUser(BaseModel):
    """Task response with user details"""
    id: str
    title: str
    description: Optional[str]
    assigned_to: dict
    assigned_by: Optional[dict]
    status: str
    priority: str
    deadline: Optional[datetime]
    completed_at: Optional[datetime]
    tags: List[str]
    attachments: List[str]
    estimated_hours: Optional[float]
    actual_hours: Optional[float]
    created_at: datetime
    updated_at: datetime


@router.get("/", response_model=PaginatedResponse)
@limiter.limit("10/minute")
async def get_tasks(
    request,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    assigned_to: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user=Depends(get_current_user)
):
    """Get tasks with pagination and filtering"""
    try:
        db = get_database()
        
        # Build query based on user role
        query = {}
        if current_user.role != "admin":
            query["assigned_to"] = ObjectId(current_user.id)
        
        if status:
            query["status"] = status
        if priority:
            query["priority"] = priority
        if assigned_to and current_user.role == "admin":
            query["assigned_to"] = ObjectId(assigned_to)
        if search:
            query["$or"] = [
                {"title": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}}
            ]
        
        # Get total count
        total = await db.tasks.count_documents(query)
        
        # Get paginated results with user details
        pipeline = [
            {"$match": query},
            {"$sort": {"created_at": -1}},
            {"$skip": (page - 1) * limit},
            {"$limit": limit},
            {
                "$lookup": {
                    "from": "users",
                    "localField": "assigned_to",
                    "foreignField": "_id",
                    "as": "assigned_to_user"
                }
            },
            {
                "$lookup": {
                    "from": "users",
                    "localField": "assigned_by",
                    "foreignField": "_id",
                    "as": "assigned_by_user"
                }
            },
            {
                "$project": {
                    "title": 1,
                    "description": 1,
                    "status": 1,
                    "priority": 1,
                    "deadline": 1,
                    "completed_at": 1,
                    "tags": 1,
                    "attachments": 1,
                    "estimated_hours": 1,
                    "actual_hours": 1,
                    "created_at": 1,
                    "updated_at": 1,
                    "assigned_to": {
                        "$arrayElemAt": ["$assigned_to_user", 0]
                    },
                    "assigned_by": {
                        "$arrayElemAt": ["$assigned_by_user", 0]
                    }
                }
            }
        ]
        
        tasks = await db.tasks.aggregate(pipeline).to_list(length=limit)
        tasks = serialize_mongo_docs(tasks)
        
        # Clean up user data
        for task in tasks:
            if task.get("assigned_to"):
                task["assigned_to"].pop("password", None)
                task["assigned_to"]["id"] = str(task["assigned_to"].pop("_id"))
            if task.get("assigned_by"):
                task["assigned_by"].pop("password", None)
                task["assigned_by"]["id"] = str(task["assigned_by"].pop("_id"))
        
        total_pages = (total + limit - 1) // limit
        
        log_database_operation(
            logger, "read", "tasks",
            user_id=current_user.id,
            duration=0.1
        )
        
        return PaginatedResponse(
            items=tasks,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )
        
    except Exception as e:
        logger.error(f"Get tasks error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch tasks"
        )


@router.get("/{task_id}")
@limiter.limit("10/minute")
async def get_task(
    request,
    task_id: str,
    current_user=Depends(get_current_user)
):
    """Get task by ID"""
    try:
        db = get_database()
        
        # Get task with user details
        pipeline = [
            {"$match": {"_id": ObjectId(task_id)}},
            {
                "$lookup": {
                    "from": "users",
                    "localField": "assigned_to",
                    "foreignField": "_id",
                    "as": "assigned_to_user"
                }
            },
            {
                "$lookup": {
                    "from": "users",
                    "localField": "assigned_by",
                    "foreignField": "_id",
                    "as": "assigned_by_user"
                }
            },
            {
                "$project": {
                    "title": 1,
                    "description": 1,
                    "status": 1,
                    "priority": 1,
                    "deadline": 1,
                    "completed_at": 1,
                    "tags": 1,
                    "attachments": 1,
                    "estimated_hours": 1,
                    "actual_hours": 1,
                    "created_at": 1,
                    "updated_at": 1,
                    "assigned_to": {
                        "$arrayElemAt": ["$assigned_to_user", 0]
                    },
                    "assigned_by": {
                        "$arrayElemAt": ["$assigned_by_user", 0]
                    }
                }
            }
        ]
        
        task_result = await db.tasks.aggregate(pipeline).to_list(length=1)
        if not task_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        task = task_result[0]
        
        # Check permissions
        if (current_user.role != "admin" and 
            str(task["assigned_to"]["_id"]) != current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        task = serialize_mongo_doc(task)
        
        # Clean up user data
        if task.get("assigned_to"):
            task["assigned_to"].pop("password", None)
            task["assigned_to"]["id"] = str(task["assigned_to"].pop("_id"))
        if task.get("assigned_by"):
            task["assigned_by"].pop("password", None)
            task["assigned_by"]["id"] = str(task["assigned_by"].pop("_id"))
        
        log_database_operation(
            logger, "read", "tasks", task_id,
            user_id=current_user.id,
            duration=0.05
        )
        
        return ApiResponse(
            success=True,
            message="Task retrieved",
            data={"task": task}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get task error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch task"
        )


@router.post("/")
@limiter.limit("5/minute")
async def create_task(
    request,
    task_data: TaskCreate,
    current_user=Depends(get_admin_user)
):
    """Create new task (admin only)"""
    try:
        db = get_database()
        
        # Check if assigned user exists
        assigned_user = await db.users.find_one({"_id": ObjectId(task_data.assigned_to)})
        if not assigned_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned user not found"
            )
        
        # Prepare task data
        task_dict = task_data.dict()
        task_dict["assigned_to"] = ObjectId(task_dict["assigned_to"])
        task_dict["assigned_by"] = ObjectId(current_user.id)
        task_dict["created_at"] = datetime.utcnow()
        task_dict["updated_at"] = datetime.utcnow()
        
        # Set status based on deadline
        if task_dict.get("deadline") and task_dict["deadline"] < datetime.utcnow():
            task_dict["status"] = TaskStatus.OVERDUE
        
        # Insert task
        result = await db.tasks.insert_one(task_dict)
        task_id = str(result.inserted_id)
        
        log_database_operation(
            logger, "create", "tasks", task_id,
            user_id=current_user.id,
            duration=0.1
        )
        
        # Get created task with user details
        created_task = await db.tasks.find_one({"_id": result.inserted_id})
        created_task = serialize_mongo_doc(created_task)
        
        return ApiResponse(
            success=True,
            message="Task created successfully",
            data={"task": created_task}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create task error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create task"
        )


@router.put("/{task_id}")
@limiter.limit("10/minute")
async def update_task(
    request,
    task_id: str,
    task_data: TaskUpdate,
    current_user=Depends(get_admin_user)
):
    """Update task (admin only)"""
    try:
        db = get_database()
        
        # Check if task exists
        existing_task = await db.tasks.find_one({"_id": ObjectId(task_id)})
        if not existing_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # Prepare update data
        update_data = task_data.dict(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow()
        
        # Handle assigned_to update
        if "assigned_to" in update_data:
            update_data["assigned_to"] = ObjectId(update_data["assigned_to"])
            
            # Check if new assigned user exists
            assigned_user = await db.users.find_one({"_id": update_data["assigned_to"]})
            if not assigned_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Assigned user not found"
                )
        
        # Update task
        result = await db.tasks.update_one(
            {"_id": ObjectId(task_id)},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No changes made"
            )
        
        log_database_operation(
            logger, "update", "tasks", task_id,
            user_id=current_user.id,
            duration=0.1
        )
        
        # Get updated task
        updated_task = await db.tasks.find_one({"_id": ObjectId(task_id)})
        updated_task = serialize_mongo_doc(updated_task)
        
        return ApiResponse(
            success=True,
            message="Task updated successfully",
            data={"task": updated_task}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update task error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update task"
        )


@router.put("/{task_id}/complete")
@limiter.limit("10/minute")
async def mark_task_complete(
    request,
    task_id: str,
    actual_hours: Optional[float] = None,
    current_user=Depends(get_current_user)
):
    """Mark task as complete (assigned user or admin)"""
    try:
        db = get_database()
        
        # Check if task exists
        task = await db.tasks.find_one({"_id": ObjectId(task_id)})
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # Check permissions
        if (current_user.role != "admin" and 
            str(task["assigned_to"]) != current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Update task
        update_data = {
            "status": TaskStatus.COMPLETED,
            "completed_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        if actual_hours is not None:
            update_data["actual_hours"] = actual_hours
        
        result = await db.tasks.update_one(
            {"_id": ObjectId(task_id)},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update task"
            )
        
        log_database_operation(
            logger, "update", "tasks", task_id,
            user_id=current_user.id,
            duration=0.1
        )
        
        return ApiResponse(
            success=True,
            message="Task marked as completed",
            data={}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Complete task error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete task"
        )


@router.delete("/{task_id}")
@limiter.limit("5/minute")
async def delete_task(
    request,
    task_id: str,
    current_user=Depends(get_admin_user)
):
    """Delete task (admin only)"""
    try:
        db = get_database()
        
        # Check if task exists
        task = await db.tasks.find_one({"_id": ObjectId(task_id)})
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # Delete task
        result = await db.tasks.delete_one({"_id": ObjectId(task_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete task"
            )
        
        log_database_operation(
            logger, "delete", "tasks", task_id,
            user_id=current_user.id,
            duration=0.1
        )
        
        return ApiResponse(
            success=True,
            message="Task deleted successfully",
            data={}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete task error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete task"
        )


@router.get("/stats/overview")
@limiter.limit("10/minute")
async def get_task_stats(
    request,
    current_user=Depends(get_current_user)
):
    """Get task statistics overview"""
    try:
        db = get_database()
        
        # Build query based on user role
        query = {}
        if current_user.role != "admin":
            query["assigned_to"] = ObjectId(current_user.id)
        
        # Get status counts
        status_pipeline = [
            {"$match": query},
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }}
        ]
        
        status_counts = await db.tasks.aggregate(status_pipeline).to_list(length=None)
        
        # Get priority counts
        priority_pipeline = [
            {"$match": query},
            {"$group": {
                "_id": "$priority",
                "count": {"$sum": 1}
            }}
        ]
        
        priority_counts = await db.tasks.aggregate(priority_pipeline).to_list(length=None)
        
        # Get overdue tasks
        overdue_count = await db.tasks.count_documents({
            **query,
            "deadline": {"$lt": datetime.utcnow()},
            "status": {"$ne": TaskStatus.COMPLETED}
        })
        
        stats = {
            "by_status": {stat["_id"]: stat["count"] for stat in status_counts},
            "by_priority": {stat["_id"]: stat["count"] for stat in priority_counts},
            "overdue": overdue_count,
            "total": sum(stat["count"] for stat in status_counts)
        }
        
        return ApiResponse(
            success=True,
            message="Task statistics retrieved",
            data={"stats": stats}
        )
        
    except Exception as e:
        logger.error(f"Get task stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch task statistics"
        )