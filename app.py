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



app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

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


if __name__=="__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)