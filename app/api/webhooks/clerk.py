"""
Clerk webhook handler for user synchronization.
Handles Clerk webhook events for user.created, user.updated, and user.deleted events.
"""

import logging
import hmac
import hashlib
from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.schemas.clerk_schemas import ClerkWebhookEvent, ClerkUser
from app.services.user_sync_service import UserSyncService
from app.services.clerk_service import get_clerk_service, ClerkService

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


async def verify_webhook_signature(request: Request) -> bool:
    """
    Verify webhook signature from Clerk.
    
    Args:
        request: FastAPI request object
        
    Returns:
        True if signature is valid
        
    Raises:
        HTTPException: If signature verification fails
    """
    current_settings = get_settings()
    if not current_settings.CLERK_WEBHOOK_SECRET:
        logger.error("Clerk webhook secret not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook secret not configured"
        )
    
    # Get signature from headers
    signature = request.headers.get("svix-signature")
    if not signature:
        logger.warning("Missing webhook signature header")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing webhook signature"
        )
    
    # Get timestamp from headers
    timestamp = request.headers.get("svix-timestamp")
    if not timestamp:
        logger.warning("Missing webhook timestamp header")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing webhook timestamp"
        )
    
    # Get request body
    body = await request.body()
    
    # Create the signed payload
    signed_payload = f"{timestamp}.{body.decode()}"
    
    # Extract signature components (Svix format: v1,signature1,signature2,...)
    signatures = {}
    for sig_part in signature.split(","):
        if "=" in sig_part:
            version, sig_value = sig_part.split("=", 1)
            signatures[version] = sig_value
    
    # Verify v1 signature
    if "v1" not in signatures:
        logger.warning("Missing v1 signature")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature format"
        )
    
    # Calculate expected signature
    expected_signature = hmac.new(
        current_settings.CLERK_WEBHOOK_SECRET.encode(),
        signed_payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures
    if not hmac.compare_digest(signatures["v1"], expected_signature):
        logger.warning("Invalid webhook signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature"
        )
    
    return True


@router.post("/clerk")
async def handle_clerk_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    clerk_service: ClerkService = Depends(get_clerk_service)
):
    """
    Handle Clerk webhook events for user synchronization.
    
    Supports the following event types:
    - user.created: Create new local user
    - user.updated: Update existing local user
    - user.deleted: Handle user deletion
    
    Args:
        request: FastAPI request object
        db: Database session
        clerk_service: Clerk service instance
        
    Returns:
        JSONResponse with processing status
    """
    try:
        # Verify webhook signature
        await verify_webhook_signature(request)
        
        # Parse webhook payload
        body = await request.body()
        webhook_data = await request.json()
        
        # Validate webhook event structure
        try:
            webhook_event = ClerkWebhookEvent(**webhook_data)
        except Exception as e:
            logger.error(f"Invalid webhook event structure: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook event structure"
            )
        
        logger.info(f"Received Clerk webhook event: {webhook_event.type}")
        
        # Initialize user sync service
        user_sync_service = UserSyncService(db)
        
        # Process event based on type
        if webhook_event.type == "user.created":
            result = await handle_user_created(webhook_event, user_sync_service)
        elif webhook_event.type == "user.updated":
            result = await handle_user_updated(webhook_event, user_sync_service)
        elif webhook_event.type == "user.deleted":
            result = await handle_user_deleted(webhook_event, user_sync_service)
        else:
            logger.info(f"Unhandled webhook event type: {webhook_event.type}")
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": "ignored",
                    "message": f"Event type {webhook_event.type} not handled",
                    "event_id": webhook_event.data.get("id")
                }
            )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed"
        )


