"""
MongoDB Models for A Square Skills Academy EMS
Using Motor (async MongoDB driver)
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field, validator
from bson import ObjectId
from enum import Enum


class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic models"""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)
    
    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class UserRole(str, Enum):
    """User roles enumeration"""
    ADMIN = "admin"
    EMPLOYEE = "employee"


class TaskStatus(str, Enum):
    """Task status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"


class LeaveStatus(str, Enum):
    """Leave status enumeration"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class AttendanceType(str, Enum):
    """Attendance type enumeration"""
    LOGIN = "login"
    LOGOUT = "logout"
    BREAK_START = "break_start"
    BREAK_END = "break_end"


# Base Models
class BaseDBModel(BaseModel):
    """Base model with common fields"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


# User Models
class User(BaseDBModel):
    """User model"""
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr = Field(..., unique=True)
    password: str = Field(..., min_length=6)
    role: UserRole = Field(default=UserRole.EMPLOYEE)
    position: Optional[str] = Field(None, max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    salary: Optional[float] = Field(None, ge=0)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)
    date_of_birth: Optional[datetime] = None
    joined_date: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
    profile_image: Optional[str] = None
    last_login: Optional[datetime] = None
    
    @validator('salary')
    def validate_salary(cls, v):
        if v is not None and v < 0:
            raise ValueError('Salary must be non-negative')
        return v


class UserCreate(BaseModel):
    """User creation schema"""
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr = Field(...)
    password: str = Field(..., min_length=6)
    role: UserRole = Field(default=UserRole.EMPLOYEE)
    position: Optional[str] = Field(None, max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    salary: Optional[float] = Field(None, ge=0)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)
    date_of_birth: Optional[datetime] = None


class UserUpdate(BaseModel):
    """User update schema"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    position: Optional[str] = Field(None, max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    salary: Optional[float] = Field(None, ge=0)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)
    date_of_birth: Optional[datetime] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """User response schema (without password)"""
    id: str
    name: str
    email: EmailStr
    role: UserRole
    position: Optional[str]
    department: Optional[str]
    salary: Optional[float]
    phone: Optional[str]
    address: Optional[str]
    date_of_birth: Optional[datetime]
    joined_date: datetime
    is_active: bool
    profile_image: Optional[str]
    last_login: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        json_encoders = {ObjectId: str}


# Task Models
class Task(BaseDBModel):
    """Task model"""
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    assigned_to: PyObjectId = Field(...)
    assigned_by: Optional[PyObjectId] = None
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    priority: str = Field(default="medium", regex="^(low|medium|high|urgent)$")
    deadline: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)
    attachments: List[str] = Field(default_factory=list)
    estimated_hours: Optional[float] = Field(None, ge=0)
    actual_hours: Optional[float] = Field(None, ge=0)
    
    @validator('deadline')
    def validate_deadline(cls, v):
        if v and v < datetime.utcnow():
            raise ValueError('Deadline cannot be in the past')
        return v


class TaskCreate(BaseModel):
    """Task creation schema"""
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    assigned_to: str = Field(...)
    priority: str = Field(default="medium", regex="^(low|medium|high|urgent)$")
    deadline: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)
    estimated_hours: Optional[float] = Field(None, ge=0)


class TaskUpdate(BaseModel):
    """Task update schema"""
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    assigned_to: Optional[str] = None
    priority: Optional[str] = Field(None, regex="^(low|medium|high|urgent)$")
    deadline: Optional[datetime] = None
    tags: Optional[List[str]] = None
    estimated_hours: Optional[float] = Field(None, ge=0)
    actual_hours: Optional[float] = Field(None, ge=0)


class TaskResponse(BaseModel):
    """Task response schema"""
    id: str
    title: str
    description: Optional[str]
    assigned_to: Dict[str, Any]
    assigned_by: Optional[Dict[str, Any]]
    status: TaskStatus
    priority: str
    deadline: Optional[datetime]
    completed_at: Optional[datetime]
    tags: List[str]
    attachments: List[str]
    estimated_hours: Optional[float]
    actual_hours: Optional[float]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        json_encoders = {ObjectId: str}


# Attendance Models
class Attendance(BaseDBModel):
    """Attendance model"""
    user_id: PyObjectId = Field(...)
    date: datetime = Field(default_factory=datetime.utcnow)
    login_time: datetime = Field(default_factory=datetime.utcnow)
    logout_time: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, ge=0)
    ip_address: Optional[str] = Field(None, max_length=45)
    location: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = Field(None, max_length=500)
    is_late: bool = Field(default=False)
    is_overtime: bool = Field(default=False)
    
    @validator('logout_time')
    def validate_logout_time(cls, v, values):
        if v and 'login_time' in values and v < values['login_time']:
            raise ValueError('Logout time cannot be before login time')
        return v


class AttendanceCreate(BaseModel):
    """Attendance creation schema"""
    user_id: str = Field(...)
    ip_address: Optional[str] = Field(None, max_length=45)
    location: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = Field(None, max_length=500)


class AttendanceResponse(BaseModel):
    """Attendance response schema"""
    id: str
    user: Dict[str, Any]
    date: datetime
    login_time: datetime
    logout_time: Optional[datetime]
    duration_minutes: Optional[int]
    ip_address: Optional[str]
    location: Optional[str]
    notes: Optional[str]
    is_late: bool
    is_overtime: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        json_encoders = {ObjectId: str}


