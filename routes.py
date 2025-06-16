from flask import current_app
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from datamanager import DataManager
from services import calculate_price
from models import db

api_bp = Blueprint('api', __name__)
admin_bp = Blueprint('admin', __name__, template_folder='templates')
dm = DataManager()


# Artists
@api_bp.route('/artists', methods=['GET'])
def list_artists():
    artists = dm.get_all_artists()
    return jsonify([{
        'id': a.id,
        'name': a.name,
        'email': a.email,
        'phone_number': a.phone_number
    } for a in artists])

@api_bp.route('/artists', methods=['POST'])
def create_artist():
    data = request.json
    artist = dm.create_artist(
        name         = data['name'],
        email        = data['email'],
        password     = data['password'],
        phone_number = data.get('phone_number'),
        address      = data.get('address')
    )
    # Set password if provided
    if 'password' in data:
        artist.set_password(data['password'])
        db.session.commit()
    return jsonify({'id': artist.id}), 201

@api_bp.route('/artists/<int:artist_id>', methods=['DELETE'])
@login_required
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
        'show_type':         r.show_type,
        'team_size':         r.team_size,
        'number_of_guests':  r.number_of_guests,
        'event_address':     r.event_address,
        'is_indoor':         r.is_indoor,
        'special_requests':  r.special_requests,
        'needs_light':       r.needs_light,
        'needs_sound':       r.needs_sound,
        'needs_fog':         r.needs_fog,
        'status':            r.status,
        'price_min':         r.price_min,
        'price_max':         r.price_max,
        'price_offered':     r.price_offered,
        'artist_ids': [a.id for a in r.artists]
    } for r in reqs])

@api_bp.route('/requests', methods=['POST'])
def create_request():
    data = request.json
    req = dm.create_request(
        client_name       = data['client_name'],
        client_email      = data['client_email'],
        event_date        = data['event_date'],
        event_time        = data['event_time'],
        duration_minutes  = data['duration_minutes'],
        event_type        = data['event_type'],
        show_type         = data['show_type'],
        team_size         = data['team_size'],
        number_of_guests  = data['number_of_guests'],
        event_address     = data['event_address'],
        is_indoor         = data['is_indoor'],
        special_requests  = data.get('special_requests',''),
        needs_light       = data.get('needs_light', False),
        needs_sound       = data.get('needs_sound', False),
        needs_fog         = data.get('needs_fog', False),
        artist_ids        = data['artist_ids'],
        distance_km       = data.get('distance_km', 0.0),
        newsletter_opt_in = data.get('newsletter_opt_in', False)
    )
    # Sum base prices
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
        needs_fog      = req.needs_fog,
        show_type      = req.show_type,
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
def set_offer(req_id):
    req = dm.get_request(req_id)
    if not req or current_user not in req.artists:
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
def get_availability():
    slots = dm.get_availabilities(current_user.id)
    return jsonify([{'id': s.id, 'date': s.date.isoformat()} for s in slots])

@api_bp.route('/availability', methods=['POST'])
@login_required
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
def remove_availability(slot_id):
    slot = dm.remove_availability(slot_id)
    if not slot or slot.artist_id != current_user.id:
        return jsonify({'error':'Forbidden'}), 403
    return jsonify({'deleted': slot_id})


# Admin rights
@admin_bp.route('/dashboard')
@login_required
def dashboard():
    if not current_user.is_admin:
        return "Forbidden", 403

    all_slots  = dm.get_all_availabilities()
    all_offers = dm.get_all_offers()
    return render_template('dashboard.html',
                           slots=all_slots,
                           offers=all_offers)