async def handle_user_created(
    webhook_event: ClerkWebhookEvent,
    user_sync_service: UserSyncService
) -> Dict[str, Any]:
    """
    Handle user.created webhook event.
    
    Args:
        webhook_event: Clerk webhook event
        user_sync_service: User synchronization service
        
    Returns:
        Dict with processing result
    """
    try:
        # Extract user data from webhook
        user_data = webhook_event.data
        clerk_user = ClerkUser(**user_data)
        
        logger.info(f"Processing user.created event for user: {clerk_user.id}")
        
        # Sync user data (create new user)
        sync_result = await user_sync_service.sync_user_data(clerk_user, force_update=False)
        
        if sync_result.success:
            logger.info(f"Successfully created user from webhook: {clerk_user.primary_email}")
            return {
                "status": "success",
                "action": "user_created",
                "user_id": sync_result.user_id,
                "message": sync_result.message,
                "clerk_user_id": clerk_user.id
            }
        else:
            logger.error(f"Failed to create user from webhook: {sync_result.errors}")
            return {
                "status": "error",
                "action": "user_created",
                "message": sync_result.message,
                "errors": sync_result.errors,
                "clerk_user_id": clerk_user.id
            }
            
    except Exception as e:
        logger.error(f"Error processing user.created webhook: {e}")
        return {
            "status": "error",
            "action": "user_created",
            "message": f"Processing failed: {str(e)}",
            "clerk_user_id": webhook_event.data.get("id")
        }


async def handle_user_updated(
    webhook_event: ClerkWebhookEvent,
    user_sync_service: UserSyncService
) -> Dict[str, Any]:
    """
    Handle user.updated webhook event.
    
    Args:
        webhook_event: Clerk webhook event
        user_sync_service: User synchronization service
        
    Returns:
        Dict with processing result
    """
    try:
        # Extract user data from webhook
        user_data = webhook_event.data
        clerk_user = ClerkUser(**user_data)
        
        logger.info(f"Processing user.updated event for user: {clerk_user.id}")
        
        # Sync user data (update existing user)
        sync_result = await user_sync_service.sync_user_data(clerk_user, force_update=True)
        
        if sync_result.success:
            logger.info(f"Successfully updated user from webhook: {clerk_user.primary_email}")
            return {
                "status": "success",
                "action": "user_updated",
                "user_id": sync_result.user_id,
                "message": sync_result.message,
                "clerk_user_id": clerk_user.id
            }
        else:
            logger.error(f"Failed to update user from webhook: {sync_result.errors}")
            return {
                "status": "error",
                "action": "user_updated",
                "message": sync_result.message,
                "errors": sync_result.errors,
                "clerk_user_id": clerk_user.id
            }
            
    except Exception as e:
        logger.error(f"Error processing user.updated webhook: {e}")
        return {
            "status": "error",
            "action": "user_updated",
            "message": f"Processing failed: {str(e)}",
            "clerk_user_id": webhook_event.data.get("id")
        }


async def handle_user_deleted(
    webhook_event: ClerkWebhookEvent,
    user_sync_service: UserSyncService
) -> Dict[str, Any]:
    """
    Handle user.deleted webhook event.
    
    Args:
        webhook_event: Clerk webhook event
        user_sync_service: User synchronization service
        
    Returns:
        Dict with processing result
    """
    try:
        # Extract user ID from webhook
        clerk_user_id = webhook_event.data.get("id")
        if not clerk_user_id:
            logger.error("Missing user ID in user.deleted webhook")
            return {
                "status": "error",
                "action": "user_deleted",
                "message": "Missing user ID in webhook data"
            }
        
        logger.info(f"Processing user.deleted event for user: {clerk_user_id}")
        
        # Handle user deletion
        await user_sync_service.handle_user_deletion(clerk_user_id)
        
        logger.info(f"Successfully handled user deletion from webhook: {clerk_user_id}")
        return {
            "status": "success",
            "action": "user_deleted",
            "message": f"User {clerk_user_id} deletion handled successfully",
            "clerk_user_id": clerk_user_id
        }
        
    except Exception as e:
        logger.error(f"Error processing user.deleted webhook: {e}")
        return {
            "status": "error",
            "action": "user_deleted",
            "message": f"Processing failed: {str(e)}",
            "clerk_user_id": webhook_event.data.get("id")
        }


# Health check endpoint for webhook monitoring
@router.get("/clerk/health")
async def webhook_health_check():
    """
    Health check endpoint for Clerk webhook handler.
    
    Returns:
        Dict with health status
    """
    return {
        "status": "healthy",
        "service": "clerk_webhook_handler",
        "webhook_secret_configured": bool(settings.CLERK_WEBHOOK_SECRET),
        "supported_events": ["user.created", "user.updated", "user.deleted"]
    }