# auth_routes.py
from flask import Blueprint, request, jsonify
from flasgger import swag_from
from flask_jwt_extended import create_access_token
from flask_jwt_extended import jwt_required
import os
from datamanager import DataManager
from flasgger import swag_from
from flask_jwt_extended import create_access_token

auth_bp = Blueprint('auth', __name__)

dm = DataManager()

# JWT-based login/ logout: client should discard the token


@auth_bp.route('/login', methods=['POST'])
@swag_from('resources/swagger/auth_login.yml')
def login():
        data = request.get_json(force=True, silent=True) or {}
        email = data.get('email')
        pw = data.get('password')
        artist = dm.get_artist_by_email(email)
        if artist and artist.check_password(pw):
            token = create_access_token(identity=str(artist.id))
            return jsonify(access_token=token,
                        user={'id': artist.id, 'email': artist.email}), 200
        return jsonify({"msg": "Invalid credentials"}), 401


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
@swag_from(os.path.join(os.path.dirname(__file__), 'resources', 'swagger', 'auth_logout.yml'))
def logout():
    return jsonify({"msg": "Logout successful"}), 200