from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True, nullable=False)
    email = Column(String, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="staff")
    must_change_password = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Document(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True, index=True) # UUID
    tenant_id = Column(String, index=True, nullable=False)
    filename = Column(String, nullable=False)
    status = Column(String, default="processing") # processing, indexed, failed
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    error_message = Column(Text, nullable=True)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False) # query, ingest, etc.
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    doc_ids_accessed = Column(JSON, nullable=True)
    query_hash = Column(String, nullable=True)


class ContractRisk(Base):
    __tablename__ = "contract_risks"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False, index=True)
    tenant_id = Column(String, index=True, nullable=False)
    clause_type = Column(String, nullable=False) # liability, indemnification, termination, non_compete, jurisdiction, confidentiality
    risk_level = Column(String, nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    excerpt = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=True)
    reasoning = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
