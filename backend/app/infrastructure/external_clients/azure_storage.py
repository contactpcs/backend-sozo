"""Azure storage client."""
import logging
from typing import Optional
from io import BytesIO


logger = logging.getLogger(__name__)


class AzureStorageClient:
    """Azure Blob Storage client."""
    
    def __init__(self, account_name: str, account_key: str, container_name: str = "documents"):
        """Initialize Azure storage client."""
        self.account_name = account_name
        self.account_key = account_key
        self.container_name = container_name
        
        try:
            from azure.storage.blob import BlobServiceClient
            self.client = BlobServiceClient(
                account_url=f"https://{account_name}.blob.core.windows.net",
                credential=account_key
            )
        except ImportError:
            logger.warning("Azure Storage SDK not installed")
            self.client = None
    
    async def upload_file(
        self,
        file_name: str,
        file_data: bytes,
        metadata: Optional[dict] = None
    ) -> str:
        """Upload file to Azure Blob Storage."""
        if not self.client:
            raise RuntimeError("Azure Storage client not initialized")
        
        try:
            container_client = self.client.get_container_client(self.container_name)
            blob_client = container_client.get_blob_client(file_name)
            
            await blob_client.upload_blob(file_data, overwrite=True)
            
            if metadata:
                blob_client.set_blob_metadata(metadata)
            
            logger.info(f"File uploaded to Azure: {file_name}")
            
            return f"{self.container_name}/{file_name}"
        
        except Exception as e:
            logger.error(f"Azure upload error: {str(e)}")
            raise
    
    async def download_file(self, file_name: str) -> bytes:
        """Download file from Azure Blob Storage."""
        if not self.client:
            raise RuntimeError("Azure Storage client not initialized")
        
        try:
            container_client = self.client.get_container_client(self.container_name)
            blob_client = container_client.get_blob_client(file_name)
            
            download_stream = await blob_client.download_blob()
            return download_stream.readall()
        
        except Exception as e:
            logger.error(f"Azure download error: {str(e)}")
            raise
    
    async def delete_file(self, file_name: str) -> bool:
        """Delete file from Azure Blob Storage."""
        if not self.client:
            raise RuntimeError("Azure Storage client not initialized")
        
        try:
            container_client = self.client.get_container_client(self.container_name)
            blob_client = container_client.get_blob_client(file_name)
            
            await blob_client.delete_blob()
            
            logger.info(f"File deleted from Azure: {file_name}")
            return True
        
        except Exception as e:
            logger.error(f"Azure delete error: {str(e)}")
            raise
    
    async def file_exists(self, file_name: str) -> bool:
        """Check if file exists in Azure Blob Storage."""
        if not self.client:
            return False
        
        try:
            container_client = self.client.get_container_client(self.container_name)
            blob_client = container_client.get_blob_client(file_name)
            
            return await blob_client.exists()
        
        except Exception:
            return False
