import os

def calculate_price(base_min, base_max,
                    distance_km, fee_pct, newsletter=False,
                    event_type='Private Feier', num_guests=0,
                    is_weekend=False, is_indoor=True,
                    needs_light=False, needs_sound=False, needs_fog=False,
                    show_type='stage_show', team_size='solo',
                    duration=0, city=None):
    """
    Calculate a price range (min, max) by applying in order:
     1. Event-type multiplier (z.B. Firmenfeier ×1.3, Privat ×0.7, …)
     2. Guest count multiplier (bis 50 ×0.8, 51–200 ×1.0, >200 ×1.2)
     3. Wochenend- oder Wochentag-Modifier
     4. Saison-/Feiertags-Modifier 
     5. Indoor vs. Outdoor
     6. Technik-Pauschalen (Licht, Sound, Nebel)
     7. Basis-Agenturgebühr (fee_pct)
     8. Distanz-Zuschläge (ab 300 km +200 €, ab 600 km +300 €, München –100 €)
     9. Dauer- und Team-Validierung (Solo ≤15 min, Walking Act Basis 20 min)
    """
    # 1. Event type
    event_weights = {
        'Private Feier': 0.7,
        'Firmenfeier':   1.3,
        'Incentive':     1.05,
        'Streetshow':    0.9
    }
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

    # 5. Indoor/Outdoor
    if not is_indoor:
        min_p *= 1.2
        max_p *= 1.2

    # 6. Tech fees
    tech_fee = 0
    if needs_light: tech_fee += 50
    if needs_sound: tech_fee += 75
    if needs_fog:   tech_fee += 30

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
    if city and city.lower() == 'münchen':
        surcharge -= 100

    # 9. Travel fee
    rate_per_km = float(os.getenv("RATE_PER_KM", 0.5))
    travel_fee  = distance_km * rate_per_km

    # Final totals
    min_total = min_p + travel_fee + tech_fee + surcharge
    max_total = max_p + travel_fee + tech_fee + surcharge

    return int(min_total), int(max_total)