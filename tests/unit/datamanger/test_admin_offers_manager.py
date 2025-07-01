import pytest
from datetime import date
from datamanager import DataManager
from models import Artist, BookingRequest, AdminOffer

def test_get_admin_offers_initially_empty(dm):
    """Gibt eine leere Liste zurück, wenn keine Admin-Angebote existieren."""
    # Noch keine Requests und keine AdminOffers in der DB
    offers = dm.get_admin_offers(1)
    assert isinstance(offers, list)
    assert offers == []

def test_create_and_get_admin_offer(dm):
    """Erstellt ein Admin-Angebot und prüft Abruf über get_admin_offers und get_admin_offer."""
    # Admin-User anlegen
    admin = dm.create_artist('Admin', 'admin@ex.de', 'pw', ['Zauberer'], is_admin=True)
    # Normalen Artist und eine Buchungsanfrage anlegen
    artist = dm.create_artist('A1', 'a1@ex.de', 'pw', ['Zauberer'])
    req = dm.create_request(
        client_name      = 'Client',
        client_email     = 'client@ex.de',
        event_date       = date.today().isoformat(),
        duration_minutes = 10,
        event_type       = 'Private Feier',
        show_discipline  = ['Zauberer'],
        team_size        = 1,
        number_of_guests = 5,
        event_address    = 'Ort',
        is_indoor        = True,
        special_requests = '',
        needs_light      = False,
        needs_sound      = False,
        artists          = [artist]
    )
    # Admin-Angebot anlegen
    admin_offer = dm.create_admin_offer(req.id, admin.id, override_price=1500, notes='Testnotiz')
    assert isinstance(admin_offer, AdminOffer)
    # Abruf über get_admin_offers
    offers = dm.get_admin_offers(req.id)
    assert any(o.id == admin_offer.id for o in offers)
    # Einzelabruf über get_admin_offer
    fetched = dm.get_admin_offer(admin_offer.id)
    assert fetched.override_price == 1500
    assert fetched.notes == 'Testnotiz'

def test_update_admin_offer(dm):
    """Aktualisiert ein bestehendes Admin-Angebot."""
    # Setup: Admin-User, Artist, Request und Angebot
    admin = dm.create_artist('Admin2', 'admin2@ex.de', 'pw', ['Zauberer'], is_admin=True)
    artist = dm.create_artist('B1', 'b1@ex.de', 'pw', ['Zauberer'])
    req = dm.create_request(
        client_name      = 'C2',
        client_email     = 'c2@ex.de',
        event_date       = date.today().isoformat(),
        duration_minutes = 15,
        event_type       = 'Private Feier',
        show_discipline  = ['Zauberer'],
        team_size        = 2,
        number_of_guests = 20,
        event_address    = 'Ort2',
        is_indoor        = False,
        special_requests = '',
        needs_light      = False,
        needs_sound      = False,
        artists          = [artist]
    )
    admin_offer = dm.create_admin_offer(req.id, admin.id, override_price=2000, notes='Initial')
    # Update: Override-Preis ändern
    updated = dm.update_admin_offer(admin_offer.id, override_price=2500)
    assert updated.override_price == 2500
    assert updated.notes == 'Initial'
    # Update: Notizen ändern
    updated2 = dm.update_admin_offer(admin_offer.id, notes='Geändert')
    assert updated2.override_price == 2500
    assert updated2.notes == 'Geändert'

def test_delete_admin_offer(dm):
    """Löscht ein Admin-Angebot und prüft Nichtvorhandensein."""
    # Setup: Admin, Artist, Request und Angebot
    admin = dm.create_artist('Admin3', 'admin3@ex.de', 'pw', ['Zauberer'], is_admin=True)
    artist = dm.create_artist('C1', 'c1@ex.de', 'pw', ['Zauberer'])
    req = dm.create_request(
        client_name      = 'D3',
        client_email     = 'd3@ex.de',
        event_date       = date.today().isoformat(),
        duration_minutes = 20,
        event_type       = 'Private Feier',
        show_discipline  = ['Zauberer'],
        team_size        = 1,
        number_of_guests = 30,
        event_address    = 'Ort3',
        is_indoor        = True,
        special_requests = '',
        needs_light      = False,
        needs_sound      = False,
        artists          = [artist]
    )
    admin_offer = dm.create_admin_offer(req.id, admin.id, override_price=1800, notes='ToDelete')
    # Delete
    deleted = dm.delete_admin_offer(admin_offer.id)
    assert deleted.id == admin_offer.id
    # Danach nicht mehr auffindbar
    assert dm.get_admin_offer(admin_offer.id) is None