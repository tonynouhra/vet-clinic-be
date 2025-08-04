"""
Dependency injection helpers for version-agnostic controllers and services.
Provides factory functions for dependency injection across all API versions.
"""

from typing import TypeVar, Type, Callable, Any
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

T = TypeVar('T')


def get_controller(controller_class: Type[T]) -> Callable[..., T]:
    """
    Factory function for version-agnostic controller dependency injection.
    
    Args:
        controller_class: The controller class to instantiate
        
    Returns:
        Callable: Dependency function that returns controller instance
        
    Example:
        @router.get("/users/")
        async def list_users(
            controller: UserController = Depends(get_controller(UserController))
        ):
            return await controller.list_users()
    """
    def _get_controller_instance(db: AsyncSession = Depends(get_db)) -> T:
        """Create controller instance with database dependency."""
        return controller_class(db)
    
    return _get_controller_instance


def get_service(service_class: Type[T]) -> Callable[..., T]:
    """
    Factory function for service dependency injection.
    
    Args:
        service_class: The service class to instantiate
        
    Returns:
        Callable: Dependency function that returns service instance
        
    Example:
        @router.get("/users/")
        async def list_users(
            service: UserService = Depends(get_service(UserService))
        ):
            return await service.list_users()
    """
    def _get_service_instance(db: AsyncSession = Depends(get_db)) -> T:
        """Create service instance with database dependency."""
        return service_class(db)
    
    return _get_service_instance


def get_authenticated_controller(controller_class: Type[T]) -> Callable[..., T]:
    """
    Factory function for authenticated controller dependency injection.
    
    Args:
        controller_class: The controller class to instantiate
        
    Returns:
        Callable: Dependency function that returns controller with authenticated user
        
    Example:
        @router.post("/pets/")
        async def create_pet(
            controller: PetController = Depends(get_authenticated_controller(PetController))
        ):
            return await controller.create_pet(pet_data)
    """
    def _get_authenticated_controller_instance(
        db: AsyncSession = Depends(get_db),
        current_user: dict = Depends(get_current_user)
    ) -> T:
        """Create controller instance with database and user dependencies."""
        controller = controller_class(db)
        controller.current_user = current_user
        return controller
    
    return _get_authenticated_controller_instance


def get_role_based_controller(
    controller_class: Type[T], 
    required_role: str
) -> Callable[..., T]:
    """
    Factory function for role-based controller dependency injection.
    
    Args:
        controller_class: The controller class to instantiate
        required_role: Required user role for access
        
    Returns:
        Callable: Dependency function that returns controller with role validation
        
    Example:
        @router.get("/admin/users/")
        async def admin_list_users(
            controller: UserController = Depends(
                get_role_based_controller(UserController, "admin")
            )
        ):
            return await controller.admin_list_users()
    """
    def _get_role_based_controller_instance(
        db: AsyncSession = Depends(get_db),
        current_user: dict = Depends(require_role(required_role))
    ) -> T:
        """Create controller instance with database and role-validated user."""
        controller = controller_class(db)
        controller.current_user = current_user
        return controller
    
    return _get_role_based_controller_instance


# Import auth helpers here to avoid circular imports
from .auth_helpers import get_current_user, require_role