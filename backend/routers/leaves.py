"""
Leaves Router for A Square Skills Academy EMS
"""

from typing import List, Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, validator
from slowapi import limiter
from bson import ObjectId

from models import (
    Leave, LeaveCreate, LeaveUpdate, LeaveStatus,
    PaginatedResponse, ApiResponse
)
from dependencies import (
    get_database, get_current_user, get_admin_user,
    serialize_mongo_doc, serialize_mongo_docs, paginate_query
)
from logging_config import setup_logging, log_database_operation

router = APIRouter()
logger = setup_logging()


class LeaveRequest(BaseModel):
    """Leave request model"""
    leave_type: str
    from_date: date
    to_date: date
    reason: str
    
    @validator('to_date')
    def validate_dates(cls, v, values):
        if 'from_date' in values and v <= values['from_date']:
            raise ValueError('To date must be after from date')
        return v


class LeaveAction(BaseModel):
    """Leave action model"""
    status: str
    rejected_reason: Optional[str] = None


@router.get("/", response_model=PaginatedResponse)
@limiter.limit("10/minute")
async def get_leaves(
    request,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None),
    leave_type: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    current_user=Depends(get_current_user)
):
    """Get leaves with pagination and filtering"""
    try:
        db = get_database()
        
        # Build query
        query = {}
        if current_user.role != "admin":
            query["user_id"] = ObjectId(current_user.id)
        elif user_id:
            query["user_id"] = ObjectId(user_id)
        
        if status:
            query["status"] = status
        if leave_type:
            query["leave_type"] = leave_type
        
        # Date filtering
        if date_from or date_to:
            date_query = {}
            if date_from:
                date_query["$gte"] = datetime.combine(date_from, datetime.min.time())
            if date_to:
                date_query["$lte"] = datetime.combine(date_to, datetime.max.time())
            query["$or"] = [
                {"from_date": date_query},
                {"to_date": date_query}
            ]
        
        # Get total count
        total = await db.leaves.count_documents(query)
        
        # Get paginated results with user details
        pipeline = [
            {"$match": query},
            {"$sort": {"created_at": -1}},
            {"$skip": (page - 1) * limit},
            {"$limit": limit},
            {
                "$lookup": {
                    "from": "users",
                    "localField": "user_id",
                    "foreignField": "_id",
                    "as": "user"
                }
            },
            {
                "$lookup": {
                    "from": "users",
                    "localField": "approved_by",
                    "foreignField": "_id",
                    "as": "approver"
                }
            },
            {
                "$project": {
                    "leave_type": 1,
                    "from_date": 1,
                    "to_date": 1,
                    "reason": 1,
                    "status": 1,
                    "approved_at": 1,
                    "rejected_reason": 1,
                    "days_requested": 1,
                    "created_at": 1,
                    "updated_at": 1,
                    "user": {"$arrayElemAt": ["$user", 0]},
                    "approved_by": {"$arrayElemAt": ["$approver", 0]}
                }
            }
        ]
        
        leaves = await db.leaves.aggregate(pipeline).to_list(length=limit)
        leaves = serialize_mongo_docs(leaves)
        
        # Clean up user data
        for leave in leaves:
            if leave.get("user"):
                leave["user"].pop("password", None)
                leave["user"]["id"] = str(leave["user"].pop("_id"))
            if leave.get("approved_by"):
                leave["approved_by"].pop("password", None)
                leave["approved_by"]["id"] = str(leave["approved_by"].pop("_id"))
        
        total_pages = (total + limit - 1) // limit
        
        log_database_operation(
            logger, "read", "leaves",
            user_id=current_user.id,
            duration=0.1
        )
        
        return PaginatedResponse(
            items=leaves,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )
        
    except Exception as e:
        logger.error(f"Get leaves error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch leaves"
        )


