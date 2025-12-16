import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Konfigurasi Upload
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app/static/uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # Batas max file 16MB
    GOOGLE_CLIENT_ID = "78011683071-fku21qpan1s84g1tm2t2hk3i9klr4qgs.apps.googleusercontent.com"
    GOOGLE_CLIENT_SECRET = "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"
    GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

