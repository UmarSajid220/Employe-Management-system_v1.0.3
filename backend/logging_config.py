"""
Logging configuration for A Square Skills Academy EMS
"""

import logging
import logging.handlers
import os
import json
from datetime import datetime
from typing import Dict, Any

# Log configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = os.getenv("LOG_DIR", "./logs")
LOG_MAX_SIZE = int(os.getenv("LOG_MAX_SIZE", "10485760"))  # 10MB
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))

# Ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)
        
        return json.dumps(log_entry)


def setup_logging() -> logging.Logger:
    """Setup application logging"""
    
    # Create logger
    logger = logging.getLogger("ems")
    logger.setLevel(getattr(logging, LOG_LEVEL.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler with colored output
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(LOG_LEVEL)
    logger.addHandler(console_handler)
    
    # File handler for general logs
    general_handler = logging.handlers.RotatingFileHandler(
        os.path.join(LOG_DIR, "ems.log"),
        maxBytes=LOG_MAX_SIZE,
        backupCount=LOG_BACKUP_COUNT
    )
    general_formatter = JSONFormatter()
    general_handler.setFormatter(general_formatter)
    general_handler.setLevel(LOG_LEVEL)
    logger.addHandler(general_handler)
    
    # File handler for errors
    error_handler = logging.handlers.RotatingFileHandler(
        os.path.join(LOG_DIR, "error.log"),
        maxBytes=LOG_MAX_SIZE,
        backupCount=LOG_BACKUP_COUNT
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(general_formatter)
    logger.addHandler(error_handler)
    
    # File handler for API requests
    api_handler = logging.handlers.RotatingFileHandler(
        os.path.join(LOG_DIR, "api.log"),
        maxBytes=LOG_MAX_SIZE,
        backupCount=LOG_BACKUP_COUNT
    )
    api_handler.setLevel(logging.INFO)
    api_handler.setFormatter(general_formatter)
    logger.addHandler(api_handler)
    
    # Security logger
    security_logger = logging.getLogger("ems.security")
    security_handler = logging.handlers.RotatingFileHandler(
        os.path.join(LOG_DIR, "security.log"),
        maxBytes=LOG_MAX_SIZE,
        backupCount=LOG_BACKUP_COUNT
    )
    security_handler.setLevel(logging.INFO)
    security_handler.setFormatter(general_formatter)
    security_logger.addHandler(security_handler)
    
    # Database logger
    db_logger = logging.getLogger("ems.database")
    db_handler = logging.handlers.RotatingFileHandler(
        os.path.join(LOG_DIR, "database.log"),
        maxBytes=LOG_MAX_SIZE,
        backupCount=LOG_BACKUP_COUNT
    )
    db_handler.setLevel(logging.INFO)
    db_handler.setFormatter(general_formatter)
    db_logger.addHandler(db_handler)
    
    return logger


def log_api_request(
    logger: logging.Logger,
    method: str,
    path: str,
    status_code: int,
    duration: float,
    user_id: str = None,
    ip_address: str = None,
    user_agent: str = None
):
    """Log API request"""
    extra_fields = {
        "request": {
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": round(duration * 1000, 2)
        },
        "user": {
            "id": user_id,
            "ip": ip_address,
            "agent": user_agent
        }
    }
    
    record = logging.LogRecord(
        name=logger.name,
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="API Request",
        args=(),
        exc_info=None
    )
    record.extra_fields = extra_fields
    logger.handle(record)


def log_security_event(
    logger: logging.Logger,
    event_type: str,
    description: str,
    user_id: str = None,
    ip_address: str = None,
    severity: str = "medium"
):
    """Log security event"""
    extra_fields = {
        "security": {
            "event_type": event_type,
            "severity": severity,
            "description": description
        },
        "user": {
            "id": user_id,
            "ip": ip_address
        }
    }
    
    level = {
        "low": logging.INFO,
        "medium": logging.WARNING,
        "high": logging.ERROR,
        "critical": logging.CRITICAL
    }.get(severity, logging.WARNING)
    
    record = logging.LogRecord(
        name=logger.name,
        level=level,
        pathname="",
        lineno=0,
        msg=f"Security Event: {event_type}",
        args=(),
        exc_info=None
    )
    record.extra_fields = extra_fields
    logger.handle(record)


def log_database_operation(
    logger: logging.Logger,
    operation: str,
    collection: str,
    document_id: str = None,
    user_id: str = None,
    duration: float = None
):
    """Log database operation"""
    extra_fields = {
        "database": {
            "operation": operation,
            "collection": collection,
            "document_id": document_id,
            "duration_ms": round(duration * 1000, 2) if duration else None
        },
        "user": {
            "id": user_id
        }
    }
    
    record = logging.LogRecord(
        name=logger.name,
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg=f"Database {operation} on {collection}",
        args=(),
        exc_info=None
    )
    record.extra_fields = extra_fields
    logger.handle(record)


# Performance monitoring
class PerformanceMonitor:
    """Monitor and log performance metrics"""
    
    def __init__(self, logger: logging.Logger, operation: str):
        self.logger = logger
        self.operation = operation
        self.start_time = datetime.utcnow()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.utcnow() - self.start_time).total_seconds()
        
        extra_fields = {
            "performance": {
                "operation": self.operation,
                "duration_ms": round(duration * 1000, 2),
                "success": exc_type is None
            }
        }
        
        if exc_type:
            extra_fields["performance"]["error"] = str(exc_val)
        
        record = logging.LogRecord(
            name=self.logger.name,
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg=f"Performance: {self.operation}",
            args=(),
            exc_info=None
        )
        record.extra_fields = extra_fields
        self.logger.handle(record)


# Export utilities
__all__ = [
    'setup_logging',
    'log_api_request',
    'log_security_event',
    'log_database_operation',
    'PerformanceMonitor',
    'JSONFormatter'
]