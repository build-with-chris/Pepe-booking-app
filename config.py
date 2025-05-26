import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY          = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///pepe.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    AGENCY_FEE_PERCENT = int(os.getenv("AGENCY_FEE_PERCENT", "20"))    
    RATE_PER_KM         = 0.5