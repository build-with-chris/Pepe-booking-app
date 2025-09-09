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
    """Allow CORS preflight (OPTIONS) without requiring a JWT."""
    if request.method == 'OPTIONS':
        return jsonify(), 200

app.register_blueprint(auth_bp,  url_prefix='/auth')
app.register_blueprint(api_bp,   url_prefix='/api')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(booking_bp)

jwt = JWTManager(app)

CORS(app)

template = {
    "openapi": "3.0.0",
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
    # Load ONLY the cleaned spec; do not expose/raw-bind any internal specs
    'urls': [
        { 'name': 'Pepe API', 'url': '/apispec_1.json' }
    ],
    'specs': [],
    'specs_route': '/api-docs',
    'ui_params': {
        'validatorUrl': None,
        'docExpansion': 'none',
        'persistAuthorization': True
    }
}

# Serve Swagger UI at /api-docs (also generates /apispec_raw.json)
swagger = Swagger(app, template=template, parse=False)

# Serve OpenAPI 3 spec at /apispec_1.json, stripping accidental Swagger 2 key if present
@app.get('/apispec_1.json')
def patched_apispec():
    """Return OpenAPI 3 spec; drop accidental Swagger 2 'swagger' field if present."""
    try:
        specs = swagger.loader()
        # If flasgger (or a fragment) injected a Swagger 2 key, remove it to keep UI happy.
        if isinstance(specs, dict) and 'openapi' in specs and 'swagger' in specs:
            specs.pop('swagger', None)
        return jsonify(specs)
    except Exception as e:
        app.logger.exception('Failed to build OpenAPI spec: %s', e)
        return error_response('openapi_error', str(e), 500)


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
        return error_response("internal_error", f"DB unavailable: {str(e)}", 503)


if __name__=="__main__":
    app.run(debug=True)