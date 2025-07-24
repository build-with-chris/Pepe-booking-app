from flask import request, jsonify
from flask import Blueprint
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.calculate_price import calculate_price
from flasgger import swag_from
from managers.artist_manager import ArtistManager
from managers.availability_manager import AvailabilityManager
from managers.booking_requests_manager import BookingRequestManager
from models import Availability
import logging


logger = logging.getLogger(__name__)

# Manager-Instanzen
artist_mgr = ArtistManager()
avail_mgr = AvailabilityManager()
request_mgr = BookingRequestManager()

"""
API-Modul: Beinhaltet Endpunkte für Artists, Verfügbarkeit und Buchungsanfragen.
"""

# Blueprint für API-Routen
api_bp = Blueprint('api', __name__)

def get_current_user():
    """Gibt ein Tupel (user_id, user) des aktuell authentifizierten JWT-Users zurück."""
    user_id = int(get_jwt_identity())
    user = artist_mgr.get_artist(user_id)
    return user_id, user


@api_bp.route('/greet')
def greet_pepe():
    return "Hello Pepe"


# Artists
@api_bp.route('/artists', methods=['GET'])
@swag_from('../resources/swagger/artists_get.yml')
def list_artists():
    """Gibt alle Artists als JSON-Liste zurück."""



    artists = artist_mgr.get_all_artists()
    return jsonify([{
        'id': a.id,
        'name': a.name,
        'email': a.email,
        'phone_number': a.phone_number,
        'disciplines': [d.name for d in a.disciplines],
    } for a in artists])

@api_bp.route('/artists', methods=['POST'])
@swag_from('../resources/swagger/artists_post.yml')
def create_artist():
    """Legt einen neuen Artist mit den übergebenen Daten an."""
    data = request.json
    disciplines = data.get('disciplines')
    if not disciplines:
        return jsonify({'error': 'Disciplines must be provided!'}), 400

    artist = artist_mgr.create_artist(
        name=data['name'],
        email=data['email'],
        password=data['password'],
        disciplines=disciplines,
        phone_number = data.get('phone_number'),
        address      = data.get('address'),
        price_min=data.get('price_min', 1500),
        price_max=data.get('price_max', 1900),
        is_admin     = data.get('is_admin'),
        
    )
    return jsonify({'id': artist.id}), 201


@api_bp.route('/artists/<int:artist_id>', methods=['DELETE'])
@jwt_required()
@swag_from('../resources/swagger/artists_delete.yml')
def delete_artist(artist_id):
    """Löscht den eingeloggten Artist, falls er mit der angegebenen ID übereinstimmt."""
    user_id = get_jwt_identity()
    # Nur der eingeloggte Artist darf sich selbst löschen
    if user_id != artist_id:
        return jsonify({'error':'Forbidden'}), 403

    success = artist_mgr.delete_artist(artist_id)
    if success:
        # und gleich ausloggen
        # from flask_login import logout_user
        # logout_user()
        return jsonify({'deleted': artist_id}), 200

    return jsonify({'error':'Not found'}), 404



# Availability
@api_bp.route('/availability', methods=['GET'])
@jwt_required()
@swag_from('../resources/swagger/availability_get.yml')
def get_availability():
    """Gibt alle Verfügbarkeitstage des eingeloggten Artists zurück."""
    user_id = get_jwt_identity()
    slots = avail_mgr.get_availabilities(user_id)
    return jsonify([{'id': s.id, 'date': s.date.isoformat()} for s in slots])

@api_bp.route('/availability', methods=['POST'])
@jwt_required()
@swag_from('../resources/swagger/availability_post.yml')
def add_availability():
    """Fügt einen oder mehrere Verfügbarkeitstage für den eingeloggten Artist hinzu."""
    # Aktuelle Benutzer-ID aus JWT abrufen
    user_id = get_jwt_identity()
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Date must be provided'}), 400

    def create_slot(item):
        date_str = item.get('date')
        if not date_str:
            raise KeyError('date')
        try:
            # parse to ensure valid format
            from datetime import datetime
            datetime.fromisoformat(date_str)
        except ValueError:
            raise ValueError('Invalid date format')
        slot = avail_mgr.add_availability(user_id, date_str)
        return {'id': slot.id, 'date': slot.date.isoformat()}

    slots = []
    # batch or single

    if isinstance(data, list):
        try:
            for item in data:
                slots.append(create_slot(item))
        except KeyError:
            return jsonify({'error': 'Date must be provided'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400
    else:
        try:
            slots.append(create_slot(data))
        except KeyError:
            return jsonify({'error': 'Date must be provided'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400
    return jsonify(slots), 201

@api_bp.route('/availability/<int:slot_id>', methods=['DELETE'])
@jwt_required()
@swag_from('../resources/swagger/availability_delete.yml')
def remove_availability(slot_id):
    """Entfernt einen Verfügbarkeitstag des eingeloggten Artists anhand der ID."""
    logger.debug(f"remove_availability called with slot_id={slot_id}")
    user_id = int(get_jwt_identity())
    # First retrieve without deleting
    slot = Availability.query.get(slot_id)
    if not slot or slot.artist_id != user_id:
        return jsonify({'error': 'Forbidden'}), 403
    # Authorized: delete now
    avail_mgr.remove_availability(slot_id)
    return jsonify({'deleted': slot_id})