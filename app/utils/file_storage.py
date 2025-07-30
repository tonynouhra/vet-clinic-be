"""
File storage utilities for Supabase integration.
"""
import os
import uuid
from typing import Optional, BinaryIO
from datetime import datetime

from app.core.config import settings


class FileStorageService:
    """Service for handling file uploads and storage."""
    
    def __init__(self):
        self.supabase_url = settings.SUPABASE_URL
        self.supabase_key = settings.SUPABASE_KEY
        self.bucket_name = settings.SUPABASE_BUCKET
    
    def generate_unique_filename(self, original_filename: str) -> str:
        """
        Generate a unique filename to prevent conflicts.
        
        Args:
            original_filename: Original file name
            
        Returns:
            str: Unique filename
        """
        file_extension = os.path.splitext(original_filename)[1]
        unique_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{timestamp}_{unique_id}{file_extension}"
    
    def validate_file_type(self, filename: str, allowed_types: list[str]) -> bool:
        """
        Validate file type based on extension.
        
        Args:
            filename: File name to validate
            allowed_types: List of allowed file extensions
            
        Returns:
            bool: True if file type is allowed
        """
        file_extension = os.path.splitext(filename)[1].lower()
        return file_extension in allowed_types
    
    def validate_file_size(self, file_size: int, max_size_mb: int = 10) -> bool:
        """
        Validate file size.
        
        Args:
            file_size: File size in bytes
            max_size_mb: Maximum allowed size in MB
            
        Returns:
            bool: True if file size is within limits
        """
        max_size_bytes = max_size_mb * 1024 * 1024
        return file_size <= max_size_bytes
    
    async def upload_file(
        self,
        file: BinaryIO,
        filename: str,
        folder: str = "uploads"
    ) -> Optional[str]:
        """
        Upload file to Supabase storage.
        
        Args:
            file: File object to upload
            filename: Original filename
            folder: Storage folder
            
        Returns:
            str: File URL if successful, None otherwise
        """
        # This is a placeholder implementation
        # In a real implementation, you would use the Supabase Python client
        # to upload the file to Supabase storage
        
        # For now, return a mock URL
        unique_filename = self.generate_unique_filename(filename)
        return f"{self.supabase_url}/storage/v1/object/public/{self.bucket_name}/{folder}/{unique_filename}"
    
    async def delete_file(self, file_path: str) -> bool:
        """
        Delete file from Supabase storage.
        
        Args:
            file_path: Path to file in storage
            
        Returns:
            bool: True if deletion successful
        """
        # This is a placeholder implementation
        # In a real implementation, you would use the Supabase Python client
        # to delete the file from Supabase storage
        return True
    
    def get_file_url(self, file_path: str) -> str:
        """
        Get public URL for a file.
        
        Args:
            file_path: Path to file in storage
            
        Returns:
            str: Public URL for the file
        """
        return f"{self.supabase_url}/storage/v1/object/public/{self.bucket_name}/{file_path}"


# Global file storage service instance
file_storage = FileStorageService()