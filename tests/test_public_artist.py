
def test_public_artists_shows_only_approved(client, artist_pending, artist_approved):
    resp = client.get("/api/artists")
    assert resp.status_code == 200
    data = resp.get_json()

    artists = data if isinstance(data, list) else data.get("artists", [])
    names = [a["name"] for a in artists]
    assert "Approved Alex" in names
    assert "Pending Paula" not in names

 