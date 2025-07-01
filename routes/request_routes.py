from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datamanager import DataManager
from services.calculate_price import calculate_price
from flask import current_app
from models import db
from flasgger import swag_from
from routes.api_routes import get_current_user

"""
Booking-Modul: Endpunkte zum Erstellen, Abrufen und Bearbeiten von Buchungsanfragen.
"""

# Blueprint für Buchungsanfragen unter /api/requests
booking_bp = Blueprint('booking', __name__, url_prefix='/api/requests')
dm = DataManager()

@booking_bp.route('/requests', methods=['GET'])
@jwt_required()
@swag_from('../resources/swagger/requests_get.yml')
def list_requests():
    """Gibt passende Buchungsanfragen für den eingeloggten Artist zurück."""
    user_id = get_jwt_identity()
    result = dm.get_requests_for_artist_with_recommendation(user_id)
    return jsonify(result)

# kein Login erforderlich!
@booking_bp.route('/requests', methods=['POST'])
@swag_from('../resources/swagger/requests_post.yml')
def create_request():
    """Erstellt eine neue Buchungsanfrage und berechnet eine Preisspanne."""
    data = request.json
    # Team-Größe normalisieren: Zahlen oder Strings wie "solo"/"duo" akzeptieren
    raw_team_size = data.get('team_size')
    if isinstance(raw_team_size, str):
        ts_lower = raw_team_size.strip().lower()
        if ts_lower == 'solo':
            team_size = 1
        elif ts_lower == 'duo':
            team_size = 2
        elif ts_lower in ('group', 'gruppe'):
            team_size = 3
            # vereinfacht, da keine Preisberechnung mehr ab 3 Personen
        else:
            try:
                team_size = int(raw_team_size)
            except ValueError:
                return jsonify({'error': 'Invalid team_size'}), 400
    else:
        team_size = raw_team_size

    disciplines = data.get('disciplines', [])
    event_date = data['event_date']
    artist_objs = dm.get_artists_by_discipline(disciplines, event_date)
    req = dm.create_request(
        client_name       = data['client_name'],
        client_email      = data['client_email'],
        event_date        = data['event_date'],
        event_time        = data['event_time'],
        duration_minutes  = data['duration_minutes'],
        event_type        = data['event_type'],
        show_discipline   = disciplines,  
        team_size         = team_size,
        number_of_guests  = data['number_of_guests'],
        event_address     = data['event_address'],
        is_indoor         = data['is_indoor'],
        special_requests  = data.get('special_requests',''),
        needs_light       = data.get('needs_light', False),
        needs_sound       = data.get('needs_sound', False),
        artists           = artist_objs,
        distance_km       = data.get('distance_km', 0.0),
        newsletter_opt_in = data.get('newsletter_opt_in', False)
    )
    # Preisspanne berechnen basierend auf ausgewählten Artists und Parametern
    if not req.artists:
        req.price_min = None
        req.price_max = None
        pmin = None
        pmax = None
    else:
        fee_pct = float(current_app.config.get("AGENCY_FEE_PERCENT", 20))
        #wenn Artisten aus verschiedenen Städten kommen
        event_city = data.get('event_address', '').split(',')[-1].strip().lower()
        external_artists = [
            a for a in artist_objs
            if a.address and event_city not in a.address.lower()
        ]
        travel_distance = req.distance_km if external_artists else 0.0

        if team_size == 1:
            base_min = min(a.price_min for a in artist_objs)
            base_max = max(a.price_max for a in artist_objs)
        elif team_size == 2:
            # hier vereinfacht - kummuliert die Preis- Unter- & -Obergrenze der ersten beiden passenden Artisten
            sorted_by_min = sorted(artist_objs, key=lambda a: a.price_min)
            sorted_by_max = sorted(artist_objs, key=lambda a: a.price_max, reverse=True)
            base_min = sum(a.price_min for a in sorted_by_min[:2])
            base_max = sum(a.price_max for a in sorted_by_max[:2])
        else:
            base_min = base_max = None

        if base_min is not None:
            args = {
                'base_min': base_min,
                'base_max': base_max,
                'distance_km': travel_distance,
                'fee_pct': fee_pct,
                'newsletter': req.newsletter_opt_in,
                'event_type': req.event_type,
                'num_guests': req.number_of_guests,
                'is_weekend': req.event_date.weekday() >= 5,
                'is_indoor': req.is_indoor,
                'needs_light': req.needs_light,
                'needs_sound': req.needs_sound,
                'show_discipline': req.show_discipline,
                'team_size': team_size,
                'duration': req.duration_minutes,
                'city': None
            }
            pmin, pmax = calculate_price(**args)
        else:
            pmin = pmax = None

        req.price_min = pmin
        req.price_max = pmax
    db.session.commit()

    return jsonify({
        'request_id': req.id,
        'price_min': pmin,
        'price_max': pmax,
        'num_available_artists': len(artist_objs)
    }), 201


