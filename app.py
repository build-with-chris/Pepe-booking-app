from flask import Flask
from config import Config
from models import db
from routes import api_bp, admin_bp
from flask_jwt_extended import JWTManager
from flask_login import LoginManager
from auth_routes import auth_bp
from flasgger import Swagger
from flask_cors import CORS

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    from datamanager import DataManager
    return DataManager().get_artist(user_id)

jwt = JWTManager(app)

template = {
"swagger": "2.0",
"info": {
    "title": "Pepe Backend API",
    "description": "This Api provides Endpoint for Artists to edit their availability, "
    "provides auth login and enables requests for the client",
    "version": "1.0"
}
}
app.config['SWAGGER'] = {
'title': "Pepe Backend API",
'uiversion': 2,
'template': './resources/flasgger/swagger_ui.html'
}
Swagger(app, template=template)

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(api_bp,  url_prefix='/api')
app.register_blueprint(admin_bp, url_prefix='/admin')

CORS(app, resources={r"/api/*": {"origins": "*"}})


if __name__=="__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)