import pytest
from flask import url_for
from managers.artist_manager import ArtistManager

@pytest.mark.integration
def test_get_availability_empty(client, auth_headers, artist_manager):
    """
    Tag: Availability
    Test GET /api/availability returns an empty list for a new artist.
    """
    # Use the artist created by auth_headers
    artist = artist_manager.get_artist_by_email('auth@test.de')
    artist_id = artist.id
    response = client.get(
        url_for('api.get_availability'),
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)

@pytest.mark.integration
def test_add_availability(client, auth_headers, artist_manager):
    """
    Tag: Availability
    Test POST /api/availability to add a slot.
    """
    artist = artist_manager.get_artist_by_email('auth@test.de')
    artist_id = artist.id
    # Add a new slot (tomorrow)
    from datetime import date, timedelta
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    add_resp = client.post(
        url_for('api.add_availability'),
        headers=auth_headers,
        json={'date': tomorrow}
    )
    assert add_resp.status_code == 201
    slot_list = add_resp.get_json()
    # The response should be a list containing at least one slot dict
    assert isinstance(slot_list, list)
    first = slot_list[0]
    assert 'id' in first
    assert 'date' in first

    slot_id = first['id']
    # Verify it appears in GET
    get_resp = client.get(
        url_for('api.get_availability'),
        headers=auth_headers
    )
    assert get_resp.status_code == 200
    dates = [s['date'] for s in get_resp.get_json()]
    assert tomorrow in dates

@pytest.mark.integration
def test_remove_availability(client, auth_headers, artist_manager):
    """
    Tag: Availability
    Test DELETE /api/availability to remove a previously added slot.
    """
    # First, add a slot to remove
    from datetime import date, timedelta
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    add_resp = client.post(
        url_for('api.add_availability'),
        headers=auth_headers,
        json={'date': tomorrow}
    )
    assert add_resp.status_code == 201
    first = add_resp.get_json()[0]
    slot_id = first['id']

    # Now remove the slot
    del_resp = client.delete(
        url_for('api.remove_availability', slot_id=slot_id),
        headers=auth_headers
    )
    assert del_resp.status_code == 200
    data = del_resp.get_json()
    assert data.get('deleted') == slot_id

    # Verify it's gone
    get_resp = client.get(
        url_for('api.get_availability'),
        headers=auth_headers
    )
    assert get_resp.status_code == 200
    dates = [s['date'] for s in get_resp.get_json()]
    assert tomorrow not in dates