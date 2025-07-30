"""
Redis connection and caching utilities.
"""
import json
from typing import Any, Optional, Union
import redis.asyncio as redis
from redis.asyncio import Redis

from app.core.config import settings


class RedisClient:
    """Redis client wrapper for caching operations."""
    
    def __init__(self):
        self.redis: Optional[Redis] = None
    
    async def connect(self) -> None:
        """Connect to Redis."""
        self.redis = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
    
    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis."""
        if not self.redis:
            await self.connect()
        return await self.redis.get(key)
    
    async def set(
        self, 
        key: str, 
        value: Union[str, dict, list], 
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in Redis with optional TTL."""
        if not self.redis:
            await self.connect()
        
        # Serialize complex data types
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        
        ttl = ttl or settings.REDIS_CACHE_TTL
        return await self.redis.setex(key, ttl, value)
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis."""
        if not self.redis:
            await self.connect()
        return bool(await self.redis.delete(key))
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        if not self.redis:
            await self.connect()
        return bool(await self.redis.exists(key))
    
    async def get_json(self, key: str) -> Optional[Union[dict, list]]:
        """Get JSON value from Redis."""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None
    
    async def set_json(
        self, 
        key: str, 
        value: Union[dict, list], 
        ttl: Optional[int] = None
    ) -> bool:
        """Set JSON value in Redis."""
        return await self.set(key, value, ttl)


# Global Redis client instance
redis_client = RedisClient()