@booking_bp.route('/requests/<int:req_id>/offer', methods=['PUT'])
@jwt_required()
@swag_from('../resources/swagger/requests_offer_put.yml')
def set_offer(req_id):
    """Ermöglicht einem eingeloggten Artist, ein Angebot für eine Anfrage abzugeben."""
    user_id, user = get_current_user()
    req = dm.get_request(req_id)
    # Zugriff prüfen: Nur beteiligte Artists oder Admins dürfen bieten
    if not req or (user_id not in [a.id for a in req.artists]
                   and not user.is_admin):
        return jsonify({'error':'Not allowed'}), 403

    data = request.json
    artist_gage = data.get('artist_gage')
    if artist_gage is None:
        return jsonify({'error': 'artist_gage is required'}), 400

    # Neue Basis berechnen: Preis des aktuellen Artists ersetzen
    base_min = sum(
        artist_gage if a.id == user_id else a.price_min
        for a in req.artists
    )
    base_max = sum(
        artist_gage if a.id == user_id else a.price_max
        for a in req.artists
    )

    fee_pct = float(current_app.config.get("AGENCY_FEE_PERCENT", 20))
    pmin, pmax = calculate_price(
        base_min       = base_min,
        base_max       = base_max,
        distance_km    = req.distance_km,
        fee_pct        = fee_pct,
        newsletter     = req.newsletter_opt_in,
        event_type     = req.event_type,
        num_guests     = req.number_of_guests,
        is_weekend     = req.event_date.weekday() >= 5,
        is_indoor      = req.is_indoor,
        needs_light    = req.needs_light,
        needs_sound    = req.needs_sound,
        show_discipline = req.show_discipline,
        team_size      = req.team_size,
        duration       = req.duration_minutes,
        city           = None
    )

    # Speichere das neue Angebot
    req = dm.set_offer(req_id, user_id, artist_gage)

    # Push-Benachrichtigung an alle Artists senden
    for artist in req.artists:
        #aktuell noch dummy
        send_push(artist, f'New offer: {pmax} EUR for request {req_id}')

    # Bei Solo-Booking sofort das eigene Angebot zurückgeben
    if req.team_size == 1:
        return jsonify({'status': req.status, 'price_offered': req.price_offered})
    # Bei Duo+ erst Preis, wenn alle offeriert haben
    elif req.price_offered is not None:
        return jsonify({'status': req.status, 'price_offered': req.price_offered})
    else:
        return jsonify({'status': req.status}), 200

def send_push(artist, message):
    """Protokolliert eine Push-Nachricht an einen Artist."""
    current_app.logger.info(f"PUSH to {artist.id}: {message}")


@booking_bp.route('/requests/<int:req_id>/status', methods=['PUT'])
@jwt_required()
@swag_from('../resources/swagger/requests_status_put.yml')
def change_status(req_id):
    """Ändert den Status einer Buchungsanfrage."""
    user_id = get_jwt_identity()
    data = request.json
    status = data.get('status')
    # Statusänderung durchführen
    req = dm.change_status(req_id, status)
    if not req:
        return jsonify({'error':'Invalid'}), 400
    return jsonify({'status': req.status})