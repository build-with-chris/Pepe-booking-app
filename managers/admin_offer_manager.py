from models import db, AdminOffer, Artist
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

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
        """Setzt den Artist auf 'approved' und speichert Admin/Datum (ohne Model-Methoden)."""
        artist = db.session.get(Artist, artist_id)  # SQLAlchemy 2.0 Weg
        if not artist:
            logger.warning("approve_artist: artist not found (id=%r)", artist_id)
            return None

        # idempotent
        if getattr(artist, "approval_status", None) == "approved":
            logger.info("approve_artist: already approved (id=%s)", artist_id)
            return artist

        try:
            artist.approval_status = "approved"
            if hasattr(artist, "rejection_reason"):
                artist.rejection_reason = None

            # approved_by NUR setzen, wenn wir eine int-ID haben
            if hasattr(artist, "approved_by"):
                if isinstance(admin_id, int):
                    artist.approved_by = admin_id
                else:
                    # wenn Spalte nullable ist: None; sonst gar nicht setzen
                    artist.approved_by = None

            if hasattr(artist, "approved_at"):
                artist.approved_at = datetime.now(timezone.utc)

            db.session.commit()
            logger.info("Artist approved: id=%s by admin_id=%s", artist_id, admin_id)
            return artist
        except Exception as e:
            logger.exception("approve_artist failed (id=%s): %s", artist_id, e)
            db.session.rollback()
            return None

       

    def reject_artist(self, artist_id: int, admin_id: int | None = None, reason: str | None = None):
        """Setzt den Artist auf 'rejected' mit optionaler Begründung (ohne Model-Methoden)."""
        artist = db.session.get(Artist, artist_id)
        if not artist:
            logger.warning("reject_artist: artist not found (id=%r)", artist_id)
            return None

        same_reason = (getattr(artist, "rejection_reason", None) or "") == (reason or "")
        if getattr(artist, "approval_status", None) == "rejected" and same_reason:
            logger.info("reject_artist: already rejected (id=%s)", artist_id)
            return artist

        try:
            artist.approval_status = "rejected"
            if hasattr(artist, "rejection_reason"):
                artist.rejection_reason = reason

            # Felder leeren, falls vorhanden
            if hasattr(artist, "approved_by"):
                artist.approved_by = None
            if hasattr(artist, "approved_at"):
                artist.approved_at = None

            db.session.commit()
            logger.info("Artist rejected: id=%s by admin_id=%s reason=%r", artist_id, admin_id, reason)
            return artist
        except Exception as e:
            logger.exception("reject_artist failed (id=%s): %s", artist_id, e)
            db.session.rollback()
            return None

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