import pytest
from flask import url_for
from datetime import date, timedelta

@pytest.mark.integration
def test_list_admin_offers_empty(client, admin_auth_headers, artist_manager, booking_request_manager):
    """
    Tag: AdminOffers
    Test GET empty offers list for a new request.
    """
    # Use the admin user created by auth_headers fixture
    admin = artist_manager.get_artist_by_email('adminuser@test.de')
    artist = artist_manager.create_artist('A1', 'a1@ex.de', 'pw', ['Zauberer'])
    req = booking_request_manager.create_request(
        client_name='Client',
        client_email='client@ex.de',
        event_date=date.today().isoformat(),
        duration_minutes=10,
        event_type='Private Feier',
        show_discipline=['Zauberer'],
        team_size=1,
        number_of_guests=5,
        event_address='Ort',
        is_indoor=True,
        special_requests='',
        needs_light=False,
        needs_sound=False,
        artists=[artist]
    )
    # List offers for the request
    resp = client.get(
        url_for('admin.list_admin_offers', req_id=req.id),
        headers=admin_auth_headers
    )
    assert resp.status_code == 200
    assert resp.get_json() == []

@pytest.mark.integration
def test_create_update_delete_admin_offer(client, admin_auth_headers, artist_manager, booking_request_manager):
    """
    Tag: AdminOffers
    Test creating, updating, and deleting an admin offer.
    """
    # Use the admin user created by auth_headers fixture
    admin = artist_manager.get_artist_by_email('adminuser@test.de')
    artist = artist_manager.create_artist('B1', 'b1@ex.de', 'pw', ['Zauberer'])
    req = booking_request_manager.create_request(
        client_name='C2',
        client_email='c2@ex.de',
        event_date=date.today().isoformat(),
        duration_minutes=15,
        event_type='Private Feier',
        show_discipline=['Zauberer'],
        team_size=1,
        number_of_guests=10,
        event_address='Ort2',
        is_indoor=False,
        special_requests='',
        needs_light=False,
        needs_sound=False,
        artists=[artist]
    )
    # Create offer
    create_resp = client.post(
        url_for('admin.create_admin_offer', req_id=req.id),
        json={'user_id': admin.id, 'override_price': 1500, 'notes': 'Testnote'},
        headers=admin_auth_headers
    )
    assert create_resp.status_code == 201
    offer = create_resp.get_json()
    print("DEBUG – offer keys:", offer.keys())
    print("DEBUG – full offer:", offer)
    # The create endpoint returns only the new offer ID
    assert 'id' in offer

    # Update offer
    update_resp = client.put(
        url_for('admin.update_admin_offer', offer_id=offer['id']),
        json={'override_price': 1800},
        headers=admin_auth_headers
    )
    assert update_resp.status_code == 200
    # The update endpoint returns only the offer ID on success
    updated = update_resp.get_json()
    assert 'id' in updated

    # Delete offer
    delete_resp = client.delete(
        url_for('admin.delete_admin_offer', offer_id=offer['id']),
        headers=admin_auth_headers
    )
    assert delete_resp.status_code == 200
    data = delete_resp.get_json()
    assert data.get('deleted') == offer['id']


@pytest.mark.integration
    def test_