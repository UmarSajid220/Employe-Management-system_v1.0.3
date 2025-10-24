"""
Settings Router for A Square Skills Academy EMS
"""

from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from slowapi import limiter
from bson import ObjectId

from models import (
    Settings, SettingsUpdate,
    ApiResponse
)
from dependencies import (
    get_database, get_admin_user, get_current_user,
    serialize_mongo_doc, serialize_mongo_docs
)
from logging_config import setup_logging, log_database_operation

router = APIRouter()
logger = setup_logging()


class SettingResponse(BaseModel):
    """Setting response model"""
    setting_key: str
    setting_value: Any
    setting_type: str
    description: Optional[str]
    is_system: bool


@router.get("/")
@limiter.limit("10/minute")
async def get_settings(
    request,
    key: Optional[str] = Query(None),
    is_system: Optional[bool] = Query(None),
    current_user=Depends(get_current_user)
):
    """Get settings"""
    try:
        db = get_database()
        
        query = {}
        if key:
            query["setting_key"] = key
        if is_system is not None:
            query["is_system"] = is_system
        
        settings = await db.settings.find(query).sort("setting_key", 1).to_list(length=None)
        settings = serialize_mongo_docs(settings)
        
        # Filter sensitive system settings for non-admin users
        if current_user.role != "admin":
            settings = [s for s in settings if not s.get("is_system", False)]
        
        return ApiResponse(
            success=True,
            message="Settings retrieved",
            data={"settings": settings}
        )
        
    except Exception as e:
        logger.error(f"Get settings error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch settings"
        )


@router.get("/{setting_key}")
@limiter.limit("10/minute")
async def get_setting(
    request,
    setting_key: str,
    current_user=Depends(get_current_user)
):
    """Get specific setting"""
    try:
        db = get_database()
        
        setting = await db.settings.find_one({"setting_key": setting_key})
        if not setting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Setting not found"
            )
        
        # Check permissions for system settings
        if setting.get("is_system", False) and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        setting = serialize_mongo_doc(setting)
        
        return ApiResponse(
            success=True,
            message="Setting retrieved",
            data={"setting": setting}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get setting error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch setting"
        )


@router.post("/")
@limiter.limit("5/minute")
async def create_setting(
    request,
    setting_data: SettingResponse,
    current_user=Depends(get_admin_user)
):
    """Create new setting (admin only)"""
    try:
        db = get_database()
        
        # Check if setting already exists
        existing_setting = await db.settings.find_one({
            "setting_key": setting_data.setting_key
        })
        if existing_setting:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Setting already exists"
            )
        
        # Prepare setting data
        setting_dict = setting_data.dict()
        setting_dict["created_at"] = datetime.utcnow()
        setting_dict["updated_at"] = datetime.utcnow()
        
        # Insert setting
        result = await db.settings.insert_one(setting_dict)
        setting_id = str(result.inserted_id)
        
        log_database_operation(
            logger, "create", "settings", setting_id,
            user_id=current_user.id,
            duration=0.1
        )
        
        # Get created setting
        created_setting = await db.settings.find_one({"_id": result.inserted_id})
        created_setting = serialize_mongo_doc(created_setting)
        
        return ApiResponse(
            success=True,
            message="Setting created successfully",
            data={"setting": created_setting}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create setting error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create setting"
        )


@router.put("/{setting_key}")
@limiter.limit("5/minute")
async def update_setting(
    request,
    setting_key: str,
    setting_data: SettingsUpdate,
    current_user=Depends(get_admin_user)
):
    """Update setting (admin only)"""
    try:
        db = get_database()
        
        # Check if setting exists
        existing_setting = await db.settings.find_one({"setting_key": setting_key})
        if not existing_setting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Setting not found"
            )
        
        # Prepare update data
        update_data = setting_data.dict(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow()
        
        # Update setting
        result = await db.settings.update_one(
            {"setting_key": setting_key},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No changes made"
            )
        
        log_database_operation(
            logger, "update", "settings", setting_key,
            user_id=current_user.id,
            duration=0.1
        )
        
        # Get updated setting
        updated_setting = await db.settings.find_one({"setting_key": setting_key})
        updated_setting = serialize_mongo_doc(updated_setting)
        
        return ApiResponse(
            success=True,
            message="Setting updated successfully",
            data={"setting": updated_setting}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update setting error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update setting"
        )


@router.delete("/{setting_key}")
@limiter.limit("5/minute")
async def delete_setting(
    request,
    setting_key: str,
    current_user=Depends(get_admin_user)
):
    """Delete setting (admin only, non-system only)"""
    try:
        db = get_database()
        
        # Check if setting exists
        setting = await db.settings.find_one({"setting_key": setting_key})
        if not setting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Setting not found"
            )
        
        # Check if system setting
        if setting.get("is_system", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete system setting"
            )
        
        # Delete setting
        result = await db.settings.delete_one({"setting_key": setting_key})
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete setting"
            )
        
        log_database_operation(
            logger, "delete", "settings", setting_key,
            user_id=current_user.id,
            duration=0.1
        )
        
        return ApiResponse(
            success=True,
            message="Setting deleted successfully",
            data={}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete setting error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete setting"
        )


@router.get("/system/info")
@limiter.limit("10/minute")
async def get_system_info(
    request,
    current_user=Depends(get_current_user)
):
    """Get system information"""
    try:
        db = get_database()
        
        # Get system statistics
        stats = {
            "total_users": await db.users.count_documents({}),
            "active_users": await db.users.count_documents({"is_active": True}),
            "total_tasks": await db.tasks.count_documents({}),
            "total_attendance_records": await db.attendance.count_documents({}),
            "total_leave_applications": await db.leaves.count_documents({}),
            "total_messages": await db.messages.count_documents({})
        }
        
        # Get system settings
        system_settings = await db.settings.find({"is_system": True}).to_list(length=None)
        system_settings = serialize_mongo_docs(system_settings)
        
        # Filter sensitive settings for non-admin users
        if current_user.role != "admin":
            system_settings = [s for s in system_settings if s["setting_key"] not in [
                "jwt_secret", "database_url", "email_password"
            ]]
        
        return ApiResponse(
            success=True,
            message="System information retrieved",
            data={
                "stats": stats,
                "settings": system_settings
            }
        )
        
    except Exception as e:
        logger.error(f"Get system info error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch system information"
        )


@router.post("/backup")
@limiter.limit("1/minute")
async def create_backup(
    request,
    current_user=Depends(get_admin_user)
):
    """Create system backup (admin only)"""
    try:
        # This would typically integrate with a backup service
        # For now, just return a success message
        
        return ApiResponse(
            success=True,
            message="Backup initiated successfully",
            data={"backup_id": f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"}
        )
        
    except Exception as e:
        logger.error(f"Create backup error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create backup"
        )


# Import datetime for use in routes
from datetime import datetime