import os

def calculate_price(base_min, base_max,
                    distance_km, fee_pct, newsletter=False,
                    event_type='Private Feier', num_guests=0,
                    is_weekend=False, is_indoor=True,
                    needs_light=False, needs_sound=False,
                    show_discipline='stage_show', team_size='solo',
                    duration=0, event_address=None):
    """
    Berechnet eine Preisspanne (Min, Max) durch Anwendung folgender Schritte in dieser Reihenfolge:

    1. Event-Typ-Multiplikator (z. B. Firmenfeier ×1.3, Privat ×0.7, …)
    2. Gästezahl-Multiplikator (≤200 ×1.0, 201–500 ×1.2, >500 ×1.35)
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
        'Private Feier': 0.6,
        'Firmenfeier':   1.5,
        'Teamevent':     1.05,
        'Streetshow':    0.7
    }
    # Verhindere Untergewichtung bei Private Feier, wenn Gage manuell kommt
    if base_min == base_max:
        # Fixweight: Private Feier darf nicht abschwächen
        w_event = max(event_weights.get(event_type, 1.0), 1.0)
    else:
        w_event = event_weights.get(event_type, 1.0)

    min_p = base_min * w_event
    max_p = base_max * w_event

    # 2. Guests (skip reduction if fixed artist fee provided)
    if base_min == base_max:
        # Artist hat festen Gagen-Wert vorgegeben, also nicht reduzieren
        g_mult = 1.0
    else:
        # Frontend liefert nun Buckets: Unter 200 (~199), 200–500 (~350), Über 500 (~501)
        # Wir mappen auf drei Stufen: ≤200, 201–500, >500
        if num_guests <= 200:
            g_mult = 1.0
        elif num_guests <= 500:
            g_mult = 1.2
        else:
            g_mult = 1.35

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
    if needs_light: tech_fee += 450
    if needs_sound: tech_fee += 450

    # 7. Agency fee
    min_p *= (1 + fee_pct/100)
    max_p *= (1 + fee_pct/100)

    # 8. Distance surcharges
    surcharge = 0
    city = None
    if event_address:
        # take substring after last comma, strip whitespace
        raw_city = event_address.split(',')[-1].strip()
        # assume format "PLZ Stadt"; split and use the last token as city name
        city = raw_city.split()[-1].lower()
    if distance_km >= 600:
        surcharge += 300
    elif distance_km >= 300:
        surcharge += 200
    # München-Rabatt
    if city in ['münchen', 'muenchen', 'munich']:
        surcharge -= 100

    # 9. Travel fee
    rate_per_km = float(os.getenv("RATE_PER_KM", 0.5))
    travel_fee  = distance_km * rate_per_km

    # Final totals
    min_total = min_p + travel_fee + tech_fee + surcharge
    max_total = max_p + travel_fee + tech_fee + surcharge

    return int(min_total), int(max_total)