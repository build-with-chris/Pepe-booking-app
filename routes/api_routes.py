from flask import request, jsonify
from flask import Blueprint
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from services.calculate_price import calculate_price
from flasgger import swag_from
from managers.artist_manager import ArtistManager
from managers.availability_manager import AvailabilityManager
from managers.booking_requests_manager import BookingRequestManager
from models import Availability, Discipline, db
import logging

from datetime import datetime

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
    """Gibt ein Tupel (user_id, artist) des aktuell authentifizierten JWT-Users zurück.
    Reihenfolge:
      1) Lookup per supabase_user_id (JWT identity)
      2) Fallback per E-Mail aus JWT-Claims und ggf. UID verknüpfen
      3) Falls noch nichts gefunden, aber eine E-Mail vorhanden ist: Minimal-Artist automatisch anlegen (status='unsubmitted')
    """
    user_id = get_jwt_identity()
    artist = None

    # 1) Direkt über UID versuchen
    try:
        artist = artist_mgr.get_artist_by_supabase_user_id(user_id)
    except Exception:
        artist = None

    # 2) Fallback per E-Mail (und UID verknüpfen)
    if not artist:
        try:
            claims = get_jwt()
            email = claims.get("email") or claims.get("user_metadata", {}).get("email")
            name = claims.get("name") or claims.get("user_metadata", {}).get("name")
            if email:
                fallback = artist_mgr.get_artist_by_email(email)
                if fallback:
                    if not getattr(fallback, "supabase_user_id", None):
                        fallback.supabase_user_id = user_id
                        db.session.commit()
                    artist = fallback
                else:
                    # 3) Minimal-Artist automatisch anlegen (erstes Login)
                    from models import Artist
                    try:
                        new_artist = Artist(
                            name=name or (email.split("@")[0] if isinstance(email, str) else None),
                            email=email,
                            supabase_user_id=user_id,
                            approval_status="unsubmitted",
                        )
                        db.session.add(new_artist)
                        db.session.commit()
                        artist = new_artist
                    except Exception:
                        db.session.rollback()
        except Exception:
            # Keine Claims/E-Mail verfügbar
            pass

    return user_id, artist


# Artists
@api_bp.route('/artists', methods=['GET'])
@swag_from('../resources/swagger/artists_get.yml')
def list_artists():
    """Gibt alle Artists als JSON-Liste zurück."""
    # Nur freigegebene Artists öffentlich listen
    artists = artist_mgr.get_approved_artists()
    return jsonify([{
        'id': a.id,
        'name': a.name,
        'email': a.email,
        'address': getattr(a, 'address', None),
        'phone_number': a.phone_number,
        'disciplines': [d.name for d in a.disciplines],
        'price_min': getattr(a, 'price_min', None),
        'price_max': getattr(a, 'price_max', None),
        'profile_image_url': getattr(a, 'profile_image_url', None),
        'bio': getattr(a, 'bio', None),
        'instagram': getattr(a, 'instagram', None),              
        'gallery_urls': getattr(a, 'gallery_urls', []) or []
    } for a in artists])


@api_bp.route('/artists', methods=['POST'])
@jwt_required()
@swag_from('../resources/swagger/artists_post.yml')
def create_artist():
    """Legt einen neuen Artist mit den übergebenen Daten an."""
    try:
        current_user_id = get_jwt_identity()
        data = request.json or {}
        disciplines = data.get('disciplines')
        if not disciplines:
            return jsonify({'error': 'Disciplines must be provided!'}), 400
        if artist_mgr.get_artist_by_email(data.get('email', '')):
            return jsonify({'error': 'Email already exists'}), 409

        artist = artist_mgr.create_artist(
            name=data['name'],
            email=data['email'],
            password=data['password'],
            disciplines=disciplines,
            phone_number=data.get('phone_number'),
            address=data.get('address'),
            price_min=data.get('price_min', 1500),
            price_max=data.get('price_max', 1900),
            is_admin=data.get('is_admin', False),
            supabase_user_id=current_user_id,
        )
        return jsonify({'id': artist.id}), 201
    except ValueError as ve:
        if 'email already exists' in str(ve).lower():
            return jsonify({'error': 'Email already exists'}), 409
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        logger.exception('Failed to create artist')
        return jsonify({'error': 'Failed to create artist', 'details': str(e)}), 500


