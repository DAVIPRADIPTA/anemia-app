from app.extensions import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False) # Perbesar panjang karakter jaga-jaga
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False) # 'PASIEN', 'DOKTER', 'ADMIN'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Kolom ini akan NULL (kosong) jika usernya adalah Pasien
    specialization = db.Column(db.String(100), nullable=True)
    consultation_price = db.Column(db.Integer, default=0) # Harga dalam Rupiah
    is_online = db.Column(db.Boolean, default=False)
    bio = db.Column(db.Text, nullable=True)

    # Fungsi untuk set password (otomatis di-hash)
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    # Fungsi untuk cek password saat login
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.email}>"