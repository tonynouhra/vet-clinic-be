"""
Common operation helpers with shared business operations and utilities.

This module provides shared business operations, audit logging, activity tracking,
and data transformation utilities that work across all API versions.
"""
import json
import uuid
from typing import Any, Dict, List, Optional, Union, Callable, Type
from datetime import datetime, date
from enum import Enum
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete
from fastapi import HTTPException, status

from app.models import User


class OperationType(str, Enum):
    """Types of operations for audit logging."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    IMPORT = "import"
    BULK_UPDATE = "bulk_update"
    BULK_DELETE = "bulk_delete"


class AuditLevel(str, Enum):
    """Audit logging levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class DataTransformationError(Exception):
    """Exception raised when data transformation fails."""
    pass


# Audit Logging Utilities

async def log_operation(
    db: AsyncSession,
    user_id: Optional[str],
    operation_type: OperationType,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    level: AuditLevel = AuditLevel.INFO,
    api_version: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> str:
    """
    Log an operation for audit purposes.
    
    Args:
        db: Database session
        user_id: ID of the user performing the operation
        operation_type: Type of operation being performed
        resource_type: Type of resource being operated on
        resource_id: ID of the specific resource (if applicable)
        details: Additional operation details
        level: Audit level
        api_version: API version used
        ip_address: Client IP address
        user_agent: Client user agent
        
    Returns:
        str: Audit log entry ID
    """
    # TODO: Implement actual audit log table
    # For now, this is a placeholder that would insert into an audit_logs table
    
    audit_entry = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "operation_type": operation_type.value,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "details": json.dumps(details) if details else None,
        "level": level.value,
        "api_version": api_version,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "timestamp": datetime.utcnow(),
    }
    
    # In a real implementation, this would insert into audit_logs table
    # await db.execute(insert(AuditLog).values(**audit_entry))
    # await db.commit()
    
    return audit_entry["id"]


def create_audit_decorator(
    operation_type: OperationType,
    resource_type: str,
    level: AuditLevel = AuditLevel.INFO
):
    """
    Create a decorator for automatic audit logging.
    
    Args:
        operation_type: Type of operation
        resource_type: Type of resource
        level: Audit level
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            # Extract common parameters
            db = kwargs.get('db') or (args[1] if len(args) > 1 else None)
            user_context = kwargs.get('user_context')
            
            # Execute the original function
            result = await func(*args, **kwargs)
            
            # Log the operation
            if db and user_context:
                await log_operation(
                    db=db,
                    user_id=str(user_context.user.id),
                    operation_type=operation_type,
                    resource_type=resource_type,
                    level=level,
                    api_version=user_context.api_version,
                    ip_address=user_context.request_metadata.get('ip_address'),
                    user_agent=user_context.request_metadata.get('user_agent')
                )
            
            return result
        return wrapper
    return decorator


# Activity Tracking Utilities

class ActivityTracker:
    """Utility class for tracking user activities."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def track_user_activity(
        self,
        user_id: str,
        activity_type: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
        api_version: Optional[str] = None
    ) -> str:
        """
        Track a user activity.
        
        Args:
            user_id: ID of the user
            activity_type: Type of activity
            description: Human-readable description
            metadata: Additional activity metadata
            api_version: API version used
            
        Returns:
            str: Activity tracking ID
        """
        # TODO: Implement actual user_activities table
        activity_entry = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "activity_type": activity_type,
            "description": description,
            "metadata": json.dumps(metadata) if metadata else None,
            "api_version": api_version,
            "timestamp": datetime.utcnow(),
        }
        
        # In a real implementation, this would insert into user_activities table
        # await self.db.execute(insert(UserActivity).values(**activity_entry))
        # await self.db.commit()
        
        return activity_entry["id"]
    
    async def get_user_activities(
        self,
        user_id: str,
        activity_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get user activities with optional filtering.
        
        Args:
            user_id: ID of the user
            activity_type: Optional activity type filter
            limit: Maximum number of activities to return
            offset: Number of activities to skip
            
        Returns:
            List of activity records
        """
        # TODO: Implement actual query against user_activities table
        # This is a placeholder
        return []


# Data Transformation Utilities

class DataTransformer:
    """Utility class for data transformation operations."""
    
    @staticmethod
    def serialize_for_json(obj: Any) -> Any:
        """
        Serialize complex objects for JSON serialization.
        
        Args:
            obj: Object to serialize
            
        Returns:
            JSON-serializable object
        """
        if isinstance(obj, datetime):
            return obj.isoformat() + "Z"
        elif isinstance(obj, date):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, uuid.UUID):
            return str(obj)
        elif isinstance(obj, Enum):
            return obj.value
        elif hasattr(obj, '__dict__'):
            # Handle SQLAlchemy models and other objects with __dict__
            return {
                key: DataTransformer.serialize_for_json(value)
                for key, value in obj.__dict__.items()
                if not key.startswith('_')
            }
        elif isinstance(obj, (list, tuple)):
            return [DataTransformer.serialize_for_json(item) for item in obj]
        elif isinstance(obj, dict):
            return {
                key: DataTransformer.serialize_for_json(value)
                for key, value in obj.items()
            }
        else:
            return obj
    
    @staticmethod
    def transform_keys(
        data: Dict[str, Any],
        transformation_map: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Transform dictionary keys based on a mapping.
        
        Args:
            data: Dictionary to transform
            transformation_map: Mapping of old_key -> new_key
            
        Returns:
            Dictionary with transformed keys
        """
        transformed = {}
        for key, value in data.items():
            new_key = transformation_map.get(key, key)
            transformed[new_key] = value
        return transformed
    
    @staticmethod
    def filter_fields(
        data: Dict[str, Any],
        allowed_fields: List[str],
        strict: bool = False
    ) -> Dict[str, Any]:
        """
        Filter dictionary to only include allowed fields.
        
        Args:
            data: Dictionary to filter
            allowed_fields: List of allowed field names
            strict: If True, raise error for unknown fields
            
        Returns:
            Filtered dictionary
            
        Raises:
            DataTransformationError: If strict=True and unknown fields found
        """
        if strict:
            unknown_fields = set(data.keys()) - set(allowed_fields)
            if unknown_fields:
                raise DataTransformationError(
                    f"Unknown fields: {', '.join(unknown_fields)}"
                )
        
        return {
            key: value for key, value in data.items()
            if key in allowed_fields
        }
    
    @staticmethod
    def flatten_nested_dict(
        data: Dict[str, Any],
        separator: str = ".",
        prefix: str = ""
    ) -> Dict[str, Any]:
        """
        Flatten a nested dictionary.
        
        Args:
            data: Dictionary to flatten
            separator: Separator for nested keys
            prefix: Prefix for keys
            
        Returns:
            Flattened dictionary
        """
        flattened = {}
        for key, value in data.items():
            new_key = f"{prefix}{separator}{key}" if prefix else key
            
            if isinstance(value, dict):
                flattened.update(
                    DataTransformer.flatten_nested_dict(value, separator, new_key)
                )
            else:
                flattened[new_key] = value
        
        return flattened
    
    @staticmethod
    def unflatten_dict(
        data: Dict[str, Any],
        separator: str = "."
    ) -> Dict[str, Any]:
        """
        Unflatten a dictionary with nested keys.
        
        Args:
            data: Flattened dictionary
            separator: Separator used in nested keys
            
        Returns:
            Nested dictionary
        """
        result = {}
        for key, value in data.items():
            keys = key.split(separator)
            current = result
            
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]
            
            current[keys[-1]] = value
        
        return result


