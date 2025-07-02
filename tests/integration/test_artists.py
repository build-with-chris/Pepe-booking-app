import pytest
from flask import url_for


@pytest.mark.integration
def test_create_and_list_artist(client, auth_headers):
    """
    Tag: Artists
    Test POST /api/artists to create a new artist, then verify it appears in GET /api/artists.
    """
    payload = {
        "name": "IntegrationTest",
        "email": "integ@example.com",
        "password": "securepass",
        "disciplines": ["Zauberer"]
    }
    # Create artist
    create_resp = client.post(
        url_for('api.create_artist'),
        json=payload,
        headers=auth_headers
    )
    assert create_resp.status_code == 201
    created = create_resp.get_json()
    assert "id" in created
    created_id = created["id"]

    # List artists and verify new one is present
    list_resp = client.get(
        url_for('api.list_artists'),
        headers=auth_headers
    )
    assert list_resp.status_code == 200
    artists = list_resp.get_json()
    ids = [a["id"] for a in artists]
    assert created_id in ids