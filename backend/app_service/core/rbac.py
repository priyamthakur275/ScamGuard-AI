from enum import Enum

from app_service.db.postgres.models import UserRole


class Permission(str, Enum):
    VIEW_OWN_DATA = "view_own_data"
    VIEW_ALL_USERS = "view_all_users"
    MANAGE_USERS = "manage_users"
    MANAGE_MODELS = "manage_models"
    VIEW_AUDIT_LOG = "view_audit_log"


ROLE_PERMISSIONS: dict[UserRole, set[Permission]] = {
    UserRole.USER: {
        Permission.VIEW_OWN_DATA,
    },
    UserRole.ADMIN: {
        Permission.VIEW_OWN_DATA,
        Permission.VIEW_ALL_USERS,
        Permission.MANAGE_USERS,
        Permission.MANAGE_MODELS,
        Permission.VIEW_AUDIT_LOG,
    },
}


def role_has_permission(role: UserRole, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())
