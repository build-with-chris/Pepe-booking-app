from flask import jsonify, request
import uuid
from typing import Optional, Dict, Any


def error_response(error: str, message: str, status: int, details: Optional[Dict[str, Any]] = None):
    """
    Return a consistent JSON error payload for the frontend with extra context.

    Existing calls do not need to change. You can optionally pass `details` for
    field-level validation errors etc.

    Example payload:
    {
        "error": "validation_failed",
        "message": "Bitte korrigiere die markierten Felder.",
        "code": 422,
        "request_id": "a1b2c3d4",
        "details": {"postal_code": "Ungültiges Format"}
    }
    """
    req_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:8]
    payload = {
        "error": error,
        "message": message,
        "code": status,
        "request_id": req_id,
    }
    if details:
        payload["details"] = details
    return jsonify(payload), status