from flask import current_app
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from datamanager import DataManager
from services import calculate_price
from models import db
from flasgger import swag_from

api_bp = Blueprint('api', __name__)
admin_bp = Blueprint('admin', __name__, template_folder='templates')
dm = DataManager()


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
@login_required
@swag_from('resources/swagger/artists_delete.yml')
def delete_artist(artist_id):
    # nur der eingeloggte Artist darf sich selbst löschen
    if current_user.id != artist_id:
        return jsonify({'error':'Forbidden'}), 403

    success = dm.delete_artist(artist_id)
    if success:
        # und gleich ausloggen
        from flask_login import logout_user
        logout_user()
        return jsonify({'deleted': artist_id}), 200

    return jsonify({'error':'Not found'}), 404

# Booking Requests
@api_bp.route('/requests', methods=['GET'])
@login_required
@swag_from('resources/swagger/requests_get.yml')
def list_requests():
    # Only show requests for this artist
    all_reqs = dm.get_all_requests()
    # Filter: only those including current_user
    reqs = [r for r in all_reqs if current_user in r.artists]
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
        # 'needs_fog' removed
        'status':            r.status,
        'price_min':         r.price_min,
        'price_max':         r.price_max,
        'price_offered':     r.price_offered,
        'artist_ids': [a.id for a in r.artists]
    } for r in reqs])

@api_bp.route('/requests', methods=['POST'])
@swag_from('resources/swagger/requests_post.yml')
def create_request():
    data = request.json
    # Determine artists by discipline instead of explicit IDs, so the customer can choose just the discipline
    disciplines = data.get('show_discipline', [])
    artist_objs = dm.get_artists_by_discipline(disciplines)
    req = dm.create_request(
        client_name       = data['client_name'],
        client_email      = data['client_email'],
        event_date        = data['event_date'],
        event_time        = data['event_time'],
        duration_minutes  = data['duration_minutes'],
        event_type        = data['event_type'],
        show_discipline   = data['show_discipline'],
        team_size         = data['team_size'],
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
        base_min = sum(a.price_min for a in req.artists)
        base_max = sum(a.price_max for a in req.artists)
        fee_pct = float(current_app.config.get("AGENCY_FEE_PERCENT", 20))
        # Calculate and store
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
            # needs_fog removed
            show_discipline = req.show_discipline,
            team_size      = req.team_size,
            duration       = req.duration_minutes,
            city           = None  # optional: extract city from event_address
        )
        req.price_min = pmin
        req.price_max = pmax
    db.session.commit()

    return jsonify({
        'request_id': req.id,
        'price_min': pmin,
        'price_max': pmax
    }), 201

@api_bp.route('/requests/<int:req_id>/offer', methods=['PUT'])
@login_required
@swag_from('resources/swagger/requests_offer_put.yml')
def set_offer(req_id):
    req = dm.get_request(req_id)
    if not req or (current_user.id not in [a.id for a in req.artists]
                   and not current_user.is_admin):
        return jsonify({'error':'Not allowed'}), 403
    data = request.json
    price = data.get('price_offered')
    dm.set_offer(req_id, price)
    # notify artists
    for artist in req.artists:
        send_push(artist, f'New offer: {price} EUR for request {req_id}')
    return jsonify({'status':'offered'})

def send_push(artist, message):
    current_app.logger.info(f"PUSH to {artist.id}: {message}")


@api_bp.route('/requests/<int:req_id>/status', methods=['PUT'])
@login_required
@swag_from('resources/swagger/requests_status_put.yml')
def change_status(req_id):
    data = request.json
    status = data.get('status')
    req = dm.change_status(req_id, status)
    if not req:
        return jsonify({'error':'Invalid'}), 400
    return jsonify({'status': req.status})

# Availability
@api_bp.route('/availability', methods=['GET'])
@login_required
@swag_from('resources/swagger/availability_get.yml')
def get_availability():
    slots = dm.get_availabilities(current_user.id)
    return jsonify([{'id': s.id, 'date': s.date.isoformat()} for s in slots])

@api_bp.route('/availability', methods=['POST'])
@login_required
@swag_from('resources/swagger/availability_post.yml')
def add_availability():
    data = request.get_json()
    if isinstance(data, list):
        slots = []
        for item in data:
            date_str = item.get('date')
            slot = dm.add_availability(current_user.id, date_str)
            slots.append({'id': slot.id})
        return jsonify(slots), 201
    else:
        date_str = data.get('date')
        slot = dm.add_availability(current_user.id, date_str)
        return jsonify({'id': slot.id}), 201

@api_bp.route('/availability/<int:slot_id>', methods=['DELETE'])
@login_required
@swag_from('resources/swagger/availability_delete.yml')
def remove_availability(slot_id):
    slot = dm.remove_availability(slot_id)
    if not slot or slot.artist_id != current_user.id:
        return jsonify({'error':'Forbidden'}), 403
    return jsonify({'deleted': slot_id})


# Admin rights
@api_bp.route('/requests/all', methods=['GET'])
@login_required
@swag_from('resources/swagger/requests_all_get.yml')
def list_all_requests():
    if not current_user.is_admin:
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


@admin_bp.route('/dashboard')
@login_required
@swag_from('resources/swagger/dashboard_get.yml')

def dashboard():
    if not current_user.is_admin:
        return "Forbidden", 403

    all_slots  = dm.get_all_availabilities()
    all_offers = dm.get_all_offers()
    return render_template('dashboard.html',
                           slots=all_slots,
                           offers=all_offers)