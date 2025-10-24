"""
Authentication Router for A Square Skills Academy EMS
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from slowapi import limiter
from slowapi.util import get_remote_address

from models import LoginRequest, Token, UserResponse
from dependencies import (
    get_database, verify_password, get_password_hash,
    create_access_token, create_refresh_token, verify_token,
    get_current_user, DatabaseUtils
)
from logging_config import setup_logging, log_security_event

router = APIRouter()
logger = setup_logging()
security = HTTPBearer()


class AuthResponse(BaseModel):
    """Authentication response"""
    success: bool
    message: str
    data: dict


@router.post("/login")
@limiter.limit("5/minute")
async def login(
    request: Request,
    response: Response,
    login_data: LoginRequest
):
    """User login endpoint"""
    try:
        db = get_database()
        
        # Find user by email
        user = await db.users.find_one({"email": login_data.email})
        if not user:
            log_security_event(
                logger, "login_failed", "Invalid email attempted",
                ip_address=request.client.host,
                severity="medium"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Verify password
        if not verify_password(login_data.password, user["password"]):
            log_security_event(
                logger, "login_failed", "Invalid password for user",
                user_id=str(user["_id"]),
                ip_address=request.client.host,
                severity="medium"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Check if user is active
        if not user.get("is_active", True):
            log_security_event(
                logger, "login_failed", "Inactive user attempted login",
                user_id=str(user["_id"]),
                ip_address=request.client.host,
                severity="medium"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive"
            )
        
        # Create tokens
        token_data = {
            "sub": user["email"],
            "user_id": str(user["_id"]),
            "role": user["role"],
            "name": user["name"]
        }
        
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data) if login_data.remember_me else None
        
        # Update last login
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"last_login": datetime.utcnow()}}
        )
        
        # Set cookies
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=3600  # 1 hour
        )
        
        if refresh_token:
            response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                httponly=True,
                secure=True,
                samesite="strict",
                max_age=2592000  # 30 days
            )
        
        log_security_event(
            logger, "login_success", "User logged in successfully",
            user_id=str(user["_id"]),
            ip_address=request.client.host,
            severity="low"
        )
        
        # Prepare user response (remove password)
        user_response = {
            "id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "position": user.get("position"),
            "department": user.get("department"),
            "profile_image": user.get("profile_image")
        }
        
        return AuthResponse(
            success=True,
            message="Login successful",
            data={
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": 3600,
                "user": user_response
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/logout")
@limiter.limit("10/minute")
async def logout(
    request: Request,
    response: Response,
    current_user: UserResponse = Depends(get_current_user)
):
    """User logout endpoint"""
    try:
        # Clear cookies
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        
        log_security_event(
            logger, "logout", "User logged out",
            user_id=current_user.id,
            ip_address=request.client.host,
            severity="low"
        )
        
        return AuthResponse(
            success=True,
            message="Logout successful",
            data={}
        )
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/refresh")
@limiter.limit("10/minute")
async def refresh_token(
    request: Request,
    response: Response,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Refresh access token"""
    try:
        # Verify refresh token
        payload = verify_token(credentials.credentials, "refresh")
        email = payload.get("sub")
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Check if user still exists
        db = get_database()
        user = await db.users.find_one({"email": email})
        if not user or not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Create new access token
        token_data = {
            "sub": user["email"],
            "user_id": str(user["_id"]),
            "role": user["role"],
            "name": user["name"]
        }
        
        new_access_token = create_access_token(token_data)
        
        # Set new access token cookie
        response.set_cookie(
            key="access_token",
            value=new_access_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=3600
        )
        
        return AuthResponse(
            success=True,
            message="Token refreshed successfully",
            data={
                "access_token": new_access_token,
                "token_type": "bearer",
                "expires_in": 3600
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/me")
@limiter.limit("10/minute")
async def get_current_user_info(
    request: Request,
    current_user: UserResponse = Depends(get_current_user)
):
    """Get current user information"""
    try:
        return AuthResponse(
            success=True,
            message="User information retrieved",
            data={
                "user": {
                    "id": current_user.id,
                    "name": current_user.name,
                    "email": current_user.email,
                    "role": current_user.role,
                    "position": current_user.position,
                    "department": current_user.department,
                    "profile_image": current_user.profile_image,
                    "joined_date": current_user.joined_date,
                    "last_login": current_user.last_login
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Get user info error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/change-password")
@limiter.limit("5/minute")
async def change_password(
    request: Request,
    current_password: str,
    new_password: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Change user password"""
    try:
        db = get_database()
        
        # Get current user from database
        user = await db.users.find_one({"_id": ObjectId(current_user.id)})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify current password
        if not verify_password(current_password, user["password"]):
            log_security_event(
                logger, "password_change_failed", "Invalid current password",
                user_id=current_user.id,
                ip_address=request.client.host,
                severity="medium"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Update password
        new_password_hash = get_password_hash(new_password)
        await db.users.update_one(
            {"_id": ObjectId(current_user.id)},
            {"$set": {"password": new_password_hash, "updated_at": datetime.utcnow()}}
        )
        
        log_security_event(
            logger, "password_changed", "Password changed successfully",
            user_id=current_user.id,
            ip_address=request.client.host,
            severity="low"
        )
        
        return AuthResponse(
            success=True,
            message="Password changed successfully",
            data={}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Change password error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    email: EmailStr
):
    """Initiate password reset"""
    try:
        db = get_database()
        
        # Check if user exists
        user = await db.users.find_one({"email": email})
        if not user:
            # Don't reveal if email exists or not
            return AuthResponse(
                success=True,
                message="If the email exists, a reset link has been sent",
                data={}
            )
        
        # Generate reset token (valid for 1 hour)
        reset_token = create_access_token(
            {"sub": email, "type": "reset"},
            timedelta(hours=1)
        )
        
        # TODO: Send reset email
        # For now, just log the token
        logger.info(f"Password reset token for {email}: {reset_token}")
        
        log_security_event(
            logger, "password_reset_requested", "Password reset requested",
            user_id=str(user["_id"]),
            ip_address=request.client.host,
            severity="medium"
        )
        
        return AuthResponse(
            success=True,
            message="If the email exists, a reset link has been sent",
            data={}
        )
        
    except Exception as e:
        logger.error(f"Forgot password error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/reset-password")
@limiter.limit("3/minute")
async def reset_password(
    request: Request,
    token: str,
    new_password: str
):
    """Reset password with token"""
    try:
        # Verify reset token
        payload = verify_token(token, "reset")
        email = payload.get("sub")
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token"
            )
        
        db = get_database()
        
        # Find user
        user = await db.users.find_one({"email": email})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token"
            )
        
        # Update password
        new_password_hash = get_password_hash(new_password)
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"password": new_password_hash, "updated_at": datetime.utcnow()}}
        )
        
        log_security_event(
            logger, "password_reset_success", "Password reset successfully",
            user_id=str(user["_id"]),
            ip_address=request.client.host,
            severity="low"
        )
        
        return AuthResponse(
            success=True,
            message="Password reset successfully",
            data={}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reset password error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Import ObjectId for use in routes
from bson import ObjectId