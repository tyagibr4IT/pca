from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, ForeignKey, Text, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base

class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    # 'metadata' is a reserved attribute on declarative base; map DB column 'metadata' to
    # a different attribute name to avoid SQLAlchemy conflicts.
    metadata_json = Column('metadata', JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=True)
    role = Column(String, default="member")  # super_admin / admin / member
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    # Optional assignment of a client (tenant) to a user for scoping
    assigned_client_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)

    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    assigned_client = relationship("Tenant", foreign_keys=[assigned_client_id])

class CurrentMetric(Base):
    __tablename__ = "current_metrics"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    provider = Column(String)  # aws/azure/gcp
    resource_type = Column(String)
    resource_id = Column(String)
    data = Column(JSON)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer)
    provider = Column(String)
    snapshot_time = Column(DateTime, server_default=func.now())
    data = Column(JSON)