import time
from typing import Deque, Tuple, Dict, Any
from collections import deque

# In-memory rate limit store: ip -> deque[timestamps]
_RATE_LIMIT_WINDOW_SECONDS = 3600  # 1 hour
_RATE_LIMIT_MAX_REQUESTS = 5       # 5 requests/hour per IP
_rate_limit_hits: Dict[str, Deque[float]] = {}

# In-memory idempotency cache: key -> (created_ts, payload_dict)
_IDEMPOTENCY_TTL_SECONDS = 3600
_idempotency_cache: Dict[str, Tuple[float, dict]] = {}

def _client_ip() -> str:
    """Best-effort client IP extraction (respects X-Forwarded-For)."""
    xff = request.headers.get('X-Forwarded-For')
    if xff:
        return xff.split(',')[0].strip()
    return request.remote_addr or 'unknown'

def _rate_limit_allow(ip: str) -> bool:
    """Return True if request is allowed under the rate limit."""
    now = time.time()
    dq = _rate_limit_hits.setdefault(ip, deque())
    # prune old entries
    cutoff = now - _RATE_LIMIT_WINDOW_SECONDS
    while dq and dq[0] < cutoff:
        dq.popleft()
    if len(dq) >= _RATE_LIMIT_MAX_REQUESTS:
        return False
    dq.append(now)
    return True

def _idempotency_lookup(key: str):
    """Return cached payload if key exists and not expired, else None."""
    if not key:
        return None
    entry = _idempotency_cache.get(key)
    if not entry:
        return None
    created, payload = entry
    if time.time() - created > _IDEMPOTENCY_TTL_SECONDS:
        # expired
        _idempotency_cache.pop(key, None)
        return None
    return payload

def _idempotency_store(key: str, payload: dict) -> None:
    if not key:
        return
    _idempotency_cache[key] = (time.time(), payload)
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.calculate_price import calculate_price
from flask import current_app
from models import db, Artist, BookingRequest
from flasgger import swag_from

from helpers.http_responses import error_response

from managers.booking_requests_manager import BookingRequestManager
from managers.artist_manager import ArtistManager

from email.message import EmailMessage
import smtplib
import ssl

# Manager-Instanzen
request_mgr = BookingRequestManager()
artist_mgr = ArtistManager()

"""
Booking module: Endpoints to create, list and manage booking requests.
"""

# --- 80/20 constants & helpers -------------------------------------------------
MAX_MATCHED_ARTISTS = 5

def _config_fee_pct():
    try:
        return float(current_app.config.get("AGENCY_FEE_PERCENT", 20))
    except Exception:
        return 20.0

REQUIRED_REQUEST_FIELDS = (
    "client_name",
    "client_email",
    "event_date",
    "event_time",
    "duration_minutes",
    "event_type",
    "number_of_guests",
    "event_address",
)

def validate_create_request_payload(data: dict) -> tuple[bool, str | None]:
    """Lightweight validation for create_request payload. Returns (ok, error_message)."""
    if not isinstance(data, dict):
        return False, "payload must be a JSON object"
    for k in REQUIRED_REQUEST_FIELDS:
        if data.get(k) in (None, ""):
            return False, f"missing field: {k}"
    # types
    try:
        int(data.get("duration_minutes"))
        int(data.get("number_of_guests"))
    except Exception:
        return False, "duration_minutes and number_of_guests must be integers"
    # disciplines optional but must be list when present
    d = data.get("disciplines")
    if d is not None and not isinstance(d, list):
        return False, "disciplines must be a list"
    return True, None

def request_brief_json(r: BookingRequest) -> dict:
    """Serialize booking request to a compact JSON structure for lists."""
    return {
        "id": r.id,
        "status": r.status,
        "created_at": r.created_at.isoformat() if getattr(r, "created_at", None) else None,
        "event_address": r.event_address,
        "event_lat": getattr(r, "event_lat", None),
        "event_lon": getattr(r, "event_lon", None),
        "price_min": getattr(r, "price_min", None),
        "price_max": getattr(r, "price_max", None),
        "num_available_artists": getattr(r, "num_available_artists", None),
    }
# ------------------------------------------------------------------------------

# Blueprint für Buchungsanfragen unter /api/requests
booking_bp = Blueprint('booking', __name__, url_prefix='/api/requests')


@booking_bp.route('/requests', methods=['GET'])
@jwt_required()
@swag_from('../resources/swagger/requests_get.yml')
def list_requests():
    """Return booking requests that match the logged-in artist."""
    user_id = get_jwt_identity()
    result = request_mgr.get_requests_for_artist_with_recommendation(user_id)
    return jsonify(result)

