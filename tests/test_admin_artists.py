# tests/test_admin_artists.py
import json
from models import Artist, db

def test_admin_list_requires_admin(client, user_headers):
    resp = client.get("/admin/artists?status=pending", headers=user_headers)
    assert resp.status_code in (401, 403)

def test_admin_list_pending_ok(client, admin_headers, artist_pending, artist_approved):
    resp = client.get("/admin/artists?status=pending", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    names = [a.get("name") for a in data]
    assert "Pending Paula" in names
    # sicherheitshalber: approved darf hier nicht auftauchen
    assert all(a.get("approval_status") == "pending" for a in data)

def test_admin_invalid_status_param(client, admin_headers):
    resp = client.get("/admin/artists?status=blabla", headers=admin_headers)
    assert resp.status_code == 400
    js = resp.get_json()
    assert "error" in js

def test_admin_approve_artist_flow(client, admin_headers, artist_pending):
    # Approve
    resp = client.post(f"/admin/artists/{artist_pending}/approve", headers=admin_headers)
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["status"] == "approved"

    # DB check
    updated = Artist.query.get(artist_pending)
    assert updated.approval_status == "approved"

    # Idempotenz: nochmal approve -> weiterhin approved
    resp2 = client.post(f"/admin/artists/{artist_pending}/approve", headers=admin_headers)
    assert resp2.status_code == 200
    assert resp2.get_json()["status"] == "approved"

def test_admin_reject_artist_flow(client, admin_headers, artist_pending):
    reason = {"reason": "Profil unvollständig"}
    resp = client.post(
        f"/admin/artists/{artist_pending}/reject",
        headers=admin_headers,
        data=json.dumps(reason),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "rejected"
    assert data["rejection_reason"] == "Profil unvollständig"

    # DB check
    updated = Artist.query.get(artist_pending)
    assert updated.approval_status == "rejected"
    assert updated.rejection_reason == "Profil unvollständig"

def test_admin_approve_not_found(client, admin_headers):
    resp = client.post("/admin/artists/999999/approve", headers=admin_headers)
    assert resp.status_code == 404

def test_admin_reject_not_found(client, admin_headers):
    resp = client.post("/admin/artists/999999/reject", headers=admin_headers, json={"reason": "nope"})
    assert resp.status_code == 404