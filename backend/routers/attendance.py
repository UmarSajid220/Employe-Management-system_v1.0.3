"""
Attendance Router for A Square Skills Academy EMS
"""

from typing import List, Optional
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from slowapi import limiter
from bson import ObjectId

from models import (
    Attendance, AttendanceCreate, AttendanceResponse,
    PaginatedResponse, ApiResponse
)
from dependencies import (
    get_database, get_current_user, get_admin_user,
    serialize_mongo_doc, serialize_mongo_docs, paginate_query
)
from logging_config import setup_logging, log_database_operation

router = APIRouter()
logger = setup_logging()


class AttendanceRequest(BaseModel):
    """Attendance request model"""
    ip_address: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None


@router.get("/", response_model=PaginatedResponse)
@limiter.limit("10/minute")
async def get_attendance(
    request,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    user_id: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    current_user=Depends(get_current_user)
):
    """Get attendance records with pagination and filtering"""
    try:
        db = get_database()
        
        # Build query based on user role
        query = {}
        if current_user.role != "admin":
            query["user_id"] = ObjectId(current_user.id)
        elif user_id:
            query["user_id"] = ObjectId(user_id)
        
        # Date filtering
        if date_from or date_to:
            date_query = {}
            if date_from:
                date_query["$gte"] = datetime.combine(date_from, datetime.min.time())
            if date_to:
                date_query["$lte"] = datetime.combine(date_to, datetime.max.time())
            query["date"] = date_query
        
        # Get total count
        total = await db.attendance.count_documents(query)
        
        # Get paginated results with user details
        pipeline = [
            {"$match": query},
            {"$sort": {"date": -1}},
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
                "$project": {
                    "date": 1,
                    "login_time": 1,
                    "logout_time": 1,
                    "duration_minutes": 1,
                    "ip_address": 1,
                    "location": 1,
                    "notes": 1,
                    "is_late": 1,
                    "is_overtime": 1,
                    "created_at": 1,
                    "updated_at": 1,
                    "user": {"$arrayElemAt": ["$user", 0]}
                }
            }
        ]
        
        attendance_records = await db.attendance.aggregate(pipeline).to_list(length=limit)
        attendance_records = serialize_mongo_docs(attendance_records)
        
        # Clean up user data
        for record in attendance_records:
            if record.get("user"):
                record["user"].pop("password", None)
                record["user"]["id"] = str(record["user"].pop("_id"))
        
        total_pages = (total + limit - 1) // limit
        
        log_database_operation(
            logger, "read", "attendance",
            user_id=current_user.id,
            duration=0.1
        )
        
        return PaginatedResponse(
            items=attendance_records,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )
        
    except Exception as e:
        logger.error(f"Get attendance error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch attendance records"
        )