# Own artist profile: read

@api_bp.route('/artists/me', methods=['GET'])
@jwt_required()
@swag_from('../resources/swagger/artists_me_get.yml')
def get_my_artist():
    """Liefert das eigene Artist-Profil (inkl. Bild & Bio) der eingeloggten Person."""
    user_id, artist = get_current_user()
    if not artist:
        return jsonify({'error': 'Current user not linked to an artist'}), 403
    return jsonify({
        'id': artist.id,
        'name': artist.name,
        'email': artist.email,
        'address': getattr(artist, 'address', None),
        'phone_number': artist.phone_number,
        'disciplines': [d.name for d in artist.disciplines],
        'price_min': getattr(artist, 'price_min', None),
        'price_max': getattr(artist, 'price_max', None),
        'profile_image_url': getattr(artist, 'profile_image_url', None),
        'bio': getattr(artist, 'bio', None),
        'instagram': getattr(artist, 'instagram', None),
        'gallery_urls': getattr(artist, 'gallery_urls', []) or [],
        'approval_status': getattr(artist, 'approval_status', None),
        'rejection_reason': getattr(artist, 'rejection_reason', None),
    }), 200


# Explizite Freigabe anfordern (Status -> pending)
@api_bp.route('/artists/me/submit_review', methods=['POST'])
@jwt_required()
@swag_from('../resources/swagger/artists_me_submit_review_post.yml', validation=False)
def submit_my_profile_for_review():
    """Setzt den Freigabe-Status des eingeloggten Artists auf 'pending' (sofern nicht bereits 'approved')."""
    user_id, artist = get_current_user()
    if not artist:
        return jsonify({'error': 'Current user not linked to an artist'}), 403

    try:
        current_status = (getattr(artist, 'approval_status', 'unsubmitted') or 'unsubmitted').lower()
        if current_status != 'approved':
            artist.approval_status = 'pending'
            # vorherige Ablehnungsgründe entfernen
            if hasattr(artist, 'rejection_reason'):
                artist.rejection_reason = None
            db.session.commit()
        return jsonify({
            'id': artist.id,
            'approval_status': getattr(artist, 'approval_status', None),
            'rejection_reason': getattr(artist, 'rejection_reason', None),
        }), 200
    except Exception as e:
        logger.exception('Failed to submit profile for review')
        return jsonify({'error': 'Failed to submit review', 'details': str(e)}), 500


