# tests/test_admin_artists.py
import json
from models import db, Artist

def test_admin_list_requires_admin(client, user_headers):
    # Ohne Adminrolle -> 403
    resp = client.get("/admin/artists?status=pending", headers=user_headers)
    assert resp.status_code in (401, 403)

def test_admin_list_pending_ok(client, admin_headers, artist_pending, artist_approved):
    resp = client.get("/admin/artists?status=pending", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    # Nur pending erwartet
    assert any(a["name"] == "Pending Paula" for a in data)
    assert all(a["approval_status"] == "pending" for a in data)

def test_admin_approve_artist_flow(client, admin_headers, artist_pending):
    # Approve
    resp = client.post(f"/admin/artists/{artist_pending.id}/approve", headers=admin_headers)
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["status"] == "approved"

    # DB-Check
    updated = Artist.query.get(artist_pending.id)
    assert updated.approval_status == "approved"

    # Idempotenz: Nochmal approven -> weiterhin 200/approved
    resp2 = client.post(f"/admin/artists/{artist_pending.id}/approve", headers=admin_headers)
    assert resp2.status_code == 200
    assert resp2.get_json()["status"] == "approved"

def test_admin_reject_artist_flow(client, admin_headers, artist_pending):
    reason = {"reason": "Profil unvollständig"}
    resp = client.post(
        f"/admin/artists/{artist_pending.id}/reject",
        headers=admin_headers,
        data=json.dumps(reason),
        content_type="application/json"
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "rejected"
    assert data["rejection_reason"] == "Profil unvollständig"

    # DB-Check
    updated = Artist.query.get(artist_pending.id)
    assert updated.approval_status == "rejected"
    assert updated.rejection_reason == "Profil unvollständig"