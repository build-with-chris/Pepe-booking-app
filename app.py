from flask import Flask
from config import Config
from models import db
from flask_jwt_extended import JWTManager
from routes.api_routes       import api_bp
from routes.auth_routes  import auth_bp
from routes.admin_routes import admin_bp
from flasgger import Swagger
from flask_cors import CORS
from routes.request_routes import booking_bp


"""
Hauptskript für den Flask-Server:
- Konfiguration laden
- DB initialisieren
- Blueprints registrieren
- Swagger‐UI und CORS einrichten
"""


app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

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
CORS(app, resources={r"/api/*": {"origins": "*"}})


if __name__=="__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)