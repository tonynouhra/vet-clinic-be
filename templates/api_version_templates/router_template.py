# Template for creating new API version routers
# Replace {VERSION}, {RESOURCE}, and placeholders with actual values

from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.{resource}.controller import {Resource}Controller  # Same controller as previous versions!
from app.api.schemas.v{VERSION}.{resource} import (
    {Resource}CreateV{VERSION}, 
    {Resource}ResponseV{VERSION}, 
    {Resource}UpdateV{VERSION},
    {Resource}FilterV{VERSION}
)
from app.app_helpers.dependency_helpers import get_controller
from app.app_helpers.response_helpers import success_response, created_response, paginated_response

router = APIRouter(prefix="/{resource}", tags=["{resource}-v{VERSION}"])


@router.get("/", response_model=dict)
async def list_{resource}_v{VERSION}(
        # Common parameters
        page: int = Query(1, ge=1, description="Page number"),
        size: int = Query(20, ge=1, le=100, description="Page size"),
        search: Optional[str] = Query(None, description="Search term"),
        is_active: Optional[bool] = Query(None, description="Filter by active status"),
        
        # Parameters from previous versions
        # Add parameters from previous API versions here
        
        # New parameters for V{VERSION}
        # new_param: Optional[str] = Query(None, description="New filter parameter"),
        
        controller: {Resource}Controller = get_controller({Resource}Controller)
):
    """V{VERSION}: List {resource} with enhanced filtering."""
    result = await controller.list_{resource}(
        page=page, 
        size=size, 
        search=search, 
        is_active=is_active,
        # Include parameters from previous versions
        # Include new V{VERSION} parameters
        # new_param=new_param,
    )

    # Format response with V{VERSION} schema
    return paginated_response(
        data=[{Resource}ResponseV{VERSION}.from_orm(item).dict() for item in result["{resource}"]],
        total=result["total"],
        page=result["page"],
        size=result["size"],
        message="{Resource} retrieved successfully"
    )


@router.post("/", response_model=dict)
async def create_{resource}_v{VERSION}(
        {resource}_data: {Resource}CreateV{VERSION},
        controller: {Resource}Controller = get_controller({Resource}Controller)
):
    """V{VERSION}: Create {resource} with enhanced fields."""
    {resource} = await controller.create_{resource}({resource}_data)
    return created_response(
        data={Resource}ResponseV{VERSION}.from_orm({resource}).dict(),
        message="{Resource} created successfully"
    )


@router.get("/{{{resource}_id}}", response_model=dict)
async def get_{resource}_v{VERSION}(
        {resource}_id: str,
        controller: {Resource}Controller = get_controller({Resource}Controller)
):
    """V{VERSION}: Get {resource} by ID with enhanced response."""
    {resource} = await controller.get_{resource}({resource}_id)
    return success_response(
        data={Resource}ResponseV{VERSION}.from_orm({resource}).dict(),
        message="{Resource} retrieved successfully"
    )


@router.put("/{{{resource}_id}}", response_model=dict)
async def update_{resource}_v{VERSION}(
        {resource}_id: str,
        {resource}_data: {Resource}UpdateV{VERSION},
        controller: {Resource}Controller = get_controller({Resource}Controller)
):
    """V{VERSION}: Update {resource} with enhanced fields."""
    {resource} = await controller.update_{resource}({resource}_id, {resource}_data)
    return success_response(
        data={Resource}ResponseV{VERSION}.from_orm({resource}).dict(),
        message="{Resource} updated successfully"
    )


@router.delete("/{{{resource}_id}}", response_model=dict)
async def delete_{resource}_v{VERSION}(
        {resource}_id: str,
        controller: {Resource}Controller = get_controller({Resource}Controller)
):
    """V{VERSION}: Delete {resource}."""
    await controller.delete_{resource}({resource}_id)
    return success_response(
        data=None,
        message="{Resource} deleted successfully"
    )


# Additional endpoints specific to V{VERSION} (if needed)
@router.get("/{{{resource}_id}}/enhanced-info", response_model=dict)
async def get_{resource}_enhanced_info_v{VERSION}(
        {resource}_id: str,
        controller: {Resource}Controller = get_controller({Resource}Controller)
):
    """V{VERSION}: Get enhanced {resource} information (new in V{VERSION})."""
    # This endpoint might be specific to V{VERSION} with new functionality
    enhanced_info = await controller.get_{resource}_enhanced_info({resource}_id)
    return success_response(
        data=enhanced_info,
        message="Enhanced {resource} information retrieved successfully"
    )