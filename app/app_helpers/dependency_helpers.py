"""
Enhanced dependency injection helper functions for version-agnostic controllers.

This module provides factory functions for creating FastAPI dependencies that support
version-agnostic controller and service injection. Controllers and services created
through these factories can work with any API version.
"""
from typing import TypeVar, Type, Callable, Optional, Any
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

# Type variables for generic dependency injection
ControllerType = TypeVar('ControllerType')
ServiceType = TypeVar('ServiceType')


def get_controller(controller_class: Type[ControllerType]) -> Callable[[], ControllerType]:
    """
    Create a dependency factory for version-agnostic controllers.
    
    This function creates a FastAPI dependency that instantiates controllers
    with proper database session injection, allowing the same controller
    to be used across all API versions.
    
    Args:
        controller_class: The controller class to instantiate
        
    Returns:
        Callable: FastAPI dependency function that returns controller instance
        
    Example:
        ```python
        # In API endpoint
        @router.get("/users")
        async def list_users(
            controller: UserController = Depends(get_controller(UserController))
        ):
            return await controller.list_users()
        ```
    """
    def controller_dependency(db: AsyncSession = Depends(get_db)) -> ControllerType:
        try:
            return controller_class(db)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to initialize controller: {str(e)}"
            )
    
    return controller_dependency


def get_service(service_class: Type[ServiceType]) -> Callable[[], ServiceType]:
    """
    Create a dependency factory for version-agnostic services.
    
    This function creates a FastAPI dependency that instantiates services
    with proper database session injection.
    
    Args:
        service_class: The service class to instantiate
        
    Returns:
        Callable: FastAPI dependency function that returns service instance
        
    Example:
        ```python
        # In controller or endpoint
        @router.get("/users")
        async def list_users(
            service: UserService = Depends(get_service(UserService))
        ):
            return await service.list_users()
        ```
    """
    def service_dependency(db: AsyncSession = Depends(get_db)) -> ServiceType:
        try:
            return service_class(db)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to initialize service: {str(e)}"
            )
    
    return service_dependency


# Advanced dependency injection patterns
def inject_controller_and_service(
    controller_class: Type[ControllerType], 
    service_class: Type[ServiceType]
) -> tuple[Callable[[], ControllerType], Callable[[], ServiceType]]:
    """
    Create dependencies for both controller and service.
    
    This is useful when you need both controller and service in the same endpoint,
    though typically you should use the controller which will handle service injection.
    
    Args:
        controller_class: The controller class
        service_class: The service class
        
    Returns:
        Tuple of dependency functions (controller_factory, service_factory)
    """
    return get_controller(controller_class), get_service(service_class)


def create_versioned_dependency(
    controller_class: Type[ControllerType],
    version_context: Optional[str] = None
) -> Callable[[], ControllerType]:
    """
    Create a version-aware dependency that can pass version context to controllers.
    
    This allows controllers to be aware of which API version is calling them,
    enabling version-specific behavior when needed.
    
    Args:
        controller_class: The controller class to instantiate
        version_context: Optional version context (e.g., "v1", "v2")
        
    Returns:
        Callable: FastAPI dependency function with version context
    """
    def versioned_controller_dependency(db: AsyncSession = Depends(get_db)) -> ControllerType:
        try:
            controller = controller_class(db)
            # Set version context if the controller supports it
            if hasattr(controller, 'set_version_context'):
                controller.set_version_context(version_context)
            return controller
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to initialize versioned controller: {str(e)}"
            )
    
    return versioned_controller_dependency


def with_transaction(dependency_func: Callable[[], Any]) -> Callable[[], Any]:
    """
    Wrap a dependency with automatic transaction management.
    
    This ensures that all database operations within the dependency
    are wrapped in a transaction that can be rolled back on error.
    
    Args:
        dependency_func: The dependency function to wrap
        
    Returns:
        Callable: Wrapped dependency with transaction management
    """
    async def transactional_dependency(db: AsyncSession = Depends(get_db)) -> Any:
        try:
            async with db.begin():
                return dependency_func(db)
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Transaction failed: {str(e)}"
            )
    
    return transactional_dependency