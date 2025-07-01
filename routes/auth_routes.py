# auth_routes.py
"""
Auth-Modul: Enthält Endpunkte für Login und Logout mittels JWT-Token.
"""
from flask import Blueprint, request, jsonify
from flasgger import swag_from
from flask_jwt_extended import create_access_token
from flask_jwt_extended import jwt_required
import os
from datamanager import DataManager

# Blueprint für Auth-Routen (Login/Logout)
auth_bp = Blueprint('auth', __name__)
dm = DataManager()

# JWT-based login/ logout


@auth_bp.route('/login', methods=['POST'])
@swag_from('resources/swagger/auth_login.yml')
def login():
    """Authentifiziert einen Artist anhand von Email und Passwort und gibt ein JWT zurück."""
    # JSON-Payload mit Email und Passwort auslesen
    data = request.get_json(force=True, silent=True) or {}
    email = data.get('email')
    pw = data.get('password')
    artist = dm.get_artist_by_email(email)
    if artist and artist.check_password(pw):
        # JWT mit der Künstler-ID erzeugen
        token = create_access_token(identity=str(artist.id))
        return jsonify(access_token=token,
                    user={'id': artist.id, 'email': artist.email}), 200

    return jsonify({"msg": "Invalid credentials"}), 401

# Geschützte Logout-Route; erfordert gültigen JWT
@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
@swag_from(os.path.join(os.path.dirname(__file__), 'resources', 'swagger', 'auth_logout.yml'))
def logout():
    """Bestätigt das Logout; der Client verwirft das JWT selbst."""
    return jsonify({"msg": "Logout successful"}), 200