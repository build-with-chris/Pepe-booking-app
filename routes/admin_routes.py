from flask import Blueprint, request, jsonify
from flasgger import swag_from
from routes.api_routes import get_current_user
from managers.booking_requests_manager import BookingRequestManager
from managers.admin_offer_manager import AdminOfferManager
from managers.availability_manager import AvailabilityManager
from routes.auth_routes import requires_auth

"""
Admin-Modul: Enthält alle Endpunkte zum Verwalten von Buchungsanfragen,
Admin-Angeboten und Dashboard-Daten. Nur für Admin-User zugänglich.
"""

# Blueprint für alle Admin-Routen mit URL-Prefix /admin
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Manager-Instanzen
request_mgr = BookingRequestManager()
offer_mgr = AdminOfferManager()
avail_mgr = AvailabilityManager()

# Admin rights
@admin_bp.route('/requests/all', methods=['GET'])
@requires_auth(required_role="admin")
@swag_from('../resources/swagger/requests_all_get.yml')
def list_all_requests():
    """Gibt alle Buchungsanfragen zurück (Admin-View)."""
    all_requests = request_mgr.get_all_requests()
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
@requires_auth(required_role="admin")
@swag_from('../resources/swagger/admin_requests_admin_offers_get.yml')
def list_admin_offers(req_id):
    """Gibt alle Admin-Angebote für eine bestimmte Buchungsanfrage zurück."""
    offers = offer_mgr.get_admin_offers(req_id)
    return jsonify([{
        'id': o.id,
        'request_id': o.request_id,
        'admin_id': o.admin_id,
        'override_price': o.override_price,
        'notes': o.notes,
        'created_at': o.created_at.isoformat()
    } for o in offers])

@admin_bp.route('/requests/<int:req_id>/admin_offers', methods=['POST'])
@requires_auth(required_role="admin")
@swag_from('../resources/swagger/admin_requests_admin_offers_post.yml')
def create_admin_offer(req_id):
    """Erstellt ein neues Admin-Angebot für eine Buchungsanfrage."""
    data = request.json
    price = data.get('override_price')
    if price is None:
        return jsonify({'error': 'override_price is required'}), 400
    notes = data.get('notes')
    user_id = None
    # Try to get user_id from g.user if available
    from flask import g
    if hasattr(g, 'user'):
        user_id = g.user.get('sub') or g.user.get('user_id')
    offer = offer_mgr.create_admin_offer(req_id, user_id, price, notes)
    return jsonify({'id': offer.id}), 201

@admin_bp.route('/admin_offers/<int:offer_id>', methods=['PUT'])
@requires_auth(required_role="admin")
@swag_from('../resources/swagger/admin_admin_offers_put.yml')
def update_admin_offer(offer_id):
    """Aktualisiert ein bestehendes Admin-Angebot."""
    data = request.json
    price = data.get('override_price')
    notes = data.get('notes')
    offer = offer_mgr.update_admin_offer(offer_id, price, notes)
    if not offer:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({
        'id': offer.id,
        'override_price': offer.override_price,
        'notes': offer.notes
    })

@admin_bp.route('/admin_offers/<int:offer_id>', methods=['DELETE'])
@requires_auth(required_role="admin")
@swag_from('../resources/swagger/admin_admin_offers_delete.yml')
def delete_admin_offer(offer_id):
    """Löscht ein Admin-Angebot anhand seiner ID."""
    deleted = offer_mgr.delete_admin_offer(offer_id)
    if not deleted:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({'deleted': deleted.id})

@admin_bp.route('/dashboard')
@requires_auth(required_role="admin")
@swag_from('../resources/swagger/dashboard_get.yml')
def dashboard():
    """Gibt Dashboard-Daten (Verfügbarkeiten und Angebote) zurück."""
    slots = avail_mgr.get_all_availabilities()
    offers = request_mgr.get_all_requests()
    return jsonify({
        'slots': [
            {'id': slot.id, 'date': slot.date.isoformat()}
            for slot in slots
        ],
        'offers': [
            {
                'id': r.id,
                'client_name': r.client_name,
                'client_email': r.client_email,
                'event_date': r.event_date.isoformat(),
                'event_time': r.event_time.isoformat() if r.event_time else None,
                'team_size': r.team_size,
                'status': r.status,
                'price_offered': r.price_offered
            }
            for r in offers
        ]
    }), 200