@api_bp.route('/artists/me/profile', methods=['PUT', 'PATCH'])
@jwt_required()
@swag_from('../resources/swagger/artists_me_profile_put.yml')
def update_my_profile():
    """Aktualisiert das Profil des eingeloggten Artists (Name, Adresse, Telefon, Preise, Disziplinen,
    Profilbild-URL, Bio, Instagram, Galerie-URLs). Optional kann approval_status='pending' gesetzt werden.
    """
    user_id, artist = get_current_user()
    if not artist:
        return jsonify({'error': 'Current user not linked to an artist'}), 403

    payload = request.get_json(silent=True) or {}

    # Einzeln auslesen (alle Felder sind optional)
    name = payload.get('name')
    address = payload.get('address')
    phone_number = payload.get('phone_number')
    price_min = payload.get('price_min')
    price_max = payload.get('price_max')
    disciplines = payload.get('disciplines')  # erwartet Liste[str]

    img_url = payload.get('profile_image_url')
    bio = payload.get('bio')
    instagram = payload.get('instagram')
    gallery_urls = payload.get('gallery_urls')
    req_status = payload.get('approval_status')

    updatable_keys = [
        name, address, phone_number, price_min, price_max, disciplines,
        img_url, bio, instagram, gallery_urls, req_status
    ]
    if all(v is None for v in updatable_keys):
        return jsonify({'error': 'Nothing to update'}), 400

    # Validierungen
    if gallery_urls is not None:
        if not isinstance(gallery_urls, list):
            return jsonify({'error': 'gallery_urls must be a list of URLs'}), 400
        gallery_urls = [str(u).strip() for u in gallery_urls if isinstance(u, (str, bytes))]
        if len(gallery_urls) > 3:
            return jsonify({'error': 'gallery_urls may contain at most 3 items'}), 400

    if disciplines is not None and not isinstance(disciplines, list):
        return jsonify({'error': 'disciplines must be a list of strings'}), 400

    try:
        # Primitive Felder
        if name is not None:
            artist.name = str(name).strip() or artist.name
        if address is not None:
            artist.address = str(address).strip() or None
        if phone_number is not None:
            artist.phone_number = str(phone_number).strip() or None
        if price_min is not None:
            artist.price_min = price_min
        if price_max is not None:
            artist.price_max = price_max

        # Social / Media
        if img_url is not None:
            artist.profile_image_url = (img_url or None)
        if bio is not None:
            artist.bio = (str(bio).strip()[:1000] if bio is not None else None)
        if instagram is not None:
            artist.instagram = (instagram.strip() or None) if isinstance(instagram, str) else None
        if gallery_urls is not None:
            artist.gallery_urls = gallery_urls

        # Disziplinen
        if disciplines is not None:
            def get_or_create_discipline(name: str):
                disc = Discipline.query.filter_by(name=name).first()
                if not disc:
                    disc = Discipline(name=name)
                    db.session.add(disc)
                    db.session.flush()
                return disc
            artist.disciplines = [get_or_create_discipline(str(d).strip()) for d in disciplines if str(d).strip()]

        # Optional: Einreichen zur Prüfung – nur 'pending' ist vom Artist aus erlaubt
        if req_status is not None:
            req_status = str(req_status).strip().lower()
            current_status = (getattr(artist, 'approval_status', 'unsubmitted') or 'unsubmitted').lower()
            if req_status == 'pending' and current_status != 'approved':
                artist.approval_status = 'pending'
                if hasattr(artist, 'rejection_reason'):
                    artist.rejection_reason = None

        db.session.commit()

        # Antwort mit allen wichtigen Feldern
        return jsonify({
            'id': artist.id,
            'name': artist.name,
            'email': artist.email,
            'address': getattr(artist, 'address', None),
            'phone_number': artist.phone_number,
            'disciplines': [d.name for d in artist.disciplines],
            'price_min': getattr(artist, 'price_min', None),
            'price_max': getattr(artist, 'price_max', None),
            'profile_image_url': getattr(artist, 'profile_image_url', None),
            'bio': getattr(artist, 'bio', None),
            'instagram': getattr(artist, 'instagram', None),
            'gallery_urls': getattr(artist, 'gallery_urls', []) or [],
            'approval_status': getattr(artist, 'approval_status', None),
            'rejection_reason': getattr(artist, 'rejection_reason', None),
        }), 200
    except Exception as e:
        logger.exception('Failed to update own profile')
        db.session.rollback()
        return jsonify({'error': 'Failed to update profile', 'details': str(e)}), 500


