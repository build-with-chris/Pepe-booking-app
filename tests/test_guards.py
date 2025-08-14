def test_unapproved_artist_cannot_view_requests(client, app, artist_pending):
    # baue JWT für den Owner des pending-Artists
    from flask_jwt_extended import create_access_token
    with app.app_context():
        token = create_access_token(identity=artist_pending.supabase_user_id)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/api/requests/requests", headers=headers)
    assert resp.status_code in (401, 403)