from flask import Blueprint, request, jsonify
from flasgger import swag_from
from routes.api_routes import get_current_user
from managers.booking_requests_manager import BookingRequestManager
from managers.admin_offer_manager import AdminOfferManager
from managers.availability_manager import AvailabilityManager
from managers.artist_manager import ArtistManager
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from models import Artist
import logging
logger = logging.getLogger(__name__)

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
artist_mgr = ArtistManager()

# Admin rights
@admin_bp.route('/requests/all', methods=['GET'])
@jwt_required()
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
        'recommended_price_min': r.price_min,
        'recommended_price_max': r.price_max,
        'price_offered':     r.price_offered,
        'artist_ids': [a.id for a in r.artists]
    } for r in all_requests])

# AdminOffer CRUD
@admin_bp.route('/requests/<int:req_id>/admin_offers', methods=['GET'])
@jwt_required()
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


@admin_bp.route('/admin_offers/<int:offer_id>', methods=['GET'])
@jwt_required()
def get_admin_offer(offer_id):
    """Gibt ein einzelnes Admin-Angebot anhand seiner ID zurück."""
    offer = offer_mgr.get_admin_offer(offer_id)
    if not offer:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(offer_mgr.serialize(offer)), 200

@admin_bp.route('/requests/<int:req_id>/admin_offers', methods=['POST'])
@jwt_required()
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
@jwt_required()
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
@jwt_required()
@swag_from('../resources/swagger/admin_admin_offers_delete.yml')
def delete_admin_offer(offer_id):
    """Löscht ein Admin-Angebot anhand seiner ID."""
    deleted = offer_mgr.delete_admin_offer(offer_id)
    if not deleted:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({'deleted': deleted.id})

# -------------------------------------------------------------
# Admin: Artist-Freigaben (Listen, Approve, Reject)
# -------------------------------------------------------------
@admin_bp.route('/artists', methods=['GET'])
@jwt_required()
@swag_from('../resources/swagger/admin_artists_get.yml')
def list_artists_by_status():
    """Listet Artists nach Freigabe-Status (default: pending)."""
    logger.debug(f"[ADMIN] list_artists_by_status called; args={dict(request.args)}")
    try:
        claims = get_jwt()
        app_md = claims.get('app_metadata') or {}
        is_admin = (isinstance(app_md, dict) and app_md.get('role') == 'admin') or (claims.get('role') == 'admin')
        if not is_admin:
            user_id, artist = get_current_user()
            is_admin = bool(artist and getattr(artist, 'is_admin', False))
        logger.debug(f"[ADMIN] list_artists_by_status claims_role={claims.get('role')} app_meta_role={(app_md or {}).get('role')} resolved_is_admin={is_admin}")
        if not is_admin:
            return jsonify({'error': 'Not allowed'}), 403

        status = (request.args.get('status') or 'pending').lower()
        if status not in {'pending', 'approved', 'rejected', 'unsubmitted'}:
            logger.warning(f"[ADMIN] invalid status parameter: {status}")
            return jsonify({'error': 'invalid status'}), 400

        try:
            if status == 'pending':
                artists = artist_mgr.get_pending_artists()
            elif status == 'approved':
                artists = artist_mgr.get_approved_artists()
            elif status == 'rejected':
                artists = artist_mgr.get_rejected_artists()
            else:
                artists = artist_mgr.get_unsubmitted_artists()
        except Exception as ex:
            logger.exception(f"[ADMIN] list_artists_by_status query failed for status={status}: {ex}")
            raise

        logger.debug(f"[ADMIN] list_artists_by_status result_count={len(artists)} for status={status}")

        def _serialize(a: Artist):
            return {
                'id': a.id,
                'name': getattr(a, 'name', None),
                'email': getattr(a, 'email', None),
                'approval_status': getattr(a, 'approval_status', None),
                'rejection_reason': getattr(a, 'rejection_reason', None),
                'approved_at': a.approved_at.isoformat() if getattr(a, 'approved_at', None) else None,
                'approved_by': getattr(a, 'approved_by', None),
                'profile_image_url': getattr(a, 'profile_image_url', None),
                'gallery_urls': getattr(a, 'gallery_urls', []),
                'disciplines': [d.name for d in getattr(a, 'disciplines', [])] if getattr(a, 'disciplines', None) else [],
                'bio': getattr(a, 'bio', None),
            }

        return jsonify([_serialize(a) for a in artists]), 200
    except Exception as e:
        logger.exception(f"[ADMIN] list_artists_by_status failed: {e}")
        return jsonify({'error': 'internal error'}), 500