@api_bp.route('/artists/me/ensure', methods=['POST'])
@jwt_required()
@swag_from('../resources/swagger/artists_me_ensure_post.yml', validation=False)
def ensure_my_artist():
    """Ensure an Artist row exists for current Supabase user; return it."""
    user_id = get_jwt_identity()
    artist = None
    # Try direct lookup by supabase_user_id
    try:
        artist = artist_mgr.get_artist_by_supabase_user_id(user_id)
    except Exception:
        artist = None
    # Fallback by email if not found
    if not artist:
        try:
            claims = get_jwt()
            email = claims.get("email") or claims.get("user_metadata", {}).get("email")
            name = claims.get("name") or claims.get("user_metadata", {}).get("name")
            if email:
                fallback = artist_mgr.get_artist_by_email(email)
                if fallback:
                    if not getattr(fallback, "supabase_user_id", None):
                        fallback.supabase_user_id = user_id
                        db.session.commit()
                    artist = fallback
                else:
                    # Minimal artist creation (unsubmitted)
                    from models import Artist
                    try:
                        new_artist = Artist(
                            name=name or (email.split("@")[0] if isinstance(email, str) else None),
                            email=email,
                            supabase_user_id=user_id,
                            approval_status="unsubmitted",
                        )
                        db.session.add(new_artist)
                        db.session.commit()
                        artist = new_artist
                    except Exception:
                        db.session.rollback()
                        artist = None
        except Exception:
            artist = None
    # If still no artist, return error
    if not artist:
        return jsonify({'error': 'Unable to ensure artist for current user'}), 500
    # Always return the artist record (existing or newly created)
    return jsonify({
        'id': artist.id,
        'name': artist.name,
        'email': artist.email,
        'address': getattr(artist, 'address', None),
        'phone_number': artist.phone_number,
        'disciplines': [d.name for d in artist.disciplines],
        'price_min': getattr(artist, 'price_min', None),
        'price_max': getattr(artist, 'price_max', None),
        'profile_image_url': getattr(artist, 'profile_image_url', None),
        'bio': getattr(artist, 'bio', None),
        'instagram': getattr(artist, 'instagram', None),
        'gallery_urls': getattr(artist, 'gallery_urls', []) or [],
        'approval_status': getattr(artist, 'approval_status', None),
        'rejection_reason': getattr(artist, 'rejection_reason', None),
    }), 200

@api_bp.route('/artists/email/<string:email>', methods=['GET'])
@jwt_required()
@swag_from('../resources/swagger/artists_email_get.yml')
def get_artist_by_email(email):
    artist = artist_mgr.get_artist_by_email(email)
    if not artist:
        return jsonify({'msg': 'Artist not found'}), 404
    return jsonify(artist.serialize()), 200


@api_bp.route('/artists/<int:artist_id>', methods=['DELETE'])
@jwt_required()
@swag_from('../resources/swagger/artists_delete.yml')
def delete_artist(artist_id):
    """Löscht den eingeloggten Artist, falls er mit der angegebenen ID übereinstimmt."""
    user_supabase_id = get_jwt_identity()
    artist = artist_mgr.get_artist(artist_id)
    if not artist:
        return jsonify({'error': 'Not found'}), 404
    if not (artist.supabase_user_id == user_supabase_id or (artist and getattr(artist, 'is_admin', False))):
        return jsonify({'error': 'Forbidden'}), 403
    success = artist_mgr.delete_artist(artist_id)
    if success:
        return jsonify({'deleted': artist_id}), 200
    return jsonify({'error': 'Not found'}), 404


