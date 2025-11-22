from flask import Blueprint, request
from app.models.user import User
from app.extensions import db
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
# Import helper respon kita
from app.utils.response import success, error
from datetime import timedelta

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# --- 1. REGISTER ---
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return error("Email dan password wajib diisi", 400)
    
    if User.query.filter_by(email=data['email']).first():
        return error("Email sudah terdaftar", 400)
    
    new_user = User(
        email=data['email'],
        full_name=data.get('full_name', 'User Tanpa Nama'),
        role=data.get('role', 'PASIEN')
    )
    new_user.set_password(data['password'])
    
    db.session.add(new_user)
    db.session.commit()
    
    # Return standar: Data user yang baru dibuat (kecuali password)
    user_data = {
        "email": new_user.email,
        "full_name": new_user.full_name
    }
    
    return success(user_data, "Registrasi berhasil", 201)

# LOGIN 
@auth_bp.route('/login', methods=['POST'])
def login():
    # Kita asumsikan Login selalu pakai JSON (Standar)
    data = request.get_json()
    
    if not data:
        return error("Data tidak valid", 400)

    email = data.get('email')
    password = data.get('password')
    
    # --- LOGIKA DETEKSI MOBILE ---
    # Ambil parameter is_mobile, defaultnya False (Web) jika tidak dikirim
    is_mobile = data.get('is_mobile', False)
    
    user = User.query.filter_by(email=email).first()
    
    if user and user.check_password(password):
        # --- TENTUKAN DURASI ---
        if is_mobile:
            expires = timedelta(days=30) # Mobile: 30 Hari
            expire_msg = "30 Days"
        else:
            expires = timedelta(days=1)  # Web/Default: 1 Hari
            expire_msg = "1 Day"

        # Buat token dengan durasi custom
        access_token = create_access_token(identity=str(user.id), expires_delta=expires)
        
        login_data = {
            "token": access_token,
            "expires_in": expire_msg, # Info tambahan biar enak dilihat saat testing
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role
            }
        }
        return success(login_data, "Login berhasil")
    
    return error("Email atau password salah", 401)

# CEK PROFILE 
@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_my_profile():
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))
    
    if not user:
        return error("User tidak ditemukan", 404)
    
    profile_data = {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "joined_at": user.created_at
    }
    
    return success(profile_data, "Berhasil mengambil data profil")
# UPDATE PROFILE
# ... (kode atas sama)

@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))
    
    if not user:
        return error("User tidak ditemukan", 404)

    data = request.get_json()
    
    # 1. Update Data Umum (Semua Role)
    if 'full_name' in data:
        user.full_name = data['full_name']
    
    if 'password' in data:
        if len(data['password']) < 6:
            return error("Password minimal 6 karakter", 400)
        user.set_password(data['password'])

    # 2. Update Data Khusus DOKTER
    if user.role == 'DOKTER':
        if 'specialization' in data:
            user.specialization = data['specialization']
        
        if 'consultation_price' in data:
            # Pastikan inputnya angka
            try:
                user.consultation_price = int(data['consultation_price'])
            except:
                return error("Harga harus berupa angka", 400)
        
        if 'bio' in data:
            user.bio = data['bio']
            
        if 'is_online' in data:
            # Menangani input boolean true/false
            user.is_online = bool(data['is_online'])

    try:
        db.session.commit()
        
        # Kembalikan data terbaru (termasuk data dokter)
        updated_data = {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "specialization": user.specialization,   # Baru
            "consultation_price": user.consultation_price, # Baru
            "bio": user.bio,                         # Baru
            "is_online": user.is_online              # Baru
        }
        return success(updated_data, "Profil berhasil diperbarui")
        
    except Exception as e:
        db.session.rollback()
        return error(f"Gagal update profil: {str(e)}", 500)