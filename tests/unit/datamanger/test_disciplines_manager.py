import pytest
from datamanager import DataManager
from models import Discipline

def test_get_or_create_known_discipline_idempotent(dm):
    """Bekannte Disziplinen werden normalisiert und sind idempotent."""
    disc1 = dm.get_or_create_discipline('Zauberer')
    assert isinstance(disc1, Discipline)
    assert disc1.name == 'Zauberer'
    # Wiederholter Aufruf mit anderer Groß-/Kleinschreibung liefert dasselbe Objekt
    disc2 = dm.get_or_create_discipline('zauberer')
    assert disc1.id == disc2.id
    # Anzahl bleibt 1 in DB
    assert Discipline.query.count() == 1

def test_whitespace_and_case_normalization(dm):
    """Führende/folgende Leerzeichen und unterschiedliche Groß-/Kleinschreibung werden entfernt/normiert."""
    disc = dm.get_or_create_discipline('  ZaUbErEr  ')
    assert disc.name == 'Zauberer'
    assert Discipline.query.filter_by(name='Zauberer').count() == 1

def test_hyphen_normalization(dm):
    """Bindestrich-Schreibweise wird auf offizielle Disziplin umgeschrieben."""
    disc = dm.get_or_create_discipline('cyr-wheel')
    assert disc.name == 'Cyr-Wheel'
    assert Discipline.query.filter_by(name='Cyr-Wheel').count() == 1

def test_create_unknown_discipline_and_persistence(dm):
    """Neue, unbekannte Disziplinen werden angelegt und in der DB gespeichert."""
    initial_count = Discipline.query.count()
    new_disc = dm.get_or_create_discipline('NeueKunst')
    assert new_disc.name == 'NeueKunst'
    # DB-Eintrag angelegt
    assert Discipline.query.count() == initial_count + 1
    # Wiederholter Aufruf erzeugt nicht erneut
    again = dm.get_or_create_discipline('NeueKunst')
    assert new_disc.id == again.id
    assert Discipline.query.count() == initial_count + 1


def test_special_characters_and_empty_string_raise_error(dm):
    """Leere Strings und Sonderzeichen werden nicht als gültige Disziplin akzeptiert."""
    initial_count = Discipline.query.count()
    # Leerer String führt zu Fehler
    with pytest.raises(ValueError):
        dm.get_or_create_discipline('')
    # Sonderzeichen führen zu Fehler
    with pytest.raises(ValueError):
        dm.get_or_create_discipline('Fun@ct!0n')
    # Keine neuen Einträge in der DB
    assert Discipline.query.count() == initial_count