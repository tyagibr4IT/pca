"""
Permission definitions and role-permission mappings for RBAC.

This module defines all available permissions in the system and maps them to roles.
Permissions follow the pattern: resource.action (e.g., 'users.create', 'clients.view')
"""

from enum import Enum
from typing import Dict, List, Set


class Permission(str, Enum):
    """
    All available permissions in the system.
    Format: RESOURCE_ACTION
    """
    # User Management Permissions
    USERS_VIEW = "users.view"
    USERS_CREATE = "users.create"
    USERS_EDIT = "users.edit"
    USERS_DELETE = "users.delete"
    USERS_MANAGE_ROLES = "users.manage_roles"
    
    # Permission Management
    PERMISSIONS_MANAGE = "permissions.manage"
    
    # Client Management Permissions
    CLIENTS_VIEW = "clients.view"
    CLIENTS_CREATE = "clients.create"
    CLIENTS_EDIT = "clients.edit"
    CLIENTS_DELETE = "clients.delete"
    CLIENTS_ASSIGN = "clients.assign"
    
    # Metrics & Monitoring Permissions
    METRICS_VIEW = "metrics.view"
    METRICS_EXPORT = "metrics.export"
    METRICS_RECOMMENDATIONS_VIEW = "metrics.recommendations.view"
    METRICS_RECOMMENDATIONS_APPLY = "metrics.recommendations.apply"
    
    # Chat/AI Assistant Permissions
    CHAT_ACCESS = "chat.access"
    CHAT_HISTORY_VIEW = "chat.history.view"
    CHAT_HISTORY_DELETE = "chat.history.delete"
    
    # System Administration Permissions
    SYSTEM_SETTINGS_VIEW = "system.settings.view"
    SYSTEM_SETTINGS_EDIT = "system.settings.edit"
    SYSTEM_AUDIT_LOGS_VIEW = "system.audit_logs.view"
    SYSTEM_REPORTS_GENERATE = "system.reports.generate"
    
    # Cloud Resource Permissions
    RESOURCES_VIEW = "resources.view"
    RESOURCES_MANAGE = "resources.manage"
    RESOURCES_COSTS_VIEW = "resources.costs.view"


class PermissionCategory(str, Enum):
    """Permission categories for organization"""
    USERS = "users"
    CLIENTS = "clients"
    METRICS = "metrics"
    CHAT = "chat"
    SYSTEM = "system"
    RESOURCES = "resources"


# Permission metadata with descriptions
PERMISSION_METADATA: Dict[str, Dict[str, str]] = {
    # User Management
    Permission.USERS_VIEW: {
        "name": "View Users",
        "description": "View user list and details",
        "category": PermissionCategory.USERS
    },
    Permission.USERS_CREATE: {
        "name": "Create Users",
        "description": "Create new users in the system",
        "category": PermissionCategory.USERS
    },
    Permission.USERS_EDIT: {
        "name": "Edit Users",
        "description": "Edit user details and information",
        "category": PermissionCategory.USERS
    },
    Permission.USERS_DELETE: {
        "name": "Delete Users",
        "description": "Delete users from the system",
        "category": PermissionCategory.USERS
    },
    Permission.USERS_MANAGE_ROLES: {
        "name": "Manage User Roles",
        "description": "Assign and change user roles",
        "category": PermissionCategory.USERS
    },
    
    # Client Management
    Permission.CLIENTS_VIEW: {
        "name": "View Clients",
        "description": "View client/tenant list and details",
        "category": PermissionCategory.CLIENTS
    },
    Permission.CLIENTS_CREATE: {
        "name": "Create Clients",
        "description": "Create new clients/tenants",
        "category": PermissionCategory.CLIENTS
    },
    Permission.CLIENTS_EDIT: {
        "name": "Edit Clients",
        "description": "Edit client details and configuration",
        "category": PermissionCategory.CLIENTS
    },
    Permission.CLIENTS_DELETE: {
        "name": "Delete Clients",
        "description": "Delete clients/tenants",
        "category": PermissionCategory.CLIENTS
    },
    Permission.CLIENTS_ASSIGN: {
        "name": "Assign Clients",
        "description": "Assign clients to users",
        "category": PermissionCategory.CLIENTS
    },
    
    # Metrics & Monitoring
    Permission.METRICS_VIEW: {
        "name": "View Metrics",
        "description": "View metrics and dashboards",
        "category": PermissionCategory.METRICS
    },
    Permission.METRICS_EXPORT: {
        "name": "Export Metrics",
        "description": "Export metrics data",
        "category": PermissionCategory.METRICS
    },
    Permission.METRICS_RECOMMENDATIONS_VIEW: {
        "name": "View Recommendations",
        "description": "View cost optimization recommendations",
        "category": PermissionCategory.METRICS
    },
    Permission.METRICS_RECOMMENDATIONS_APPLY: {
        "name": "Apply Recommendations",
        "description": "Apply optimization recommendations",
        "category": PermissionCategory.METRICS
    },
    
    # Chat/AI Assistant
    Permission.CHAT_ACCESS: {
        "name": "Access Chat",
        "description": "Access AI chat assistant",
        "category": PermissionCategory.CHAT
    },
    Permission.CHAT_HISTORY_VIEW: {
        "name": "View Chat History",
        "description": "View chat conversation history",
        "category": PermissionCategory.CHAT
    },
    Permission.CHAT_HISTORY_DELETE: {
        "name": "Delete Chat History",
        "description": "Delete chat conversation history",
        "category": PermissionCategory.CHAT
    },
    
    # System Administration
    Permission.SYSTEM_SETTINGS_VIEW: {
        "name": "View Settings",
        "description": "View system settings and configuration",
        "category": PermissionCategory.SYSTEM
    },
    Permission.SYSTEM_SETTINGS_EDIT: {
        "name": "Edit Settings",
        "description": "Edit system settings and configuration",
        "category": PermissionCategory.SYSTEM
    },
    Permission.SYSTEM_AUDIT_LOGS_VIEW: {
        "name": "View Audit Logs",
        "description": "View system audit logs",
        "category": PermissionCategory.SYSTEM
    },
    Permission.SYSTEM_REPORTS_GENERATE: {
        "name": "Generate Reports",
        "description": "Generate system reports",
        "category": PermissionCategory.SYSTEM
    },
    
    # Cloud Resources
    Permission.RESOURCES_VIEW: {
        "name": "View Resources",
        "description": "View cloud resources",
        "category": PermissionCategory.RESOURCES
    },
    Permission.RESOURCES_MANAGE: {
        "name": "Manage Resources",
        "description": "Manage cloud resources (start/stop VMs, etc.)",
        "category": PermissionCategory.RESOURCES
    },
    Permission.RESOURCES_COSTS_VIEW: {
        "name": "View Costs",
        "description": "View cost analysis and reports",
        "category": PermissionCategory.RESOURCES
    },
}