@router.post("/start")
@limiter.limit("5/minute")
async def start_attendance(
    request,
    attendance_data: AttendanceRequest,
    current_user=Depends(get_current_user)
):
    """Start attendance session (login)"""
    try:
        db = get_database()
        
        # Check if already logged in today
        today = datetime.utcnow().date()
        existing_attendance = await db.attendance.find_one({
            "user_id": ObjectId(current_user.id),
            "date": datetime.combine(today, datetime.min.time())
        })
        
        if existing_attendance and not existing_attendance.get("logout_time"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already logged in today"
            )
        
        # Check office hours (assuming 9 AM to 6 PM)
        current_time = datetime.utcnow()
        office_start = current_time.replace(hour=9, minute=0, second=0, microsecond=0)
        office_end = current_time.replace(hour=18, minute=0, second=0, microsecond=0)
        
        is_late = current_time > office_start
        
        # Create attendance record
        attendance_dict = {
            "user_id": ObjectId(current_user.id),
            "date": datetime.combine(today, datetime.min.time()),
            "login_time": current_time,
            "ip_address": attendance_data.ip_address or request.client.host,
            "location": attendance_data.location,
            "notes": attendance_data.notes,
            "is_late": is_late,
            "is_overtime": False,
            "created_at": current_time,
            "updated_at": current_time
        }
        
        result = await db.attendance.insert_one(attendance_dict)
        attendance_id = str(result.inserted_id)
        
        log_database_operation(
            logger, "create", "attendance", attendance_id,
            user_id=current_user.id,
            duration=0.1
        )
        
        return ApiResponse(
            success=True,
            message="Attendance started successfully",
            data={
                "attendance_id": attendance_id,
                "login_time": current_time,
                "is_late": is_late
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Start attendance error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start attendance"
        )


@router.post("/end")
@limiter.limit("5/minute")
async def end_attendance(
    request,
    attendance_data: AttendanceRequest,
    current_user=Depends(get_current_user)
):
    """End attendance session (logout)"""
    try:
        db = get_database()
        
        # Find today's attendance record
        today = datetime.utcnow().date()
        attendance_record = await db.attendance.find_one({
            "user_id": ObjectId(current_user.id),
            "date": datetime.combine(today, datetime.min.time()),
            "logout_time": {"$exists": False}
        })
        
        if not attendance_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active attendance session found"
            )
        
        # Calculate duration
        current_time = datetime.utcnow()
        login_time = attendance_record["login_time"]
        duration_minutes = int((current_time - login_time).total_seconds() / 60)
        
        # Check overtime (assuming 8 hours = 480 minutes)
        is_overtime = duration_minutes > 480
        
        # Update attendance record
        update_data = {
            "logout_time": current_time,
            "duration_minutes": duration_minutes,
            "is_overtime": is_overtime,
            "updated_at": current_time
        }
        
        if attendance_data.notes:
            update_data["notes"] = attendance_data.notes
        
        result = await db.attendance.update_one(
            {"_id": attendance_record["_id"]},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to end attendance"
            )
        
        log_database_operation(
            logger, "update", "attendance", str(attendance_record["_id"]),
            user_id=current_user.id,
            duration=0.1
        )
        
        return ApiResponse(
            success=True,
            message="Attendance ended successfully",
            data={
                "logout_time": current_time,
                "duration_minutes": duration_minutes,
                "is_overtime": is_overtime
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"End attendance error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to end attendance"
        )


@router.get("/today/status")
@limiter.limit("10/minute")
async def get_today_attendance_status(
    request,
    current_user=Depends(get_current_user)
):
    """Get today's attendance status"""
    try:
        db = get_database()
        
        today = datetime.utcnow().date()
        attendance_record = await db.attendance.find_one({
            "user_id": ObjectId(current_user.id),
            "date": datetime.combine(today, datetime.min.time())
        })
        
        if not attendance_record:
            return ApiResponse(
                success=True,
                message="No attendance record for today",
                data={
                    "has_attended": False,
                    "is_logged_in": False
                }
            )
        
        attendance_record = serialize_mongo_doc(attendance_record)
        
        return ApiResponse(
            success=True,
            message="Attendance status retrieved",
            data={
                "has_attended": True,
                "is_logged_in": attendance_record.get("logout_time") is None,
                "login_time": attendance_record["login_time"],
                "logout_time": attendance_record.get("logout_time"),
                "duration_minutes": attendance_record.get("duration_minutes"),
                "is_late": attendance_record.get("is_late", False),
                "is_overtime": attendance_record.get("is_overtime", False)
            }
        )
        
    except Exception as e:
        logger.error(f"Get attendance status error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get attendance status"
        )


@router.get("/stats/overview")
@limiter.limit("10/minute")
async def get_attendance_stats(
    request,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    current_user=Depends(get_current_user)
):
    """Get attendance statistics"""
    try:
        db = get_database()
        
        # Build query
        query = {}
        if current_user.role != "admin":
            query["user_id"] = ObjectId(current_user.id)
        
        # Date filtering
        if date_from or date_to:
            date_query = {}
            if date_from:
                date_query["$gte"] = datetime.combine(date_from, datetime.min.time())
            if date_to:
                date_query["$lte"] = datetime.combine(date_to, datetime.max.time())
            query["date"] = date_query
        
        # Get statistics
        pipeline = [
            {"$match": query},
            {
                "$group": {
                    "_id": None,
                    "total_records": {"$sum": 1},
                    "total_hours": {"$sum": "$duration_minutes"},
                    "avg_hours": {"$avg": "$duration_minutes"},
                    "late_days": {
                        "$sum": {"$cond": ["$is_late", 1, 0]}
                    },
                    "overtime_days": {
                        "$sum": {"$cond": ["$is_overtime", 1, 0]}
                    }
                }
            }
        ]
        
        stats_result = await db.attendance.aggregate(pipeline).to_list(length=1)
        
        if stats_result:
            stats = stats_result[0]
            stats["total_hours"] = stats.get("total_hours", 0) / 60  # Convert to hours
            stats["avg_hours"] = stats.get("avg_hours", 0) / 60 if stats.get("avg_hours") else 0
        else:
            stats = {
                "total_records": 0,
                "total_hours": 0,
                "avg_hours": 0,
                "late_days": 0,
                "overtime_days": 0
            }
        
        return ApiResponse(
            success=True,
            message="Attendance statistics retrieved",
            data={"stats": stats}
        )
        
    except Exception as e:
        logger.error(f"Get attendance stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch attendance statistics"
        )


@router.get("/calendar/{year}/{month}")
@limiter.limit("10/minute")
async def get_monthly_attendance(
    request,
    year: int,
    month: int,
    user_id: Optional[str] = Query(None),
    current_user=Depends(get_current_user)
):
    """Get monthly attendance calendar"""
    try:
        db = get_database()
        
        # Check permissions
        if current_user.role != "admin" and user_id and user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Build query
        target_user_id = ObjectId(user_id) if user_id else ObjectId(current_user.id)
        
        # Get attendance for the month
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(seconds=1)
        
        query = {
            "user_id": target_user_id,
            "date": {"$gte": start_date, "$lte": end_date}
        }
        
        attendance_records = await db.attendance.find(query).sort("date", 1).to_list(length=None)
        attendance_records = serialize_mongo_docs(attendance_records)
        
        # Create calendar data
        calendar_data = {}
        for record in attendance_records:
            day = record["date"].day
            calendar_data[day] = {
                "present": True,
                "login_time": record["login_time"],
                "logout_time": record.get("logout_time"),
                "duration_minutes": record.get("duration_minutes"),
                "is_late": record.get("is_late", False),
                "is_overtime": record.get("is_overtime", False)
            }
        
        return ApiResponse(
            success=True,
            message="Monthly attendance retrieved",
            data={
                "calendar": calendar_data,
                "year": year,
                "month": month
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get monthly attendance error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch monthly attendance"
        )


# Import datetime for use in routes
from datetime import datetime, date, timedelta