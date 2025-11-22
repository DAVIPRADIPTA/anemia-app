from flask import Blueprint, request
from datetime import datetime, timedelta
from app.extensions import db
from app.models.consultation import Consultation, Payment, ChatMessage
from app.models.user import User
from app.utils.response import success, error
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db, socketio # <--- Tambahkan socketio
from app.services.payment_service import payment_service

consultation_bp = Blueprint('consultation', __name__, url_prefix='/api/consultation')

# --- 1. BOOKING DOKTER (Membuat Tagihan) ---
@consultation_bp.route('/book', methods=['POST'])
@jwt_required()
def book_consultation():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id) # Ambil data user buat dikirim ke Midtrans
    
    data = request.get_json()
    doctor_id = data.get('doctor_id')
    
    if not doctor_id:
        return error("Doctor ID wajib diisi", 400)
        
    doctor = User.query.get(doctor_id)
    if not doctor or doctor.role != 'DOKTER':
        return error("Dokter tidak ditemukan", 404)

    # 1. Buat Data Konsultasi
    new_consultation = Consultation(
        patient_id=current_user_id,
        doctor_id=doctor_id,
        status='pending'
    )
    db.session.add(new_consultation)
    db.session.flush()

    # 2. Buat Order ID Unik (PENTING: Midtrans menolak ID yang sama dipakai 2x)
    # Format: ORDER-{timestamp}-{consultation_id}
    order_id = f"ORDER-{int(datetime.now().timestamp())}-{new_consultation.id}"

    # 3. Buat Data Payment di Database Kita
    new_payment = Payment(
        consultation_id=new_consultation.id,
        amount=doctor.consultation_price,
        status='pending',
        payment_method='midtrans',
        transaction_id=order_id # Simpan Order ID ini
    )
    db.session.add(new_payment)
    
    # 4. Panggil Midtrans (Minta Link Bayar)
    customer_info = {
        "first_name": user.full_name,
        "email": user.email,
    }
    
    midtrans_resp = payment_service.create_transaction(
        order_id=order_id,
        amount=doctor.consultation_price,
        customer_details=customer_info
    )
    
    if not midtrans_resp:
        db.session.rollback()
        return error("Gagal menghubungi gateway pembayaran", 500)

    db.session.commit()
    
    return success({
        "consultation_id": new_consultation.id,
        "payment_id": new_payment.id,
        "amount": new_payment.amount,
        "status": "Menunggu Pembayaran",
        # INI YANG PENTING:
        "payment_url": midtrans_resp['redirect_url'], 
        "payment_token": midtrans_resp['token']
    }, "Booking berhasil, silakan akses payment_url untuk membayar")

# --- 2. PEMBAYARAN MOCK (Pura-pura Bayar Langsung Lunas) ---
# Nanti endpoint ini diganti dengan Webhook Midtrans
@consultation_bp.route('/pay/<int:payment_id>', methods=['POST'])
@jwt_required()
def mock_payment_success(payment_id):
    payment = Payment.query.get(payment_id)
    
    if not payment:
        return error("Tagihan tidak ditemukan", 404)
        
    # 1. Update Status Pembayaran
    payment.status = 'success'
    payment.transaction_id = f"MOCK-{datetime.now().timestamp()}"
    
    # 2. Aktifkan Sesi Konsultasi
    consultation = Consultation.query.get(payment.consultation_id)
    consultation.status = 'active'
    
    # 3. Set Durasi 1 JAM dari sekarang
    consultation.expired_at = datetime.utcnow() + timedelta(hours=1)
    
    db.session.commit()
    
    return success({
        "consultation_id": consultation.id,
        "expired_at": consultation.expired_at,
        "status": "active"
    }, "Pembayaran Berhasil! Sesi Chat dimulai (Berlaku 1 Jam).")