# Default role-permission mappings
DEFAULT_ROLE_PERMISSIONS: Dict[str, List[str]] = {
    "superadmin": [
        # All permissions - full access
        Permission.USERS_VIEW,
        Permission.USERS_CREATE,
        Permission.USERS_EDIT,
        Permission.USERS_DELETE,
        Permission.USERS_MANAGE_ROLES,
        
        Permission.CLIENTS_VIEW,
        Permission.CLIENTS_CREATE,
        Permission.CLIENTS_EDIT,
        Permission.CLIENTS_DELETE,
        Permission.CLIENTS_ASSIGN,
        
        Permission.METRICS_VIEW,
        Permission.METRICS_EXPORT,
        Permission.METRICS_RECOMMENDATIONS_VIEW,
        Permission.METRICS_RECOMMENDATIONS_APPLY,
        
        Permission.CHAT_ACCESS,
        Permission.CHAT_HISTORY_VIEW,
        Permission.CHAT_HISTORY_DELETE,
        
        Permission.SYSTEM_SETTINGS_VIEW,
        Permission.SYSTEM_SETTINGS_EDIT,
        Permission.SYSTEM_AUDIT_LOGS_VIEW,
        Permission.SYSTEM_REPORTS_GENERATE,
        
        Permission.RESOURCES_VIEW,
        Permission.RESOURCES_MANAGE,
        Permission.RESOURCES_COSTS_VIEW,
    ],
    
    "admin": [
        # Management access - no role management or system settings edit
        Permission.USERS_VIEW,
        Permission.USERS_CREATE,
        Permission.USERS_EDIT,
        
        Permission.CLIENTS_VIEW,
        Permission.CLIENTS_CREATE,
        Permission.CLIENTS_EDIT,
        Permission.CLIENTS_DELETE,
        Permission.CLIENTS_ASSIGN,
        
        Permission.METRICS_VIEW,
        Permission.METRICS_EXPORT,
        Permission.METRICS_RECOMMENDATIONS_VIEW,
        Permission.METRICS_RECOMMENDATIONS_APPLY,
        
        Permission.CHAT_ACCESS,
        Permission.CHAT_HISTORY_VIEW,
        Permission.CHAT_HISTORY_DELETE,
        
        Permission.SYSTEM_SETTINGS_VIEW,
        Permission.SYSTEM_AUDIT_LOGS_VIEW,
        Permission.SYSTEM_REPORTS_GENERATE,
        
        Permission.RESOURCES_VIEW,
        Permission.RESOURCES_MANAGE,
        Permission.RESOURCES_COSTS_VIEW,
    ],
    
    "member": [
        # Limited access - view only for most resources
        Permission.CLIENTS_VIEW,  # Only assigned clients
        
        Permission.METRICS_VIEW,
        Permission.METRICS_RECOMMENDATIONS_VIEW,
        
        Permission.CHAT_ACCESS,
        Permission.CHAT_HISTORY_VIEW,
        
        Permission.RESOURCES_VIEW,  # Only assigned clients
        Permission.RESOURCES_COSTS_VIEW,
    ],
}


def get_role_permissions(role_name: str) -> Set[str]:
    """
    Get all permissions for a given role.
    
    Args:
        role_name: Name of the role (superadmin, admin, member)
    
    Returns:
        Set of permission strings for the role
    """
    return set(DEFAULT_ROLE_PERMISSIONS.get(role_name.lower(), []))


def get_all_permissions() -> List[Dict[str, str]]:
    """
    Get all available permissions with metadata.
    
    Returns:
        List of permission dictionaries with name, description, category
    """
    return [
        {
            "permission": perm.value,
            **PERMISSION_METADATA[perm]
        }
        for perm in Permission
    ]


def get_permissions_by_category() -> Dict[str, List[Dict[str, str]]]:
    """
    Get permissions grouped by category.
    
    Returns:
        Dictionary mapping category to list of permissions
    """
    result = {}
    for perm in Permission:
        category = PERMISSION_METADATA[perm]["category"]
        if category not in result:
            result[category] = []
        result[category].append({
            "permission": perm.value,
            "name": PERMISSION_METADATA[perm]["name"],
            "description": PERMISSION_METADATA[perm]["description"],
        })
    return result
