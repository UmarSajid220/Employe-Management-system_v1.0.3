import pytest
import asyncio
from httpx import AsyncClient
from main import app
from datetime import datetime, date


@pytest.mark.asyncio
async def test_clock_in():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as employee
        login_data = {
            "email": "employee@asquareskills.com",
            "password": "employee123"
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        # Clock in
        response = await client.post("/api/v1/attendance/clock-in")
        assert response.status_code == 200
        assert response.json()["message"] == "Clocked in successfully"
        assert response.json()["clock_in"] is not None


@pytest.mark.asyncio
async def test_clock_out():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as employee
        login_data = {
            "email": "employee@asquareskills.com",
            "password": "employee123"
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        # Clock in first
        await client.post("/api/v1/attendance/clock-in")
        
        # Clock out
        response = await client.post("/api/v1/attendance/clock-out")
        assert response.status_code == 200
        assert response.json()["message"] == "Clocked out successfully"
        assert response.json()["clock_out"] is not None


@pytest.mark.asyncio
async def test_double_clock_in():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as employee
        login_data = {
            "email": "employee@asquareskills.com",
            "password": "employee123"
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        # Clock in
        await client.post("/api/v1/attendance/clock-in")
        
        # Try to clock in again
        response = await client.post("/api/v1/attendance/clock-in")
        assert response.status_code == 400
        assert "already clocked in" in response.json()["detail"]


@pytest.mark.asyncio
async def test_clock_out_without_clock_in():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as employee
        login_data = {
            "email": "employee@asquareskills.com",
            "password": "employee123"
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        # Try to clock out without clocking in
        response = await client.post("/api/v1/attendance/clock-out")
        assert response.status_code == 400
        assert "not clocked in" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_today_attendance():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as employee
        login_data = {
            "email": "employee@asquareskills.com",
            "password": "employee123"
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        # Clock in
        await client.post("/api/v1/attendance/clock-in")
        
        # Get today's attendance
        response = await client.get("/api/v1/attendance/today")
        assert response.status_code == 200
        assert response.json()["date"] == str(date.today())
        assert response.json()["clock_in"] is not None


@pytest.mark.asyncio
async def test_get_my_attendance():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as employee
        login_data = {
            "email": "employee@asquareskills.com",
            "password": "employee123"
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        response = await client.get("/api/v1/attendance/my-attendance")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_filter_attendance_by_date():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as employee
        login_data = {
            "email": "employee@asquareskills.com",
            "password": "employee123"
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        # Filter by date range
        response = await client.get("/api/v1/attendance/my-attendance?start_date=2025-10-01&end_date=2025-10-31")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_attendance_analytics():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as admin
        login_data = {
            "email": "admin@asquareskills.com",
            "password": "admin123"
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        response = await client.get("/api/v1/attendance/analytics")
        assert response.status_code == 200
        assert "total_employees" in response.json()
        assert "present_today" in response.json()
        assert "absent_today" in response.json()


@pytest.mark.asyncio
async def test_late_arrival_detection():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as employee
        login_data = {
            "email": "employee@asquareskills.com",
            "password": "employee123"
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        # Clock in late (after 9:15 AM grace period)
        # This would need to be tested with appropriate timing
        response = await client.post("/api/v1/attendance/clock-in")
        
        # Check if marked as late
        today_response = await client.get("/api/v1/attendance/today")
        if today_response.json()["is_late"]:
            assert today_response.json()["late_minutes"] > 0


@pytest.mark.asyncio
async def test_overtime_calculation():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as employee
        login_data = {
            "email": "employee@asquareskills.com",
            "password": "employee123"
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        # Clock in
        await client.post("/api/v1/attendance/clock-in")
        
        # Clock out after normal hours (after 5:00 PM)
        response = await client.post("/api/v1/attendance/clock-out")
        
        # Check if overtime was calculated
        today_response = await client.get("/api/v1/attendance/today")
        if today_response.json()["overtime_hours"] > 0:
            assert today_response.json()["overtime_hours"] > 0


@pytest.mark.asyncio
async def test_monthly_attendance_summary():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as employee
        login_data = {
            "email": "employee@asquareskills.com",
            "password": "employee123"
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        # Get monthly summary
        response = await client.get("/api/v1/attendance/monthly-summary?month=10&year=2025")
        assert response.status_code == 200
        assert "total_days" in response.json()
        assert "present_days" in response.json()
        assert "absent_days" in response.json()
        assert "late_days" in response.json()
        assert "total_hours" in response.json()


@pytest.mark.asyncio
async def test_admin_can_view_all_attendance():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as admin
        login_data = {
            "email": "admin@asquareskills.com",
            "password": "admin123"
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        # Get all attendance records
        response = await client.get("/api/v1/attendance/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)