@api_bp.route('/artists/<int:artist_id>', methods=['PUT', 'PATCH'])
@jwt_required()
@swag_from('../resources/swagger/artists_put.yml')
def update_artist(artist_id):
    """Aktualisiert einen vorhandenen Artist."""
    try:
        current_user_id = get_jwt_identity()
        current_user = artist_mgr.get_artist_by_supabase_user_id(current_user_id)
        data = request.json or {}
        logger.info(f'Update attempt for artist {artist_id} by user {current_user_id}')
        logger.info(f'Updating artist {artist_id} with data: {data}')
        artist = artist_mgr.get_artist(artist_id)
        if not artist:
            return jsonify({'error': 'Artist not found'}), 404
        if not (getattr(current_user, 'is_admin', False) or artist.supabase_user_id == current_user_id):
            return jsonify({'error': 'Forbidden'}), 403
        if 'name' in data:
            artist.name = data['name']
        if 'email' in data:
            new_email = data['email']
            if new_email != artist.email and artist_mgr.get_artist_by_email(new_email):
                return jsonify({'error': 'Email already exists'}), 409
            artist.email = new_email
        if 'password' in data:
            artist.set_password(data['password'])
        if 'phone_number' in data:
            artist.phone_number = data['phone_number']
        if 'address' in data:
            artist.address = data['address']
        if 'price_min' in data:
            artist.price_min = data.get('price_min')
        if 'price_max' in data:
            artist.price_max = data.get('price_max')
        if 'instagram' in data:
            val = data.get('instagram')
            artist.instagram = (val.strip() if isinstance(val, str) and val.strip() else None)
        if 'gallery_urls' in data:
            val = data.get('gallery_urls')
            if val is not None:
                if not isinstance(val, list):
                    return jsonify({'error': 'gallery_urls must be a list of URLs'}), 400
                urls = [str(u).strip() for u in val if isinstance(u, (str, bytes))]
                if len(urls) > 3:
                    return jsonify({'error': 'gallery_urls may contain at most 3 items'}), 400
                artist.gallery_urls = urls
        if 'disciplines' in data:
            def get_or_create_discipline(name):
                disc = Discipline.query.filter_by(name=name).first()
                if not disc:
                    disc = Discipline(name=name)
                    db.session.add(disc)
                    db.session.flush()
                return disc
            artist.disciplines = [get_or_create_discipline(d) for d in data['disciplines']]
        db.session.commit()
        return jsonify({'id': artist.id}), 200
    except Exception as e:
        logger.exception('Failed to update artist')
        return jsonify({'error': 'Failed to update artist', 'details': str(e)}), 500


# Availability

@api_bp.route('/availability', methods=['GET'])
@jwt_required()
@swag_from('../resources/swagger/availability_get.yml')
def get_availability():
    """Gibt alle Verfügbarkeitstage des eingeloggten Artists zurück oder, falls angegeben, eines anderen Artists (mit Berechtigung)."""
    current_supabase_id = get_jwt_identity()
    logger.debug(f"get_availability called by supabase_user_id={current_supabase_id} with args={request.args}")

    artist_id_param = request.args.get('artist_id')

    # resolve current artist from token
    current_artist = artist_mgr.get_artist_by_supabase_user_id(current_supabase_id)
    if not current_artist:
        logger.warning(f"Current user {current_supabase_id} not linked to an artist")
        return jsonify({'error': 'Current user not linked to an artist'}), 403

    target_artist = current_artist
    if artist_id_param:
        try:
            artist_id_int = int(artist_id_param)
            artist_candidate = artist_mgr.get_artist(artist_id_int)
            if artist_candidate:
                # permission: same artist or admin
                if artist_candidate.id != current_artist.id and not getattr(current_artist, 'is_admin', False):
                    logger.warning(f"User {current_supabase_id} forbidden from viewing availability of artist {artist_candidate.id}")
                    return jsonify({'error': 'Forbidden'}), 403
                target_artist = artist_candidate
            else:
                logger.warning(f"Artist candidate not found for id {artist_id_int}, falling back to current artist")
            
        except ValueError:
            logger.warning(f"Invalid artist_id parameter: {artist_id_param}, ignoring and using current artist")
    
    # fetch and return slots: if target is current artist use user-specific helper for better handling
    try:
        if target_artist.id == current_artist.id:
            slots = avail_mgr.get_availabilities_for_user(current_supabase_id)
        else:
            slots = avail_mgr.get_availabilities(target_artist.id)
    except Exception as e:
        logger.exception(f"Failed to fetch availabilities for artist {target_artist.id}")
        return jsonify({'error': 'Failed to fetch availabilities', 'details': str(e)}), 500

    result = [{'id': s.id, 'artist_id': s.artist_id, 'date': s.date.isoformat()} for s in slots]
    logger.debug(f"Returning {len(result)} availability slots for artist {target_artist.id}")
    return jsonify(result)


