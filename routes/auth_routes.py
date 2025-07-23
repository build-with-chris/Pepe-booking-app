# auth_routes.py

from flask import Blueprint, request, jsonify
from flasgger import swag_from
from flask_jwt_extended import create_access_token
import os
from jose import jwt, JWTError
from flask import request, jsonify, g
from functools import wraps
from dotenv import load_dotenv
load_dotenv()

print("Loaded SUPABASE_JWT_SECRET:", (SUPABASE_JWT_SECRET or "")[:10], "…", len(SUPABASE_JWT_SECRET or ""))

# Symmetric key for HS256 token verification
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")

from managers.artist_manager import ArtistManager



# Blueprint für Auth-Routen (Login/Logout)
auth_bp = Blueprint('auth', __name__)

# Manager-Instanz für Artist-Operationen
artist_mgr = ArtistManager()

# Supabase JWT verification setup
SUPABASE_AUD = os.getenv("SUPABASE_AUD")
# Use Supabase JWKS endpoint (fallback to /auth/v1/keys)
JWKS_URL = os.getenv("JWKS_URL") or f"{SUPABASE_AUD}/auth/v1/keys"


# Decorator for protecting routes using Supabase JWT and optional role check
def requires_auth(required_role=None):
    """Decorator to protect routes using Supabase JWT and optional role check."""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return jsonify({"msg": "Missing or malformed Authorization header"}), 401
            token = auth_header.split(" ", 1)[1].strip()
            try:
                # Symmetric HS256 verification using Supabase JWT Secret
                payload = jwt.decode(
                    token,
                    SUPABASE_JWT_SECRET,
                    algorithms=["HS256"],
                    options={"verify_exp": True}
                )
                g.user = payload
                if required_role:
                    role = payload.get("role") or payload.get("user_metadata", {}).get("role")
                    if role != required_role:
                        return jsonify({"msg": "Forbidden"}), 403
                return f(*args, **kwargs)
            except (StopIteration, JWTError) as e:
                return jsonify({"msg": f"Token verification failed: {str(e)}"}), 401
        return wrapped
    return decorator

# JWT-based login/ logout


@auth_bp.route('/login', methods=['POST'])
@swag_from('../resources/swagger/auth_login.yml')
def login():
    """Authentifiziert einen Artist anhand von Email und Passwort und gibt ein JWT zurück."""
    # JSON-Payload mit Email und Passwort auslesen
    data = request.get_json(force=True, silent=True) or {}
    email = data.get('email')
    pw = data.get('password')
    artist = artist_mgr.get_artist_by_email(email)
    if artist and artist.check_password(pw):
        # JWT mit der Künstler-ID erzeugen
        token = create_access_token(identity=str(artist.id))
        return jsonify(access_token=token,
                    user={'id': artist.id, 'email': artist.email}), 200

    return jsonify({"msg": "Invalid credentials"}), 401

# Geschützte Logout-Route; erfordert gültigen JWT
@auth_bp.route('/logout', methods=['POST'])
@requires_auth()
@swag_from('../resources/swagger/auth_logout.yml')
def logout():
    """Bestätigt das Logout; der Client verwirft das JWT selbst."""
    return jsonify({"msg": "Logout successful"}), 200


# Supabase JWT verification endpoint
@auth_bp.route('/verify', methods=['POST'])
def verify_token():
    """Verifiziert ein Supabase-JWT aus dem Authorization-Header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"msg": "Missing or malformed Authorization header"}), 401

    token = auth_header.split(" ", 1)[1].strip()
    try:
        # Symmetric HS256 verification using Supabase JWT Secret
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_exp": True}
        )
        return jsonify({"user": payload}), 200
    except (StopIteration, JWTError) as e:
        return jsonify({"msg": f"Token verification failed: {str(e)}"}), 401