"""
Session management service for secure user session handling with Redis.
Provides session creation, validation, and cleanup functionality.
"""

import json
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

from app.core.redis import redis_client
from app.core.config import get_settings
from app.core.exceptions import AuthenticationError, ValidationError

logger = logging.getLogger(__name__)
settings = get_settings()


class SessionService:
    """Service for managing user sessions with Redis backend."""

    def __init__(self):
        self.redis = redis_client
        self.session_prefix = "session:"
        self.user_sessions_prefix = "user_sessions:"
        self.default_ttl = 3600 * 24  # 24 hours
        self.max_sessions_per_user = 10

    async def create_session(
        self,
        user_id: str,
        clerk_id: str,
        email: str,
        role: str,
        permissions: List[str],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        ttl: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a new user session.
        
        Args:
            user_id: User ID
            clerk_id: Clerk user ID
            email: User email
            role: User role
            permissions: User permissions
            ip_address: Client IP address
            user_agent: Client user agent
            ttl: Session TTL in seconds
            
        Returns:
            Dict containing session information
        """
        try:
            session_id = str(uuid.uuid4())
            session_ttl = ttl or self.default_ttl
            
            session_data = {
                "session_id": session_id,
                "user_id": user_id,
                "clerk_id": clerk_id,
                "email": email,
                "role": role,
                "permissions": permissions,
                "created_at": datetime.utcnow().isoformat(),
                "last_activity": datetime.utcnow().isoformat(),
                "ip_address": ip_address,
                "user_agent": user_agent,
                "is_active": True
            }
            
            # Store session data
            session_key = f"{self.session_prefix}{session_id}"
            await self.redis.setex(
                session_key,
                session_ttl,
                json.dumps(session_data)
            )
            
            # Add session to user's session list
            await self._add_user_session(user_id, session_id, session_ttl)
            
            # Cleanup old sessions if user has too many
            await self._cleanup_user_sessions(user_id)
            
            logger.info(f"Created session {session_id} for user {user_id}")
            return session_data
            
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            raise AuthenticationError("Failed to create session")

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data by session ID.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session data or None if not found
        """
        try:
            session_key = f"{self.session_prefix}{session_id}"
            session_data = await self.redis.get(session_key)
            
            if not session_data:
                return None
            
            return json.loads(session_data)
            
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            return None

    async def validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Validate session and update last activity.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session data if valid, None otherwise
        """
        try:
            session_data = await self.get_session(session_id)
            
            if not session_data or not session_data.get("is_active"):
                return None
            
            # Update last activity
            session_data["last_activity"] = datetime.utcnow().isoformat()
            
            # Update session in Redis
            session_key = f"{self.session_prefix}{session_id}"
            ttl = await self.redis.ttl(session_key)
            
            if ttl > 0:
                await self.redis.setex(
                    session_key,
                    ttl,
                    json.dumps(session_data)
                )
            
            return session_data
            
        except Exception as e:
            logger.error(f"Error validating session {session_id}: {e}")
            return None

    async def invalidate_session(self, session_id: str) -> bool:
        """
        Invalidate a specific session.
        
        Args:
            session_id: Session ID to invalidate
            
        Returns:
            True if session was invalidated
        """
        try:
            # Get session data to find user ID
            session_data = await self.get_session(session_id)
            if not session_data:
                return False
            
            user_id = session_data.get("user_id")
            
            # Remove session
            session_key = f"{self.session_prefix}{session_id}"
            await self.redis.delete(session_key)
            
            # Remove from user's session list
            if user_id:
                await self._remove_user_session(user_id, session_id)
            
            logger.info(f"Invalidated session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error invalidating session {session_id}: {e}")
            return False

    async def invalidate_user_sessions(
        self, 
        user_id: str, 
        exclude_session: Optional[str] = None
    ) -> int:
        """
        Invalidate all sessions for a user.
        
        Args:
            user_id: User ID
            exclude_session: Session ID to exclude from invalidation
            
        Returns:
            Number of sessions invalidated
        """
        try:
            user_sessions = await self.get_user_sessions(user_id)
            invalidated_count = 0
            
            for session in user_sessions:
                session_id = session.get("session_id")
                if session_id and session_id != exclude_session:
                    if await self.invalidate_session(session_id):
                        invalidated_count += 1
            
            logger.info(f"Invalidated {invalidated_count} sessions for user {user_id}")
            return invalidated_count
            
        except Exception as e:
            logger.error(f"Error invalidating user sessions for {user_id}: {e}")
            return 0

    async def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all active sessions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of active sessions
        """
        try:
            user_sessions_key = f"{self.user_sessions_prefix}{user_id}"
            session_ids = await self.redis.smembers(user_sessions_key)
            
            sessions = []
            for session_id in session_ids:
                session_data = await self.get_session(session_id.decode())
                if session_data and session_data.get("is_active"):
                    sessions.append(session_data)
            
            return sessions
            
        except Exception as e:
            logger.error(f"Error getting user sessions for {user_id}: {e}")
            return []

    async def refresh_session(self, session_id: str, ttl: Optional[int] = None) -> bool:
        """
        Refresh session TTL.
        
        Args:
            session_id: Session ID
            ttl: New TTL in seconds
            
        Returns:
            True if session was refreshed
        """
        try:
            session_data = await self.get_session(session_id)
            if not session_data:
                return False
            
            session_ttl = ttl or self.default_ttl
            session_key = f"{self.session_prefix}{session_id}"
            
            # Update last activity
            session_data["last_activity"] = datetime.utcnow().isoformat()
            
            # Refresh session with new TTL
            await self.redis.setex(
                session_key,
                session_ttl,
                json.dumps(session_data)
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error refreshing session {session_id}: {e}")
            return False

    async def cleanup_expired_sessions(self) -> int:
        """
        Cleanup expired sessions from user session lists.
        
        Returns:
            Number of expired sessions cleaned up
        """
        try:
            # This is a maintenance operation that should be run periodically
            # Get all user session keys
            pattern = f"{self.user_sessions_prefix}*"
            user_session_keys = []
            
            async for key in self.redis.scan_iter(match=pattern):
                user_session_keys.append(key.decode())
            
            cleaned_count = 0
            for user_sessions_key in user_session_keys:
                user_id = user_sessions_key.replace(self.user_sessions_prefix, "")
                session_ids = await self.redis.smembers(user_sessions_key)
                
                for session_id in session_ids:
                    session_id_str = session_id.decode()
                    session_data = await self.get_session(session_id_str)
                    
                    # If session doesn't exist or is inactive, remove from user list
                    if not session_data or not session_data.get("is_active"):
                        await self._remove_user_session(user_id, session_id_str)
                        cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} expired sessions")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}")
            return 0

    async def _add_user_session(self, user_id: str, session_id: str, ttl: int) -> None:
        """Add session to user's session list."""
        try:
            user_sessions_key = f"{self.user_sessions_prefix}{user_id}"
            await self.redis.sadd(user_sessions_key, session_id)
            await self.redis.expire(user_sessions_key, ttl + 3600)  # Extra hour buffer
        except Exception as e:
            logger.error(f"Error adding user session: {e}")

    async def _remove_user_session(self, user_id: str, session_id: str) -> None:
        """Remove session from user's session list."""
        try:
            user_sessions_key = f"{self.user_sessions_prefix}{user_id}"
            await self.redis.srem(user_sessions_key, session_id)
        except Exception as e:
            logger.error(f"Error removing user session: {e}")

    async def _cleanup_user_sessions(self, user_id: str) -> None:
        """Cleanup old sessions if user has too many."""
        try:
            user_sessions = await self.get_user_sessions(user_id)
            
            if len(user_sessions) > self.max_sessions_per_user:
                # Sort by last activity and remove oldest sessions
                user_sessions.sort(key=lambda x: x.get("last_activity", ""))
                sessions_to_remove = user_sessions[:-self.max_sessions_per_user]
                
                for session in sessions_to_remove:
                    session_id = session.get("session_id")
                    if session_id:
                        await self.invalidate_session(session_id)
                        
        except Exception as e:
            logger.error(f"Error cleaning up user sessions: {e}")


# Global service instance
session_service = SessionService()


def get_session_service() -> SessionService:
    """Get session service instance."""
    return session_service