# Leave Models
class Leave(BaseDBModel):
    """Leave model"""
    user_id: PyObjectId = Field(...)
    leave_type: str = Field(..., regex="^(annual|sick|personal|maternity|paternity|other)$")
    from_date: datetime = Field(...)
    to_date: datetime = Field(...)
    reason: str = Field(..., min_length=10, max_length=1000)
    status: LeaveStatus = Field(default=LeaveStatus.PENDING)
    approved_by: Optional[PyObjectId] = None
    approved_at: Optional[datetime] = None
    rejected_reason: Optional[str] = Field(None, max_length=500)
    days_requested: int = Field(..., ge=1)
    
    @validator('to_date')
    def validate_dates(cls, v, values):
        if 'from_date' in values and v <= values['from_date']:
            raise ValueError('To date must be after from date')
        return v
    
    @validator('days_requested')
    def calculate_days(cls, v, values):
        if 'from_date' in values and 'to_date' in values:
            delta = values['to_date'] - values['from_date']
            return delta.days + 1
        return v


class LeaveCreate(BaseModel):
    """Leave creation schema"""
    leave_type: str = Field(..., regex="^(annual|sick|personal|maternity|paternity|other)$")
    from_date: datetime = Field(...)
    to_date: datetime = Field(...)
    reason: str = Field(..., min_length=10, max_length=1000)


class LeaveUpdate(BaseModel):
    """Leave update schema"""
    status: LeaveStatus
    rejected_reason: Optional[str] = Field(None, max_length=500)


class LeaveResponse(BaseModel):
    """Leave response schema"""
    id: str
    user: Dict[str, Any]
    leave_type: str
    from_date: datetime
    to_date: datetime
    reason: str
    status: LeaveStatus
    approved_by: Optional[Dict[str, Any]]
    approved_at: Optional[datetime]
    rejected_reason: Optional[str]
    days_requested: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        json_encoders = {ObjectId: str}


# Message Models
class Message(BaseDBModel):
    """Message model"""
    sender_id: PyObjectId = Field(...)
    receiver_id: PyObjectId = Field(...)
    message: str = Field(..., min_length=1, max_length=5000)
    is_read: bool = Field(default=False)
    read_at: Optional[datetime] = None
    attachments: List[str] = Field(default_factory=list)
    reply_to: Optional[PyObjectId] = None
    
    @validator('sender_id')
    def validate_sender(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError('Invalid sender ID')
        return v
    
    @validator('receiver_id')
    def validate_receiver(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError('Invalid receiver ID')
        return v


class MessageCreate(BaseModel):
    """Message creation schema"""
    receiver_id: str = Field(...)
    message: str = Field(..., min_length=1, max_length=5000)
    attachments: List[str] = Field(default_factory=list)
    reply_to: Optional[str] = None


class MessageResponse(BaseModel):
    """Message response schema"""
    id: str
    sender: Dict[str, Any]
    receiver: Dict[str, Any]
    message: str
    is_read: bool
    read_at: Optional[datetime]
    attachments: List[str]
    reply_to: Optional[str]
    created_at: datetime
    
    class Config:
        json_encoders = {ObjectId: str}


# Report Models
class ReportType(str, Enum):
    """Report type enumeration"""
    EMPLOYEE_SUMMARY = "employee_summary"
    ATTENDANCE_REPORT = "attendance_report"
    TASK_REPORT = "task_report"
    LEAVE_REPORT = "leave_report"
    PERFORMANCE_REPORT = "performance_report"


class ReportRequest(BaseModel):
    """Report request schema"""
    report_type: ReportType
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    user_id: Optional[str] = None
    department: Optional[str] = None
    format: str = Field(default="json", regex="^(json|pdf|csv)$")
    
    @validator('date_to')
    def validate_date_range(cls, v, values):
        if v and 'date_from' in values and values['date_from'] and v < values['date_from']:
            raise ValueError('End date must be after start date')
        return v


class ReportResponse(BaseModel):
    """Report response schema"""
    report_type: ReportType
    generated_at: datetime
    data: Dict[str, Any]
    summary: Dict[str, Any]
    filters: Dict[str, Any]


# Settings Models
class Settings(BaseDBModel):
    """System settings model"""
    setting_key: str = Field(..., unique=True)
    setting_value: Any
    setting_type: str = Field(default="string", regex="^(string|number|boolean|array|object)$")
    description: Optional[str] = Field(None, max_length=500)
    is_system: bool = Field(default=False)
    
    class Config:
        json_encoders = {ObjectId: str}


class SettingsUpdate(BaseModel):
    """Settings update schema"""
    setting_value: Any
    description: Optional[str] = Field(None, max_length=500)


# Authentication Models
class Token(BaseModel):
    """JWT token model"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int


class LoginRequest(BaseModel):
    """Login request schema"""
    email: EmailStr
    password: str
    remember_me: bool = False


class PasswordChangeRequest(BaseModel):
    """Password change request schema"""
    current_password: str
    new_password: str = Field(..., min_length=6)


# Dashboard Models
class DashboardStats(BaseModel):
    """Dashboard statistics model"""
    total_employees: int
    active_tasks: int
    pending_leaves: int
    attendance_today: int
    tasks_completed_today: int
    new_messages: int
    upcoming_deadlines: int


class ActivityItem(BaseModel):
    """Activity item model"""
    id: str
    user_initials: str
    description: str
    timestamp: str
    action_type: str
    user_id: str


# API Response Models
class ApiResponse(BaseModel):
    """Standard API response model"""
    success: bool
    message: str
    data: Optional[Any] = None
    errors: Optional[List[str]] = None
    meta: Optional[Dict[str, Any]] = None


class PaginatedResponse(BaseModel):
    """Paginated response model"""
    items: List[Any]
    total: int
    page: int
    limit: int
    total_pages: int
    has_next: bool
    has_prev: bool


# Error Models
class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    message: str
    status_code: int
    details: Optional[Dict[str, Any]] = None