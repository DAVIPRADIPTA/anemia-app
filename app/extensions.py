from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_jwt_extended import JWTManager # <--- Tambah ini
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
migrate = Migrate()
cors = CORS()
socketio = SocketIO(cors_allowed_origins="*") # Siap untuk real-time chat
jwt = JWTManager() # <--- Tambah ini
bcrypt = Bcrypt()
