import os

def calculate_price(base_min, base_max,
                    distance_km, fee_pct, newsletter=False,
                    event_type='Private Feier', num_guests=0, show_discipline=False,
                    is_weekend=False, is_indoor=True,
                    needs_light=False, needs_sound=False,
                    team_size='solo',
                    duration=0, event_address=None, team_count=None):
    """
    Berechnet eine Preisspanne (Min, Max) durch Anwendung folgender Schritte in dieser Reihenfolge:

    1. Event-Typ-Multiplikator ('Private Feier': 0.6,'Firmenfeier': 1.35, 'Teamevent': 1.05, Streetshow': 0.7)
    2. Gästezahl-Multiplikator (≤200 ×1.0, 201–500 ×1.2, >500 ×1.35)
    3. Wochenend- oder Wochentag-Modifikator (1.05)
    5. Indoor- vs. Outdoor-Faktor (1.2) 
    6. Dauer-Multiplikator basierend auf der Performance-Dauer
    7. Technikpauschalen (Licht, Sound) jeweils 450€
    8. Basis-Agenturgebühr (20 fee_pct)
    9. Distanzzuschläge (ab 300 km +200 €, ab 600 km +300 €, München –100 €)
    10. Fahrkosten pro Artist (0,5€/ km * team_count)

    Travel costs are applied per artist via team_count (defaults to 1 if not provided, or derived from team_size).
    """
    # derive effective team count (number of artists) for per-person costs
    people = 1
    if team_count is not None:
        try:
            people = max(1, int(team_count))
        except Exception:
            people = 1
    else:
        # fallback: infer from team_size if provided (e.g., 'solo'|'duo'|int)
        try:
            if isinstance(team_size, (int, float)):
                people = max(1, int(team_size))
            else:
                ts = str(team_size).strip().lower()
                if ts in ('duo', '2'):
                    people = 2
                elif ts in ('trio', '3'):
                    people = 3
                elif ts in ('quartet', '4'):
                    people = 4
                else:
                    people = 1
        except Exception:
            people = 1

    # 1. Event type
    event_weights = {
        'Private Feier': 0.6,
        'Firmenfeier':   1.35,
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
            g_mult = 0.9
        elif num_guests <= 500:
            g_mult = 1.1
        else:
            g_mult = 1.25

    min_p *= g_mult
    max_p *= g_mult

    # 3. Weekend
    if is_weekend:
        min_p *= 1.05
        max_p *= 1.15

    # 4. Newsletter discount (5%)
    if newsletter:
        min_p *= 0.95
        max_p *= 0.95

    # 5. Indoor/Outdoor
    if not is_indoor:
        min_p *= 1.2
        max_p *= 1.2

    # 6. Duration multiplier based on performance duration
    # Round up duration to nearest 5 minutes
    rounded_duration = ((duration + 4) // 5) * 5  # duration in minutes rounded up to nearest 5
    if rounded_duration <= 5:
        duration_factor = 1.0
    else:
        # Base factors for 10 and 15 minutes
        if rounded_duration == 10:
            duration_factor = 1.2
        elif rounded_duration == 15:
            duration_factor = 1.3
        elif rounded_duration > 15:
            # For each additional 5 minutes above 15, add 0.1
            extra_intervals = (rounded_duration - 15) // 5
            duration_factor = 1.3 + (extra_intervals * 0.1)
        else:
            # For durations between 6 and 9 (rounded to 10), fallback to 1.4
            duration_factor = 1.2

    min_p *= duration_factor
    max_p *= duration_factor

    # 7. Tech fees
    tech_fee = 0
    if needs_light: tech_fee += 450
    if needs_sound: tech_fee += 450

    # 8. Agency fee
    min_p *= (1 + fee_pct/100)
    max_p *= (1 + fee_pct/100)

    # 9. Distance surcharges
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

    # 10. Travel fee
    rate_per_km = float(os.getenv("RATE_PER_KM", 0.5))
    travel_fee_single = distance_km * rate_per_km
    travel_fee = travel_fee_single * max(1, people)

    # Final totals
    min_total = min_p + travel_fee + tech_fee + surcharge
    max_total = max_p + travel_fee + tech_fee + surcharge

    return int(min_total), int(max_total)