from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User

web_bp = Blueprint('web', __name__)

# Halaman Login Admin
@web_bp.route('/admin/login', methods=['GET', 'POST'])
def login_page():
    # Kalau sudah login, langsung lempar ke dashboard
    if current_user.is_authenticated:
        return redirect('/admin')

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        # Cek Password & Role Admin
        if user and user.check_password(password):
            if user.role == 'ADMIN':
                login_user(user) # Buat Sesi Browser
                return redirect('/admin') # Sukses -> Masuk Dashboard
            else:
                flash('Anda bukan Admin!')
        else:
            flash('Email atau Password salah!')
            
    return render_template('login.html')

# Logout
@web_bp.route('/admin/logout')
@login_required
def logout_page():
    logout_user()
    return redirect(url_for('web.login_page'))