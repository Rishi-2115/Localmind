# LocalMind Architecture

## Overview
LocalMind is a privacy-first AI Copilot tailored for Indian law firms, focusing on DPDP Act compliance. Each tenant operates in a completely isolated environment (dedicated namespace or VPC). No customer data leaves the tenant's infrastructure boundary.

## Components
- **API Gateway (FastAPI)**: Handles routing, authentication, rate limiting.
- **Ingestion (Celery/Redis)**: Asynchronously parses (PDF, DOCX), chunks, and embeds documents using Ollama.
- **Retrieval (FAISS + MinIO)**: Fast semantic search over tenant-specific documents.
- **Cache (Redis)**: Context Caching Engine ensures queries with high cosine similarity reuse LLM outputs to save cost and time.
- **Generation (Ollama)**: Local LLM execution. Default: `llama3.2:3b`.
- **Frontend (React)**: User interface for chat, upload, and audit.

## Multi-Tenancy Strategy
- Isolated Kubernetes namespaces via Helm.
- Separate database schemas, FAISS indexes (in MinIO), and cache keys.
- Completely air-gapped data planes for enterprise customers if required.
