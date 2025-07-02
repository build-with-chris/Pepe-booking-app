import pytest
from flask import url_for

@pytest.mark.integration
def test_login_with_valid_credentials(client, db, artist_manager):
    """
    Tag: Auth
    Test POST /auth/login with valid credentials returns access token.
    """
    # Arrange: create a test user via ArtistManager
    artist = artist_manager.create_artist('TestUser', 'testuser@example.com', 'password', ['Zauberer'])
    
    # Act: attempt login
    response = client.post(
        url_for('auth.login'),
        json={'email': 'testuser@example.com', 'password': 'password'}
    )
    
    # Assert
    assert response.status_code == 200
    data = response.get_json()
    assert 'access_token' in data
    assert data['user']['email'] == 'testuser@example.com'

@pytest.mark.integration
def test_login_with_invalid_credentials(client):
    """
    Tag: Auth
    Test POST /auth/login with invalid credentials returns 401.
    """
    response = client.post(
        url_for('auth.login'),
        json={'email': 'nonexistent@example.com', 'password': 'wrong'}
    )
    assert response.status_code == 401
    data = response.get_json()
    assert data.get('msg') in ('Bad username or password', 'Unauthorized', 'Invalid credentials')
