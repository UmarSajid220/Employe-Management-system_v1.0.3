import pytest
import asyncio
from httpx import AsyncClient
from main import app
from dependencies import get_password_hash, verify_password
from models import LoginRequest


@pytest.mark.asyncio
async def test_login_success():
    async with AsyncClient(app=app, base_url="http://test") as client:
        login_data = {
            "email": "admin@asquareskills.com",
            "password": "admin123"
        }
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert "token_type" in response.json()


@pytest.mark.asyncio
async def test_login_invalid_credentials():
    async with AsyncClient(app=app, base_url="http://test") as client:
        login_data = {
            "email": "admin@asquareskills.com",
            "password": "wrongpassword"
        }
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_password_hashing():
    password = "testpassword123"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed)
    assert not verify_password("wrongpassword", hashed)


@pytest.mark.asyncio
async def test_protected_route_without_token():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/employees/")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_with_invalid_token():
    async with AsyncClient(app=app, base_url="http://test") as client:
        headers = {"Authorization": "Bearer invalid_token"}
        response = await client.get("/api/v1/employees/", headers=headers)
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # First login
        login_data = {
            "email": "admin@asquareskills.com",
            "password": "admin123"
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        # Then logout
        response = await client.post("/api/v1/auth/logout")
        assert response.status_code == 200
        assert response.json()["message"] == "Successfully logged out"