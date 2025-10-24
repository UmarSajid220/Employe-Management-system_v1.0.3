"""
Employees Router for A Square Skills Academy EMS
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import EmailStr
from slowapi import limiter
from bson import ObjectId

from models import (
    User, UserCreate, UserUpdate, UserResponse, 
    PaginatedResponse, ApiResponse
)
from dependencies import (
    get_database, get_admin_user, get_current_user,
    get_password_hash, paginate_query, serialize_mongo_doc,
    serialize_mongo_docs
)
from logging_config import setup_logging, log_database_operation

router = APIRouter()
logger = setup_logging()


@router.get("/", response_model=PaginatedResponse)
@limiter.limit("10/minute")
async def get_employees(
    request,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(get_admin_user)
):
    """Get all employees with pagination and filtering"""
    try:
        db = get_database()
        
        # Build query
        query = {}
        if search:
            query["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"email": {"$regex": search, "$options": "i"}},
                {"position": {"$regex": search, "$options": "i"}}
            ]
        if role:
            query["role"] = role
        if department:
            query["department"] = department
        if is_active is not None:
            query["is_active"] = is_active
        
        # Get total count
        total = await db.users.count_documents(query)
        
        # Get paginated results
        cursor = db.users.find(query).sort("created_at", -1)
        cursor = paginate_query(cursor, page, limit)
        employees = await cursor.to_list(length=limit)
        
        # Serialize documents
        employees = serialize_mongo_docs(employees)
        
        # Remove passwords
        for emp in employees:
            emp.pop("password", None)
        
        total_pages = (total + limit - 1) // limit
        
        log_database_operation(
            logger, "read", "users", 
            user_id=current_user.id,
            duration=0.1  # Mock duration
        )
        
        return PaginatedResponse(
            items=employees,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )
        
    except Exception as e:
        logger.error(f"Get employees error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch employees"
        )


@router.get("/search")
@limiter.limit("10/minute")
async def search_employees(
    request,
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user)
):
    """Search employees"""
    try:
        db = get_database()
        
        query = {
            "$or": [
                {"name": {"$regex": q, "$options": "i"}},
                {"email": {"$regex": q, "$options": "i"}},
                {"position": {"$regex": q, "$options": "i"}}
            ],
            "is_active": True
        }
        
        cursor = db.users.find(query).limit(limit)
        employees = await cursor.to_list(length=limit)
        employees = serialize_mongo_docs(employees)
        
        # Remove sensitive data
        for emp in employees:
            emp.pop("password", None)
            emp.pop("salary", None)
        
        return ApiResponse(
            success=True,
            message="Employees found",
            data={"employees": employees}
        )
        
    except Exception as e:
        logger.error(f"Search employees error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search employees"
        )


@router.get("/{employee_id}")
@limiter.limit("10/minute")
async def get_employee(
    request,
    employee_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get employee by ID"""
    try:
        db = get_database()
        
        # Check permissions
        if current_user.role != "admin" and str(current_user.id) != employee_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        employee = await db.users.find_one({"_id": ObjectId(employee_id)})
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee not found"
            )
        
        employee = serialize_mongo_doc(employee)
        employee.pop("password", None)
        
        log_database_operation(
            logger, "read", "users", employee_id,
            user_id=current_user.id,
            duration=0.05
        )
        
        return ApiResponse(
            success=True,
            message="Employee retrieved",
            data={"employee": employee}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get employee error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch employee"
        )


@router.post("/")
@limiter.limit("5/minute")
async def create_employee(
    request,
    employee_data: UserCreate,
    current_user: User = Depends(get_admin_user)
):
    """Create new employee"""
    try:
        db = get_database()
        
        # Check if email already exists
        existing_user = await db.users.find_one({"email": employee_data.email})
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Hash password
        password_hash = get_password_hash(employee_data.password)
        
        # Prepare user data
        user_data = employee_data.dict()
        user_data["password"] = password_hash
        user_data["created_at"] = datetime.utcnow()
        user_data["updated_at"] = datetime.utcnow()
        
        # Insert user
        result = await db.users.insert_one(user_data)
        user_id = str(result.inserted_id)
        
        log_database_operation(
            logger, "create", "users", user_id,
            user_id=current_user.id,
            duration=0.1
        )
        
        # Get created user
        created_user = await db.users.find_one({"_id": result.inserted_id})
        created_user = serialize_mongo_doc(created_user)
        created_user.pop("password", None)
        
        return ApiResponse(
            success=True,
            message="Employee created successfully",
            data={"employee": created_user}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create employee error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create employee"
        )


