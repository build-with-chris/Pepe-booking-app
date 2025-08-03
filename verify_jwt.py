
import jwt, json
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJhdXRoZW50aWNhdGVkIiwic3ViIjoiZjJjNDg2OTQtMzUzNC00ODc0LTk4NTItMmEyMDQ3MDU1ODYyIiwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJlbWFpbCI6ImNocmlzLmhlcm1hbm45Mzk3QGdtYWlsLmNvbSIsImV4cCI6MTc1NDIzNDk1MCwiaWF0IjoxNzU0MjMxMzUwLCJpc3MiOiJodHRwczovL2ZxZXdlbXRza2NwZWxzZ3hjc3FoLnN1cGFiYXNlLmNvLyJ9.GgPFjXpT6yz3PJ93z4NIrLkjt9QWyEkqtNDo-X8OH78"
secret = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZxZXdlbXRza2NwZWxzZ3hjc3FoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTMyNjA5ODAsImV4cCI6MjA2ODgzNjk4MH0.I4da47nYTuMMRmC8sck6UKL8H8ilwf8OTKkvh599U0s"
try:
    payload = jwt.decode(
        token,
        secret,
        algorithms=["HS256"],
        audience="authenticated",
        issuer="https://fqewemtskcpelsgxcsqh.supabase.co/"
    )
    print("✅ Token gültig:", json.dumps(payload, indent=2))
except Exception as e:
    print("❌ Verifikationsfehler:", e)
