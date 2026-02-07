"""
SQLAlchemy ORM models for Cloud Optimizer database schema.

This module defines the database schema using SQLAlchemy's declarative ORM.
All models inherit from Base and map to PostgreSQL tables. The schema supports
multi-tenancy, user management, metrics caching, and chat history with vector embeddings.

Database Tables:
    - tenants: Client/organization records with cloud credentials
    - users: User accounts with role-based access control
    - current_metrics: Latest metrics snapshot per resource
    - metric_snapshots: Historical metrics for time-series analysis
    - cloud_metrics_cache: 30-minute TTL cache for resource inventory
    - chat_messages: Chat history with optional vector embeddings for semantic search

Relationships:
    - User → Tenant (many-to-one): User belongs to a tenant
    - User → Tenant (assigned_client): Optional client assignment for scoped access
    - CloudMetricsCache → Tenant: Cache entries linked to tenants

Indexes:
    - tenants.name: Unique index for fast tenant lookup
    - users.username, users.email: Unique indexes for authentication
    - cloud_metrics_cache: Composite index on (tenant_id, provider, fetched_at)

Migrations:
    Use Alembic for schema changes:
        alembic revision --autogenerate -m "description"
        alembic upgrade head

Author: Cloud Optimizer Team
Version: 2.0.0
Last Modified: 2026-01-25
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, ForeignKey, Text, Float, Index, Table
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base


# Association table for many-to-many relationship between roles and permissions
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True),
    Column('created_at', DateTime, server_default=func.now())
)

# Association table for user-specific permission overrides
user_permissions = Table(
    'user_permissions',
    Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
    Column('permission_id', Integer, ForeignKey('permissions.id', ondelete='CASCADE'), nullable=False),
    Column('created_at', DateTime, server_default=func.now()),
    Index('ix_user_permission_unique', 'user_id', 'permission_id', unique=True)
)

class Tenant(Base):
    """
    Client/Organization model for multi-tenant cloud management.
    
    Each tenant represents a separate organization/customer with their own cloud
    provider credentials. Tenants are isolated from each other in the system.
    
    Attributes:
        id (int): Primary key, auto-incrementing tenant ID
        name (str): Unique tenant name (e.g., "Acme Corp", "HLLMMU")
        metadata_json (dict): JSON object containing:
            - provider (str): Cloud provider ("aws", "azure", "gcp")
            - Cloud credentials (varies by provider):
                AWS: clientId, clientSecret, region
                Azure: tenantId, clientId, clientSecret, subscriptionId
                GCP: projectId, serviceAccountJson
        created_at (datetime): Tenant creation timestamp (UTC)
    
    Relationships:
        - users: List of User objects belonging to this tenant
        - cache_entries: List of CloudMetricsCache objects for this tenant
    
    SQLAlchemy Note:
        'metadata' column is mapped to 'metadata_json' attribute to avoid
        conflict with SQLAlchemy's reserved 'metadata' attribute.
    
    Example metadata_json for AWS:
        {
            "provider": "aws",
            "clientId": "AKIAIOSFODNN7EXAMPLE",
            "clientSecret": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "region": "us-east-1"
        }
    """
    __tablename__ = "tenants"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    # 'metadata' is a reserved attribute on declarative base; map DB column 'metadata' to
    # a different attribute name to avoid SQLAlchemy conflicts.
    metadata_json = Column('metadata', JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class Role(Base):
    """
    Role model for RBAC (Role-Based Access Control).
    
    Roles define groups of permissions that can be assigned to users.
    Default roles: superadmin, admin, member.
    
    Attributes:
        id (int): Primary key, auto-incrementing role ID
        name (str): Unique role name (e.g., "superadmin", "admin", "member")
        description (str): Human-readable description of the role
        is_system (bool): System role (cannot be deleted/modified)
        created_at (datetime): Role creation timestamp (UTC)
    
    Relationships:
        - permissions: List of Permission objects assigned to this role
        - users: List of User objects with this role
    
    Example:
        role = Role(
            name="admin",
            description="Administrator with management access",
            is_system=True
        )
    """
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(String, nullable=True)
    is_system = Column(Boolean, default=False)  # System roles cannot be deleted
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")
    users = relationship("User", back_populates="role_obj")


class Permission(Base):
    """
    Permission model for fine-grained access control.
    
    Permissions define specific actions that can be performed on resources.
    Format: resource.action (e.g., 'users.create', 'clients.view')
    
    Attributes:
        id (int): Primary key, auto-incrementing permission ID
        name (str): Unique permission name (e.g., "users.create")
        resource (str): Resource type (e.g., "users", "clients", "metrics")
        action (str): Action on resource (e.g., "view", "create", "edit", "delete")
        description (str): Human-readable description of the permission
        created_at (datetime): Permission creation timestamp (UTC)
    
    Relationships:
        - roles: List of Role objects that have this permission
    
    Example:
        permission = Permission(
            name="users.create",
            resource="users",
            action="create",
            description="Create new users in the system"
        )
    """
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    resource = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")


class User(Base):
    """
    User account model with role-based access control (RBAC).
    
    Users belong to a tenant and have assigned roles that control their
    permissions. Supports both local authentication (hashed password) and
    external identity providers (Azure AD).
    
    Attributes:
        id (int): Primary key, auto-incrementing user ID
        tenant_id (int): Foreign key to tenant the user belongs to (required)
        username (str): Unique username for login (e.g., "john.doe")
        email (str): Unique email address for notifications
        hashed_password (str): Bcrypt hashed password (null for SSO users)
        role (str): User role for authorization:
            - "super_admin": Full system access, manage all tenants
            - "admin": Manage tenant, add/remove users
            - "member": Read-only access to tenant resources
        is_active (bool): Account status (false = disabled/suspended)
        created_at (datetime): Account creation timestamp (UTC)
        assigned_client_id (int): Optional client assignment for scoped access
    
    Relationships:
        - tenant: Tenant object this user belongs to
        - assigned_client: Optional Tenant object for client-specific access
    
    Authentication:
        - Local: Username + hashed_password (bcrypt)
        - Azure AD: Username + external identity (hashed_password = null)
    
    Authorization Hierarchy:
        super_admin > admin > member
    
    Example:
        user = User(
            tenant_id=1,
            username="alice",
            email="alice@example.com",
            hashed_password=hash_password("secret123"),
            role="admin",
            is_active=True
        )
    """
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)  # Foreign key to roles table
    is_active = Column(Boolean, default=True)
    status = Column(String, default="active")  # active / inactive
    created_at = Column(DateTime, server_default=func.now())
    # Optional assignment of a client (tenant) to a user for scoping
    assigned_client_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)

    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    assigned_client = relationship("Tenant", foreign_keys=[assigned_client_id])
    role_obj = relationship("Role", back_populates="users")
    # Many-to-many relationship with clients through UserClientPermission
    client_permissions = relationship("UserClientPermission", back_populates="user", cascade="all, delete-orphan")
    # Many-to-many relationship with permissions (user-specific overrides)
    user_permissions = relationship("Permission", secondary=user_permissions, backref="users_with_permission")

class UserClientPermission(Base):
    """
    Association table for user-client access with permission levels.
    
    Allows a user to have access to multiple clients with different permission
    levels (viewer, editor, approver) for each client.
    
    Attributes:
        id (int): Primary key
        user_id (int): Foreign key to users table
        client_id (int): Foreign key to tenants table (the client)
        permission (str): Permission level for this user-client pair:
            - "viewer": Read-only access to client resources
            - "editor": Can modify client resources
            - "approver": Can approve changes and access sensitive data
        created_at (datetime): Permission grant timestamp
    
    Relationships:
        - user: User object this permission belongs to
        - client: Tenant object (client) this permission grants access to
    """
    __tablename__ = "user_client_permissions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    client_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    permission = Column(String, default="viewer", nullable=False)  # viewer / editor / approver
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="client_permissions")
    client = relationship("Tenant")
    
    # Ensure unique user-client pairs
    __table_args__ = (
        Index('ix_user_client_unique', 'user_id', 'client_id', unique=True),
    )

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

class CloudMetricsCache(Base):
    """
    30-minute TTL cache for cloud resource inventory.
    
    This model stores complete resource inventory snapshots to minimize expensive
    cloud provider API calls. Cache entries are validated by age and refreshed
    when stale (>30 minutes) or when explicitly requested (force_refresh=true).
    
    Cache Strategy:
        - TTL: 30 minutes (METRICS_CACHE_TTL_MINUTES constant)
        - Key: (tenant_id, provider) - one cache entry per tenant per provider
        - Invalidation: Age-based (automatic) or explicit (force_refresh parameter)
    
    Attributes:
        id (int): Primary key, auto-incrementing cache entry ID
        tenant_id (int): Foreign key to tenant (indexed for fast lookup)
        provider (str): Cloud provider ("aws", "azure", "gcp") - indexed
        metrics_data (dict): Complete resource inventory JSON containing:
            - resources (dict): Nested structure by category:
                - compute: ec2, vm, instances, lambda, etc.
                - database: rds, sql, cloud_sql, etc.
                - storage: s3, blob, buckets, etc.
                - networking: vpc, vnet, networks, etc.
            - summary (dict): Resource counts by type
        fetched_at (datetime): When data was fetched from cloud (indexed for TTL)
    
    Relationships:
        - tenant: Tenant object this cache belongs to
    
    Indexes:
        - tenant_id: Fast lookup by tenant
        - provider: Fast lookup by cloud provider
        - fetched_at: Fast age-based cache validation
        - Composite: (tenant_id, provider, fetched_at) for optimal query performance
    
    Performance:
        - Cache hit: ~50ms (database query)
        - Cache miss: 5-15 seconds (cloud provider API fetch)
        - Reduces cloud API costs by ~95% (assuming typical usage patterns)
    
    Example metrics_data:
        {
            "resources": {
                "compute": {
                    "ec2": [
                        {"id": "i-123", "type": "t2.micro", "state": "running", ...}
                    ]
                },
                "storage": {
                    "s3": [{"bucket": "my-bucket", ...}]
                }
            },
            "summary": {"compute_ec2": 1, "storage_s3": 1}
        }
    """
    __tablename__ = "cloud_metrics_cache"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    provider = Column(String, nullable=False, index=True)  # aws/azure/gcp
    metrics_data = Column(JSON, nullable=False)  # Complete resource inventory
    fetched_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    
    tenant = relationship("Tenant", foreign_keys=[tenant_id])

class ChatMessage(Base):
    """
    Chat conversation history with optional vector embeddings for semantic search.
    
    Stores chat messages between users and the AI assistant, with support for
    vector embeddings to enable semantic search over conversation history.
    This allows the AI to reference past discussions and maintain context.
    
    Attributes:
        id (int): Primary key, auto-incrementing message ID
        tenant_id (int): Foreign key to tenant (conversation isolation)
        sender (str): Message sender ("user" or "assistant")
        message (str): Message content (plain text or markdown)
        timestamp (datetime): Message creation time (UTC)
        meta_data (dict): Optional metadata for function calls, tool usage:
            - function_name (str): Name of function called (if applicable)
            - function_args (dict): Function arguments
            - tool_outputs (list): Results from tool invocations
            - model (str): AI model used (e.g., "gpt-4o-mini")
        embedding (str): JSON array string of 1536-dimensional vector
            - Generated by OpenAI text-embedding-3-small model
            - Used for semantic similarity search
            - Format: "[0.123, -0.456, 0.789, ...]"
    
    Vector Embeddings:
        - Dimensions: 1536 (OpenAI text-embedding-3-small)
        - Use Case: Find similar past conversations
        - Storage: JSON string for portability (can use pgvector extension)
        - Search: Cosine similarity between query embedding and message embeddings
    
    Indexes:
        - tenant_id: Fast filtering by client
        - timestamp: Fast sorting by time
        - (tenant_id, timestamp): Optimized for loading chat history
    
    SQLAlchemy Note:
        'metadata' column is mapped to 'meta_data' attribute to avoid
        conflict with SQLAlchemy's reserved 'metadata' attribute.
    
    Example for user message:
        {
            "sender": "user",
            "message": "Show me my AWS EC2 instances",
            "meta_data": null,
            "embedding": "[0.012, -0.034, 0.056, ...]"
        }
    
    Example for assistant message with function call:
        {
            "sender": "assistant",
            "message": "Here are your 5 EC2 instances in us-east-1...",
            "meta_data": {
                "function_name": "fetch_aws_resources",
                "function_args": {"client_id": 13, "credentials": {...}},
                "model": "gpt-4o-mini"
            },
            "embedding": "[0.123, -0.234, 0.345, ...]"
        }
    """
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    sender = Column(String, nullable=False)  # 'user' or 'assistant'
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, server_default=func.now(), index=True)
    # map 'meta_data' Python attribute to 'metadata' DB column (avoid SQLAlchemy conflict)
    meta_data = Column('metadata', JSON, nullable=True)  # store function calls, tool usage, etc.
    # Vector embedding for semantic search (1536 dimensions for OpenAI text-embedding-3-small)
    embedding = Column(Text, nullable=True)  # Store as JSON array string for portability
    
    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    
    # Composite indexes for optimized queries
    __table_args__ = (
        # Index for loading chat history (most common query)
        Index('ix_chat_tenant_timestamp', 'tenant_id', 'timestamp'),
    )