@router.get("/{leave_id}")
@limiter.limit("10/minute")
async def get_leave(
    request,
    leave_id: str,
    current_user=Depends(get_current_user)
):
    """Get leave by ID"""
    try:
        db = get_database()
        
        # Get leave with user details
        pipeline = [
            {"$match": {"_id": ObjectId(leave_id)}},
            {
                "$lookup": {
                    "from": "users",
                    "localField": "user_id",
                    "foreignField": "_id",
                    "as": "user"
                }
            },
            {
                "$lookup": {
                    "from": "users",
                    "localField": "approved_by",
                    "foreignField": "_id",
                    "as": "approver"
                }
            },
            {
                "$project": {
                    "leave_type": 1,
                    "from_date": 1,
                    "to_date": 1,
                    "reason": 1,
                    "status": 1,
                    "approved_at": 1,
                    "rejected_reason": 1,
                    "days_requested": 1,
                    "created_at": 1,
                    "updated_at": 1,
                    "user": {"$arrayElemAt": ["$user", 0]},
                    "approved_by": {"$arrayElemAt": ["$approver", 0]}
                }
            }
        ]
        
        leave_result = await db.leaves.aggregate(pipeline).to_list(length=1)
        if not leave_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Leave not found"
            )
        
        leave = leave_result[0]
        
        # Check permissions
        if (current_user.role != "admin" and 
            str(leave["user"]["_id"]) != current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        leave = serialize_mongo_doc(leave)
        
        # Clean up user data
        if leave.get("user"):
            leave["user"].pop("password", None)
            leave["user"]["id"] = str(leave["user"].pop("_id"))
        if leave.get("approved_by"):
            leave["approved_by"].pop("password", None)
            leave["approved_by"]["id"] = str(leave["approved_by"].pop("_id"))
        
        log_database_operation(
            logger, "read", "leaves", leave_id,
            user_id=current_user.id,
            duration=0.05
        )
        
        return ApiResponse(
            success=True,
            message="Leave retrieved",
            data={"leave": leave}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get leave error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch leave"
        )


@router.post("/")
@limiter.limit("5/minute")
async def create_leave(
    request,
    leave_data: LeaveRequest,
    current_user=Depends(get_current_user)
):
    """Apply for leave"""
    try:
        db = get_database()
        
        # Check for overlapping leaves
        overlapping_leave = await db.leaves.find_one({
            "user_id": ObjectId(current_user.id),
            "status": {"$in": [LeaveStatus.PENDING, LeaveStatus.APPROVED]},
            "$or": [
                {
                    "from_date": {"$lte": datetime.combine(leave_data.to_date, datetime.max.time())},
                    "to_date": {"$gte": datetime.combine(leave_data.from_date, datetime.min.time())}
                }
            ]
        })
        
        if overlapping_leave:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Leave request overlaps with existing leave"
            )
        
        # Calculate days requested
        from_datetime = datetime.combine(leave_data.from_date, datetime.min.time())
        to_datetime = datetime.combine(leave_data.to_date, datetime.max.time())
        days_requested = (to_datetime - from_datetime).days + 1
        
        # Prepare leave data
        leave_dict = leave_data.dict()
        leave_dict["user_id"] = ObjectId(current_user.id)
        leave_dict["days_requested"] = days_requested
        leave_dict["status"] = LeaveStatus.PENDING
        leave_dict["created_at"] = datetime.utcnow()
        leave_dict["updated_at"] = datetime.utcnow()
        leave_dict["from_date"] = from_datetime
        leave_dict["to_date"] = to_datetime
        
        # Insert leave
        result = await db.leaves.insert_one(leave_dict)
        leave_id = str(result.inserted_id)
        
        log_database_operation(
            logger, "create", "leaves", leave_id,
            user_id=current_user.id,
            duration=0.1
        )
        
        # Get created leave
        created_leave = await db.leaves.find_one({"_id": result.inserted_id})
        created_leave = serialize_mongo_doc(created_leave)
        
        return ApiResponse(
            success=True,
            message="Leave application submitted successfully",
            data={"leave": created_leave}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create leave error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create leave"
        )


@router.put("/{leave_id}/approve")
@limiter.limit("5/minute")
async def approve_leave(
    request,
    leave_id: str,
    current_user=Depends(get_admin_user)
):
    """Approve leave (admin only)"""
    try:
        db = get_database()
        
        # Check if leave exists
        leave = await db.leaves.find_one({"_id": ObjectId(leave_id)})
        if not leave:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Leave not found"
            )
        
        # Check if already processed
        if leave["status"] != LeaveStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Leave has already been processed"
            )
        
        # Update leave
        update_data = {
            "status": LeaveStatus.APPROVED,
            "approved_by": ObjectId(current_user.id),
            "approved_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await db.leaves.update_one(
            {"_id": ObjectId(leave_id)},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to approve leave"
            )
        
        log_database_operation(
            logger, "update", "leaves", leave_id,
            user_id=current_user.id,
            duration=0.1
        )
        
        return ApiResponse(
            success=True,
            message="Leave approved successfully",
            data={}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Approve leave error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to approve leave"
        )


@router.put("/{leave_id}/reject")
@limiter.limit("5/minute")
async def reject_leave(
    request,
    leave_id: str,
    action_data: LeaveAction,
    current_user=Depends(get_admin_user)
):
    """Reject leave (admin only)"""
    try:
        db = get_database()
        
        # Check if leave exists
        leave = await db.leaves.find_one({"_id": ObjectId(leave_id)})
        if not leave:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Leave not found"
            )
        
        # Check if already processed
        if leave["status"] != LeaveStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Leave has already been processed"
            )
        
        # Update leave
        update_data = {
            "status": LeaveStatus.REJECTED,
            "rejected_reason": action_data.rejected_reason,
            "approved_by": ObjectId(current_user.id),
            "approved_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await db.leaves.update_one(
            {"_id": ObjectId(leave_id)},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to reject leave"
            )
        
        log_database_operation(
            logger, "update", "leaves", leave_id,
            user_id=current_user.id,
            duration=0.1
        )
        
        return ApiResponse(
            success=True,
            message="Leave rejected successfully",
            data={}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reject leave error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reject leave"
        )


