import os
from dotenv import load_dotenv

load_dotenv()

def normalize_db_url(raw: str) -> str:
    if raw.startswith("postgres://"):
        return raw.replace("postgres://", "postgresql+psycopg://", 1)
    if raw.startswith("postgresql://") and not raw.startswith("postgresql+psycopg://"):
        return raw.replace("postgresql://", "postgresql+psycopg://", 1)
    return raw

class Config:
    SECRET_KEY = os.getenv("SUPABASE_JWT_SECRET")
    JWT_SECRET_KEY = os.getenv("SUPABASE_JWT_SECRET")
    raw_db = os.getenv("DATABASE_URL", "")
    if raw_db:
        SQLALCHEMY_DATABASE_URI = normalize_db_url(raw_db)
    else:
        SQLALCHEMY_DATABASE_URI = "sqlite:///pepe.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    AGENCY_FEE_PERCENT = int(os.getenv("AGENCY_FEE_PERCENT", "20"))
    RATE_PER_KM = 0.5

class TestConfig(Config):
    """Konfiguration für Tests mit In-Memory-Datenbank."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")