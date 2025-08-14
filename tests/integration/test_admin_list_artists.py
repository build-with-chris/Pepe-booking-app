def test_list_pending_artists(client, admin_headers, artist_pending, artist_approved):
    resp = client.get("/admin/artists?status=pending", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    # nur pending
    assert all(a.get("approval_status") == "pending" for a in data)
    ids = [a["id"] for a in data]
    assert artist_pending in ids
    assert artist_approved not in ids


def test_list_approved_artists(client, admin_headers, artist_pending, artist_approved):
    resp = client.get("/admin/artists?status=approved", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert all(a.get("approval_status") == "approved" for a in data)
    ids = [a["id"] for a in data]
    assert artist_approved in ids
    assert artist_pending not in ids


def test_list_rejected_artists(client, admin_headers, artist_pending):
    # erst ablehnen
    client.post(
        f"/admin/artists/{artist_pending}/reject",
        headers=admin_headers,
        json={"reason": "check"},
    )
    resp = client.get("/admin/artists?status=rejected", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert all(a.get("approval_status") == "rejected" for a in data)
    ids = [a["id"] for a in data]
    assert artist_pending in ids


def test_list_unsubmitted_artists_empty_ok(client, admin_headers):
    # Falls du unsubmitted hast: kann leer sein, aber sollte 200 liefern
    resp = client.get("/admin/artists?status=unsubmitted", headers=admin_headers)
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


def test_list_artists_invalid_status(client, admin_headers):
    resp = client.get("/admin/artists?status=does-not-exist", headers=admin_headers)
    assert resp.status_code == 400
    js = resp.get_json()
    assert "error" in js