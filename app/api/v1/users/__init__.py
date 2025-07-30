"""
User API endpoints package.

This package contains all user-related API endpoints organized by HTTP methods:
- get.py: GET endpoints (list users, get user by ID, etc.)
- post.py: POST endpoints (create user, etc.)
- put.py: PUT endpoints (update user, etc.)
- delete.py: DELETE endpoints (delete user, etc.)
"""
from fastapi import APIRouter
from . import get, post, put, delete

# Create the main users router
router = APIRouter(prefix="/users", tags=["users"])

# Include all HTTP method routers
router.include_router(get.router)
router.include_router(post.router)
router.include_router(put.router)
router.include_router(delete.router)

__all__ = ["router"]