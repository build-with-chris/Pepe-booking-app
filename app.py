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
import yaml

from helpers.http_responses import error_response
from urllib.parse import urlparse



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

app.register_blueprint(auth_bp,  url_prefix='/auth')
app.register_blueprint(api_bp,   url_prefix='/api')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(booking_bp)

jwt = JWTManager(app)

# --- CORS (dynamic via ENV CORS_ORIGINS with wildcard support) ---
origins_env = os.getenv("CORS_ORIGINS", "")
allowed_patterns = [o.strip() for o in origins_env.split(",") if o.strip()]

# Fallback, falls ENV leer ist
if not allowed_patterns:
    allowed_patterns = [
        "http://localhost:5173",
        "https://pepeshows.de",
    ]

def origin_allowed(origin: str) -> bool:
    if not origin:
        return False
    # Exaktes Match
    if origin in allowed_patterns:
        return True
    # Wildcard: z. B. "https://*.vercel.app" oder "http://*.foo.bar"
    try:
        parsed = urlparse(origin)
        host = parsed.hostname or ""
        scheme = parsed.scheme
    except Exception:
        return False
    for pattern in allowed_patterns:
        if pattern.startswith("https://*") and scheme == "https":
            suffix = pattern.replace("https://*", "", 1)
            if host.endswith(suffix):
                return True
        if pattern.startswith("http://*") and scheme == "http":
            suffix = pattern.replace("http://*", "", 1)
            if host.endswith(suffix):
                return True
    return False

CORS(
    app,
    origins=origin_allowed,  # zentrale, wildcard-fähige Prüfung
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["Content-Type", "Authorization", "X-Request-ID"],
    supports_credentials=False,
)

template = {
    "openapi": "3.0.3",
    "info": {
        "title": "Pepe Backend API",
        "description": (
            "This API provides endpoints for artists to manage availability, "
            "authentication, and client booking requests."
        ),
        "version": "1.0.0",
    },
    "components": {
        "securitySchemes": {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT Authorization header using the Bearer scheme. Example: 'Authorization: Bearer <token>'",
            }
        }
    },
    "security": [{"bearerAuth": []}],
}

# --- Merge shared OpenAPI component schemas -----------------------------------
try:
    BASE_DIR = os.path.dirname(__file__)
    SCHEMAS_PATH = os.path.join(BASE_DIR, 'resources', 'swagger', 'components', 'schemas.yml')
    if os.path.exists(SCHEMAS_PATH):
        with open(SCHEMAS_PATH, 'r', encoding='utf-8') as f:
            schemas_doc = yaml.safe_load(f) or {}
        # schemas_doc should look like { components: { schemas: { ... } } }
        shared_schemas = (
            schemas_doc.get('components', {}).get('schemas', {})
            if isinstance(schemas_doc, dict) else {}
        )
        if shared_schemas:
            template.setdefault('components', {})
            template['components'].setdefault('schemas', {})
            # extend without overwriting existing keys
            template['components']['schemas'].update(shared_schemas)
except Exception as e:
    app.logger.exception('Failed to load shared OpenAPI schemas: %s', e)
# -----------------------------------------------------------------------------

app.config['SWAGGER'] = {
    'title': "Pepe Backend API",
    'uiversion': 3,
    'openapi': '3.0.3',
    'specs': [
        {
            'endpoint': 'apispec_1',
            'route': '/apispec_1.json',
        }
    ],
    'specs_route': '/api-docs/',
    'ui_params': {
        'validatorUrl': None,
        'docExpansion': 'none',
        'persistAuthorization': True,
        'displayRequestDuration': True,
    }
}

# Serve Swagger UI at /api-docs (also generates /apispec_raw.json)
swagger = Swagger(app, template=template, parse=False)

# Debug route for DB config
@app.get("/__debug/db")
def debug_db():
    return {
        "uri": app.config.get("SQLALCHEMY_DATABASE_URI"),
        "testing": app.config.get("TESTING", False)
    }

# Debug route for CORS config
@app.get("/__debug/cors")
def debug_cors():
    test_origin = request.args.get("origin")
    is_allowed = None
    if test_origin:
        try:
            is_allowed = origin_allowed(test_origin)
        except Exception as e:
            is_allowed = f"error: {e}"
    return {
        "allowed_patterns": allowed_patterns,
        "test_origin": test_origin,
        "is_allowed": is_allowed,
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
        return error_response("internal_error", f"DB unavailable: {str(e)}", 503)


if __name__=="__main__":
    app.run(debug=True)