@router.delete("/{leave_id}")
@limiter.limit("5/minute")
async def delete_leave(
    request,
    leave_id: str,
    current_user=Depends(get_current_user)
):
    """Delete leave (only if pending and own leave)"""
    try:
        db = get_database()
        
        # Check if leave exists
        leave = await db.leaves.find_one({"_id": ObjectId(leave_id)})
        if not leave:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Leave not found"
            )
        
        # Check permissions
        if (current_user.role != "admin" and 
            str(leave["user_id"]) != current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Check if can delete (only pending leaves can be deleted by owner)
        if (str(leave["user_id"]) == current_user.id and 
            leave["status"] != LeaveStatus.PENDING):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only pending leaves can be deleted"
            )
        
        # Delete leave
        result = await db.leaves.delete_one({"_id": ObjectId(leave_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete leave"
            )
        
        log_database_operation(
            logger, "delete", "leaves", leave_id,
            user_id=current_user.id,
            duration=0.1
        )
        
        return ApiResponse(
            success=True,
            message="Leave deleted successfully",
            data={}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete leave error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete leave"
        )


@router.get("/stats/overview")
@limiter.limit("10/minute")
async def get_leave_stats(
    request,
    current_user=Depends(get_current_user)
):
    """Get leave statistics overview"""
    try:
        db = get_database()
        
        # Build query based on user role
        query = {}
        if current_user.role != "admin":
            query["user_id"] = ObjectId(current_user.id)
        
        # Get current year
        current_year = datetime.utcnow().year
        year_query = {**query}
        year_query["$expr"] = {"$eq": [{"$year": "$from_date"}, current_year]}
        
        # Get statistics by status
        status_pipeline = [
            {"$match": year_query},
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1},
                "total_days": {"$sum": "$days_requested"}
            }}
        ]
        
        status_stats = await db.leaves.aggregate(status_pipeline).to_list(length=None)
        
        # Get statistics by type
        type_pipeline = [
            {"$match": year_query},
            {"$group": {
                "_id": "$leave_type",
                "count": {"$sum": 1},
                "total_days": {"$sum": "$days_requested"}
            }}
        ]
        
        type_stats = await db.leaves.aggregate(type_pipeline).to_list(length=None)
        
        # Calculate total approved days
        total_approved_days = sum(
            stat["total_days"] for stat in status_stats 
            if stat["_id"] == LeaveStatus.APPROVED
        )
        
        stats = {
            "by_status": {
                stat["_id"]: {
                    "count": stat["count"],
                    "total_days": stat["total_days"]
                } for stat in status_stats
            },
            "by_type": {
                stat["_id"]: {
                    "count": stat["count"],
                    "total_days": stat["total_days"]
                } for stat in type_stats
            },
            "total_approved_days": total_approved_days
        }
        
        return ApiResponse(
            success=True,
            message="Leave statistics retrieved",
            data={"stats": stats}
        )
        
    except Exception as e:
        logger.error(f"Get leave stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch leave statistics"
        )


@router.get("/balance/{user_id}")
@limiter.limit("10/minute")
async def get_leave_balance(
    request,
    user_id: str,
    current_user=Depends(get_current_user)
):
    """Get leave balance for a user"""
    try:
        # Check permissions
        if current_user.role != "admin" and current_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        db = get_database()
        
        # Get current year
        current_year = datetime.utcnow().year
        
        # Get approved leaves for current year
        approved_leaves = await db.leaves.aggregate([
            {
                "$match": {
                    "user_id": ObjectId(user_id),
                    "status": LeaveStatus.APPROVED,
                    "$expr": {"$eq": [{"$year": "$from_date"}, current_year]}
                }
            },
            {
                "$group": {
                    "_id": "$leave_type",
                    "used_days": {"$sum": "$days_requested"}
                }
            }
        ]).to_list(length=None)
        
        # Define leave quotas (this could be configurable)
        leave_quotas = {
            "annual": 21,
            "sick": 10,
            "personal": 5,
            "maternity": 90,
            "paternity": 7,
            "other": 0
        }
        
        # Calculate balances
        balances = {}
        for leave_type, total_quota in leave_quotas.items():
            used_days = next(
                (leave["used_days"] for leave in approved_leaves 
                 if leave["_id"] == leave_type), 0
            )
            balances[leave_type] = {
                "total": total_quota,
                "used": used_days,
                "remaining": max(0, total_quota - used_days)
            }
        
        return ApiResponse(
            success=True,
            message="Leave balance retrieved",
            data={"balances": balances}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get leave balance error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch leave balance"
        )