@api_bp.route('/availability', methods=['POST'])
@jwt_required()
@swag_from('../resources/swagger/availability_post.yml')
def add_availability():
    """Fügt einen oder mehrere Verfügbarkeitstage für den eingeloggten Artist hinzu (oder, wenn admin, für einen anderen über artist_id)."""
    current_supabase_id = get_jwt_identity()
    current_artist = artist_mgr.get_artist_by_supabase_user_id(current_supabase_id)
    if not current_artist:
        return jsonify({'error': 'Current user not linked to an artist'}), 403

    # resolve target artist (optional override for admin)
    artist_id_param = request.args.get('artist_id')
    target_artist = current_artist
    if artist_id_param:
        try:
            artist_id_int = int(artist_id_param)
        except ValueError:
            return jsonify({'error': 'artist_id must be integer'}), 400
        candidate = artist_mgr.get_artist(artist_id_int)
        if not candidate:
            return jsonify({'error': 'Artist not found'}), 404
        if candidate.id != current_artist.id and not getattr(current_artist, 'is_admin', False):
            return jsonify({'error': 'Forbidden'}), 403
        target_artist = candidate

    artist_id = target_artist.id
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Date must be provided'}), 400

    def create_slot(item):
        date_str = item.get('date')
        if not date_str:
            raise KeyError('date')
        try:
            from datetime import datetime
            datetime.fromisoformat(date_str)
        except ValueError:
            raise ValueError('Invalid date format')
        slot = avail_mgr.add_availability(artist_id, date_str)
        return {'id': slot.id, 'date': slot.date.isoformat()}

    slots = []
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


@api_bp.route('/availability', methods=['PUT'])
@jwt_required()
@swag_from('../resources/swagger/availability_put.yml')
def replace_availability():
    """Ersetzt die Verfügbarkeiten des eingeloggten Artists komplett mit der übergebenen Liste von dates (oder, wenn admin, eines anderen Artists via artist_id)."""
    current_supabase_id = get_jwt_identity()
    current_artist = artist_mgr.get_artist_by_supabase_user_id(current_supabase_id)
    if not current_artist:
        return jsonify({'error': 'Current user not linked to an artist'}), 403

    # resolve target artist (optional override for admin)
    artist_id_param = request.args.get('artist_id')
    target_artist = current_artist
    if artist_id_param:
        try:
            artist_id_int = int(artist_id_param)
        except ValueError:
            return jsonify({'error': 'artist_id must be integer'}), 400
        candidate = artist_mgr.get_artist(artist_id_int)
        if not candidate:
            return jsonify({'error': 'Artist not found'}), 404
        if candidate.id != current_artist.id and not getattr(current_artist, 'is_admin', False):
            return jsonify({'error': 'Forbidden'}), 403
        target_artist = candidate

    data = request.get_json()
    if not data or 'dates' not in data:
        return jsonify({'error': 'dates list required'}), 400
    if artist_id_param:
        result = avail_mgr.replace_availabilities_for_artist(target_artist.id, data['dates'])
    else:
        result = avail_mgr.replace_availabilities_for_user(current_supabase_id, data['dates'])
    return jsonify(result), 200


@api_bp.route('/availability/<int:slot_id>', methods=['DELETE'])
@jwt_required()
@swag_from('../resources/swagger/availability_delete.yml')
def remove_availability(slot_id):
    """Entfernt einen Verfügbarkeitstag des eingeloggten Artists anhand der ID. Admins können auch andere löschen."""
    logger.debug(f"remove_availability called with slot_id={slot_id}")
    current_supabase_id = get_jwt_identity()
    current_artist = artist_mgr.get_artist_by_supabase_user_id(current_supabase_id)
    if not current_artist:
        return jsonify({'error': 'Current user not linked to an artist'}), 403
    slot = Availability.query.get(slot_id)
    if not slot:
        return jsonify({'error': 'Not found'}), 404
    # permission: owner or admin
    if slot.artist_id != current_artist.id and not getattr(current_artist, 'is_admin', False):
        return jsonify({'error': 'Forbidden'}), 403
    avail_mgr.remove_availability(slot_id)
    return jsonify({'deleted': slot_id})
