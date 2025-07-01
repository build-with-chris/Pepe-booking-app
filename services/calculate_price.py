import os

def calculate_price(base_min, base_max,
                    distance_km, fee_pct, newsletter=False,
                    event_type='Private Feier', num_guests=0,
                    is_weekend=False, is_indoor=True,
                    needs_light=False, needs_sound=False,
                    show_discipline='stage_show', team_size='solo',
                    duration=0, city=None):
    """
    Berechnet eine Preisspanne (Min, Max) durch Anwendung folgender Schritte in dieser Reihenfolge:

    1. Event-Typ-Multiplikator (z. B. Firmenfeier ×1.3, Privat ×0.7, …)
    2. Gästezahl-Multiplikator (bis 50 ×0.8, 51–200 ×1.0, >200 ×1.2)
    3. Wochenend- oder Wochentag-Modifikator
    4. Newsletter-Rabatt
    5. Indoor- vs. Outdoor-Faktor
    6. Technikpauschalen (Licht, Sound)
    7. Basis-Agenturgebühr (fee_pct)
    8. Distanzzuschläge (ab 300 km +200 €, ab 600 km +300 €, München –100 €)
    9. Fahrkosten
    """
    # 1. Event type
    event_weights = {
        'Private Feier': 0.7,
        'Firmenfeier':   1.3,
        'Incentive':     1.05,
        'Streetshow':    0.9
    }
    # Verhindere Untergewichtung bei Private Feier, wenn Gage manuell kommt
    if base_min == base_max:
        # Fixweight: Private Feier darf nicht abschwächen
        w_event = max(event_weights.get(event_type, 1.0), 1.0)
    else:
        w_event = event_weights.get(event_type, 1.0)

    min_p = base_min * w_event
    max_p = base_max * w_event

    # 2. Guests
    if num_guests <= 50:
        g_mult = 0.8
    elif num_guests <= 200:
        g_mult = 1.0
    else:
        g_mult = 1.2
    min_p *= g_mult
    max_p *= g_mult

    # 3. Weekend
    if is_weekend:
        min_p *= 1.15
        max_p *= 1.15

    # 4. Newsletter discount (5%)
    if newsletter:
        min_p *= 0.95
        max_p *= 0.95

    # 5. Indoor/Outdoor
    if not is_indoor:
        min_p *= 1.2
        max_p *= 1.2

    # 6. Tech fees
    tech_fee = 0
    if needs_light: tech_fee += 50
    if needs_sound: tech_fee += 75

    # 7. Agency fee
    min_p *= (1 + fee_pct/100)
    max_p *= (1 + fee_pct/100)

    # 8. Distance surcharges
    surcharge = 0
    if distance_km >= 600:
        surcharge += 300
    elif distance_km >= 300:
        surcharge += 200
    # München-Rabatt
    if city and city.lower() in ['münchen', 'muenchen', 'munich']:
        surcharge -= 100

    # 9. Travel fee
    rate_per_km = float(os.getenv("RATE_PER_KM", 0.5))
    travel_fee  = distance_km * rate_per_km

    # Final totals
    min_total = min_p + travel_fee + tech_fee + surcharge
    max_total = max_p + travel_fee + tech_fee + surcharge

    return int(min_total), int(max_total)