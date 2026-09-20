import os
import faiss
import numpy as np
import boto3
import json
import logging

logger = logging.getLogger(__name__)

MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin")

s3_client = boto3.client(
    's3',
    endpoint_url=f"http://{MINIO_ENDPOINT}",
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
)

class Retriever:
    def __init__(self):
        self.local_index_path = "/tmp/faiss_indexes"
        os.makedirs(self.local_index_path, exist_ok=True)

    def _get_tenant_index_path(self, tenant_id: str):
        return os.path.join(self.local_index_path, f"{tenant_id}.index")

    def _get_tenant_metadata_path(self, tenant_id: str):
        return os.path.join(self.local_index_path, f"{tenant_id}_meta.json")

    async def _download_index(self, tenant_id: str):
        bucket_name = f"tenant-{tenant_id}"
        index_file = self._get_tenant_index_path(tenant_id)
        meta_file = self._get_tenant_metadata_path(tenant_id)
        
        try:
            s3_client.download_file(bucket_name, "faiss.index", index_file)
            s3_client.download_file(bucket_name, "metadata.json", meta_file)
            return True
        except Exception as e:
            logger.error(f"Could not download index for tenant {tenant_id}: {e}")
            return False

    async def retrieve(self, tenant_id: str, query_embedding: list[float], top_k: int = 5):
        index_file = self._get_tenant_index_path(tenant_id)
        meta_file = self._get_tenant_metadata_path(tenant_id)
        
        if not os.path.exists(index_file):
            success = await self._download_index(tenant_id)
            if not success:
                return []

        try:
            index = faiss.read_index(index_file)
            query_vec = np.array([query_embedding], dtype=np.float32)
            faiss.normalize_L2(query_vec)
            
            distances, indices = index.search(query_vec, top_k)
            
            with open(meta_file, 'r') as f:
                metadata = json.load(f)
            
            results = []
            for idx in indices[0]:
                if idx != -1 and str(idx) in metadata:
                    results.append(metadata[str(idx)])
            
            return results
        except Exception as e:
            logger.error(f"Error during retrieval for tenant {tenant_id}: {e}")
            return []

retriever = Retriever()
