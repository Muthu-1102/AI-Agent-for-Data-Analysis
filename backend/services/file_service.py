import os
import uuid
import shutil
from fastapi import UploadFile

class FileService:
    """
    Backend Engineer Service responsible for handling local file operations, 
    specifically managing the secure ingestion and storage of uploaded CSV datasets.
    """
    def __init__(self):
        # Resolve the absolute path to the global 'data' directory.
        # Assuming the standard structure where 'data/' sits alongside 'backend/'
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.data_dir = os.path.join(base_dir, "data")
        
        # Ensure the target directory exists before we attempt to write there
        os.makedirs(self.data_dir, exist_ok=True)
        
    async def save_upload_file(self, file: UploadFile) -> str:
        """
        Ingests a FastAPI UploadFile, securely writes it to the local filesystem
        in chunks (to prevent OOM errors on massive datasets), and returns a unique ID.
        """
        # Minor security validation: Only accept CSV
        if not file.filename.endswith('.csv'):
            raise ValueError("Invalid file format. Only .csv files are supported.")
            
        # Generate a unique cryptographic dataset ID to prevent naming collisions
        dataset_id = f"dataset_{uuid.uuid4().hex[:8]}.csv"
        file_path = os.path.join(self.data_dir, dataset_id)
        
        try:
            # Write out to disk chunk-by-chunk using shutil
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            raise RuntimeError(f"FileService failed to persist dataset to disk: {str(e)}")
        finally:
            # Always cleanly close the SpooledTemporaryFile handler 
            file.file.close()
            
        return dataset_id

    def get_file_path(self, dataset_id: str) -> str:
        """
        Resolves a dataset_id back to its absolute hardware file path.
        """
        file_path = os.path.join(self.data_dir, dataset_id)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Dataset block {dataset_id} is missing from storage.")
        return file_path
