from flask import Flask
from config import Config
from app.extensions import db, migrate, cors, socketio, jwt, bcrypt, login_manager
from flask_login import LoginManager
from app.models.user import User
from app.extensions import oauth



def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app)
    socketio.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    oauth.init_app(app)


    oauth.register(
    name="google",
    client_id=app.config["GOOGLE_CLIENT_ID"],
    client_secret=app.config["GOOGLE_CLIENT_SECRET"],
    server_metadata_url=app.config["GOOGLE_DISCOVERY_URL"],
    client_kwargs={
        "scope": "openid email profile"
    },
    )

    # Flask-Login: tentukan halaman login
    login_manager.login_view = 'web_auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from app.routes.auth_routes import auth_bp
    from app.routes.article_routes import article_bp
    from app.routes.screening_routes import screening_bp
    from app.routes.consultation_routes import consultation_bp

    from app.web.auth_routes import web_auth_bp
    from app.web.admin_routes import admin_bp
    from app.web.doctor_routes import doctor_bp
    from app.web.doctor_articles import doctor_article_bp
    from app.web.doctor_consultation import doctor_consult_bp
    from app.web.google_auth_routes import google_auth_bp





    app.register_blueprint(auth_bp)
    app.register_blueprint(article_bp)
    app.register_blueprint(screening_bp)
    app.register_blueprint(consultation_bp)
    app.register_blueprint(web_auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(doctor_bp)
    app.register_blueprint(doctor_article_bp)
    app.register_blueprint(doctor_consult_bp)
    app.register_blueprint(google_auth_bp)



    # Import SocketIO Events
    from app import socket_events

    @app.route('/')
    def index():
        return "Health App Backend is Running!"

    return app