@admin_bp.route('/artists/<int:artist_id>/approve', methods=['POST'])
@jwt_required()
@swag_from('../resources/swagger/admin_artists_id_approve_post.yml')
def approve_artist(artist_id):
    """Gibt einen Artist frei (setzt approval_status=approved)."""
    logger.debug(f"[ADMIN] approve_artist called; artist_id={artist_id}")
    try:
        claims = get_jwt()
        app_md = claims.get('app_metadata') or {}
        is_admin = (isinstance(app_md, dict) and app_md.get('role') == 'admin') or (claims.get('role') == 'admin')
        if not is_admin:
            user_id, artist = get_current_user()
            is_admin = bool(artist and getattr(artist, 'is_admin', False))
        logger.debug(f"[ADMIN] approve_artist claims_role={claims.get('role')} app_meta_role={(app_md or {}).get('role')} resolved_is_admin={is_admin}")
        if not is_admin:
            return jsonify({'error': 'Not allowed'}), 403

        admin_id = claims.get('user_id') or claims.get('sub') or get_jwt_identity()
        logger.debug(f"[ADMIN] approve_artist admin_id={admin_id}")

        artist = offer_mgr.approve_artist(artist_id=artist_id, admin_id=admin_id)
        if not artist:
            logger.warning(f"[ADMIN] approve_artist not found: artist_id={artist_id}")
            return jsonify({'error': 'Not found'}), 404

        logger.info(f"[ADMIN] artist approved: artist_id={artist.id} by admin_id={admin_id}")
        return jsonify({
            'id': artist.id,
            'status': artist.approval_status,
            'approved_at': artist.approved_at.isoformat() if artist.approved_at else None,
            'approved_by': artist.approved_by,
        }), 200
    except Exception as e:
        logger.exception(f"[ADMIN] approve_artist failed for artist_id={artist_id}: {e}")
        return jsonify({'error': 'internal error'}), 500


@admin_bp.route('/artists/<int:artist_id>/reject', methods=['POST'])
@jwt_required()
@swag_from('../resources/swagger/admin_artists_id_reject_post.yml')
def reject_artist(artist_id):
    """Lehnt einen Artist ab (approval_status=rejected) und speichert optionalen Grund."""
    logger.debug(f"[ADMIN] reject_artist called; artist_id={artist_id}")
    try:
        claims = get_jwt()
        app_md = claims.get('app_metadata') or {}
        is_admin = (isinstance(app_md, dict) and app_md.get('role') == 'admin') or (claims.get('role') == 'admin')
        if not is_admin:
            user_id, artist = get_current_user()
            is_admin = bool(artist and getattr(artist, 'is_admin', False))
        logger.debug(f"[ADMIN] reject_artist claims_role={claims.get('role')} app_meta_role={(app_md or {}).get('role')} resolved_is_admin={is_admin}")
        if not is_admin:
            return jsonify({'error': 'Not allowed'}), 403

        body = request.get_json(silent=True) or {}
        reason = (body.get('reason') or body.get('comment') or '').strip()
        admin_id = claims.get('user_id') or claims.get('sub') or get_jwt_identity()
        logger.debug(f"[ADMIN] reject_artist admin_id={admin_id} reason={reason!r}")

        artist = offer_mgr.reject_artist(artist_id=artist_id, admin_id=admin_id, reason=reason)
        if not artist:
            logger.warning(f"[ADMIN] reject_artist not found: artist_id={artist_id}")
            return jsonify({'error': 'Not found'}), 404

        logger.info(f"[ADMIN] artist rejected: artist_id={artist.id} by admin_id={admin_id} reason={reason!r}")
        return jsonify({
            'id': artist.id,
            'status': artist.approval_status,
            'rejection_reason': artist.rejection_reason,
            'approved_at': artist.approved_at.isoformat() if artist.approved_at else None,
            'approved_by': artist.approved_by,
        }), 200
    except Exception as e:
        logger.exception(f"[ADMIN] reject_artist failed for artist_id={artist_id}: {e}")
        return jsonify({'error': 'internal error'}), 500

