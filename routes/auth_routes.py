from flask import Blueprint, request, jsonify
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
    user_id = get_jwt_identity()
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
            options={"verify_exp": True, "verify_aud": False}
        )
        return jsonify({"user": payload}), 200
    except (StopIteration, JWTError) as e:
        return jsonify({"msg": f"Token verification failed: {str(e)}"}), 401

# Debug route to inspect loaded JWT secret
@auth_bp.route('/debug-secret', methods=['GET'])
def debug_secret():
    """Gives information about the loaded SUPABASE_JWT_SECRET."""
    secret = os.getenv("SUPABASE_JWT_SECRET")
    return jsonify({
        "loaded": bool(secret),
        "length": len(secret or ""),
        "preview": (secret or "")[:8] + "…" if secret else None
    }), 200