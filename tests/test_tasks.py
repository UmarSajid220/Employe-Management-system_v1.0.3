import pytest
import asyncio
from httpx import AsyncClient
from main import app
from models import TaskStatus, TaskPriority


@pytest.mark.asyncio
async def test_create_task():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as admin
        login_data = {
            "email": "admin@asquareskills.com",
            "password": "admin123"
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        # Create task
        task_data = {
            "title": "Test Task",
            "description": "This is a test task",
            "assigned_to": "employee@asquareskills.com",
            "priority": TaskPriority.MEDIUM,
            "due_date": "2025-12-31"
        }
        
        response = await client.post("/api/v1/tasks/", json=task_data)
        assert response.status_code == 201
        assert response.json()["title"] == "Test Task"
        assert response.json()["status"] == TaskStatus.PENDING


@pytest.mark.asyncio
async def test_get_tasks():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as admin
        login_data = {
            "email": "admin@asquareskills.com",
            "password": "admin123"
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        response = await client.get("/api/v1/tasks/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_my_tasks():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as employee
        login_data = {
            "email": "employee@asquareskills.com",
            "password": "employee123"
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        response = await client.get("/api/v1/tasks/my-tasks")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_update_task_status():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as employee
        login_data = {
            "email": "employee@asquareskills.com",
            "password": "employee123"
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        # Get user's tasks
        tasks_response = await client.get("/api/v1/tasks/my-tasks")
        task_id = tasks_response.json()[0]["id"]
        
        # Update task status
        update_data = {
            "status": TaskStatus.IN_PROGRESS,
            "progress": 50
        }
        
        response = await client.put(f"/api/v1/tasks/{task_id}/status", json=update_data)
        assert response.status_code == 200
        assert response.json()["status"] == TaskStatus.IN_PROGRESS
        assert response.json()["progress"] == 50


@pytest.mark.asyncio
async def test_complete_task():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as employee
        login_data = {
            "email": "employee@asquareskills.com",
            "password": "employee123"
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        # Get user's tasks
        tasks_response = await client.get("/api/v1/tasks/my-tasks")
        task_id = tasks_response.json()[0]["id"]
        
        # Complete task
        response = await client.put(f"/api/v1/tasks/{task_id}/complete")
        assert response.status_code == 200
        assert response.json()["status"] == TaskStatus.COMPLETED
        assert response.json()["completed_at"] is not None


@pytest.mark.asyncio
async def test_filter_tasks_by_status():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as admin
        login_data = {
            "email": "admin@asquareskills.com",
            "password": "admin123"
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        # Filter by status
        response = await client.get("/api/v1/tasks/?status=pending")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        
        # All returned tasks should be pending
        for task in response.json():
            assert task["status"] == TaskStatus.PENDING


@pytest.mark.asyncio
async def test_filter_tasks_by_priority():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as admin
        login_data = {
            "email": "admin@asquareskills.com",
            "password": "admin123"
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        # Filter by priority
        response = await client.get("/api/v1/tasks/?priority=high")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        
        # All returned tasks should be high priority
        for task in response.json():
            assert task["priority"] == TaskPriority.HIGH


@pytest.mark.asyncio
async def test_assign_task():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as admin
        login_data = {
            "email": "admin@asquareskills.com",
            "password": "admin123"
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        # Create task without assignment
        task_data = {
            "title": "Task to Assign",
            "description": "This task will be assigned later",
            "priority": TaskPriority.MEDIUM
        }
        
        create_response = await client.post("/api/v1/tasks/", json=task_data)
        task_id = create_response.json()["id"]
        
        # Assign task to employee
        assign_data = {
            "assigned_to": "employee@asquareskills.com"
        }
        
        response = await client.put(f"/api/v1/tasks/{task_id}/assign", json=assign_data)
        assert response.status_code == 200
        assert response.json()["assigned_to"] == "employee@asquareskills.com"


@pytest.mark.asyncio
async def test_delete_task():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as admin
        login_data = {
            "email": "admin@asquareskills.com",
            "password": "admin123"
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        # Create a test task to delete
        task_data = {
            "title": "Task to Delete",
            "description": "This task will be deleted",
            "priority": TaskPriority.LOW
        }
        
        create_response = await client.post("/api/v1/tasks/", json=task_data)
        task_id = create_response.json()["id"]
        
        # Delete the task
        response = await client.delete(f"/api/v1/tasks/{task_id}")
        assert response.status_code == 204
        
        # Verify deletion
        get_response = await client.get(f"/api/v1/tasks/{task_id}")
        assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_task_analytics():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as admin
        login_data = {
            "email": "admin@asquareskills.com",
            "password": "admin123"
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        # Get task analytics
        response = await client.get("/api/v1/tasks/analytics")
        assert response.status_code == 200
        assert "total_tasks" in response.json()
        assert "completed_tasks" in response.json()
        assert "pending_tasks" in response.json()
        assert "overdue_tasks" in response.json()