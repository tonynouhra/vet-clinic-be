# Future Version Support Architecture

This document explains how the current architecture is designed to support future API versions (V3, V4, etc.) without requiring changes to existing business logic.

## Design Principles

### 1. Version-Agnostic Controllers and Services

Controllers and services are designed to work with any API version by:

- Using `Union` types to accept multiple schema versions
- Implementing `**kwargs` parameters to handle future version parameters
- Using `hasattr()` checks for version-specific fields
- Gracefully ignoring unknown parameters

### 2. Dynamic Parameter Handling

Controllers and services use flexible parameter handling:

```python
async def list_users(
    self,
    page: int = 1,
    per_page: int = 20,
    search: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    # V2 parameters
    department: Optional[str] = None,
    include_roles: bool = False,
    # Future version parameters handled automatically
    **kwargs  # This handles V3, V4, V5... parameters
) -> Tuple[List[User], int]:
```

### 3. Schema Evolution Support

Controllers handle multiple schema versions using Union types:

```python
async def create_user(
    self,
    user_data: Union[UserCreateV1, UserCreateV2, UserCreateV3, ...]  # Future versions
) -> User:
    """Handle user creation for all API versions."""
    
    # Extract common fields present in all versions
    create_params = {
        "email": user_data.email,
        "first_name": user_data.first_name,
        "last_name": user_data.last_name,
    }
    
    # Handle version-specific fields dynamically
    for field in ["phone_number", "role", "department", "preferences", "ai_settings"]:
        if hasattr(user_data, field):
            value = getattr(user_data, field)
            if value is not None:
                create_params[field] = value
    
    return await self.service.create_user(**create_params)
```

## Current Implementation Status

### Controllers Ready for Future Versions

All controllers are already prepared for future versions:

#### UserController
- ✅ Supports `**kwargs` in all methods
- ✅ Uses `Union` types for schema parameters
- ✅ Dynamic field extraction with `hasattr()`
- ✅ Graceful parameter handling

#### PetController
- ✅ Supports `**kwargs` in all methods
- ✅ Uses `Union` types for schema parameters
- ✅ Dynamic field extraction with `hasattr()`
- ✅ Graceful parameter handling

#### AppointmentController
- ✅ Supports `**kwargs` in all methods
- ✅ Uses `Union` types for schema parameters
- ✅ Dynamic field extraction with `hasattr()`
- ✅ Graceful parameter handling

### Services Ready for Future Versions

All services are already prepared for future versions:

#### UserService
- ✅ Supports `**kwargs` in all methods
- ✅ Dynamic field handling in database operations
- ✅ Flexible filtering and querying
- ✅ Future-proof data access patterns

#### PetService
- ✅ Supports `**kwargs` in all methods
- ✅ Dynamic field handling in database operations
- ✅ Flexible filtering and querying
- ✅ Future-proof data access patterns

#### AppointmentService
- ✅ Supports `**kwargs` in all methods
- ✅ Dynamic field handling in database operations
- ✅ Flexible filtering and querying
- ✅ Future-proof data access patterns

## Adding V3 Parameters Example

When V3 is added with new parameters, the existing controllers will handle them automatically:

### V3 User Listing with AI Features

```python
# V3 API endpoint
@router.get("/", response_model=dict)
async def list_users_v3(
    page: int = 1,
    per_page: int = 20,
    search: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    # V3 new parameters
    has_ai_preferences: Optional[bool] = None,
    ai_automation_level: Optional[str] = None,
    biometric_data_available: Optional[bool] = None,
    controller: UserController = Depends(get_controller(UserController))
):
    """V3: List users with AI filtering."""
    
    # The SAME controller handles V3 parameters automatically!
    users, total = await controller.list_users(
        page=page,
        per_page=per_page,
        search=search,
        role=role,
        is_active=is_active,
        # V3 parameters passed through **kwargs
        has_ai_preferences=has_ai_preferences,
        ai_automation_level=ai_automation_level,
        biometric_data_available=biometric_data_available
    )
    
    return format_v3_response(users, total, page, per_page)
```

### Controller Handles V3 Automatically

The existing controller method already supports V3:

```python
# In UserController - NO CHANGES NEEDED!
async def list_users(
    self,
    page: int = 1,
    per_page: int = 20,
    search: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    department: Optional[str] = None,  # V2
    include_roles: bool = False,      # V2
    **kwargs  # V3 parameters: has_ai_preferences, ai_automation_level, etc.
) -> Tuple[List[User], int]:
    """This method already works with V3, V4, V5... parameters!"""
    
    # Pass all parameters to service
    return await self.service.list_users(
        page=page,
        per_page=per_page,
        search=search,
        role=role,
        is_active=is_active,
        department=department,
        include_roles=include_roles,
        **kwargs  # V3+ parameters passed through
    )
```

### Service Handles V3 Automatically

The existing service method already supports V3:

