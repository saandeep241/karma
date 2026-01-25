"""
Storage Service - Abstracts file operations for local filesystem and Cloud Storage.
Supports both local development and GCP Cloud Storage.
"""

import json
from typing import Optional, Dict, Any
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)

# Try to import Cloud Storage (optional)
try:
    from google.cloud import storage
    from google.cloud.exceptions import NotFound
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False
    storage = None
    NotFound = Exception


class StorageService:
    """Abstract storage service that works with local filesystem or Cloud Storage."""
    
    def __init__(self):
        self.settings = get_settings()
        self.use_cloud_storage = self.settings.use_cloud_storage
        self.bucket_name = self.settings.gcs_bucket_name
        
        # Note: Local filesystem paths are kept for reference but not used
        # when Cloud Storage is disabled (files are not written)
        
        # Note: We don't create local directories anymore since files are only written
        # when Cloud Storage is enabled. The database is the primary source of truth.
        
        # Initialize Cloud Storage client if enabled
        self.gcs_client = None
        self.gcs_bucket = None
        if self.use_cloud_storage:
            self._init_cloud_storage()
    
    
    def _init_cloud_storage(self):
        """Initialize Google Cloud Storage client and bucket."""
        if not GCS_AVAILABLE:
            logger.warning("⚠️ Cloud Storage library not available. Install: pip install google-cloud-storage")
            self.use_cloud_storage = False
            return
        
        try:
            self.gcs_client = storage.Client()
            self.gcs_bucket = self.gcs_client.bucket(self.bucket_name)
            
            # Verify bucket exists
            if not self.gcs_bucket.exists():
                logger.warning(f"⚠️ Cloud Storage bucket '{self.bucket_name}' does not exist. Files will not be written.")
                self.use_cloud_storage = False
            else:
                logger.info(f"✅ Cloud Storage enabled: gs://{self.bucket_name}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Cloud Storage: {e}. Files will not be written.")
            self.use_cloud_storage = False
    
    
    def _write_file_gcs(self, blob_path: str, content: str) -> None:
        """Write content to Cloud Storage."""
        if not self.gcs_bucket:
            raise RuntimeError("Cloud Storage not initialized")
        
        blob = self.gcs_bucket.blob(blob_path)
        blob.upload_from_string(content, content_type='application/json')
    
    def _read_file_gcs(self, blob_path: str) -> Optional[str]:
        """Read content from Cloud Storage."""
        if not self.gcs_bucket:
            raise RuntimeError("Cloud Storage not initialized")
        
        try:
            blob = self.gcs_bucket.blob(blob_path)
            if not blob.exists():
                return None
            return blob.download_as_text()
        except NotFound:
            return None
    
    def _file_exists_gcs(self, blob_path: str) -> bool:
        """Check if file exists in Cloud Storage."""
        if not self.gcs_bucket:
            return False
        
        try:
            blob = self.gcs_bucket.blob(blob_path)
            return blob.exists()
        except Exception:
            return False
    
    def write_json(self, directory: str, filename: str, data: Dict[str, Any]) -> bool:
        """
        Write JSON data to storage.
        
        If Cloud Storage is disabled, files are NOT written (they're just backups/audit logs).
        The database is the primary source of truth.
        
        Args:
            directory: Directory name (tasks, reasoning, memory, task_details)
            filename: Filename (e.g., "2026-01-17.json")
            data: Data to write (will be serialized to JSON)
        
        Returns:
            True if successful, False otherwise (or if storage is disabled)
        """
        # If Cloud Storage is disabled, skip writing files (they're not functionally required)
        if not self.use_cloud_storage:
            logger.debug(f"⏭️  Skipping file write (Cloud Storage disabled): {directory}/{filename}")
            return True  # Return True to indicate "success" (no-op)
        
        try:
            content = json.dumps(data, indent=2, ensure_ascii=False)
            blob_path = f"{directory}/{filename}"
            self._write_file_gcs(blob_path, content)
            logger.debug(f"📤 Wrote to Cloud Storage: {blob_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to write {directory}/{filename}: {e}")
            return False
    
    def read_json(self, directory: str, filename: str) -> Optional[Dict[str, Any]]:
        """
        Read JSON data from storage.
        
        If Cloud Storage is disabled, returns None (files are not written/read).
        
        Args:
            directory: Directory name (tasks, reasoning, memory, task_details)
            filename: Filename (e.g., "2026-01-17.json")
        
        Returns:
            Parsed JSON data or None if not found or storage is disabled
        """
        # If Cloud Storage is disabled, files don't exist (they're not written)
        if not self.use_cloud_storage:
            return None
        
        try:
            blob_path = f"{directory}/{filename}"
            content = self._read_file_gcs(blob_path)
            if content:
                logger.debug(f"📥 Read from Cloud Storage: {blob_path}")
                return json.loads(content)
            return None
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse JSON from {directory}/{filename}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Failed to read {directory}/{filename}: {e}")
            return None
    
    @property
    def is_cloud_storage_enabled(self) -> bool:
        """Check if Cloud Storage is enabled."""
        return self.use_cloud_storage
    
    def file_exists(self, directory: str, filename: str) -> bool:
        """
        Check if a file exists in storage.
        
        If Cloud Storage is disabled, returns False (files are not written).
        
        Args:
            directory: Directory name
            filename: Filename
        
        Returns:
            True if file exists, False otherwise
        """
        # If Cloud Storage is disabled, files don't exist
        if not self.use_cloud_storage:
            return False
        
        try:
            blob_path = f"{directory}/{filename}"
            return self._file_exists_gcs(blob_path)
        except Exception as e:
            logger.error(f"❌ Failed to check existence of {directory}/{filename}: {e}")
            return False
    
    def append_to_file(self, directory: str, filename: str, content: str) -> bool:
        """
        Append content to a file (for log files).
        
        If Cloud Storage is disabled, files are NOT written.
        
        Args:
            directory: Directory name
            filename: Filename
            content: Content to append
        
        Returns:
            True if successful, False otherwise (or if storage is disabled)
        """
        # If Cloud Storage is disabled, skip writing files
        if not self.use_cloud_storage:
            logger.debug(f"⏭️  Skipping file append (Cloud Storage disabled): {directory}/{filename}")
            return True  # Return True to indicate "success" (no-op)
        
        try:
            # For Cloud Storage, we need to read, append, and write
            blob_path = f"{directory}/{filename}"
            existing_content = self._read_file_gcs(blob_path) or ""
            new_content = existing_content + content
            self._write_file_gcs(blob_path, new_content)
            logger.debug(f"📝 Appended to Cloud Storage: {blob_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to append to {directory}/{filename}: {e}")
            return False


# Global storage service instance
_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """Get the global storage service instance."""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
