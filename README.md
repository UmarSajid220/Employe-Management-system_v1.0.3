# Employee Management System (EMS)

A full-stack, web-based Employee Management System for A Square Skills Academy.

## Overview

This system provides comprehensive employee management capabilities including:
- Employee CRUD operations
- Task management and assignment
- Attendance tracking
- Leave management
- Real-time messaging
- Report generation
- Role-based access control

## Tech Stack

- **Backend**: FastAPI + Motor (async MongoDB)
- **Frontend**: HTML, CSS, Vanilla JavaScript
- **Database**: MongoDB
- **Authentication**: JWT with cookie storage
- **Testing**: pytest
- **Deployment**: uvicorn

## Quick Start

1. Clone the repository
2. Create virtual environment: `python -m venv venv`
3. Activate virtual environment: `source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows)
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and configure values
6. Start MongoDB locally
7. Seed initial data: `python scripts/seed.py`
8. Run the server: `uvicorn backend.main:app --reload`
9. Access the application at `http://localhost:8000`

## Project Structure

```
employee-management-system/
├── backend/          # FastAPI backend application
├── frontend/         # HTML/CSS/JS frontend
├── tests/           # pytest test suite
├── scripts/         # Utility scripts
├── requirements.txt # Python dependencies
└── README.md        # This file
```

## Features

### Admin Features
- Full employee management (CRUD)
- Task assignment and monitoring
- Attendance overview
- Leave approval/rejection
- Comprehensive reporting
- System settings management

### Employee Features
- Personal dashboard
- Task management (view/update own tasks)
- Attendance tracking
- Leave application
- Personal reports
- Messaging system

## Security

- JWT-based authentication
- Password hashing with bcrypt
- Rate limiting on login attempts
- Input validation and sanitization
- Secure cookie storage
- CORS protection

## Development

Run tests: `pytest tests/`
Generate coverage: `pytest --cov=backend tests/`
Lint code: `flake8 backend/`

## License

Private - A Square Skills Academy Internal Use Only

## File Structure

employee-management-system/
├── backend/
│   ├── main.py
│   ├── dependencies.py
│   ├── routers/
│   │   ├── auth.py
│   │   ├── employees.py
│   │   ├── tasks.py
│   │   ├── attendance.py
│   │   ├── leaves.py
│   │   ├── messages.py
│   │   ├── reports.py
│   │   └── settings.py
│   ├── models.py
│   ├── schemas.py
│   ├── utils.py
│   ├── logging_config.py
│   └── uploads/
├── frontend/
│   ├── index.html
│   ├── 404.html
│   ├── admin/
│   │   ├── dashboard.html
│   │   ├── employees.html
│   │   ├── tasks.html
│   │   ├── attendance.html
│   │   ├── leaves.html
│   │   ├── reports.html
│   │   └── settings.html
│   ├── employee/
│   │   ├── dashboard.html
│   │   ├── my-tasks.html
│   │   ├── attendance.html
│   │   ├── leaves.html
│   │   ├── reports.html
│   │   └── profile.html
│   ├── css/
│   │   └── styles.css
│   ├── js/
│   │   └── app.js
│   └── assets/
├── tests/
│   ├── test_auth.py
│   ├── test_employees.py
│   ├── test_tasks.py
│   ├── test_attendance.py
│   └── test_leaves.py
├── scripts/
│   ├── seed.py
│   ├── backup.sh
│   └── restore.sh
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
