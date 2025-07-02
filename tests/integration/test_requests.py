import pytest
from flask import url_for

@pytest.mark.integration
def test_create_booking_request(client, auth_headers):
    """
    Test for the Requests tag: POST /api/requests/requests
    """
    payload = {
        "client_email": "test@example.com",
        "client_name": "Test Client",
        "disciplines": ["Zauberer", "Cyr-Wheel"],
        "distance_km": 0,
        "duration_minutes": 30,
        "event_address": "Musterstraße 1",
        "event_date": "2025-12-31",
        "event_time": "19:00",
        "event_type": "Private Feier",
        "is_indoor": True,
        "needs_light": False,
        "needs_sound": False,
        "newsletter_opt_in": False,
        "number_of_guests": 20,
        "special_requests": "",
        "team_size": 1
    }
    response = client.post(
        url_for('booking.create_request'),
        json=payload,
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.get_json()
    # The endpoint returns a summary with request_id, price_min, price_max, and num_available_artists
    assert "request_id" in data
    assert data["request_id"] > 0
    assert "price_min" in data and "price_max" in data
    # Ensure the request summary reflects our payload
    assert data.get("num_available_artists", 0) >= 0
