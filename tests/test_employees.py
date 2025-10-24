import pytest
import asyncio
from httpx import AsyncClient
from main import app
from models import UserRole


@pytest.mark.asyncio
async def test_create_employee():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as admin
        login_data = {
            "email": "admin@asquareskills.com",
            "password": "admin123"
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        # Create employee
        employee_data = {
            "name": "Test Employee",
            "email": "test.employee@asquareskills.com",
            "password": "employee123",
            "position": "Software Developer",
            "department": "Technology",
            "salary": 75000.0,
            "role": UserRole.EMPLOYEE
        }
        
        response = await client.post("/api/v1/employees/", json=employee_data)
        assert response.status_code == 201
        assert response.json()["name"] == "Test Employee"
        assert response.json()["email"] == "test.employee@asquareskills.com"


@pytest.mark.asyncio
async def test_get_employees():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as admin
        login_data = {
            "email": "admin@asquareskills.com",
            "password": "admin123"
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        response = await client.get("/api/v1/employees/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) > 0


@pytest.mark.asyncio
async def test_get_employee_by_id():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as admin
        login_data = {
            "email": "admin@asquareskills.com",
            "password": "admin123"
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        # Get first employee
        employees_response = await client.get("/api/v1/employees/")
        employee_id = employees_response.json()[0]["id"]
        
        response = await client.get(f"/api/v1/employees/{employee_id}")
        assert response.status_code == 200
        assert response.json()["id"] == employee_id


@pytest.mark.asyncio
async def test_update_employee():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as admin
        login_data = {
            "email": "admin@asquareskills.com",
            "password": "admin123"
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        # Get first employee
        employees_response = await client.get("/api/v1/employees/")
        employee_id = employees_response.json()[0]["id"]
        
        update_data = {
            "name": "Updated Employee Name",
            "position": "Senior Developer",
            "salary": 80000.0
        }
        
        response = await client.put(f"/api/v1/employees/{employee_id}", json=update_data)
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Employee Name"
        assert response.json()["position"] == "Senior Developer"


@pytest.mark.asyncio
async def test_delete_employee():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as admin
        login_data = {
            "email": "admin@asquareskills.com",
            "password": "admin123"
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        # Create a test employee to delete
        employee_data = {
            "name": "Employee to Delete",
            "email": "delete.me@asquareskills.com",
            "password": "delete123",
            "position": "Test Position",
            "department": "Technology",
            "role": UserRole.EMPLOYEE
        }
        
        create_response = await client.post("/api/v1/employees/", json=employee_data)
        employee_id = create_response.json()["id"]
        
        # Delete the employee
        response = await client.delete(f"/api/v1/employees/{employee_id}")
        assert response.status_code == 204
        
        # Verify deletion
        get_response = await client.get(f"/api/v1/employees/{employee_id}")
        assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_employee_cannot_access_admin_routes():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as employee
        login_data = {
            "email": "employee@asquareskills.com",
            "password": "employee123"
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        # Try to access admin-only route
        response = await client.get("/api/v1/employees/")
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_search_employees():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as admin
        login_data = {
            "email": "admin@asquareskills.com",
            "password": "admin123"
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        # Search employees
        response = await client.get("/api/v1/employees/search?q=john")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_filter_employees_by_department():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as admin
        login_data = {
            "email": "admin@asquareskills.com",
            "password": "admin123"
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        # Filter by department
        response = await client.get("/api/v1/employees/?department=Technology")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        
        # All returned employees should be from Technology department
        for employee in response.json():
            assert employee["department"] == "Technology"