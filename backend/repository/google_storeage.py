import os
import logging
from typing import Optional, List, Dict
from google.cloud import storage
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class GCSHelper:
    """Helper class for Google Cloud Storage operations"""
    
    def __init__(self, bucket_name: str = None):
        """
        Initialize GCS client.
        
        Args:
            bucket_name: Name of the GCS bucket (defaults to env variable)
        """
        self.client = storage.Client()
        self.bucket_name = bucket_name or os.getenv('GCS_BUCKET_NAME', 'woo-hackathon')
        self.bucket = self.client.bucket(self.bucket_name)
        logger.info(f"GCS Helper initialized for bucket: {self.bucket_name}")
    
    def upload_file(
        self,
        local_filepath: str,
        destination_blob_name: str = None,
        content_type: str = None,
        make_public: bool = False
    ) -> Dict[str, str]:
        """
        Upload a file to Google Cloud Storage.
        
        Args:
            local_filepath: Path to the local file
            destination_blob_name: Destination path in GCS (defaults to filename)
            content_type: MIME type of the file
            make_public: Whether to make the file publicly accessible
            
        Returns:
            Dict with 'url', 'blob_name', 'public_url' (if public)
        """
        try:
            # Default blob name to filename with timestamp
            if not destination_blob_name:
                filename = os.path.basename(local_filepath)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                destination_blob_name = f"documents/{timestamp}_{filename}"
            
            # Create blob
            blob = self.bucket.blob(destination_blob_name)
            
            # Set content type if provided
            if content_type:
                blob.content_type = content_type
            elif local_filepath.lower().endswith('.pdf'):
                blob.content_type = 'application/pdf'
            
            # Upload file
            logger.info(f"Uploading {local_filepath} to gs://{self.bucket_name}/{destination_blob_name}")
            blob.upload_from_filename(local_filepath)
            
            # Make public if requested
            public_url = None
            if make_public:
                blob.make_public()
                public_url = blob.public_url
                logger.info(f"File made public: {public_url}")
            
            # Generate signed URL (valid for 7 days)
            signed_url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(days=7),
                method="GET"
            )
            
            result = {
                'blob_name': destination_blob_name,
                'url': signed_url,
                'bucket': self.bucket_name,
                'size': blob.size,
                'content_type': blob.content_type,
                'created': blob.time_created.isoformat() if blob.time_created else None
            }
            
            if public_url:
                result['public_url'] = public_url
            
            logger.info(f"✓ Successfully uploaded to GCS: {destination_blob_name}")
            return result
            
        except Exception as e:
            logger.error(f"Error uploading to GCS: {e}")
            raise
    
    def download_file(
        self,
        blob_name: str,
        destination_filepath: str
    ) -> str:
        """
        Download a file from Google Cloud Storage.
        
        Args:
            blob_name: Path to the file in GCS
            destination_filepath: Local path to save the file
            
        Returns:
            Local file path
        """
        try:
            blob = self.bucket.blob(blob_name)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(destination_filepath), exist_ok=True)
            
            logger.info(f"Downloading gs://{self.bucket_name}/{blob_name} to {destination_filepath}")
            blob.download_to_filename(destination_filepath)
            
            logger.info(f"✓ Successfully downloaded from GCS")
            return destination_filepath
            
        except Exception as e:
            logger.error(f"Error downloading from GCS: {e}")
            raise
    
    def list_files(self, prefix: str = None, max_results: int = 100) -> List[Dict]:
        """
        List files in the bucket.
        
        Args:
            prefix: Filter files by prefix (e.g., 'documents/')
            max_results: Maximum number of results
            
        Returns:
            List of file metadata dicts
        """
        try:
            blobs = self.client.list_blobs(
                self.bucket_name,
                prefix=prefix,
                max_results=max_results
            )
            
            files = []
            for blob in blobs:
                files.append({
                    'name': blob.name,
                    'size': blob.size,
                    'content_type': blob.content_type,
                    'created': blob.time_created.isoformat() if blob.time_created else None,
                    'updated': blob.updated.isoformat() if blob.updated else None,
                    'public_url': blob.public_url if blob.public_url else None
                })
            
            return files
            
        except Exception as e:
            logger.error(f"Error listing files from GCS: {e}")
            raise
    
    def delete_file(self, blob_name: str) -> bool:
        """
        Delete a file from Google Cloud Storage.
        
        Args:
            blob_name: Path to the file in GCS
            
        Returns:
            True if successful
        """
        try:
            blob = self.bucket.blob(blob_name)
            blob.delete()
            logger.info(f"✓ Deleted {blob_name} from GCS")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file from GCS: {e}")
            raise
    
    def get_signed_url(self, blob_name: str, expiration_days: int = 7) -> str:
        """
        Generate a signed URL for temporary access to a file.
        
        Args:
            blob_name: Path to the file in GCS
            expiration_days: Number of days the URL is valid
            
        Returns:
            Signed URL
        """
        try:
            blob = self.bucket.blob(blob_name)
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(days=expiration_days),
                method="GET"
            )
            return url
            
        except Exception as e:
            logger.error(f"Error generating signed URL: {e}")
            raise