# Business Operation Utilities

class BusinessOperationHelper:
    """Helper class for common business operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def bulk_update_resources(
        self,
        model_class: Type,
        updates: List[Dict[str, Any]],
        id_field: str = "id",
        user_context: Optional[Any] = None
    ) -> int:
        """
        Perform bulk updates on resources.
        
        Args:
            model_class: SQLAlchemy model class
            updates: List of update dictionaries with id and fields to update
            id_field: Name of the ID field
            user_context: User context for audit logging
            
        Returns:
            Number of records updated
        """
        updated_count = 0
        
        for update_data in updates:
            resource_id = update_data.pop(id_field)
            
            # Perform the update
            result = await self.db.execute(
                update(model_class)
                .where(getattr(model_class, id_field) == resource_id)
                .values(**update_data)
            )
            
            if result.rowcount > 0:
                updated_count += result.rowcount
                
                # Log the operation if user context is provided
                if user_context:
                    await log_operation(
                        db=self.db,
                        user_id=str(user_context.user.id),
                        operation_type=OperationType.UPDATE,
                        resource_type=model_class.__tablename__,
                        resource_id=str(resource_id),
                        details={"updated_fields": list(update_data.keys())},
                        api_version=user_context.api_version
                    )
        
        await self.db.commit()
        return updated_count
    
    async def soft_delete_resource(
        self,
        model_class: Type,
        resource_id: str,
        user_context: Optional[Any] = None,
        deleted_field: str = "is_deleted"
    ) -> bool:
        """
        Perform soft delete on a resource.
        
        Args:
            model_class: SQLAlchemy model class
            resource_id: ID of the resource to delete
            user_context: User context for audit logging
            deleted_field: Name of the soft delete field
            
        Returns:
            True if resource was deleted, False if not found
        """
        # Check if the model has the soft delete field
        if not hasattr(model_class, deleted_field):
            raise ValueError(f"Model {model_class.__name__} does not have field {deleted_field}")
        
        # Perform soft delete
        result = await self.db.execute(
            update(model_class)
            .where(model_class.id == resource_id)
            .values(**{deleted_field: True, "deleted_at": datetime.utcnow()})
        )
        
        if result.rowcount > 0:
            # Log the operation if user context is provided
            if user_context:
                await log_operation(
                    db=self.db,
                    user_id=str(user_context.user.id),
                    operation_type=OperationType.DELETE,
                    resource_type=model_class.__tablename__,
                    resource_id=resource_id,
                    details={"soft_delete": True},
                    api_version=user_context.api_version
                )
            
            await self.db.commit()
            return True
        
        return False
    
    async def check_resource_ownership(
        self,
        model_class: Type,
        resource_id: str,
        user_id: str,
        owner_field: str = "user_id"
    ) -> bool:
        """
        Check if a user owns a specific resource.
        
        Args:
            model_class: SQLAlchemy model class
            resource_id: ID of the resource
            user_id: ID of the user
            owner_field: Name of the owner field in the model
            
        Returns:
            True if user owns the resource, False otherwise
        """
        result = await self.db.execute(
            select(model_class)
            .where(
                model_class.id == resource_id,
                getattr(model_class, owner_field) == user_id
            )
        )
        
        return result.scalar_one_or_none() is not None
    
    async def get_resource_statistics(
        self,
        model_class: Type,
        user_id: Optional[str] = None,
        date_field: str = "created_at",
        owner_field: str = "user_id"
    ) -> Dict[str, Any]:
        """
        Get statistics for a resource type.
        
        Args:
            model_class: SQLAlchemy model class
            user_id: Optional user ID to filter by
            date_field: Name of the date field for time-based stats
            owner_field: Name of the owner field
            
        Returns:
            Dictionary with resource statistics
        """
        from sqlalchemy import func, and_
        
        # Base query
        query = select(func.count(model_class.id))
        
        # Filter by user if provided
        if user_id:
            query = query.where(getattr(model_class, owner_field) == user_id)
        
        # Total count
        total_result = await self.db.execute(query)
        total_count = total_result.scalar()
        
        # Count by date (last 30 days)
        thirty_days_ago = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        thirty_days_ago = thirty_days_ago.replace(day=thirty_days_ago.day - 30)
        
        recent_query = query.where(getattr(model_class, date_field) >= thirty_days_ago)
        recent_result = await self.db.execute(recent_query)
        recent_count = recent_result.scalar()
        
        return {
            "total_count": total_count,
            "recent_count": recent_count,
            "recent_period_days": 30,
            "resource_type": model_class.__tablename__
        }


# Utility Functions

def generate_operation_id() -> str:
    """Generate a unique operation ID."""
    return str(uuid.uuid4())


def validate_operation_permissions(
    user_context: Any,
    required_permissions: List[str],
    resource_owner_id: Optional[str] = None
) -> bool:
    """
    Validate that a user has permissions for an operation.
    
    Args:
        user_context: User context with permissions
        required_permissions: List of required permissions
        resource_owner_id: Optional resource owner ID for ownership check
        
    Returns:
        True if user has permissions, False otherwise
    """
    # Check if user owns the resource
    if resource_owner_id and str(user_context.user.id) == str(resource_owner_id):
        return True
    
    # Check if user has any of the required permissions
    return any(
        user_context.has_permission(permission)
        for permission in required_permissions
    )


def create_operation_context(
    user_context: Any,
    operation_type: OperationType,
    resource_type: str,
    resource_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create an operation context for tracking and logging.
    
    Args:
        user_context: User context
        operation_type: Type of operation
        resource_type: Type of resource
        resource_id: Optional resource ID
        
    Returns:
        Operation context dictionary
    """
    return {
        "operation_id": generate_operation_id(),
        "user_id": str(user_context.user.id),
        "operation_type": operation_type.value,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "api_version": user_context.api_version,
        "timestamp": datetime.utcnow(),
        "ip_address": user_context.request_metadata.get('ip_address'),
        "user_agent": user_context.request_metadata.get('user_agent')
    }


# Version-aware operation helpers

def create_version_aware_operation(
    v1_operation: Callable,
    v2_operation: Callable,
    default_operation: Optional[Callable] = None
) -> Callable:
    """
    Create an operation that behaves differently based on API version.
    
    Args:
        v1_operation: Operation function for API v1
        v2_operation: Operation function for API v2
        default_operation: Default operation for unknown versions
        
    Returns:
        Version-aware operation function
    """
    async def version_aware_operation(*args, api_version: Optional[str] = None, **kwargs):
        if api_version == "v1":
            return await v1_operation(*args, **kwargs)
        elif api_version == "v2":
            return await v2_operation(*args, **kwargs)
        elif default_operation:
            return await default_operation(*args, **kwargs)
        else:
            # Use v2 as default for forward compatibility
            return await v2_operation(*args, **kwargs)
    
    return version_aware_operation