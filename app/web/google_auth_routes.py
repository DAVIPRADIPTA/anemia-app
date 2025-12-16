from flask import Blueprint, redirect, url_for, request
from flask_login import login_user
from app.extensions import oauth, db
from app.models.user import User

google_auth_bp = Blueprint("google_auth", __name__)

# STEP 1: User klik tombol Google
@google_auth_bp.route("/auth/google/login")
def google_login():
    # Role asal login dikirim dari tombol:
    # role=ADMIN atau role=DOKTER (web)
    # default-nya PASIEN tapi untuk web kita tidak pakai
    role = request.args.get("role", "PASIEN")

    redirect_uri = url_for("google_auth.google_callback", role=role, _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


# STEP 2: Callback dari Google (khusus WEB: admin & dokter)
@google_auth_bp.route("/auth/google/callback")
def google_callback():
    token = oauth.google.authorize_access_token()
    user_info = token.get("userinfo")  # { email, name, picture, ... }

    if not user_info:
        return "Google Login Failed", 400

    email = user_info["email"]
    name = user_info["name"]
    picture = user_info.get("picture")
    role_from_login = request.args.get("role", "PASIEN")

    # Cari user di DB
    user = User.query.filter_by(email=email).first()

    # === USER BELUM ADA → HANDLE SESUAI ROLE ===
    if not user:
        # 1. JANGAN pernah auto-buat ADMIN
        if role_from_login == "ADMIN":
            return "Akun admin ini belum terdaftar. Hubungi super admin.", 403

        # 2. DOKTER: boleh auto-buat, tapi BELUM terverifikasi
        if role_from_login == "DOKTER":
            user = User(
                email=email,
                full_name=name,
                role="DOKTER",
                is_verified=False,   # wajib verifikasi oleh admin
            )

        # 3. PASIEN: normal auto-register (kalau suatu saat dipakai untuk web)
        elif role_from_login == "PASIEN":
            user = User(
                email=email,
                full_name=name,
                role="PASIEN",
                is_verified=True,
            )

        # Simpan foto profil kalau field-nya ada
        if hasattr(User, "profile_image") and picture:
            user.profile_image = picture

        db.session.add(user)
        db.session.commit()

    # === USER SUDAH ADA → langsung login, role ikut DB, bukan dari URL ===
    login_user(user)

    # Redirect sesuai role yang tersimpan di DB
    if user.role == "ADMIN":
        return redirect(url_for("admin.dashboard"))
    elif user.role == "DOKTER":
        return redirect(url_for("doctor.dashboard"))
    else:
        # misalnya PASIEN atau role lain
        return redirect("/")

    print("REDIRECT_URI TEST:", url_for("google_auth.google_callback", role="ADMIN", _external=True))
    