@booking_bp.route('/requests/list', methods=['GET'])
@jwt_required()
def list_requests_admin():
    """Admin list of booking requests.
    
    Allows optional filtering by status and sorting by creation date.
    Query parameters:
      - status: optional (e.g. requested | offered | accepted | rejected | cancelled)
      - sort: created_desc (default) | created_asc
      - limit: number of results (default 50)
      - offset: pagination offset
    """
    try:
        status = request.args.get('status') or None
        sort = request.args.get('sort') or 'created_desc'
        limit = int(request.args.get('limit') or 50)
        offset = int(request.args.get('offset') or 0)
    except Exception as e:
        current_app.logger.warning(f"Invalid query params: {e}")
        return error_response("validation_error", "Invalid query parameters", 400)

    items, total = request_mgr.list_requests(status=status, sort=sort, limit=limit, offset=offset)

    return jsonify({
        "items": [request_brief_json(r) for r in items],
        "total": total,
        "limit": limit,
        "offset": offset,
        "sort": sort,
        "status": status,
    })

# kein Login erforderlich!
@booking_bp.route('/requests', methods=['POST'])
@swag_from('../resources/swagger/requests_post.yml')
def create_request():
    """Create a new booking request and calculate a price range."""
    try:
        data = request.get_json(force=True)
        current_app.logger.debug("create_request payload: %s", data)

        # --- Simple per-IP rate limiting (5 req/hour)
        ip = _client_ip()
        if not _rate_limit_allow(ip):
            return error_response("rate_limited", "Too many requests. Try again later.", 429)

        # --- Idempotency-Key support (prevent duplicate creations on reload)
        idem_key = request.headers.get('Idempotency-Key')
        cached = _idempotency_lookup(idem_key) if idem_key else None
        if cached is not None:
            resp = jsonify(cached)
            resp.status_code = 201
            resp.headers["Location"] = cached.get("_location", "")
            resp.headers["Idempotent-Replay"] = "true"
            return resp

        # --- Validation
        ok, err = validate_create_request_payload(data)
        if not ok:
            return error_response("validation_error", err, 400)

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
            else:
                try:
                    team_size = int(raw_team_size)
                except ValueError:
                    return error_response("validation_error", "Invalid team_size", 400)
        else:
            team_size = raw_team_size

        # Disciplines normalization and validation
        raw_disc = data.get('disciplines')
        if raw_disc is None:
            disciplines = []
        elif isinstance(raw_disc, list):
            disciplines = raw_disc
        else:
            return error_response("validation_error", "disciplines must be a list", 400)

        event_date = data['event_date']  # will raise KeyError if missing
        artist_objs = artist_mgr.get_artists_by_discipline(disciplines, event_date) or []
        # Filter only approved artists
        artist_objs = [a for a in artist_objs if getattr(a, 'approval_status', '') == 'approved']
        # Für die UI: kompaktes Matched-Payload (max. MAX_MATCHED_ARTISTS Artists)
        matched_payload = [
            {
                "id": getattr(a, 'id', None),
                "name": getattr(a, 'name', None),
                "price_min": getattr(a, 'price_min', None),
                "price_max": getattr(a, 'price_max', None),
            }
            for a in (artist_objs[:MAX_MATCHED_ARTISTS] if artist_objs else [])
        ]
        req = request_mgr.create_request(
            client_name       = data['client_name'],
            client_email      = data['client_email'],
            event_date        = data['event_date'],
            event_time        = data['event_time'],
            duration_minutes  = data['duration_minutes'],
            event_type        = data['event_type'],
            show_type         = data.get('show_type'),
            show_discipline   = disciplines,
            team_size         = team_size,
            number_of_guests  = data['number_of_guests'],
            event_address     = data['event_address'],
            is_indoor         = data.get('is_indoor', False),
            special_requests  = data.get('special_requests', ''),
            needs_light       = data.get('needs_light', False),
            needs_sound       = data.get('needs_sound', False),
            artists           = artist_objs,
            distance_km       = data.get('distance_km', 0.0),
            newsletter_opt_in = data.get('newsletter_opt_in', False)
        )

        # Preisspanne berechnen basierend auf ausgewählten Artists und Parametern
        duo_min = duo_max = None
        if not req.artists:
            req.price_min = None
            req.price_max = None
            pmin = None
            pmax = None
        else:
            fee_pct = _config_fee_pct()
            event_city = data.get('event_address', '').split(',')[-1].strip().lower()
            external_artists = [
                a for a in artist_objs
                if a.address and event_city not in a.address.lower()
            ]
            travel_distance = req.distance_km if external_artists else 0.0

            # Basis definieren je Teamgröße
            if team_size == 1:
                # Solo: min/max aus den verfügbaren Artists (bisheriges Verhalten)
                base_min = min(a.price_min for a in artist_objs)
                base_max = max(a.price_max for a in artist_objs)
            elif team_size == 2:
                # Duo: nur wenn mindestens 2 Artists verfügbar sind
                if len(artist_objs) >= 2:
                    pair = artist_objs[:2]  # exakt die ersten zwei aus der gematchten Liste
                    duo_min = sum(getattr(a, 'price_min', 0) for a in pair)
                    duo_max = sum(getattr(a, 'price_max', 0) for a in pair)
                    base_min = duo_min
                    base_max = duo_max
                else:
                    base_min = base_max = None
            else:
                # Gruppe (3+): keine Preisspanne
                base_min = base_max = None

            # Wenn wir für Duo bereits die Summe der beiden Artists gebildet haben,
            # soll die Preisfunktion NICHT erneut pro Person mitteln/skalieren.
            team_size_for_calc = 1 if (team_size == 2 and base_min is not None and duo_min is not None) else team_size

            try:
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
                        'team_size': team_size_for_calc,
                        'team_count': (2 if team_size == 2 else (team_size if team_size and int(team_size) >= 1 else 1)),
                        'duration': req.duration_minutes,
                        'event_address': req.event_address
                    }
                    pmin, pmax = calculate_price(**args)
                else:
                    pmin = pmax = None
            except Exception as e:
                current_app.logger.exception("calculate_price failed: %s", e)
                pmin = pmax = None

            # In die DB schreiben
            req.price_min = pmin
            req.price_max = pmax
        db.session.commit()

        # --- Notify matched artists via email (first simple version) ---
        try:
            date_str = req.event_date.strftime('%d.%m.%Y') if isinstance(req.event_date, datetime) else str(req.event_date)
            city = (req.event_address.split(',')[-1].strip() if req.event_address else '')
            subject = f"Neue Booking-Anfrage – {date_str}{', ' + city if city else ''}"

            for artist in artist_objs:
                # Skip if no email available
                if not getattr(artist, 'email', None):
                    current_app.logger.warning(f"Skipping email for artist {getattr(artist, 'id', '?')} – no email on record")
                    continue

                html = build_artist_new_request_email(artist, req)
                send_email(artist.email, subject, html)
        except Exception as e:
            # Do not fail the API if email sending has issues; just log it.
            current_app.logger.exception(f"Error while sending artist notification emails: {e}")

        resp = {
            'request_id': req.id,
            'price_min': pmin,
            'price_max': pmax,
            'num_available_artists': len(artist_objs),
            'matched_artists': matched_payload,
        }
        # Duo-Zusatzpreise nur dann mitsenden, wenn tatsächlich >= 2 Artists vorhanden
        if team_size == 2 and len(artist_objs) >= 2 and duo_min is not None and duo_max is not None:
            resp['duo_price_min'] = duo_min
            resp['duo_price_max'] = duo_max
        # Gruppe: Flag setzen, keine Preise
        if team_size and int(team_size) >= 3:
            resp['group_pricing_pending'] = True

        location_value = f"/api/requests/requests/{req.id}"
        resp["_location"] = location_value  # internal for idempotent replays

        # Cache the response if an Idempotency-Key was provided
        if idem_key:
            _idempotency_store(idem_key, resp)

        response = jsonify(resp)
        response.status_code = 201
        response.headers["Location"] = location_value
        if idem_key:
            response.headers["Idempotent-Replay"] = "false"
        return response

    except KeyError as ke:
        current_app.logger.warning("Missing field in create_request: %s", ke)
        return error_response("missing_field", f"Missing field: {str(ke)}", 400)
    except Exception as e:
        current_app.logger.exception("Error in create_request")
        return error_response("internal_error", f"create_request failed: {str(e)}", 500)


@booking_bp.route('/requests/<int:req_id>/offer', methods=['PUT'])
@jwt_required()
@swag_from('../resources/swagger/requests_offer_put.yml')
def set_offer(req_id):
    """Allow a logged-in artist to submit an offer for a request."""
    # Ermittle internen Artist anhand der Supabase JWT Identity
    supabase_id = get_jwt_identity()
    current_app.logger.debug(">>> Supabase ID aus Token: %s", supabase_id)
    user = Artist.query.filter_by(supabase_user_id=supabase_id).first()
    if not user:
        return error_response("forbidden", "Artist not found or not allowed", 403)
    user_id = user.id

    req = request_mgr.get_request(req_id)
    # Zugriff prüfen: Nur beteiligte Artists oder Admins dürfen bieten
    if not req or (user_id not in [a.id for a in req.artists] and not user.is_admin):
        return error_response("forbidden", "Not allowed to offer on this request", 403)

    data = request.json
    artist_gage = data.get('artist_gage')
    if artist_gage is None:
        return error_response("validation_error", "artist_gage is required", 400)

    # Neue Basis berechnen: Preis des aktuellen Artists ersetzen
    base_min = sum(
        artist_gage if a.id == user_id else getattr(a, 'price_min', 0)
        for a in req.artists
    )
    base_max = sum(
        artist_gage if a.id == user_id else getattr(a, 'price_max', 0)
        for a in req.artists
    )

    fee_pct = _config_fee_pct()
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
        event_address  = req.event_address
    )

    # Speichere das neue Angebot direkt am BookingRequest
    booking = BookingRequest.query.get(req_id)
    booking.artist_gage = artist_gage
    booking.artist_offer_date = datetime.utcnow()
    booking.status = 'angeboten'
    db.session.commit()
    req = booking

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

