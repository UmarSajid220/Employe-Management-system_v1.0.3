"""
Utility functions for A Square Skills Academy EMS
"""

import re
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path

# File upload utilities
ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.gif', '.txt', '.xlsx', '.pptx'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_phone(phone: str) -> bool:
    """Validate phone number format"""
    # Remove all non-numeric characters
    numeric_phone = re.sub(r'[^\d]', '', phone)
    # Check if it has 10-15 digits
    return 10 <= len(numeric_phone) <= 15


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal"""
    # Remove path separators and other potentially dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Limit length
    filename = filename[:100]
    return filename


def validate_file_upload(filename: str, file_size: int) -> tuple[bool, str]:
    """Validate file upload"""
    if file_size > MAX_FILE_SIZE:
        return False, f"File size exceeds maximum allowed size of {MAX_FILE_SIZE // (1024*1024)}MB"
    
    # Get file extension
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"File type {ext} not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
    
    return True, ""


def generate_unique_filename(original_filename: str) -> str:
    """Generate unique filename"""
    name, ext = os.path.splitext(original_filename)
    unique_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    sanitized_name = sanitize_filename(name)
    return f"{sanitized_name}_{timestamp}_{unique_id}{ext}"


def get_file_extension(filename: str) -> str:
    """Get file extension"""
    return os.path.splitext(filename)[1].lower()


def get_mime_type(filename: str) -> str:
    """Get MIME type based on file extension"""
    mime_types = {
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.txt': 'text/plain',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    }
    ext = get_file_extension(filename)
    return mime_types.get(ext, 'application/octet-stream')


# Date and time utilities
def get_month_start_end(date: datetime) -> tuple:
    """Get start and end of month"""
    start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1, day=1) - timedelta(microseconds=1)
    else:
        end = start.replace(month=start.month + 1, day=1) - timedelta(microseconds=1)
    return start, end


def get_week_start_end(date: datetime) -> tuple:
    """Get start and end of week (Monday to Sunday)"""
    start = date - timedelta(days=date.weekday())
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=999999)
    return start, end


def calculate_working_days(start_date: datetime, end_date: datetime) -> int:
    """Calculate working days between two dates"""
    if start_date > end_date:
        return 0
    
    working_days = 0
    current_date = start_date
    
    while current_date <= end_date:
        # Skip weekends (0=Monday, 6=Sunday)
        if current_date.weekday() < 5:
            working_days += 1
        current_date += timedelta(days=1)
    
    return working_days


def format_duration(minutes: int) -> str:
    """Format duration in minutes to human readable format"""
    hours = minutes // 60
    mins = minutes % 60
    
    if hours > 0:
        if mins > 0:
            return f"{hours}h {mins}m"
        return f"{hours}h"
    return f"{mins}m"


def parse_duration(duration_str: str) -> int:
    """Parse duration string to minutes"""
    # Handle formats like "2h 30m", "1.5h", "45m"
    total_minutes = 0
    
    # Extract hours
    hours_match = re.search(r'(\d+(?:\.\d+)?)h', duration_str)
    if hours_match:
        total_minutes += int(float(hours_match.group(1)) * 60)
    
    # Extract minutes
    minutes_match = re.search(r'(\d+)m', duration_str)
    if minutes_match:
        total_minutes += int(minutes_match.group(1))
    
    return total_minutes


# Text processing utilities
def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to specified length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def generate_initials(name: str) -> str:
    """Generate initials from name"""
    parts = name.split()
    if len(parts) >= 2:
        return f"{parts[0][0]}{parts[-1][0]}".upper()
    return name[:2].upper()


def clean_html(html: str) -> str:
    """Remove HTML tags from text"""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', html)


def strip_whitespace(text: str) -> str:
    """Strip and normalize whitespace"""
    return ' '.join(text.split())


# Data validation utilities
def validate_object_id(object_id: str) -> bool:
    """Validate MongoDB ObjectId"""
    try:
        from bson import ObjectId
        ObjectId(object_id)
        return True
    except:
        return False


def validate_date_range(start_date: datetime, end_date: datetime) -> tuple[bool, str]:
    """Validate date range"""
    if start_date > end_date:
        return False, "Start date cannot be after end date"
    
    if end_date - start_date > timedelta(days=365):
        return False, "Date range cannot exceed 1 year"
    
    return True, ""


def validate_salary(salary: float) -> tuple[bool, str]:
    """Validate salary"""
    if salary < 0:
        return False, "Salary cannot be negative"
    
    if salary > 1000000:  # 1 million
        return False, "Salary seems unrealistic"
    
    return True, ""


# Security utilities
def generate_secure_token(length: int = 32) -> str:
    """Generate secure random token"""
    import secrets
    return secrets.token_urlsafe(length)


def hash_sensitive_data(data: str) -> str:
    """Hash sensitive data"""
    import hashlib
    return hashlib.sha256(data.encode()).hexdigest()


def mask_sensitive_data(data: str, show_chars: int = 4) -> str:
    """Mask sensitive data (e.g., email, phone)"""
    if len(data) <= show_chars:
        return "*" * len(data)
    
    return data[:show_chars] + "*" * (len(data) - show_chars)


# Export utilities
def export_to_csv(data: List[Dict[str, Any]], filename: str) -> str:
    """Export data to CSV format"""
    import csv
    import io
    
    if not data:
        return ""
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    
    return output.getvalue()


def export_to_json(data: List[Dict[str, Any]]) -> str:
    """Export data to JSON format"""
    import json
    return json.dumps(data, indent=2, default=str)


# Cache utilities
class SimpleCache:
    """Simple in-memory cache with TTL"""
    
    def __init__(self):
        self._cache = {}
        self._timestamps = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key in self._cache:
            # Check if expired
            if self._timestamps[key] > datetime.now():
                return self._cache[key]
            else:
                # Remove expired entry
                del self._cache[key]
                del self._timestamps[key]
        return None
    
    def set(self, key: str, value: Any, ttl_minutes: int = 60) -> None:
        """Set value in cache with TTL"""
        self._cache[key] = value
        self._timestamps[key] = datetime.now() + timedelta(minutes=ttl_minutes)
    
    def delete(self, key: str) -> None:
        """Delete value from cache"""
        if key in self._cache:
            del self._cache[key]
            del self._timestamps[key]
    
    def clear(self) -> None:
        """Clear all cache"""
        self._cache.clear()
        self._timestamps.clear()


# Statistics utilities
def calculate_percentage(part: int, total: int) -> float:
    """Calculate percentage"""
    if total == 0:
        return 0.0
    return round((part / total) * 100, 2)


def calculate_average(values: List[float]) -> float:
    """Calculate average"""
    if not values:
        return 0.0
    return round(sum(values) / len(values), 2)


def calculate_median(values: List[float]) -> float:
    """Calculate median"""
    if not values:
        return 0.0
    
    sorted_values = sorted(values)
    n = len(sorted_values)
    
    if n % 2 == 0:
        return (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
    else:
        return sorted_values[n//2]


# Export all utilities
__all__ = [
    'validate_email',
    'validate_phone',
    'sanitize_filename',
    'validate_file_upload',
    'generate_unique_filename',
    'get_file_extension',
    'get_mime_type',
    'get_month_start_end',
    'get_week_start_end',
    'calculate_working_days',
    'format_duration',
    'parse_duration',
    'truncate_text',
    'generate_initials',
    'clean_html',
    'strip_whitespace',
    'validate_object_id',
    'validate_date_range',
    'validate_salary',
    'generate_secure_token',
    'hash_sensitive_data',
    'mask_sensitive_data',
    'export_to_csv',
    'export_to_json',
    'SimpleCache',
    'calculate_percentage',
    'calculate_average',
    'calculate_median',
    'ALLOWED_EXTENSIONS',
    'MAX_FILE_SIZE'
]