from flask import Flask
from config import Config
from models import db
from routes import api_bp
from flask_jwt_extended import JWTManager
from auth import auth_bp
from flask_cors import CORS

app = Flask(__name__)
app.config.from_object(Config)

jwt = JWTManager(app)
app.register_blueprint(auth_bp, url_prefix='/auth')

CORS(app, resources={r"/api/*": {"origins": "*"}})

db.init_app(app)
app.register_blueprint(api_bp, url_prefix="/api")

if __name__=="__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)