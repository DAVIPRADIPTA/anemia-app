from flask import Flask
from config import Config
from app.extensions import db, migrate, cors, socketio, jwt, bcrypt
from flask_login import LoginManager
from app.models.user import User

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 1. Init Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app)
    socketio.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)

    # 2. Setup Flask-Login (Untuk Admin Panel)
    login_manager = LoginManager()
    login_manager.init_app(app)
    # Nanti kita buat route 'web.login_page' di web_routes.py
    login_manager.login_view = 'web.login_page' 

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # 3. Setup Admin Panel (Flask-Admin)
    from app.admin import setup_admin
    setup_admin(app)

    # 4. Register Blueprints (API Routes)
    from app.routes.auth_routes import auth_bp
    from app.routes.article_routes import article_bp
    from app.routes.screening_routes import screening_bp
    from app.routes.consultation_routes import consultation_bp
    # Nanti kita buat web_routes.py untuk login admin HTML
    from app.routes.web_routes import web_bp 

    app.register_blueprint(auth_bp)
    app.register_blueprint(article_bp)
    app.register_blueprint(screening_bp)
    app.register_blueprint(consultation_bp)
    app.register_blueprint(web_bp)

    # 5. Import Socket Events
    from app import socket_events

    @app.route('/')
    def index():
        return "Health App Backend is Running!"

    return app