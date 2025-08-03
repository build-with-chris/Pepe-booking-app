import os
import time
import json
import jwt  # pip install PyJWT
from pathlib import Path
from dotenv import load_dotenv

# Projektverzeichnis und .env laden
project_root = Path(__file__).resolve().parent
dotenv_path = project_root / ".env"
load_dotenv(dotenv_path)

# Konfiguration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://fqewemtskcpelsgxcsqh.supabase.co").rstrip("/")
JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
USER_ID = os.getenv("SUPABASE_USER_ID")
EMAIL = os.getenv("SUPABASE_EMAIL", "chris.hermann9397@gmail.com")

# Diagnose fehlender Werte
missing = []
if not JWT_SECRET:
    missing.append("SUPABASE_JWT_SECRET")
if not USER_ID:
    missing.append("SUPABASE_USER_ID")
if missing:
    print(f"Fehlt {', '.join(missing)} in der Umgebung.")
    print(f"Aktuell geladen: SUPABASE_JWT_SECRET={'set' if JWT_SECRET else 'MISSING'}, SUPABASE_USER_ID={'set' if USER_ID else 'MISSING'}")
    print(f".env-Pfad: {dotenv_path}")
    exit(1)

now = int(time.time())
payload = {
    "aud": "authenticated",
    "sub": USER_ID,
    "role": "authenticated",
    "email": EMAIL,
    "exp": now + 3600,
    "iat": now,
    "iss": f"{SUPABASE_URL}"
}

try:
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    # PyJWT returns str in newer versions, but bytes in older; normalize
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    print(token)
except Exception as e:
    print("Fehler beim Erzeugen des Tokens:", e)
    exit(1)