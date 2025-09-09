from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt

def is_admin_claims(claims: dict) -> bool:
    app_md = claims.get('app_metadata') or {}
    return (isinstance(app_md, dict) and app_md.get('role') == 'admin') or (claims.get('role') == 'admin')

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if not is_admin_claims(claims):
            from routes.api_routes import get_current_user
            _uid, artist = get_current_user()
            if not (artist and getattr(artist, 'is_admin', False)):
                return jsonify({'error': 'Not allowed'}), 403
        return fn(*args, **kwargs)
    return wrapper