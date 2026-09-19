# LocalMind API Documentation

## Authentication
- **`POST /api/v1/auth/login`**: Authenticate and retrieve JWT token.

## Query
- **`POST /api/v1/query`**: Submit a natural language query over indexed documents. Returns SSE stream of the generated response.

## Ingestion
- **`POST /api/v1/ingest/upload`**: Upload documents (PDF, DOCX) for processing. Returns an array of task IDs.
- **`GET /api/v1/ingest/status/{task_id}`**: Check the status of an ingestion task.

## Administration
- **`GET /api/v1/admin/users`**: List users for the current tenant.
- **`GET /api/v1/admin/documents`**: List indexed documents for the current tenant.

## Audit
- **`GET /api/v1/audit/`**: Retrieve the full audit log of queries and ingestions (Admin only).