@api_bp.route('/requests/requests', methods=['GET'])
@jwt_required()
@swag_from('../resources/swagger/booking_requests_get.yml')
def list_my_booking_requests():
    """Gibt die für den eingeloggten Artist relevanten BookingRequests zurück (mit Empfehlung)."""
    user_id = get_jwt_identity()
    logger.debug(f"list_my_booking_requests called with supabase_user_id={user_id}")
    artist = artist_mgr.get_artist_by_supabase_user_id(user_id)
    if not artist:
        logger.warning(f"Current user {user_id} not linked to an artist")
        return jsonify({'error': 'Current user not linked to an artist'}), 403
    # Nur freigegebene Artists können Anfragen erhalten/einsehen
    if getattr(artist, 'approval_status', '') != 'approved':
        return jsonify({'error': 'Artist not approved yet'}), 403
    logger.debug(f"Resolved artist: id={artist.id}, supabase_user_id={artist.supabase_user_id}")
    requests = request_mgr.get_requests_for_artist_with_recommendation(artist.id)

    # Fallback-Diagnose: wenn keine empfohlenen Anfragen, hole die rohen verknüpften Requests
    if not requests:
        raw_reqs = request_mgr.get_requests_for_artist(artist.id)
        logger.debug(f"Raw get_requests_for_artist returned: {[r.id for r in raw_reqs]}")
    try:
        request_ids = [r.get('id') if isinstance(r, dict) else getattr(r, 'id', None) for r in requests]
    except Exception:
        request_ids = str(requests)
    logger.debug(f"list_my_booking_requests result count={len(requests)} ids={request_ids}")
    return jsonify(requests), 200



# Combined GET/PUT endpoint for artist offer
@api_bp.route('/requests/requests/<int:req_id>/offer', methods=['GET', 'PUT'])
@jwt_required()
@swag_from('../resources/swagger/requests_offer_get_put.yml')
def artist_offer(req_id):
    """GET: liefert das eigene Angebot; PUT: speichert/aktualisiert die eigene Gage und setzt Status auf 'angeboten'."""
    user_id, artist = get_current_user()
    logger.debug(f"artist_offer called by supabase_user_id={user_id} for req_id={req_id} method={request.method}")
    if not artist:
        return jsonify({'error': 'Current user not linked to an artist'}), 403
    if getattr(artist, 'approval_status', '') != 'approved':
        return jsonify({'error': 'Artist not approved yet'}), 403

    if request.method == 'PUT':
        try:
            payload = request.get_json(silent=True) or {}
            price_offered = payload.get('price_offered')
            if price_offered is None:
                return jsonify({'error': 'price_offered is required'}), 400
            # persist in pivot and set status='angeboten'
            request_mgr.set_offer(req_id, artist.id, price_offered)
            # Nach dem Speichern erneut aus Pivot lesen
            offer_data = request_mgr.get_artist_offer(req_id, artist.id)
            logger.debug(f"artist_offer PUT stored; pivot now: {offer_data}")
            return jsonify(offer_data or {'price_offered': price_offered, 'status': 'angeboten'}), 200
        except Exception as e:
            logger.exception('Failed to set artist offer')
            return jsonify({'error': 'Failed to set offer', 'details': str(e)}), 500

    # GET-Fall
    logger.debug(f"Resolved artist for offer lookup: id={artist.id} name={getattr(artist, 'name', None)}")
    offer_data = request_mgr.get_artist_offer(req_id, artist.id)
    logger.debug(f"artist_offer GET result: {offer_data}")
    if offer_data is None:
        return jsonify({'error': 'Offer not found or not permitted'}), 404
    return jsonify(offer_data), 200


# =============================
# Invoices (Option A – UID-Folder in Supabase)
# =============================
try:
    from models import Invoice  # optional: only if model exists
    HAS_INVOICE_MODEL = True
except Exception:
    HAS_INVOICE_MODEL = False


