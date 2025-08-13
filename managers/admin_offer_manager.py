from models import db, AdminOffer, Artist

class AdminOfferManager:
    """
    Verwaltet alle Admin-Angebote für Buchungsanfragen.
    """

    def __init__(self):
        """Initialisiert den AdminOfferManager mit der Datenbanksitzung."""
        self.db = db

    def get_admin_offers(self, request_id):
        """Gibt alle Admin-Angebote für eine bestimmte Buchungsanfrage zurück."""
        return AdminOffer.query.filter_by(request_id=request_id).all()

    def get_admin_offer(self, offer_id):
        """Gibt ein bestimmtes Admin-Angebot anhand seiner ID zurück."""
        return AdminOffer.query.get(offer_id)

    def create_admin_offer(self, request_id, admin_id, override_price, notes=None):
        """Erstellt ein neues Admin-Angebot für eine Buchungsanfrage."""
        offer = AdminOffer(
            request_id=request_id,
            admin_id=admin_id,
            override_price=override_price,
            notes=notes
        )
        self.db.session.add(offer)
        self.db.session.commit()
        return offer

    def update_admin_offer(self, offer_id, override_price=None, notes=None):
        """Aktualisiert Preis oder Notizen eines bestehenden Admin-Angebots."""
        offer = self.get_admin_offer(offer_id)
        if not offer:
            return None
        if override_price is not None:
            offer.override_price = override_price
        if notes is not None:
            offer.notes = notes
        self.db.session.commit()
        return offer

    def delete_admin_offer(self, offer_id):
        """Löscht ein Admin-Angebot anhand seiner ID und gibt das gelöschte Objekt zurück."""
        offer = self.get_admin_offer(offer_id)
        if not offer:
            return None
        deleted_offer = offer
        self.db.session.delete(offer)
        self.db.session.commit()
        return deleted_offer

    def serialize(self, offer):
        """Serialisiert ein AdminOffer-Instanz in ein Dictionary."""
        return {
            'id': offer.id,
            'request_id': offer.request_id,
            'admin_id': offer.admin_id,
            'override_price': offer.override_price,
            'notes': offer.notes,
            'created_at': offer.created_at.isoformat() if offer.created_at else None
        }

    # --- Admin: Artist-Freigaben ---
    def approve_artist(self, artist_id: int, admin_id: int | None = None):
        """Setzt den Artist auf 'approved' und speichert Admin/Datum."""
        artist = Artist.query.get(artist_id)
        if not artist:
            return None
        # nutzt die Model-Methode aus Artist
        artist.approve(admin_id=admin_id)
        self.db.session.commit()
        return artist

    def reject_artist(self, artist_id: int, admin_id: int | None = None, reason: str | None = None):
        """Setzt den Artist auf 'rejected' mit optionaler Begründung und speichert Admin/Datum."""
        artist = Artist.query.get(artist_id)
        if not artist:
            return None
        artist.reject(admin_id=admin_id, reason=reason)
        self.db.session.commit()
        return artist

    def serialize_artist(self, artist):
        return {
            'id': artist.id,
            'name': artist.name,
            'email': getattr(artist, 'email', None),
            'approval_status': getattr(artist, 'approval_status', None),
            'rejection_reason': getattr(artist, 'rejection_reason', None),
            'approved_at': artist.approved_at.isoformat() if getattr(artist, 'approved_at', None) else None,
            'approved_by': getattr(artist, 'approved_by', None),
        }