from models import Artist, db

def test_reject_artist_success(client, admin_headers, artist_pending, get_artist):
    artist_id = artist_pending
    resp = client.post(
        f"/admin/artists/{artist_id}/reject",
        headers=admin_headers,
        json={"reason": "Profil unvollständig"},
    )
    assert resp.status_code == 200, resp.get_data(as_text=True)
    data = resp.get_json()
    assert data["id"] == artist_id
    assert data["status"] == "rejected"
    assert data["rejection_reason"] == "Profil unvollständig"

    # DB-Check frisch laden
    updated = get_artist(artist_id)
    assert updated is not None
    assert updated.approval_status == "rejected"
    assert updated.rejection_reason == "Profil unvollständig"
    # Wenn approved_by/approved_at Felder existieren, sollten sie geleert sein
    if hasattr(updated, "approved_by"):
        assert updated.approved_by is None
    if hasattr(updated, "approved_at"):
        assert updated.approved_at is None


def test_reject_artist_forbidden_for_non_admin(client, user_headers, artist_pending):
    artist_id = artist_pending
    resp = client.post(
        f"/admin/artists/{artist_id}/reject",
        headers=user_headers,
        json={"reason": "nope"},
    )
    assert resp.status_code in (401, 403), resp.get_data(as_text=True)


def test_reject_artist_not_found(client, admin_headers):
    resp = client.post(
        "/admin/artists/999999/reject",
        headers=admin_headers,
        json={"reason": "not existing"},
    )
    assert resp.status_code == 404, resp.get_data(as_text=True)