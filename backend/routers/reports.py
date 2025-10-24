"""
Reports Router for A Square Skills Academy EMS
"""

from typing import List, Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from slowapi import limiter
from bson import ObjectId

from models import (
    ReportRequest, ReportResponse, ReportType,
    ApiResponse
)
from dependencies import (
    get_database, get_admin_user, get_current_user,
    serialize_mongo_docs
)
from logging_config import setup_logging, log_database_operation
from services.report_service import ReportService

router = APIRouter()
logger = setup_logging()


@router.post("/generate")
@limiter.limit("5/minute")
async def generate_report(
    request,
    report_request: ReportRequest,
    current_user=Depends(get_current_user)
):
    """Generate report"""
    try:
        # Check permissions
        if current_user.role != "admin" and report_request.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        report_service = ReportService()
        
        # Generate report
        report_data = await report_service.generate_report(
            report_type=report_request.report_type,
            date_from=report_request.date_from,
            date_to=report_request.date_to,
            user_id=report_request.user_id,
            department=report_request.department,
            current_user=current_user
        )
        
        log_database_operation(
            logger, "create", "reports",
            user_id=current_user.id,
            duration=0.5
        )
        
        return ApiResponse(
            success=True,
            message="Report generated successfully",
            data={"report": report_data}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Generate report error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate report"
        )


@router.get("/export")
@limiter.limit("3/minute")
async def export_report(
    request,
    report_type: ReportType = Query(...),
    format: str = Query("pdf"),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    user_id: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    current_user=Depends(get_current_user)
):
    """Export report in specified format"""
    try:
        # Check permissions
        if current_user.role != "admin" and user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        report_service = ReportService()
        
        # Generate report data
        report_data = await report_service.generate_report(
            report_type=report_type,
            date_from=date_from,
            date_to=date_to,
            user_id=user_id,
            department=department,
            current_user=current_user
        )
        
        # Export based on format
        if format == "pdf":
            pdf_content = await report_service.export_to_pdf(report_data)
            filename = f"report_{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            media_type = "application/pdf"
            
        elif format == "csv":
            csv_content = await report_service.export_to_csv(report_data)
            filename = f"report_{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            media_type = "text/csv"
            
        elif format == "json":
            json_content = await report_service.export_to_json(report_data)
            filename = f"report_{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            media_type = "application/json"
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported format"
            )
        
        log_database_operation(
            logger, "export", "reports",
            user_id=current_user.id,
            duration=1.0
        )
        
        return StreamingResponse(
            content=pdf_content if format == "pdf" else 
                   csv_content if format == "csv" else json_content,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export report error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export report"
        )


@router.get("/templates")
@limiter.limit("10/minute")
async def get_report_templates(
    request,
    current_user=Depends(get_current_user)
):
    """Get available report templates"""
    try:
        templates = [
            {
                "type": ReportType.EMPLOYEE_SUMMARY,
                "name": "Employee Summary",
                "description": "Summary of all employees with basic information",
                "parameters": ["department", "status", "date_range"]
            },
            {
                "type": ReportType.ATTENDANCE_REPORT,
                "name": "Attendance Report",
                "description": "Detailed attendance records and statistics",
                "parameters": ["user_id", "date_range", "department"]
            },
            {
                "type": ReportType.TASK_REPORT,
                "name": "Task Report",
                "description": "Task completion and performance metrics",
                "parameters": ["user_id", "date_range", "status", "priority"]
            },
            {
                "type": ReportType.LEAVE_REPORT,
                "name": "Leave Report",
                "description": "Leave applications and balance summary",
                "parameters": ["user_id", "date_range", "leave_type", "status"]
            },
            {
                "type": ReportType.PERFORMANCE_REPORT,
                "name": "Performance Report",
                "description": "Comprehensive performance analysis",
                "parameters": ["user_id", "date_range", "department"]
            }
        ]
        
        return ApiResponse(
            success=True,
            message="Report templates retrieved",
            data={"templates": templates}
        )
        
    except Exception as e:
        logger.error(f"Get report templates error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch report templates"
        )


