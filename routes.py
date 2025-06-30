from flask import current_app, request, jsonify
from flask import Blueprint, render_template
from datamanager import DataManager
from services import calculate_price
from models import db
from flasgger import swag_from
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

api_bp = Blueprint('api', __name__)
admin_bp = Blueprint('admin', __name__, template_folder='templates')
auth_bp = Blueprint('auth', __name__)
dm = DataManager()

def get_current_user():
    """
    Returns a tuple (user_id, user) for the currently authenticated JWT user.
    """
    user_id = get_jwt_identity()
    user = dm.get_artist(user_id)
    return user_id, user

#auth-route
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email')
    pw = data.get('password')
    artist = dm.get_artist_by_email(email)
    if artist and artist.check_password(pw):
        token = create_access_token(identity=artist.id)
        return jsonify(access_token=token,
                       user={'id': artist.id, 'email': artist.email}), 200
    return jsonify({"msg": "Invalid credentials"}), 401


@auth_bp.route('/logout')
def logout():
    # Logout functionality remains unchanged
    pass


# Artists
@api_bp.route('/artists', methods=['GET'])
@swag_from('resources/swagger/artists_get.yml')
def list_artists():
    artists = dm.get_all_artists()
    return jsonify([{
        'id': a.id,
        'name': a.name,
        'email': a.email,
        'phone_number': a.phone_number,
        'disciplines': [d.name for d in a.disciplines],
    } for a in artists])

