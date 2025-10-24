"""
FastAPI Dependencies and Database Configuration
"""

import os
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
from passlib.context import CryptContext
from bson import ObjectId

from models import User, UserRole, Token
from logging_config import setup_logging

logger = setup_logging()

# Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/ems")
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXP_SECONDS = int(os.getenv("JWT_EXP_SECONDS", "3600"))
JWT_LONG_EXP_SECONDS = int(os.getenv("JWT_LONG_EXP_SECONDS", "2592000"))

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Database client
client: Optional[AsyncIOMotorClient] = None
database = None


async def init_database():
    """Initialize database connection"""
    global client, database
    try:
        client = AsyncIOMotorClient(MONGO_URI)
        database = client.get_default_database()
        
        # Test connection
        await client.admin.command('ping')
        logger.info("Database connection established successfully")
        
        # Create indexes
        await create_indexes()
        
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


async def create_indexes():
    """Create database indexes"""
    try:
        # Users collection indexes
        await database.users.create_index("email", unique=True)
        await database.users.create_index("created_at")
        await database.users.create_index("role")
        
        # Tasks collection indexes
        await database.tasks.create_index("assigned_to")
        await database.tasks.create_index("status")
        await database.tasks.create_index("deadline")
        await database.tasks.create_index("created_at")
        
        # Attendance collection indexes
        await database.attendance.create_index("user_id")
        await database.attendance.create_index("date")
        await database.attendance.create_index([("user_id", 1), ("date", 1)])
        
        # Leaves collection indexes
        await database.leaves.create_index("user_id")
        await database.leaves.create_index("status")
        await database.leaves.create_index("from_date")
        await database.leaves.create_index("to_date")
        
        # Messages collection indexes
        await database.messages.create_index("sender_id")
        await database.messages.create_index("receiver_id")
        await database.messages.create_index([("sender_id", 1), ("receiver_id", 1)])
        await database.messages.create_index("created_at")
        
        logger.info("Database indexes created successfully")
        
    except Exception as e:
        logger.error(f"Error creating indexes: {e}")


def get_database():
    """Get database instance"""
    if database is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database not initialized"
        )
    return database


# Password hashing utilities
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)


# JWT utilities
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(seconds=JWT_EXP_SECONDS)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(seconds=JWT_LONG_EXP_SECONDS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> dict:
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != token_type:
            raise JWTError("Invalid token type")
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Authentication dependencies
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Get current authenticated user"""
    token = credentials.credentials
    payload = verify_token(token, "access")
    
    email: str = payload.get("sub")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    db = get_database()
    user_dict = await db.users.find_one({"email": email})
    if user_dict is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Convert _id to string for Pydantic compatibility
    user_dict["id"] = str(user_dict.pop("_id"))
    return User(**user_dict)


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get admin user (role-based access)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# Database query utilities
class DatabaseUtils:
    """Database utility functions"""
    
    @staticmethod
    async def get_user_by_email(email: str) -> Optional[dict]:
        """Get user by email"""
        db = get_database()
        return await db.users.find_one({"email": email})
    
    @staticmethod
    async def get_user_by_id(user_id: str) -> Optional[dict]:
        """Get user by ID"""
        db = get_database()
        try:
            object_id = ObjectId(user_id)
            return await db.users.find_one({"_id": object_id})
        except:
            return None
    
    @staticmethod
    async def create_user(user_data: dict) -> str:
        """Create new user"""
        db = get_database()
        result = await db.users.insert_one(user_data)
        return str(result.inserted_id)
    
    @staticmethod
    async def update_user(user_id: str, update_data: dict) -> bool:
        """Update user"""
        db = get_database()
        update_data["updated_at"] = datetime.utcnow()
        try:
            object_id = ObjectId(user_id)
            result = await db.users.update_one(
                {"_id": object_id},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except:
            return False
    
    @staticmethod
    async def delete_user(user_id: str) -> bool:
        """Delete user"""
        db = get_database()
        try:
            object_id = ObjectId(user_id)
            result = await db.users.delete_one({"_id": object_id})
            return result.deleted_count > 0
        except:
            return False


# Pagination utilities
def paginate_query(query, page: int = 1, limit: int = 10):
    """Add pagination to MongoDB query"""
    skip = (page - 1) * limit
    return query.skip(skip).limit(limit)


def serialize_mongo_doc(doc: dict) -> dict:
    """Serialize MongoDB document for JSON response"""
    if doc and "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc


def serialize_mongo_docs(docs: list) -> list:
    """Serialize multiple MongoDB documents"""
    return [serialize_mongo_doc(doc) for doc in docs]


# File upload utilities
ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.gif'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def validate_file_upload(filename: str, file_size: int) -> bool:
    """Validate file upload"""
    if file_size > MAX_FILE_SIZE:
        return False
    
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS


# Date utilities
def get_date_range(start_date: datetime, end_date: datetime):
    """Generate date range"""
    current_date = start_date
    while current_date <= end_date:
        yield current_date
        current_date += timedelta(days=1)


def get_month_start_end(date: datetime) -> tuple:
    """Get start and end of month"""
    start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    next_month = start.replace(month=start.month + 1) if start.month < 12 else start.replace(year=start.year + 1, month=1)
    end = next_month - timedelta(seconds=1)
    return start, end


# Export utilities
__all__ = [
    'init_database',
    'get_database',
    'verify_password',
    'get_password_hash',
    'create_access_token',
    'create_refresh_token',
    'verify_token',
    'get_current_user',
    'get_current_active_user',
    'get_admin_user',
    'DatabaseUtils',
    'paginate_query',
    'serialize_mongo_doc',
    'serialize_mongo_docs',
    'validate_file_upload',
    'ALLOWED_EXTENSIONS',
    'MAX_FILE_SIZE'
]