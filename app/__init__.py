from flask import Flask
from config import Config
from app.extensions import db, migrate, cors, socketio,jwt

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 1. Init Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app)
    socketio.init_app(app)
    jwt.init_app(app)

    # 2. Register Blueprints (Routes/Controllers)
    from app.routes.auth_routes import auth_bp
    app.register_blueprint(auth_bp)
    from app.routes.article_routes import article_bp
    app.register_blueprint(article_bp)
    from app.routes.screening_routes import screening_bp
    app.register_blueprint(screening_bp)
    from app.routes.consultation_routes import consultation_bp
    app.register_blueprint(consultation_bp)
    
    # 3. Import Models (PENTING: agar migrate mendeteksi tabel)
    from app.models import user
    from app.models import article
    from app.models import medical
    from app.models import consultation
    from app import socket_events

    @app.route('/')
    def index():
        return "Health App Backend is Running!"

    return app