@api_bp.route('/artists', methods=['POST'])
@swag_from('resources/swagger/artists_post.yml')
def create_artist():
    data = request.json
    disciplines = data.get('disciplines')
    if not disciplines:
        return jsonify({'error': 'Disciplines must be provided!'}), 400

    artist = dm.create_artist(
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

    # Set password if provided
    if 'password' in data:
        artist.set_password(data['password'])
    db.session.commit()
    return jsonify({'id': artist.id}), 201

@api_bp.route('/artists/<int:artist_id>', methods=['DELETE'])
@jwt_required()
@swag_from('resources/swagger/artists_delete.yml')
def delete_artist(artist_id):
    user_id = get_jwt_identity()
    # nur der eingeloggte Artist darf sich selbst löschen
    if user_id != artist_id:
        return jsonify({'error':'Forbidden'}), 403

    success = dm.delete_artist(artist_id)
    if success:
        # und gleich ausloggen
        # from flask_login import logout_user
        # logout_user()
        return jsonify({'deleted': artist_id}), 200

    return jsonify({'error':'Not found'}), 404

# Booking Requests
@api_bp.route('/requests', methods=['GET'])
@jwt_required()
@swag_from('resources/swagger/requests_get.yml')
def list_requests():
    user_id = get_jwt_identity()
    # Liefere persönliche Empfehlungen für den eingeloggten Artist
    result = dm.get_requests_for_artist_with_recommendation(user_id)
    return jsonify(result)

@api_bp.route('/requests', methods=['POST'])
@swag_from('resources/swagger/requests_post.yml')
def create_request():
    data = request.json
    # Normalize team_size: accept numeric or strings "solo"/"duo"
    raw_team_size = data.get('team_size')
    if isinstance(raw_team_size, str):
        ts_lower = raw_team_size.strip().lower()
        if ts_lower == 'solo':
            team_size = 1
        elif ts_lower == 'duo':
            team_size = 2
        elif ts_lower in ('group', 'gruppe'):
            team_size = 3
            # simplified, because we don't calculate pmin or pmax for more than 2 people
        else:
            try:
                team_size = int(raw_team_size)
            except ValueError:
                return jsonify({'error': 'Invalid team_size'}), 400
    else:
        team_size = raw_team_size
    # Einheitlicher Key: 'disciplines'
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
        show_discipline   = disciplines,  # hier auch korrekt!
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
    # Sum base prices
    if not req.artists:
        req.price_min = None
        req.price_max = None
        pmin = None
        pmax = None
    else:
        fee_pct = float(current_app.config.get("AGENCY_FEE_PERCENT", 20))
        # Travel fee only if at least one artist from a different city
        event_city = data.get('event_address', '').split(',')[-1].strip().lower()
        external_artists = [
            a for a in artist_objs
            if a.address and event_city not in a.address.lower()
        ]
        travel_distance = req.distance_km if external_artists else 0.0

        # Determine base_min/base_max by team size
        if team_size == 1:
            base_min = min(a.price_min for a in artist_objs)
            base_max = max(a.price_max for a in artist_objs)
        elif team_size == 2:
            sorted_by_min = sorted(artist_objs, key=lambda a: a.price_min)
            sorted_by_max = sorted(artist_objs, key=lambda a: a.price_max, reverse=True)
            base_min = sum(a.price_min for a in sorted_by_min[:2])
            base_max = sum(a.price_max for a in sorted_by_max[:2])
        else:
            base_min = base_max = None

        # Calculate price if solo or duo, else manual review
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

@api_bp.route('/requests/<int:req_id>/offer', methods=['PUT'])
@jwt_required()
@swag_from('resources/swagger/requests_offer_put.yml')
def set_offer(req_id):
    user_id, user = get_current_user()
    req = dm.get_request(req_id)
    if not req or (user_id not in [a.id for a in req.artists]
                   and not user.is_admin):
        return jsonify({'error':'Not allowed'}), 403

    data = request.json
    artist_gage = data.get('artist_gage')
    if artist_gage is None:
        return jsonify({'error': 'artist_gage is required'}), 400

    # Berechne neue Basis: Ersetze nur die Gage des aktuellen Artists
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

    # Benachrichtige Artists
    for artist in req.artists:
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
    current_app.logger.info(f"PUSH to {artist.id}: {message}")


@api_bp.route('/requests/<int:req_id>/status', methods=['PUT'])
@jwt_required()
@swag_from('resources/swagger/requests_status_put.yml')
def change_status(req_id):
    user_id = get_jwt_identity()
    data = request.json
    status = data.get('status')
    req = dm.change_status(req_id, status)
    if not req:
        return jsonify({'error':'Invalid'}), 400
    return jsonify({'status': req.status})

# Availability
@api_bp.route('/availability', methods=['GET'])
@jwt_required()
@swag_from('resources/swagger/availability_get.yml')
def get_availability():
    user_id = get_jwt_identity()
    slots = dm.get_availabilities(user_id)
    return jsonify([{'id': s.id, 'date': s.date.isoformat()} for s in slots])

@api_bp.route('/availability', methods=['POST'])
@jwt_required()
@swag_from('resources/swagger/availability_post.yml')
def add_availability():
    user_id = get_jwt_identity()
    data = request.get_json()
    if isinstance(data, list):
        slots = []
        for item in data:
            date_str = item.get('date')
            slot = dm.add_availability(user_id, date_str)
            slots.append({'id': slot.id})
        return jsonify(slots), 201
    else:
        date_str = data.get('date')
        slot = dm.add_availability(user_id, date_str)
        return jsonify({'id': slot.id}), 201

@api_bp.route('/availability/<int:slot_id>', methods=['DELETE'])
@jwt_required()
@swag_from('resources/swagger/availability_delete.yml')
def remove_availability(slot_id):
    user_id = get_jwt_identity()
    slot = dm.remove_availability(slot_id)
    if not slot or slot.artist_id != user_id:
        return jsonify({'error':'Forbidden'}), 403
    return jsonify({'deleted': slot_id})


# Admin rights
@api_bp.route('/requests/all', methods=['GET'])
@jwt_required()
@swag_from('resources/swagger/requests_all_get.yml')
def list_all_requests():
    user_id, user = get_current_user()
    if not user.is_admin:
        return jsonify({'error': 'Forbidden'}), 403

    all_requests = dm.get_all_requests()
    return jsonify([{
        'id':                r.id,
        'client_name':       r.client_name,
        'client_email':      r.client_email,
        'event_date':        r.event_date.isoformat(),
        'event_time':        r.event_time.isoformat() if r.event_time else None,
        'duration_minutes':  r.duration_minutes,
        'event_type':        r.event_type,
        'show_discipline':   r.show_discipline,
        'team_size':         r.team_size,
        'number_of_guests':  r.number_of_guests,
        'event_address':     r.event_address,
        'is_indoor':         r.is_indoor,
        'special_requests':  r.special_requests,
        'needs_light':       r.needs_light,
        'needs_sound':       r.needs_sound,
        'status':            r.status,
        'price_min':         r.price_min,
        'price_max':         r.price_max,
        'price_offered':     r.price_offered,
        'artist_ids': [a.id for a in r.artists]
    } for r in all_requests])

# AdminOffer CRUD
@admin_bp.route('/requests/<int:req_id>/admin_offers', methods=['GET'])
@jwt_required()
@swag_from('resources/swagger/admin_requests_admin_offers_get.yml')
def list_admin_offers(req_id):
    user_id, user = get_current_user()
    if not user.is_admin:
        return jsonify({'error': 'Forbidden'}), 403
    offers = dm.get_admin_offers(req_id)
    return jsonify([{
        'id': o.id,
        'request_id': o.request_id,
        'admin_id': o.admin_id,
        'override_price': o.override_price,
        'notes': o.notes,
        'created_at': o.created_at.isoformat()
    } for o in offers])

@admin_bp.route('/requests/<int:req_id>/admin_offers', methods=['POST'])
@jwt_required()
@swag_from('resources/swagger/admin_requests_admin_offers_post.yml')
def create_admin_offer(req_id):
    user_id, user = get_current_user()
    if not user.is_admin:
        return jsonify({'error': 'Forbidden'}), 403
    data = request.json
    price = data.get('override_price')
    if price is None:
        return jsonify({'error': 'override_price is required'}), 400
    notes = data.get('notes')
    offer = dm.create_admin_offer(req_id, user_id, price, notes)
    return jsonify({'id': offer.id}), 201

@admin_bp.route('/admin_offers/<int:offer_id>', methods=['PUT'])
@jwt_required()
@swag_from('resources/swagger/admin_admin_offers_put.yml')
def update_admin_offer(offer_id):
    user_id, user = get_current_user()
    if not user.is_admin:
        return jsonify({'error': 'Forbidden'}), 403
    data = request.json
    price = data.get('override_price')
    notes = data.get('notes')
    offer = dm.update_admin_offer(offer_id, price, notes)
    if not offer:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({
        'id': offer.id,
        'override_price': offer.override_price,
        'notes': offer.notes
    })

@admin_bp.route('/admin_offers/<int:offer_id>', methods=['DELETE'])
@jwt_required()
@swag_from('resources/swagger/admin_admin_offers_delete.yml')
def delete_admin_offer(offer_id):
    user_id, user = get_current_user()
    if not user.is_admin:
        return jsonify({'error': 'Forbidden'}), 403
    success = dm.delete_admin_offer(offer_id)
    if not success:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({'deleted': offer_id})

@admin_bp.route('/dashboard')
@jwt_required()
@swag_from('resources/swagger/dashboard_get.yml')
def dashboard():
    user_id, user = get_current_user()
    if not user.is_admin:
        return "Forbidden", 403

    all_slots  = dm.get_all_availabilities()
    all_offers = dm.get_all_offers()
    return render_template('dashboard.html',
                           slots=all_slots,
                           offers=all_offers)