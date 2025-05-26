import os

def calculate_price(base_min, base_max, distance_km,
                    fee_pct, newsletter=False):
    """
    Calculate a price range (min, max) by applying:
     - + fee_pct % on base price
     - + distance_km * RATE_PER_KM
     - –5% if newsletter opted in
    """
    rate_per_km = float(os.getenv("RATE_PER_KM", 0.5))
    # Apply agency fee
    min_with_fee = base_min * (1 + fee_pct/100)
    max_with_fee = base_max * (1 + fee_pct/100)

    # Add travel fee
    travel_fee = distance_km * rate_per_km
    min_total = min_with_fee + travel_fee
    max_total = max_with_fee + travel_fee

    # Newsletter discount
    if newsletter:
        min_total *= 0.95
        max_total *= 0.95

    return int(min_total), int(max_total)

def send_push(artist, message):
    """
    Stub for push notifications.
    Later integrate FCM or Web Push here, using artist.push_token.
    """
    # Example: print to console for now
    print(f"Push to {artist.id}: {message}")