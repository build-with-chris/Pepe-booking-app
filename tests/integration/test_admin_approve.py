# tests/integration/test_admin_approve.py
from models import Artist

def test_approve_artist_success(client, admin_headers, artist_pending, get_artist):
    # artist_pending ist jetzt eine ID
    artist_id = artist_pending

    resp = client.post(f"/admin/artists/{artist_id}/approve", headers=admin_headers)
    assert resp.status_code == 200, resp.get_data(as_text=True)

    data = resp.get_json()
    assert data["id"] == artist_id
    assert data["status"] == "approved"
    if data.get("approved_at"):
        assert isinstance(data["approved_at"], str)

    # DB-Check (frisch laden)
    updated = get_artist(artist_id)
    assert updated is not None
    assert updated.approval_status == "approved"


def test_approve_artist_forbidden_for_non_admin(client, user_headers, artist_pending):
    artist_id = artist_pending
    resp = client.post(f"/admin/artists/{artist_id}/approve", headers=user_headers)
    assert resp.status_code in (401, 403), resp.get_data(as_text=True)


def test_approve_artist_not_found(client, admin_headers):
    resp = client.post("/admin/artists/999999/approve", headers=admin_headers)
    assert resp.status_code == 404, resp.get_data(as_text=True)