@router.get("/dashboard/summary")
@limiter.limit("10/minute")
async def get_dashboard_summary(
    request,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    current_user=Depends(get_current_user)
):
    """Get dashboard summary data"""
    try:
        db = get_database()
        
        # Build date query
        date_query = {}
        if date_from:
            date_query["$gte"] = datetime.combine(date_from, datetime.min.time())
        if date_to:
            date_query["$lte"] = datetime.combine(date_to, datetime.max.time())
        
        # Get summary data
        summary_data = {}
        
        # Employee count
        employee_query = {}
        if current_user.role != "admin":
            employee_query["_id"] = ObjectId(current_user.id)
        
        summary_data["total_employees"] = await db.users.count_documents(employee_query)
        
        # Active employees (present today)
        today = datetime.utcnow().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        
        attendance_query = {
            "date": {"$gte": today_start, "$lte": today_end}
        }
        if current_user.role != "admin":
            attendance_query["user_id"] = ObjectId(current_user.id)
        
        summary_data["present_today"] = await db.attendance.count_documents(attendance_query)
        
        # Task statistics
        task_query = {}
        if current_user.role != "admin":
            task_query["assigned_to"] = ObjectId(current_user.id)
        
        task_stats = await db.tasks.aggregate([
            {"$match": task_query},
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }}
        ]).to_list(length=None)
        
        summary_data["tasks"] = {stat["_id"]: stat["count"] for stat in task_stats}
        
        # Leave statistics
        leave_query = {}
        if current_user.role != "admin":
            leave_query["user_id"] = ObjectId(current_user.id)
        
        current_month = datetime.utcnow().month
        leave_query["$expr"] = {"$eq": [{"$month": "$from_date"}, current_month]}
        
        leave_stats = await db.leaves.aggregate([
            {"$match": leave_query},
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }}
        ]).to_list(length=None)
        
        summary_data["leaves"] = {stat["_id"]: stat["count"] for stat in leave_stats}
        
        return ApiResponse(
            success=True,
            message="Dashboard summary retrieved",
            data={"summary": summary_data}
        )
        
    except Exception as e:
        logger.error(f"Get dashboard summary error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch dashboard summary"
        )


@router.get("/activity/recent")
@limiter.limit("10/minute")
async def get_recent_activity(
    request,
    limit: int = Query(10, ge=1, le=50),
    current_user=Depends(get_current_user)
):
    """Get recent system activity"""
    try:
        db = get_database()
        
        # Get recent activity from different collections
        activities = []
        
        # Recent tasks
        task_query = {}
        if current_user.role != "admin":
            task_query["assigned_to"] = ObjectId(current_user.id)
        
        recent_tasks = await db.tasks.find(task_query).sort("updated_at", -1).limit(limit).to_list(length=None)
        for task in recent_tasks:
            activities.append({
                "type": "task",
                "description": f"Task '{task['title']}' updated",
                "timestamp": task["updated_at"],
                "user_initials": "SYS",
                "action_type": "UPDATE"
            })
        
        # Recent leaves
        leave_query = {}
        if current_user.role != "admin":
            leave_query["user_id"] = ObjectId(current_user.id)
        
        recent_leaves = await db.leaves.find(leave_query).sort("updated_at", -1).limit(limit).to_list(length=None)
        for leave in recent_leaves:
            activities.append({
                "type": "leave",
                "description": f"Leave request updated - {leave['status']}",
                "timestamp": leave["updated_at"],
                "user_initials": "SYS",
                "action_type": "UPDATE"
            })
        
        # Sort by timestamp and limit
        activities.sort(key=lambda x: x["timestamp"], reverse=True)
        activities = activities[:limit]
        
        return ApiResponse(
            success=True,
            message="Recent activity retrieved",
            data={"activities": activities}
        )
        
    except Exception as e:
        logger.error(f"Get recent activity error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch recent activity"
        )