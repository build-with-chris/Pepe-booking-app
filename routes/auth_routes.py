from flask import Blueprint, request, jsonify, current_app
from helpers.http_responses import error_response
import os
from flasgger import swag_from
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

from managers.artist_manager import ArtistManager



# Blueprint für Auth-Routen (Login/Logout)
auth_bp = Blueprint('auth', __name__)

# Manager-Instanz für Artist-Operationen
artist_mgr = ArtistManager()

# JWT-based login/ logout


@auth_bp.route('/login', methods=['POST'])
@swag_from('../resources/swagger/auth_login.yml')
def login():
    """Authentifiziert einen Artist anhand von Email und Passwort und gibt ein JWT zurück."""
    try:
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
        return error_response("unauthorized", "Invalid credentials", 401)
    except Exception as e:
        current_app.logger.error("Error in login", exc_info=True)
        return error_response("internal_error", f"Login failed: {str(e)}", 500)

# Geschützte Logout-Route; erfordert gültigen JWT
@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
@swag_from('../resources/swagger/auth_logout.yml')
def logout():
    """Bestätigt das Logout; der Client verwirft das JWT selbst."""
    try:
        user_id = get_jwt_identity()
        return jsonify({"msg": "Logout successful"}), 200
    except Exception as e:
        current_app.logger.error("Error in logout", exc_info=True)
        return error_response("internal_error", f"Logout failed: {str(e)}", 500)



# Verify the JWT token issued by login
@auth_bp.route('/verify', methods=['POST'])
@jwt_required()
def verify_token():
    """
    Protected endpoint to verify the JWT and return the user identity.
    """
    try:
        user_id = get_jwt_identity()
        return jsonify({"user": {"id": user_id}}), 200
    except Exception as e:
        current_app.logger.error("Error in verify_token:", exc_info=True)
        return error_response("internal_error", f"Token verification failed: {str(e)}", 500)

# Debug route to inspect loaded JWT secret
@auth_bp.route('/debug-secret', methods=['GET'])
def debug_secret():
    """Gives information about the loaded SUPABASE_JWT_SECRET."""
    try:
        secret = os.getenv("SUPABASE_JWT_SECRET")
        return jsonify({
            "loaded": bool(secret),
            "length": len(secret or ""),
            "preview": (secret or "")[:8] + "…" if secret else None
        }), 200
    except Exception as e:
        current_app.logger.error("Error in debug_secret", exc_info=True)
        return error_response("internal_error", f"Debug secret failed: {str(e)}", 500)