# helpers/authz.py
from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt
from helpers.http_responses import error_response

def admin_required(fn):
    """Allow access only if the JWT indicates an admin user.
    Accepts multiple token shapes (is_admin flag, role fields, roles/permissions arrays,
    or Supabase-like app_metadata/user_metadata containers).
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request(optional=False)
        claims = get_jwt() or {}

        def _truthy(v):
            return v is True or str(v).lower() in {"1", "true", "yes", "y"}

        is_admin = False
        try:
            # Simple boolean flag
            if _truthy(claims.get("is_admin")):
                is_admin = True

            # Flat role field
            if str(claims.get("role", "")).lower() in {"admin", "superadmin"}:
                is_admin = True

            # Arrays
            roles = claims.get("roles") or []
            perms = claims.get("permissions") or []
            if isinstance(roles, (list, tuple)) and any(str(r).lower() == "admin" for r in roles):
                is_admin = True
            if isinstance(perms, (list, tuple)) and any(str(p).lower() in {"admin", "manage:all"} for p in perms):
                is_admin = True

            # Supabase-style metadata
            app_meta = claims.get("app_metadata") or {}
            user_meta = claims.get("user_metadata") or {}
            if str(app_meta.get("role", "")).lower() in {"admin", "superadmin"}:
                is_admin = True
            if _truthy(app_meta.get("is_admin")) or _truthy(user_meta.get("is_admin")):
                is_admin = True

        except Exception:
            is_admin = False

        if not is_admin:
            return error_response("forbidden", "Forbidden", 403)

        return fn(*args, **kwargs)
    return wrapper