@booking_bp.route('/requests/<int:req_id>/accept', methods=['PUT'])
@jwt_required()
def accept_request(req_id: int):
    """Set a booking request status to 'accepted'."""
    try:
        updated = request_mgr.change_status(req_id, 'akzeptiert')
        if not updated:
            return error_response("not_found", "Request not found or invalid status", 404)
        return jsonify({"ok": True, "id": updated.id, "status": updated.status})
    except Exception as e:
        current_app.logger.exception(f"accept_request failed for id={req_id}: {e}")
        return error_response("internal_error", f"accept_request failed: {str(e)}", 500)

@booking_bp.route('/requests/<int:req_id>', methods=['DELETE'])
@jwt_required()
def delete_request(req_id: int):
    """Delete a booking request by ID."""
    try:
        ok = request_mgr.delete(req_id)
        if not ok:
            return error_response("not_found", "Request not found", 404)
        return jsonify({"ok": True, "deleted_id": req_id})
    except Exception as e:
        current_app.logger.exception(f"delete_request failed for id={req_id}: {e}")
        return error_response("internal_error", f"delete_request failed: {str(e)}", 500)

def send_push(artist, message):
    """Log a push notification for an artist (placeholder)."""
    current_app.logger.info(f"PUSH to {artist.id}: {message}")


def build_artist_new_request_email(artist, req):
    """Build a minimal HTML email for a new booking request."""
    app_url = current_app.config.get('APP_URL', 'https://app.example.com')
    date_str = req.event_date.strftime('%d.%m.%Y') if isinstance(req.event_date, datetime) else str(req.event_date)
    city = (req.event_address.split(',')[-1].strip() if req.event_address else '')
    price_range = None
    try:
        if req.price_min is not None and req.price_max is not None:
            price_range = f"{int(req.price_min)}–{int(req.price_max)} €"
    except Exception:
        price_range = None

    artist_name = getattr(artist, 'name', 'Künstler:in')

    return f"""
    <html>
      <body style="font-family: Arial, Helvetica, sans-serif; line-height:1.5;">
        <h2>Neue Anfrage für dich, {artist_name}!</h2>
        <p>
          <strong>Datum:</strong> {date_str}<br/>
          <strong>Ort:</strong> {city or '—'}<br/>
          <strong>Event:</strong> {req.event_type or '—'}<br/>
          <strong>Disziplin(en):</strong> {', '.join(req.show_discipline) if getattr(req, 'show_discipline', None) else '—'}<br/>
          <strong>Teamgröße:</strong> {req.team_size or '—'}<br/>
          <strong>Dauer:</strong> {req.duration_minutes or '—'} Minuten<br/>
          <strong>Preisrahmen:</strong> {price_range or 'wird noch abgestimmt'}
        </p>
        <p>
          <a href="{app_url}/meine-anfragen" style="background:#111;color:#fff;padding:10px 16px;text-decoration:none;border-radius:6px;">Zu meinen Anfragen</a>
        </p>
        <hr style="border:none;border-top:1px solid #e5e5e5;"/>
        <small>Diese E-Mail wurde automatisch gesendet. Bitte nicht direkt antworten.</small>
      </body>
    </html>
    """


def send_email(to_email: str, subject: str, html: str) -> bool:
    """Send an HTML email using SMTP settings from Flask config.
    
    Required config keys:
      - SMTP_HOST
      - SMTP_PORT (default 587)
      - SMTP_USER
      - SMTP_PASSWORD
      - SMTP_FROM (defaults to SMTP_USER)
    """
    host = current_app.config.get('SMTP_HOST')
    port = int(current_app.config.get('SMTP_PORT', 587))
    user = current_app.config.get('SMTP_USER')
    password = current_app.config.get('SMTP_PASSWORD')
    from_addr = current_app.config.get('SMTP_FROM', user)

    if not (host and user and password and to_email):
        current_app.logger.warning("Email not sent — missing SMTP config or recipient")
        return False

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = to_email
    msg.set_content("Neue Anfrage – bitte im Browser öffnen.")
    msg.add_alternative(html, subtype='html')

    try:
        with smtplib.SMTP(host, port) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(user, password)
            server.send_message(msg)
        current_app.logger.info(f"Email sent to {to_email} (subject: {subject})")
        return True
    except Exception as e:
        current_app.logger.exception(f"Failed to send email to {to_email}: {e}")
        return False