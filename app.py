from flask import Flask, jsonify, request
from config import Config
from models import db
from flask_jwt_extended import JWTManager
from routes.api_routes       import api_bp
from routes.auth_routes  import auth_bp
from routes.admin_routes import admin_bp
from flasgger import Swagger
from flask_cors import CORS
from routes.request_routes import booking_bp
from flask_migrate import Migrate

from sqlalchemy import text

import logging
import os



# --- Flask app & config ---
app = Flask(__name__)
app.config.from_object(Config)
# Ensure robust DB connections (survive restarts/plan changes)
app.config.setdefault('SQLALCHEMY_ENGINE_OPTIONS', {
    'pool_pre_ping': True,     # validates connections before using them
    'pool_recycle': 1800,      # recycle connections every 30 minutes
    'pool_size': 5,
    'max_overflow': 5,
    # If your provider requires SSL (e.g. Supabase/managed PG), uncomment:
    # 'connect_args': {'sslmode': 'require'},
})
# Hilfsfunktion: Passwort in der DB-URL maskieren für Logs
def mask_db_uri(uri: str) -> str:
    import re
    return re.sub(r'(://[^:]+:)([^@]+)(@)', r"\1****\3", uri)


app.logger.info("DB URI: %s | TESTING=%s | ENV=%s",
                app.config.get("SQLALCHEMY_DATABASE_URI"),
                app.config.get("TESTING"),
                os.getenv("FLASK_CONFIG") or os.getenv("FLASK_ENV") or "unset")

logging.getLogger().info(f"Using DB URI: {mask_db_uri(app.config.get('SQLALCHEMY_DATABASE_URI',''))}")
db.init_app(app)
migrate = Migrate(app, db)

@app.before_request
def _skip_jwt_for_options():
    """Ermöglicht CORS-Preflight (OPTIONS) ohne JWT-Header."""
    if request.method == 'OPTIONS':
        return jsonify(), 200

app.register_blueprint(auth_bp,  url_prefix='/auth')
app.register_blueprint(api_bp,   url_prefix='/api')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(booking_bp)

jwt = JWTManager(app)

template = {
"swagger": "2.0",
"info": {
    "title": "Pepe Backend API",
    "description": "This Api provides Endpoint for Artists to edit their availability, "
    "provides auth login and enables requests for the client",
        "version": "1.0"
    },
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "JWT Authorization header using the Bearer scheme. Example: 'Authorization: Bearer <token>'"
        }
    },
    "security": [
        {
            "Bearer": []
        }
    ]
}
app.config['SWAGGER'] = {
    'title': "Pepe Backend API",
    'uiversion': 2
}

Swagger(app, template=template)
CORS(app)


# Debug route for DB config
@app.get("/__debug/db")
def debug_db():
    return {
        "uri": app.config.get("SQLALCHEMY_DATABASE_URI"),
        "testing": app.config.get("TESTING", False)
    }

# Health check endpoint that verifies DB connectivity
@app.get("/healthz")
def healthz():
    """Simple health check that verifies DB connectivity."""
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        app.logger.exception("Health check failed: %s", e)
        return jsonify({"status": "db_unavailable", "error": str(e)}), 503


if __name__=="__main__":
    app.run(debug=True)