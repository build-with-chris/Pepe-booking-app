import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    
    SECRET_KEY = os.getenv("SUPABASE_JWT_SECRET")
    # JWT secret key for flask_jwt_extended, using the Supabase JWT secret
    JWT_SECRET_KEY = os.getenv("SUPABASE_JWT_SECRET")
    # Use DATABASE_URL if set, otherwise default to local SQLite file
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL") or "sqlite:///pepe.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    AGENCY_FEE_PERCENT = int(os.getenv("AGENCY_FEE_PERCENT", "20"))    
    RATE_PER_KM         = 0.5

class TestConfig(Config):
    """Konfiguration für Tests mit In-Memory-Datenbank."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")