"""
Seed script for A Square Skills Academy EMS
Initial data seeding for development and testing
"""

import asyncio
import os
from datetime import datetime, timedelta
from bson import ObjectId
from dotenv import load_dotenv

from dependencies import get_database, get_password_hash
from models import UserRole, TaskStatus, LeaveStatus
from logging_config import setup_logging

load_dotenv()
logger = setup_logging()


async def seed_initial_data():
    """Seed initial data for the application"""
    try:
        db = await get_database()
        
        # Check if data already exists
        user_count = await db.users.count_documents({})
        if user_count > 0:
            logger.info("Data already exists, skipping seed")
            return
        
        logger.info("Starting data seeding...")
        
        # Create admin user
        admin_email = os.getenv("ADMIN_EMAIL", "admin@askillsacademy.com")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
        
        admin_user = {
            "_id": ObjectId(),
            "name": "System Administrator",
            "email": admin_email,
            "password": get_password_hash(admin_password),
            "role": UserRole.ADMIN,
            "position": "System Administrator",
            "department": "IT",
            "salary": 100000,
            "phone": "+1-555-0001",
            "address": "123 Admin Street, Admin City",
            "is_active": True,
            "joined_date": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        admin_result = await db.users.insert_one(admin_user)
        admin_id = admin_result.inserted_id
        logger.info(f"Created admin user: {admin_email}")
        
        # Create sample employees
        sample_employees = [
            {
                "_id": ObjectId(),
                "name": "John Smith",
                "email": "john.smith@askillsacademy.com",
                "password": get_password_hash("employee123"),
                "role": UserRole.EMPLOYEE,
                "position": "Senior Developer",
                "department": "Engineering",
                "salary": 75000,
                "phone": "+1-555-0002",
                "address": "456 Developer Ave, Tech City",
                "is_active": True,
                "joined_date": datetime.utcnow() - timedelta(days=30),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "_id": ObjectId(),
                "name": "Sarah Johnson",
                "email": "sarah.johnson@askillsacademy.com",
                "password": get_password_hash("employee123"),
                "role": UserRole.EMPLOYEE,
                "position": "HR Manager",
                "department": "Human Resources",
                "salary": 65000,
                "phone": "+1-555-0003",
                "address": "789 HR Blvd, People City",
                "is_active": True,
                "joined_date": datetime.utcnow() - timedelta(days=45),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "_id": ObjectId(),
                "name": "Michael Chen",
                "email": "michael.chen@askillsacademy.com",
                "password": get_password_hash("employee123"),
                "role": UserRole.EMPLOYEE,
                "position": "Marketing Specialist",
                "department": "Marketing",
                "salary": 55000,
                "phone": "+1-555-0004",
                "address": "321 Market St, Ad City",
                "is_active": True,
                "joined_date": datetime.utcnow() - timedelta(days=60),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "_id": ObjectId(),
                "name": "Emily Davis",
                "email": "emily.davis@askillsacademy.com",
                "password": get_password_hash("employee123"),
                "role": UserRole.EMPLOYEE,
                "position": "UX Designer",
                "department": "Design",
                "salary": 60000,
                "phone": "+1-555-0005",
                "address": "654 Design Lane, Creative City",
                "is_active": True,
                "joined_date": datetime.utcnow() - timedelta(days=15),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "_id": ObjectId(),
                "name": "David Wilson",
                "email": "david.wilson@askillsacademy.com",
                "password": get_password_hash("employee123"),
                "role": UserRole.EMPLOYEE,
                "position": "Sales Representative",
                "department": "Sales",
                "salary": 50000,
                "phone": "+1-555-0006",
                "address": "987 Sales Ave, Business City",
                "is_active": True,
                "joined_date": datetime.utcnow() - timedelta(days=90),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        ]
        
        employee_results = await db.users.insert_many(sample_employees)
        employee_ids = employee_results.inserted_ids
        logger.info(f"Created {len(sample_employees)} sample employees")
        
        # Create sample tasks
        sample_tasks = [
            {
                "_id": ObjectId(),
                "title": "Implement user authentication",
                "description": "Implement JWT-based authentication system with login, logout, and token refresh functionality",
                "assigned_to": employee_ids[0],  # John Smith
                "assigned_by": admin_id,
                "status": TaskStatus.COMPLETED,
                "priority": "high",
                "deadline": datetime.utcnow() - timedelta(days=7),
                "completed_at": datetime.utcnow() - timedelta(days=8),
                "tags": ["authentication", "security", "backend"],
                "estimated_hours": 16,
                "actual_hours": 18,
                "created_at": datetime.utcnow() - timedelta(days=20),
                "updated_at": datetime.utcnow() - timedelta(days=8)
            },
            {
                "_id": ObjectId(),
                "title": "Design employee dashboard UI",
                "description": "Create wireframes and mockups for the employee dashboard with modern, minimalist design",
                "assigned_to": employee_ids[3],  # Emily Davis
                "assigned_by": admin_id,
                "status": TaskStatus.IN_PROGRESS,
                "priority": "medium",
                "deadline": datetime.utcnow() + timedelta(days=3),
                "tags": ["design", "ui", "dashboard"],
                "estimated_hours": 12,
                "created_at": datetime.utcnow() - timedelta(days=5),
                "updated_at": datetime.utcnow() - timedelta(days=1)
            },
            {
                "_id": ObjectId(),
                "title": "Set up CI/CD pipeline",
                "description": "Configure automated testing and deployment pipeline using GitHub Actions",
                "assigned_to": employee_ids[0],  # John Smith
                "assigned_by": admin_id,
                "status": TaskStatus.PENDING,
                "priority": "high",
                "deadline": datetime.utcnow() + timedelta(days=7),
                "tags": ["devops", "ci-cd", "automation"],
                "estimated_hours": 8,
                "created_at": datetime.utcnow() - timedelta(days=2),
                "updated_at": datetime.utcnow() - timedelta(days=2)
            },
            {
                "_id": ObjectId(),
                "title": "Conduct employee onboarding session",
                "description": "Organize and conduct onboarding session for new hires including system training",
                "assigned_to": employee_ids[1],  # Sarah Johnson
                "assigned_by": admin_id,
                "status": TaskStatus.PENDING,
                "priority": "medium",
                "deadline": datetime.utcnow() + timedelta(days=5),
                "tags": ["hr", "onboarding", "training"],
                "estimated_hours": 6,
                "created_at": datetime.utcnow() - timedelta(days=1),
                "updated_at": datetime.utcnow() - timedelta(days=1)
            },
            {
                "_id": ObjectId(),
                "title": "Create marketing campaign for Q4",
                "description": "Develop comprehensive marketing strategy and campaign materials for Q4 product launch",
                "assigned_to": employee_ids[2],  # Michael Chen
                "assigned_by": admin_id,
                "status": TaskStatus.PENDING,
                "priority": "medium",
                "deadline": datetime.utcnow() + timedelta(days=14),
                "tags": ["marketing", "campaign", "strategy"],
                "estimated_hours": 20,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        ]
        
        await db.tasks.insert_many(sample_tasks)
        logger.info(f"Created {len(sample_tasks)} sample tasks")
        
        # Create sample attendance records
        sample_attendance = []
        for i, employee_id in enumerate([admin_id] + list(employee_ids)):
            # Create attendance for last 7 days
            for day_offset in range(1, 8):
                date = datetime.utcnow() - timedelta(days=day_offset)
                login_time = date.replace(hour=9, minute=0, second=0, microsecond=0)
                logout_time = date.replace(hour=17, minute=30, second=0, microsecond=0)
                duration_minutes = int((logout_time - login_time).total_seconds() / 60)
                
                # Some employees might be late or absent
                is_late = (i + day_offset) % 5 == 0  # 20% chance of being late
                is_present = (i + day_offset) % 7 != 0  # ~85% attendance rate
                
                if is_present:
                    sample_attendance.append({
                        "_id": ObjectId(),
                        "user_id": employee_id,
                        "date": date.date(),
                        "login_time": login_time,
                        "logout_time": logout_time,
                        "duration_minutes": duration_minutes,
                        "ip_address": f"192.168.1.{100 + i}",
                        "location": "Office",
                        "is_late": is_late,
                        "is_overtime": False,
                        "created_at": login_time,
                        "updated_at": logout_time
                    })
        
        await db.attendance.insert_many(sample_attendance)
        logger.info(f"Created {len(sample_attendance)} sample attendance records")
        
        # Create sample leave applications
        sample_leaves = [
            {
                "_id": ObjectId(),
                "user_id": employee_ids[0],  # John Smith
                "leave_type": "annual",
                "from_date": datetime.utcnow() + timedelta(days=10),
                "to_date": datetime.utcnow() + timedelta(days=12),
                "reason": "Family vacation planned for summer break",
                "status": LeaveStatus.APPROVED,
                "approved_by": admin_id,
                "approved_at": datetime.utcnow() - timedelta(days=2),
                "days_requested": 3,
                "created_at": datetime.utcnow() - timedelta(days=5),
                "updated_at": datetime.utcnow() - timedelta(days=2)
            },
            {
                "_id": ObjectId(),
                "user_id": employee_ids[1],  # Sarah Johnson
                "leave_type": "sick",
                "from_date": datetime.utcnow() - timedelta(days=3),
                "to_date": datetime.utcnow() - timedelta(days=2),
                "reason": "Flu symptoms, need rest and recovery",
                "status": LeaveStatus.APPROVED,
                "approved_by": admin_id,
                "approved_at": datetime.utcnow() - timedelta(days=3),
                "days_requested": 2,
                "created_at": datetime.utcnow() - timedelta(days=4),
                "updated_at": datetime.utcnow() - timedelta(days=3)
            },
            {
                "_id": ObjectId(),
                "user_id": employee_ids[2],  # Michael Chen
                "leave_type": "personal",
                "from_date": datetime.utcnow() + timedelta(days=5),
                "to_date": datetime.utcnow() + timedelta(days=5),
                "reason": "Personal appointment and family matter",
                "status": LeaveStatus.PENDING,
                "days_requested": 1,
                "created_at": datetime.utcnow() - timedelta(days=1),
                "updated_at": datetime.utcnow() - timedelta(days=1)
            },
            {
                "_id": ObjectId(),
                "user_id": employee_ids[3],  # Emily Davis
                "leave_type": "annual",
                "from_date": datetime.utcnow() + timedelta(days=20),
                "to_date": datetime.utcnow() + timedelta(days=24),
                "reason": "Attending design conference out of state",
                "status": LeaveStatus.PENDING,
                "days_requested": 5,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        ]
        
        await db.leaves.insert_many(sample_leaves)
        logger.info(f"Created {len(sample_leaves)} sample leave applications")
        
        # Create sample messages
        sample_messages = [
            {
                "_id": ObjectId(),
                "sender_id": admin_id,
                "receiver_id": employee_ids[0],  # Admin to John
                "message": "Welcome to the team! Let me know if you need any help with the authentication implementation.",
                "is_read": True,
                "read_at": datetime.utcnow() - timedelta(days=18),
                "created_at": datetime.utcnow() - timedelta(days=19),
                "updated_at": datetime.utcnow() - timedelta(days=18)
            },
            {
                "_id": ObjectId(),
                "sender_id": employee_ids[0],  # John to Admin
                "receiver_id": admin_id,
                "message": "Thank you! The authentication system is now complete. I'll move on to the CI/CD pipeline next.",
                "is_read": True,
                "read_at": datetime.utcnow() - timedelta(days=8),
                "created_at": datetime.utcnow() - timedelta(days=9),
                "updated_at": datetime.utcnow() - timedelta(days=8)
            },
            {
                "_id": ObjectId(),
                "sender_id": employee_ids[3],  # Emily to Admin
                "receiver_id": admin_id,
                "message": "I've started working on the dashboard design. Should I focus on mobile-first approach?",
                "is_read": False,
                "created_at": datetime.utcnow() - timedelta(days=1),
                "updated_at": datetime.utcnow() - timedelta(days=1)
            },
            {
                "_id": ObjectId(),
                "sender_id": employee_ids[1],  # Sarah to Admin
                "receiver_id": admin_id,
                "message": "I've scheduled the onboarding session for next week. Should I prepare any specific materials?",
                "is_read": False,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        ]
        
        await db.messages.insert_many(sample_messages)
        logger.info(f"Created {len(sample_messages)} sample messages")
        
        # Create system settings
        system_settings = [
            {
                "_id": ObjectId(),
                "setting_key": "app_name",
                "setting_value": "A Square Skills Academy EMS",
                "setting_type": "string",
                "description": "Application name displayed in UI",
                "is_system": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "_id": ObjectId(),
                "setting_key": "app_version",
                "setting_value": "1.0.0",
                "setting_type": "string",
                "description": "Current application version",
                "is_system": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "_id": ObjectId(),
                "setting_key": "max_file_upload_size",
                "setting_value": 10485760,  # 10MB in bytes
                "setting_type": "number",
                "description": "Maximum file upload size in bytes",
                "is_system": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "_id": ObjectId(),
                "setting_key": "allowed_file_types",
                "setting_value": [".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png", ".gif"],
                "setting_type": "array",
                "description": "Allowed file types for uploads",
                "is_system": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "_id": ObjectId(),
                "setting_key": "office_start_time",
                "setting_value": "09:00",
                "setting_type": "string",
                "description": "Office start time for attendance tracking",
                "is_system": False,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "_id": ObjectId(),
                "setting_key": "office_end_time",
                "setting_value": "18:00",
                "setting_type": "string",
                "description": "Office end time for attendance tracking",
                "is_system": False,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "_id": ObjectId(),
                "setting_key": "annual_leave_quota",
                "setting_value": 21,
                "setting_type": "number",
                "description": "Annual leave quota in days",
                "is_system": False,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "_id": ObjectId(),
                "setting_key": "sick_leave_quota",
                "setting_value": 10,
                "setting_type": "number",
                "description": "Sick leave quota in days",
                "is_system": False,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        ]
        
        await db.settings.insert_many(system_settings)
        logger.info(f"Created {len(system_settings)} system settings")
        
        logger.info("Data seeding completed successfully!")
        logger.info(f"Admin Login: {admin_email} / {admin_password}")
        logger.info("Employee Login: Use any employee email with password 'employee123'")
        
    except Exception as e:
        logger.error(f"Error during data seeding: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(seed_initial_data())