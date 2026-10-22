"""
Auth Router
===========

Exposes the current user's identity and roles so the UI can hide controls
the user is not allowed to use. Enforcement happens in AuthMiddleware.
"""

import sys

from fastapi import APIRouter, Request

from ..schemas import AuthInfo
from ..services.chat_constants import ROOT_DIR
from ..utils import auth

# Ensure root is on sys.path for registry import
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/me", response_model=AuthInfo)
async def get_current_user(request: Request) -> AuthInfo:
    """Return the authenticated user and their effective roles."""
    settings = auth.get_settings()
    if not settings.enabled:
        return AuthInfo(enabled=False, is_admin=True, default_role=auth.ROLE_ADMIN)

    user = auth.get_request_user(request)
    if user is None:
        # Unreachable when the middleware is installed; fail closed anyway.
        return AuthInfo(enabled=True, is_admin=False, default_role=auth.ROLE_NONE)

    from registry import list_registered_projects

    config = auth.get_role_config()
    admin = auth.is_admin(user, config)
    projects = {
        name: auth.project_role(user, name, config)
        for name in list_registered_projects()
    }
    return AuthInfo(
        enabled=True,
        user=user.name,
        groups=list(user.groups),
        is_admin=admin,
        default_role=auth.ROLE_ADMIN if admin else config.default_role,
        projects={name: role for name, role in projects.items() if role != auth.ROLE_NONE},
    )