@router.put("/{employee_id}")
@limiter.limit("10/minute")
async def update_employee(
    request,
    employee_id: str,
    employee_data: UserUpdate,
    current_user: User = Depends(get_admin_user)
):
    """Update employee"""
    try:
        db = get_database()
        
        # Check if employee exists
        existing_employee = await db.users.find_one({"_id": ObjectId(employee_id)})
        if not existing_employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee not found"
            )
        
        # Prepare update data
        update_data = employee_data.dict(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow()
        
        # Update employee
        result = await db.users.update_one(
            {"_id": ObjectId(employee_id)},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No changes made"
            )
        
        log_database_operation(
            logger, "update", "users", employee_id,
            user_id=current_user.id,
            duration=0.1
        )
        
        # Get updated employee
        updated_employee = await db.users.find_one({"_id": ObjectId(employee_id)})
        updated_employee = serialize_mongo_doc(updated_employee)
        updated_employee.pop("password", None)
        
        return ApiResponse(
            success=True,
            message="Employee updated successfully",
            data={"employee": updated_employee}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update employee error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update employee"
        )


@router.delete("/{employee_id}")
@limiter.limit("5/minute")
async def delete_employee(
    request,
    employee_id: str,
    current_user: User = Depends(get_admin_user)
):
    """Delete employee"""
    try:
        db = get_database()
        
        # Check if employee exists
        employee = await db.users.find_one({"_id": ObjectId(employee_id)})
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee not found"
            )
        
        # Don't allow deleting own account
        if str(employee["_id"]) == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )
        
        # Delete employee
        result = await db.users.delete_one({"_id": ObjectId(employee_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete employee"
            )
        
        log_database_operation(
            logger, "delete", "users", employee_id,
            user_id=current_user.id,
            duration=0.1
        )
        
        return ApiResponse(
            success=True,
            message="Employee deleted successfully",
            data={}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete employee error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete employee"
        )


@router.get("/{employee_id}/stats")
@limiter.limit("10/minute")
async def get_employee_stats(
    request,
    employee_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get employee statistics"""
    try:
        # Check permissions
        if current_user.role != "admin" and str(current_user.id) != employee_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        db = get_database()
        
        # Get task statistics
        task_stats = await db.tasks.aggregate([
            {"$match": {"assigned_to": ObjectId(employee_id)}},
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }}
        ]).to_list(length=None)
        
        # Get attendance statistics for last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        attendance_stats = await db.attendance.aggregate([
            {
                "$match": {
                    "user_id": ObjectId(employee_id),
                    "date": {"$gte": thirty_days_ago}
                }
            },
            {"$group": {
                "_id": None,
                "total_days": {"$sum": 1},
                "total_hours": {"$sum": "$duration_minutes"},
                "avg_hours": {"$avg": "$duration_minutes"}
            }}
        ]).to_list(length=None)
        
        # Get leave statistics for current year
        current_year = datetime.utcnow().year
        leave_stats = await db.leaves.aggregate([
            {
                "$match": {
                    "user_id": ObjectId(employee_id),
                    "status": "approved",
                    "$expr": {"$eq": [{"$year": "$from_date"}, current_year]}
                }
            },
            {"$group": {
                "_id": "$leave_type",
                "total_days": {"$sum": "$days_requested"}
            }}
        ]).to_list(length=None)
        
        stats = {
            "tasks": {stat["_id"]: stat["count"] for stat in task_stats},
            "attendance": attendance_stats[0] if attendance_stats else {},
            "leaves": {stat["_id"]: stat["total_days"] for stat in leave_stats}
        }
        
        return ApiResponse(
            success=True,
            message="Employee statistics retrieved",
            data={"stats": stats}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get employee stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch employee statistics"
        )


# Import datetime for use in routes
from datetime import datetime, timedelta