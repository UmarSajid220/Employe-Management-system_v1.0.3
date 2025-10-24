# A Square Skills Academy - Employee Management System Setup Guide

## Table of Contents
1. [System Requirements](#system-requirements)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Database Setup](#database-setup)
5. [Running the Application](#running-the-application)
6. [Testing](#testing)
7. [Production Deployment](#production-deployment)
8. [Troubleshooting](#troubleshooting)

## System Requirements

### Backend Requirements
- **Python**: 3.8 or higher
- **MongoDB**: 4.4 or higher
- **Redis**: 6.0 or higher (for caching and sessions)
- **Node.js**: 16.0 or higher (for frontend development)

### System Dependencies
- **Operating System**: Windows 10, macOS 10.15+, or Linux (Ubuntu 18.04+)
- **Memory**: Minimum 4GB RAM (8GB recommended)
- **Storage**: Minimum 2GB free space
- **Network**: Internet connection for package installation

### Development Tools
- **Git**: Latest version
- **VS Code**: Recommended IDE with Python and JavaScript extensions
- **Postman**: For API testing (optional)
- **MongoDB Compass**: For database visualization (optional)

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/a-square-skills-ems.git
cd a-square-skills-ems
```

### 2. Create Virtual Environment
```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Backend Dependencies
```bash
# Navigate to backend directory
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Install test dependencies
pip install -r ../tests/requirements.txt
```

### 4. Install Frontend Dependencies (Optional)
```bash
# Navigate to frontend directory
cd ../frontend

# Install Node.js dependencies (if using any build tools)
npm install
```

## Configuration

### 1. Environment Variables
Create a `.env` file in the backend directory:

```env
# Database Configuration
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=ems_db

# Security Configuration
SECRET_KEY=your-secret-key-here-make-it-long-and-random
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application Configuration
DEBUG=True
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000"]

# Email Configuration (Optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Redis Configuration (Optional)
REDIS_URL=redis://localhost:6379
```

### 2. Generate Secret Key
```python
# Run this Python script to generate a secure secret key
import secrets
print(secrets.token_urlsafe(32))
```

## Database Setup

### 1. Install and Start MongoDB

#### On Windows:
```bash
# Download and install MongoDB from https://www.mongodb.com/try/download/community
# Start MongoDB service
net start MongoDB
```

#### On macOS:
```bash
# Using Homebrew
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb/brew/mongodb-community
```

#### On Ubuntu:
```bash
# Install MongoDB
wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list
sudo apt-get update
sudo apt-get install -y mongodb-org

# Start MongoDB
sudo systemctl start mongod
sudo systemctl enable mongod
```

### 2. Initialize Database
The application will automatically create the database and collections on first run. The seed script will populate initial data.

### 3. Verify Database Connection
```bash
# Connect to MongoDB
mongosh

# Check databases
show databases

# Check collections
use ems_db
show collections
```

## Running the Application

### 1. Start the Backend Server
```bash
# Navigate to backend directory
cd backend

# Run the application
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or use the startup script
python start_server.py
```

### 2. Access the Application
- **API Documentation**: http://localhost:8000/docs
- **Alternative API Docs**: http://localhost:8000/redoc
- **Frontend**: Open `frontend/index.html` in your browser

### 3. Default Login Credentials
```
# Admin Account
Email: admin@asquareskills.com
Password: admin123

# Employee Account
Email: employee@asquareskills.com
Password: employee123
```

## Testing

### 1. Run All Tests
```bash
# Navigate to project root
cd ..

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=backend --cov-report=html

# Run specific test file
pytest tests/test_auth.py -v
```

### 2. Run Tests in Parallel
```bash
# Install pytest-xdist for parallel testing
pip install pytest-xdist

# Run tests in parallel
pytest tests/ -n auto
```

### 3. API Testing with cURL
```bash
# Test login
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@asquareskills.com", "password": "admin123"}'

# Test protected route (replace TOKEN with actual token)
curl -X GET "http://localhost:8000/api/v1/employees/" \
  -H "Authorization: Bearer TOKEN"
```

## Production Deployment

### 1. Environment Configuration
Create a production environment file `.env.production`:

```env
# Production Database
MONGODB_URL=mongodb://your-production-mongodb-url
DATABASE_NAME=ems_production

# Production Security
SECRET_KEY=your-production-secret-key
DEBUG=False

# Production Server
UVICORN_WORKERS=4
UVICORN_PORT=8000
UVICORN_HOST=0.0.0.0
```

### 2. Using Gunicorn (Recommended for Production)
```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 3. Docker Deployment
Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
# Build Docker image
docker build -t a-square-skills-ems .

# Run container
docker run -p 8000:8000 a-square-skills-ems
```

### 4. Using Docker Compose
Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - mongodb
      - redis
    environment:
      - MONGODB_URL=mongodb://mongodb:27017
      - REDIS_URL=redis://redis:6379

  mongodb:
    image: mongo:6.0
    ports:
      - "27017:27017"
    volumes:
      - mongodb_data:/data/db

  redis:
    image: redis:7.0
    ports:
      - "6379:6379"

volumes:
  mongodb_data:
```

Run with Docker Compose:
```bash
docker-compose up -d
```

## Troubleshooting

### Common Issues

#### 1. MongoDB Connection Error
```bash
# Check if MongoDB is running
sudo systemctl status mongod

# Restart MongoDB
sudo systemctl restart mongod

# Check MongoDB logs
sudo tail -f /var/log/mongodb/mongod.log
```

#### 2. Port Already in Use
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use a different port
uvicorn main:app --reload --port 8001
```

#### 3. Import Errors
```bash
# Ensure you're in the correct directory
cd backend

# Check Python path
python -c "import sys; print(sys.path)"

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

#### 4. Authentication Issues
```bash
# Clear cookies and local storage in browser
# Check JWT secret key in .env file
# Verify user exists in database
```

#### 5. CORS Issues
```bash
# Update CORS origins in .env file
CORS_ORIGINS=["http://localhost:3000", "http://your-frontend-domain.com"]
```

### Performance Optimization

#### 1. Database Optimization
```python
# Create indexes for better performance
# These will be created automatically by the application
# But you can manually create them for immediate effect
```

#### 2. Application Optimization
```bash
# Use production server settings
uvicorn main:app --workers 4 --host 0.0.0.0 --port 8000

# Enable response compression
pip install brotlipy
```

#### 3. Frontend Optimization
```bash
# Minify CSS and JavaScript (if using build tools)
npm run build

# Enable gzip compression on web server
```

### Security Considerations

1. **Change default passwords immediately**
2. **Use HTTPS in production**
3. **Regular security updates**
4. **Implement rate limiting**
5. **Use strong JWT secret keys**
6. **Enable MongoDB authentication**
7. **Regular database backups**

### Backup and Recovery

#### Database Backup
```bash
# Backup MongoDB
mongodump --db ems_db --out /path/to/backup/

# Restore MongoDB
mongorestore --db ems_db /path/to/backup/ems_db/
```

#### Application Backup
```bash
# Backup application files
tar -czf ems_backup.tar.gz /path/to/application/

# Restore application files
tar -xzf ems_backup.tar.gz
```

### Monitoring and Logging

#### 1. Application Logs
```bash
# View application logs
tail -f logs/app.log

# View error logs
tail -f logs/error.log
```

#### 2. Database Monitoring
```bash
# Monitor MongoDB
mongostat

# Check database size
db.stats()
```

## Support

For technical support or questions:
1. Check the troubleshooting section above
2. Review the API documentation at `/docs`
3. Check the GitHub issues page
4. Contact the development team

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Last Updated**: October 2025  
**Version**: 1.0.0  
**Author**: A Square Skills Academy Development Team