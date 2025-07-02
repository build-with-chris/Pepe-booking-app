import re
from models import db, Discipline

# Liste der erlaubten Disziplinen, die ein Artist ausüben kann
ALLOWED_DISCIPLINES = [
    "Zauberer",
    "Cyr-Wheel",
    "Bodenakrobatik",
    "Luftakrobatik",
    "Partnerakrobatik",
    "Chinese Pole",
    "Hula Hoop",
    "Handstand",
    "Contemporary Dance",
    "Breakdance",
    "Teeterboard",
    "Jonglage",
    "Moderation",
    "Pantomime/Entertainment"
]


class DisciplineManager:
    """
    Verwaltet Disziplinen: Normalisierung, Validierung und Anlage.
    """
    def __init__(self):
        """Initialisiert den DisciplineManager mit der Datenbanksitzung."""
        self.db = db

    def get_or_create_discipline(self, name):
        """
        Gibt eine vorhandene Disziplin anhand des Namens zurück oder legt sie an, falls sie nicht existiert.
        """
        name = name.strip()
        # Offizielle Schreibweise prüfen und normalisieren
        for allowed in ALLOWED_DISCIPLINES:
            if allowed.lower() == name.lower():
                name = allowed
                break

        # Validierung für unbekannte Namen (leer oder mit unzulässigen Zeichen)
        if name not in ALLOWED_DISCIPLINES:
            if not name:
                raise ValueError("Disziplinname darf nicht leer sein")
            if not re.match(r'^[A-Za-z0-9 äöüÄÖÜß/\-]+$', name):
                raise ValueError(f"Ungültige Disziplin: {name}")

        # Existenz prüfen oder neu anlegen
        disc = Discipline.query.filter_by(name=name).first()
        if not disc:
            disc = Discipline(name=name)
            self.db.session.add(disc)
            self.db.session.commit()
        return disc