# --- WEBHOOK MIDTRANS (PENTING) ---
# Endpoint ini dipanggil oleh Server Midtrans, bukan oleh User!
@consultation_bp.route('/notification', methods=['POST'])
def midtrans_notification():
    # Ambil data JSON yang dikirim Midtrans
    notification_data = request.get_json()
    
    order_id = notification_data.get('order_id')
    transaction_status = notification_data.get('transaction_status')
    fraud_status = notification_data.get('fraud_status')
    
    print(f"🔔 Midtrans Notification: {order_id} -> {transaction_status}")

    # Cari Payment di Database kita berdasarkan order_id
    payment = Payment.query.filter_by(transaction_id=order_id).first()
    if not payment:
        return error("Order ID not found", 404)

    # Logika Status Midtrans
    # Settlement / Capture = Sukses (Uang masuk)
    # Pending = Menunggu
    # Deny / Cancel / Expire = Gagal
    
    if transaction_status == 'capture':
        if fraud_status == 'challenge':
            payment.status = 'challenge'
        else:
            payment.status = 'success'
            activate_consultation(payment) # Fungsi helper (lihat bawah)
            
    elif transaction_status == 'settlement':
        payment.status = 'success'
        activate_consultation(payment)
        
    elif transaction_status in ['cancel', 'deny', 'expire']:
        payment.status = 'failed'
        
    elif transaction_status == 'pending':
        payment.status = 'pending'

    db.session.commit()
    return success(None, "Notification processed")

def activate_consultation(payment):
    """Mengaktifkan sesi konsultasi (Durasi 1 Jam)"""
    consultation = Consultation.query.get(payment.consultation_id)
    if consultation:
        consultation.status = 'active'
        consultation.expired_at = datetime.utcnow() + timedelta(hours=1)

# --- 3. KIRIM PESAN (Chatting) ---
@consultation_bp.route('/send', methods=['POST'])
@jwt_required()
def send_message():
    current_user_id = int(get_jwt_identity())
    
    data = request.get_json()
    consultation_id = data.get('consultation_id')
    message_text = data.get('message')
    
    if not consultation_id or not message_text:
        return error("Data tidak lengkap", 400)
        
    consultation = Consultation.query.get(consultation_id)
    
    # Validasi Sesi
    if not consultation:
        return error("Sesi tidak ditemukan", 404)
        
    # Cek apakah user terlibat dalam sesi ini (Safety)
    if current_user_id not in [consultation.patient_id, consultation.doctor_id]:
        return error("Anda tidak memiliki akses ke sesi ini", 403)
        
    # Cek Status Aktif
    if consultation.status != 'active':
        return error("Sesi chat belum aktif (belum bayar) atau sudah selesai.", 400)
        
    # Cek Kedaluwarsa Waktu (1 Jam tadi)
    if datetime.utcnow() > consultation.expired_at:
        consultation.status = 'completed' # Tutup otomatis
        db.session.commit()
        return error("Waktu konsultasi telah habis.", 400)

    # Simpan Pesan
    new_chat = ChatMessage(
        consultation_id=consultation_id,
        sender_id=current_user_id,
        message=message_text
    )
    db.session.add(new_chat)
    db.session.commit()
    
    # --- UPDATE: KIRIM SINYAL REAL-TIME ---
    # 1. Tentukan nama room (misal: consultation_10)
    room_id = f"consultation_{consultation_id}"
    
    # 2. Siapkan data pesan yang mau dikirim ke layar lawan bicara
    message_data = {
        "id": new_chat.id,
        "sender_id": new_chat.sender_id,
        "message": new_chat.message,
        "timestamp": new_chat.created_at.isoformat(),
        # Flag ini nanti diatur frontend, tapi kita kirim false defaultnya
        "is_me": False 
    }
    
    # 3. Teriakkan ke Room!
    print(f"📢 Mengirim notifikasi ke room: {room_id}")
    socketio.emit('new_message', message_data, to=room_id)
    # --------------------------------------
    
    return success(None, "Pesan terkirim")

# --- 4. LIHAT RIWAYAT CHAT ---
@consultation_bp.route('/<int:consultation_id>/messages', methods=['GET'])
@jwt_required()
def get_chat_history(consultation_id):
    current_user_id = int(get_jwt_identity())
    consultation = Consultation.query.get(consultation_id)
    
    if not consultation:
        return error("Sesi tidak ditemukan", 404)
        
    # Validasi Akses
    if current_user_id not in [consultation.patient_id, consultation.doctor_id]:
        return error("Akses ditolak", 403)
        
    # Ambil pesan urut dari yang terlama ke terbaru
    messages = ChatMessage.query.filter_by(consultation_id=consultation_id)\
        .order_by(ChatMessage.created_at.asc()).all()
        
    output = []
    for msg in messages:
        output.append({
            "id": msg.id,
            "sender_id": msg.sender_id,
            "message": msg.message,
            "timestamp": msg.created_at,
            "is_me": msg.sender_id == current_user_id # Flag untuk frontend (bubble kanan/kiri)
        })
        
    return success(output, "Riwayat chat berhasil diambil")