@api_bp.route('/invoices', methods=['POST'])
@jwt_required()
@swag_from('../resources/swagger/invoices_post.yml', validation=False)
def create_invoice_entry():
    """Registriert eine Rechnung zu einem Artist. Erwartet mindestens `storage_path` (z. B. `user/<uid>/<file>`).
    Hinweis: Die Datei selbst liegt in Supabase Storage (Bucket `invoices`).
    Wenn das `Invoice`-Model nicht vorhanden ist, wird ein No-Op mit 200 zurückgegeben (soft rollout).
    """
    user_id, artist = get_current_user()
    if not artist:
        return jsonify({'error': 'Current user not linked to an artist'}), 403

    payload = request.get_json(silent=True) or {}
    storage_path = (payload.get('storage_path') or '').strip()
    amount_cents = payload.get('amount_cents')
    currency = (payload.get('currency') or 'EUR').upper()
    invoice_date_raw = payload.get('invoice_date')  # ISO (YYYY-MM-DD) optional
    notes = payload.get('notes')

    if not storage_path:
        return jsonify({'error': 'storage_path is required'}), 400

    # parse date if provided
    invoice_date = None
    if isinstance(invoice_date_raw, str) and invoice_date_raw.strip():
        try:
            invoice_date = datetime.fromisoformat(invoice_date_raw).date()
        except Exception:
            return jsonify({'error': 'invoice_date must be ISO date (YYYY-MM-DD)'}), 400

    if not HAS_INVOICE_MODEL:
        # Soft success so Frontend-Uploadflow funktioniert auch ohne DB-Tracking
        return jsonify({
            'ok': True,
            'note': 'Invoice model not installed; stored only in Supabase Storage',
            'artist_id': artist.id,
            'storage_path': storage_path,
        }), 200

    try:
        # De-dupe by (artist_id, storage_path)
        existing = Invoice.query.filter_by(artist_id=artist.id, storage_path=storage_path).first()
        if existing:
            # update optional fields
            if amount_cents is not None:
                existing.amount_cents = int(amount_cents)
            if currency:
                existing.currency = currency
            if invoice_date is not None:
                existing.invoice_date = invoice_date
            if notes is not None:
                existing.notes = notes
            db.session.commit()
            return jsonify({'id': existing.id, 'artist_id': artist.id, 'storage_path': storage_path}), 200

        inv = Invoice(
            artist_id=artist.id,
            storage_path=storage_path,
            amount_cents=(int(amount_cents) if amount_cents is not None else None),
            currency=currency,
            invoice_date=invoice_date,
            notes=notes,
        )
        db.session.add(inv)
        db.session.commit()
        return jsonify({'id': inv.id, 'artist_id': artist.id, 'storage_path': inv.storage_path}), 201
    except Exception as e:
        logger.exception('Failed to create/update invoice entry')
        db.session.rollback()
        return jsonify({'error': 'Failed to create invoice', 'details': str(e)}), 500


@api_bp.route('/invoices', methods=['GET'])
@jwt_required()
@swag_from('../resources/swagger/invoices_get.yml', validation=False)
def list_invoices():
    """Listet die registrierten Rechnungen des eingeloggten Artists (nur, wenn `Invoice`-Model vorhanden ist).
    Ohne Model gibt es 204 (No Content), da die Dateien direkt in Supabase gelistet werden.
    """
    user_id, artist = get_current_user()
    if not artist:
        return jsonify({'error': 'Current user not linked to an artist'}), 403

    if not HAS_INVOICE_MODEL:
        return ('', 204)

    try:
        rows = Invoice.query.filter_by(artist_id=artist.id).order_by(Invoice.created_at.desc()).all()
        return jsonify([
            {
                'id': r.id,
                'storage_path': r.storage_path,
                'status': getattr(r, 'status', None),
                'amount_cents': getattr(r, 'amount_cents', None),
                'currency': getattr(r, 'currency', 'EUR'),
                'invoice_date': (r.invoice_date.isoformat() if getattr(r, 'invoice_date', None) else None),
                'created_at': (r.created_at.isoformat() if getattr(r, 'created_at', None) else None),
                'updated_at': (r.updated_at.isoformat() if getattr(r, 'updated_at', None) else None),
            }
            for r in rows
        ]), 200
    except Exception as e:
        logger.exception('Failed to list invoices')
        return jsonify({'error': 'Failed to list invoices', 'details': str(e)}), 500