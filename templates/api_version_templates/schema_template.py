# Template for creating new API version schemas
# Replace {VERSION}, {RESOURCE}, and {PREVIOUS_VERSION} with actual values

from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, List, Union
from datetime import datetime
from enum import Enum

# Import previous version for reference (optional)
# from app.api.schemas.v{PREVIOUS_VERSION}.{resource} import {Resource}ResponseV{PREVIOUS_VERSION}

class {Resource}CreateV{VERSION}(BaseModel):
    """V{VERSION} {resource} creation schema - enhanced with new fields."""
    
    # Core fields (present in all versions)
    # Add your core required fields here
    
    # Fields from previous versions
    # Copy relevant fields from previous version schemas
    
    # New fields for V{VERSION}
    # Add new optional fields specific to this version
    # new_field: Optional[str] = None  # New in V{VERSION}
    
    class Config:
        # Add any Pydantic configuration
        str_strip_whitespace = True
        validate_assignment = True

class {Resource}ResponseV{VERSION}(BaseModel):
    """V{VERSION} {resource} response schema - enhanced fields."""
    
    # Core fields (present in all versions)
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Fields from previous versions
    # Copy relevant fields from previous version schemas
    
    # New fields for V{VERSION}
    # Add new fields specific to this version
    # new_field: Optional[str]  # New in V{VERSION}
    
    class Config:
        from_attributes = True
        # Add any additional Pydantic configuration

class {Resource}UpdateV{VERSION}(BaseModel):
    """V{VERSION} {resource} update schema - enhanced fields."""
    
    # All fields should be optional for updates
    # Include fields from previous versions + new V{VERSION} fields
    
    # Fields from previous versions (all optional)
    # Copy relevant fields from previous version update schemas
    
    # New fields for V{VERSION} (all optional)
    # new_field: Optional[str] = None  # New in V{VERSION}
    
    class Config:
        # Add any Pydantic configuration
        str_strip_whitespace = True
        validate_assignment = True

# Additional schemas as needed (List, Filter, etc.)
class {Resource}FilterV{VERSION}(BaseModel):
    """V{VERSION} {resource} filtering schema."""
    
    # Common filter fields
    page: int = 1
    size: int = 20
    search: Optional[str] = None
    is_active: Optional[bool] = None
    
    # Fields from previous versions
    # Copy relevant filter fields from previous versions
    
    # New filter fields for V{VERSION}
    # new_filter_field: Optional[str] = None  # New in V{VERSION}
    
    class Config:
        str_strip_whitespace = True

# Example enum for new version (if needed)
class {Resource}StatusV{VERSION}(str, Enum):
    """V{VERSION} {resource} status enum - enhanced with new statuses."""
    
    # Statuses from previous versions
    ACTIVE = "active"
    INACTIVE = "inactive"
    
    # New statuses for V{VERSION}
    # NEW_STATUS = "new_status"  # New in V{VERSION}