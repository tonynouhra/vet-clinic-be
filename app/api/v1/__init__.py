"""
V1 API Routes - Version-specific endpoints using shared controllers
"""
from fastapi import APIRouter

# Import routers (will be created in future tasks)
# from app.api.v1 import auth, users, pets, appointments, clinics, chat, ecommerce, social, emergency

api_router = APIRouter()

# Include routers (will be uncommented as they are created)
# api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
# api_router.include_router(users.router, prefix="/users", tags=["users"])
# api_router.include_router(pets.router, prefix="/pets", tags=["pets"])
# api_router.include_router(appointments.router, prefix="/appointments", tags=["appointments"])
# api_router.include_router(clinics.router, prefix="/clinics", tags=["clinics"])
# api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
# api_router.include_router(ecommerce.router, prefix="/ecommerce", tags=["ecommerce"])
# api_router.include_router(social.router, prefix="/social", tags=["social"])
# api_router.include_router(emergency.router, prefix="/emergency", tags=["emergency"])

@api_router.get("/")
async def api_root():
    """API v1 root endpoint."""
    return {"message": "Veterinary Clinic Platform API v1"}