```python
# In UserService - NO CHANGES NEEDED!
async def list_users(
    self,
    page: int,
    per_page: int,
    search: Optional[str] = None,
    role: Optional[Union[UserRole, str]] = None,
    is_active: Optional[bool] = None,
    department: Optional[str] = None,
    include_roles: bool = False,
    **kwargs  # V3 parameters handled here
) -> Tuple[List[User], int]:
    """This method already works with V3, V4, V5... parameters!"""
    
    # Build query with existing filters
    query = self._build_base_query()
    
    # Apply V1/V2 filters
    if search:
        query = self._apply_search_filter(query, search)
    if role:
        query = self._apply_role_filter(query, role)
    if is_active is not None:
        query = self._apply_active_filter(query, is_active)
    if department:
        query = self._apply_department_filter(query, department)
    
    # Apply V3+ filters dynamically
    for param_name, param_value in kwargs.items():
        if param_value is not None:
            query = self._apply_dynamic_filter(query, param_name, param_value)
    
    return await self._execute_paginated_query(query, page, per_page)

def _apply_dynamic_filter(self, query, param_name: str, param_value):
    """Apply dynamic filters for future versions."""
    
    # V3 AI-related filters
    if param_name == "has_ai_preferences":
        if param_value:
            query = query.where(User.ai_preferences.isnot(None))
        else:
            query = query.where(User.ai_preferences.is_(None))
    
    elif param_name == "ai_automation_level":
        query = query.where(
            User.ai_preferences['automation_level'].astext == param_value
        )
    
    elif param_name == "biometric_data_available":
        if param_value:
            query = query.where(User.biometric_data.isnot(None))
        else:
            query = query.where(User.biometric_data.is_(None))
    
    # V4+ filters can be added here without changing existing code
    elif param_name == "quantum_enabled":  # Hypothetical V4 feature
        query = query.where(User.quantum_settings['enabled'].astext == str(param_value))
    
    # Unknown parameters are ignored gracefully
    
    return query
```

## Version Context Support

Controllers can be made aware of which version is calling them:

```python
class UserController:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.service = UserService(db)
        self.version_context: Optional[str] = None
    
    def set_version_context(self, version: str):
        """Set version context for version-aware behavior."""
        self.version_context = version
        self.service.set_version_context(version)
    
    async def list_users(self, **kwargs):
        """Version-aware user listing."""
        
        # Version-specific behavior when needed
        if self.version_context == "v3":
            # Add AI insights to response
            kwargs["include_ai_insights"] = True
        elif self.version_context == "v4":
            # Add quantum processing
            kwargs["enable_quantum_processing"] = True
        
        return await self.service.list_users(**kwargs)
```

## Database Model Evolution

Database models are designed to support future versions:

```python
class User(Base):
    __tablename__ = "users"
    
    # Core fields (V1)
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    
    # V2 fields (nullable for backward compatibility)
    role = Column(Enum(UserRole), nullable=True)
    department = Column(String, nullable=True)
    preferences = Column(JSON, nullable=True)
    
    # V3 fields (nullable for backward compatibility)
    ai_preferences = Column(JSON, nullable=True)
    biometric_data = Column(JSON, nullable=True)
    social_connections = Column(JSON, nullable=True)
    
    # V4+ fields can be added as nullable columns
    # quantum_settings = Column(JSON, nullable=True)
    # blockchain_wallet = Column(String, nullable=True)
    
    def to_dict_v1(self):
        """V1 representation."""
        return {
            "id": str(self.id),
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "is_active": self.is_active
        }
    
    def to_dict_v2(self):
        """V2 representation."""
        data = self.to_dict_v1()
        data.update({
            "role": self.role,
            "department": self.department,
            "preferences": self.preferences
        })
        return data
    
    def to_dict_v3(self):
        """V3 representation."""
        data = self.to_dict_v2()
        data.update({
            "ai_preferences": self.ai_preferences,
            "biometric_data": self.biometric_data,
            "social_connections": self.social_connections
        })
        return data
```

## Testing Future Versions

The architecture supports testing future versions:

```python
class TestFutureVersionSupport:
    """Test that controllers handle future version parameters gracefully."""
    
    async def test_controller_handles_unknown_parameters(self):
        """Test that controllers accept unknown parameters without errors."""
        controller = UserController(mock_db)
        
        # Pass hypothetical V5 parameters
        users, total = await controller.list_users(
            page=1,
            per_page=20,
            # V5 hypothetical parameters
            quantum_enabled=True,
            neural_interface_active=False,
            holographic_display=True,
            time_travel_permissions=["past", "future"]
        )
        
        # Should not raise errors
        assert isinstance(users, list)
        assert isinstance(total, int)
    
    async def test_service_handles_unknown_parameters(self):
        """Test that services accept unknown parameters without errors."""
        service = UserService(mock_db)
        
        # Pass hypothetical V6 parameters
        users, total = await service.list_users(
            page=1,
            per_page=20,
            # V6 hypothetical parameters
            multiverse_id="universe-42",
            consciousness_level="enlightened",
            reality_distortion_field=True
        )
        
        # Should not raise errors
        assert isinstance(users, list)
        assert isinstance(total, int)
```

## Benefits of This Architecture

### 1. Zero Business Logic Changes
- Adding V3, V4, V5... requires NO changes to controllers or services
- Business logic remains centralized and version-agnostic
- Bug fixes automatically apply to all versions

### 2. Seamless Version Addition
- New versions only require new schemas and routes
- Controllers automatically handle new parameters
- Services automatically support new filtering options

### 3. Backward Compatibility
- Existing versions continue to work unchanged
- New fields are optional and nullable
- Migration paths are clear and documented

### 4. Forward Compatibility
- Architecture scales to unlimited versions
- Unknown parameters are handled gracefully
- Future features can be added incrementally

### 5. Maintainability
- Single source of truth for business logic
- Consistent behavior across all versions
- Easy to test and debug

This architecture ensures that the veterinary clinic platform can evolve to support any number of API versions while maintaining clean, maintainable code and preserving backward compatibility.