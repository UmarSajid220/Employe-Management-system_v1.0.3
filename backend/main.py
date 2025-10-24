"""
A Square Skills Academy - Employee Management System
FastAPI Backend Application
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uvicorn

# Import routers
from routers import auth, employees, tasks, attendance, leaves, messages, reports, settings
from dependencies import get_current_user
from models import User
from logging_config import setup_logging

# Setup logging
logger = setup_logging()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Environment configuration
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:8000").split(",")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting A Square Skills Academy EMS Backend")
    
    # Initialize database connection
    from dependencies import init_database
    await init_database()
    
    # Seed initial data if needed
    from scripts.seed import seed_initial_data
    await seed_initial_data()
    
    logger.info("Backend startup complete")
    yield
    
    # Shutdown
    logger.info("Shutting down backend")

# Create FastAPI application
app = FastAPI(
    title="A Square Skills Academy EMS",
    description="Employee Management System API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(employees.router, prefix="/api/v1/employees", tags=["Employees"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["Tasks"])
app.include_router(attendance.router, prefix="/api/v1/attendance", tags=["Attendance"])
app.include_router(leaves.router, prefix="/api/v1/leaves", tags=["Leaves"])
app.include_router(messages.router, prefix="/api/v1/messages", tags=["Messages"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
app.include_router(settings.router, prefix="/api/v1/settings", tags=["Settings"])

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "A Square Skills Academy EMS API",
        "version": "1.0.0",
        "docs": "/api/docs"
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "ems-backend"}

# Protected endpoint example
@app.get("/api/v1/me")
@limiter.limit("10/minute")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user

# Dashboard stats endpoint
@app.get("/api/v1/dashboard/stats")
@limiter.limit("10/minute")
async def get_dashboard_stats(current_user: User = Depends(get_current_user)):
    """Get dashboard statistics"""
    try:
        from services.dashboard_service import DashboardService
        service = DashboardService()
        stats = await service.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to load dashboard stats")

# Recent activity endpoint
@app.get("/api/v1/dashboard/activity")
@limiter.limit("10/minute")
async def get_recent_activity(
    limit: int = 10,
    current_user: User = Depends(get_current_user)
):
    """Get recent system activity"""
    try:
        from services.dashboard_service import DashboardService
        service = DashboardService()
        activity = await service.get_recent_activity(limit)
        return activity
    except Exception as e:
        logger.error(f"Error getting recent activity: {e}")
        raise HTTPException(status_code=500, detail="Failed to load recent activity")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )