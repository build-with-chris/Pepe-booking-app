# auth_routes.py

from flask import Blueprint, request, jsonify
from flasgger import swag_from
from flask_jwt_extended import create_access_token
from flask_jwt_extended import jwt_required
import os
import requests
from jose import jwt, JWTError
from flask import request, jsonify, g
from functools import wraps

from managers.artist_manager import ArtistManager



# Blueprint für Auth-Routen (Login/Logout)
auth_bp = Blueprint('auth', __name__)

# Manager-Instanz für Artist-Operationen
artist_mgr = ArtistManager()

# Supabase JWT verification setup
SUPABASE_AUD = os.getenv("SUPABASE_AUD")
JWKS_URL     = os.getenv("JWKS_URL")
_jwks = requests.get(JWKS_URL).json()

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
                header = jwt.get_unverified_header(token)
                # Debug: list available JWKS kids and token kid
                print("Available JWKS kids:", [k["kid"] for k in _jwks["keys"]])
                print("Token kid:", header["kid"])
                key = next(k for k in _jwks["keys"] if k["kid"] == header["kid"])
                payload = jwt.decode(
                    token,
                    key,
                    algorithms=[header["alg"]],
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
@jwt_required()
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
        header = jwt.get_unverified_header(token)
        # Debug: list available JWKS kids and token kid
        print("Available JWKS kids:", [k["kid"] for k in _jwks["keys"]])
        print("Token kid:", header["kid"])
        key = next(k for k in _jwks["keys"] if k["kid"] == header["kid"])
        payload = jwt.decode(
            token,
            key,
            algorithms=[header["alg"]],
            options={"verify_exp": True}
        )
        return jsonify({"user": payload}), 200
    except (StopIteration, JWTError) as e:
        return jsonify({"msg": f"Token verification failed: {str(e)}"}), 401