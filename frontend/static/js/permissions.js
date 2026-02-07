/**
 * Permission Management System
 * Handles user permissions for frontend access control
 */

// Store user permissions
let userPermissions = [];

/**
 * Check if user has a specific permission
 * @param {string} permission - Permission to check (e.g., "users.view")
 * @returns {boolean}
 */
function hasPermission(permission) {
    return userPermissions.includes(permission);
}

/**
 * Check if user has any of the specified permissions
 * @param {Array<string>} permissions - Array of permissions to check
 * @returns {boolean}
 */
function hasAnyPermission(permissions) {
    return permissions.some(perm => userPermissions.includes(perm));
}

/**
 * Check if user has all of the specified permissions
 * @param {Array<string>} permissions - Array of permissions to check
 * @returns {boolean}
 */
function hasAllPermissions(permissions) {
    return permissions.every(perm => userPermissions.includes(perm));
}

/**
 * Load user permissions from the backend
 * @returns {Promise<Array<string>>}
 */
async function loadUserPermissions() {
    try {
        const token = localStorage.getItem('token');
        if (!token) {
            console.warn('No access token found');
            return [];
        }

        const API_BASE = window.APP_CONFIG?.API_BASE || 'http://localhost:8000/api';
        const response = await fetch(`${API_BASE}/auth/me`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            throw new Error('Failed to load user permissions');
        }

        const data = await response.json();
        userPermissions = data.permissions || [];
        
        console.log('Loaded permissions:', userPermissions);
        return userPermissions;
    } catch (error) {
        console.error('Error loading permissions:', error);
        return [];
    }
}

/**
 * Initialize permissions and apply UI restrictions
 * @returns {Promise<void>}
 */
async function initializePermissions() {
    await loadUserPermissions();
    applyPermissionRestrictions();
}

/**
 * Apply permission-based restrictions to the UI
 * Hide/disable elements based on user permissions
 */
function applyPermissionRestrictions() {
    // Get all elements with data-require-permission attribute
    document.querySelectorAll('[data-require-permission]').forEach(element => {
        const requiredPermission = element.dataset.requirePermission;
        
        if (!hasPermission(requiredPermission)) {
            // Hide the element if user doesn't have permission
            element.style.display = 'none';
        }
    });

    // Get all elements with data-require-any-permission attribute
    document.querySelectorAll('[data-require-any-permission]').forEach(element => {
        const requiredPermissions = element.dataset.requireAnyPermission.split(',').map(p => p.trim());
        
        if (!hasAnyPermission(requiredPermissions)) {
            element.style.display = 'none';
        }
    });

    // Get all elements with data-require-all-permissions attribute
    document.querySelectorAll('[data-require-all-permissions]').forEach(element => {
        const requiredPermissions = element.dataset.requireAllPermissions.split(',').map(p => p.trim());
        
        if (!hasAllPermissions(requiredPermissions)) {
            element.style.display = 'none';
        }
    });
}

/**
 * Show element if user has permission
 * @param {string} elementId - Element ID to show
 * @param {string} permission - Required permission
 */
function showIfHasPermission(elementId, permission) {
    const element = document.getElementById(elementId);
    if (element && hasPermission(permission)) {
        element.style.display = '';
    }
}

/**
 * Disable element if user doesn't have permission
 * @param {string} elementId - Element ID to disable
 * @param {string} permission - Required permission
 */
function disableIfNoPermission(elementId, permission) {
    const element = document.getElementById(elementId);
    if (element && !hasPermission(permission)) {
        element.disabled = true;
        element.classList.add('disabled');
    }
}

/**
 * Get current user's permissions
 * @returns {Array<string>}
 */
function getUserPermissions() {
    return [...userPermissions];
}

// Export functions for use in other scripts
window.PermissionManager = {
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    loadUserPermissions,
    initializePermissions,
    showIfHasPermission,
    disableIfNoPermission,
    getUserPermissions
};