# -------------------------------------------------------------
# Per-Artist-Status einer Anfrage (Admin) 08.08.25
# -------------------------------------------------------------
@admin_bp.route('/requests/<int:req_id>/artist_status', methods=['GET'])
@jwt_required()
@swag_from('../resources/swagger/admin_artist_status_get.yml')
def admin_get_artist_statuses(req_id):
    """Gibt pro Artist den Status für eine Anfrage zurück (nur Admins)."""
    claims = get_jwt()
    app_md = claims.get('app_metadata') or {}
    is_admin = (isinstance(app_md, dict) and app_md.get('role') == 'admin') or (claims.get('role') == 'admin')
    if not is_admin:
        user_id, artist = get_current_user()
        is_admin = bool(artist and getattr(artist, 'is_admin', False))
    logger.debug(f"admin_get_artist_statuses called for req_id={req_id}; is_admin={is_admin}")
    if not is_admin:
        return jsonify({'error': 'Not allowed'}), 403
    statuses = request_mgr.get_artist_statuses(req_id)
    logger.debug(f"artist_statuses count={len(statuses)} sample={statuses[0] if statuses else None}")
    return jsonify(statuses), 200

@admin_bp.route('/requests/<int:req_id>/artist_status/<int:artist_id>', methods=['PUT'])
@jwt_required()
@swag_from('../resources/swagger/admin_artist_status_put.yml')
def admin_set_artist_status(req_id, artist_id):
    """Setzt den Status für genau einen Artist (nur Admins)."""
    claims = get_jwt()
    app_md = claims.get('app_metadata') or {}
    is_admin = (isinstance(app_md, dict) and app_md.get('role') == 'admin') or (claims.get('role') == 'admin')
    if not is_admin:
        user_id, artist = get_current_user()
        is_admin = bool(artist and getattr(artist, 'is_admin', False))
    if not is_admin:
        return jsonify({'error': 'Not allowed'}), 403
    data = request.get_json(silent=True) or {}
    new_status = data.get('status')
    comment = data.get('comment') or data.get('remark')
    if not new_status:
        return jsonify({'error': 'status is required'}), 400
    ok = request_mgr.set_artist_status(req_id, artist_id, new_status, comment)
    if not ok:
        return jsonify({'error': 'Invalid request/artist/status'}), 400
    return jsonify({'artist_id': artist_id, 'status': new_status, 'comment': comment}), 200

@admin_bp.route('/requests/<int:req_id>/artist_status', methods=['PUT'])
@jwt_required()
@swag_from('../resources/swagger/admin_artist_status_bulk_put.yml')
def admin_set_artists_status_bulk(req_id):
    """Setzt den Status für alle oder eine Liste von Artists (nur Admins)."""
    claims = get_jwt()
    app_md = claims.get('app_metadata') or {}
    is_admin = (isinstance(app_md, dict) and app_md.get('role') == 'admin') or (claims.get('role') == 'admin')
    if not is_admin:
        user_id, artist = get_current_user()
        is_admin = bool(artist and getattr(artist, 'is_admin', False))
    if not is_admin:
        return jsonify({'error': 'Not allowed'}), 403
    data = request.get_json(silent=True) or {}
    new_status = data.get('status')
    comment = data.get('comment') or data.get('remark')
    artist_ids = data.get('artist_ids')  # optional Liste von Artist-IDs
    if not new_status:
        return jsonify({'error': 'status is required'}), 400
    if artist_ids and isinstance(artist_ids, list):
        updated = request_mgr.set_artists_status(req_id, artist_ids, new_status, comment)
    else:
        updated = request_mgr.set_all_artists_status(req_id, new_status, comment)
    return jsonify({'updated': updated, 'status': new_status, 'comment': comment}), 200

@admin_bp.route('/dashboard')
@jwt_required()
@swag_from('../resources/swagger/dashboard_get.yml')
def dashboard():
    """Gibt Dashboard-Daten (Verfügbarkeiten und Angebote) zurück."""
    slots = avail_mgr.get_all_availabilities()
    offers = request_mgr.get_all_requests()
    return jsonify({
        'slots': slots,  
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