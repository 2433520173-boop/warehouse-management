from . import db, login_manager
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime

# --- BẢNG MỚI: BORROW SLIP ---
class BorrowSlip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True, nullable=False) # Trạng thái của phiếu (True=đang mượn, False=đã trả hết)
    
    # Mối quan hệ: Một phiếu có nhiều giao dịch
    transactions = db.relationship('Transaction', backref='borrow_slip', lazy=True)
    user = db.relationship('User')

class User(UserMixin, db.Model):
    # (Không thay đổi class User)
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    full_name = db.Column(db.String(100))
    student_id = db.Column(db.String(20), unique=True)
    class_name = db.Column(db.String(50))
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    transactions = db.relationship('Transaction', backref='user', lazy=True)

    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id): return User.query.get(int(user_id))

class Device(db.Model):
    # (Không thay đổi class Device)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    serial = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), default='Other')
    status = db.Column(db.String(20), default='available')
    quantity = db.Column(db.Integer, default=1, nullable=False)
    location = db.Column(db.String(100), default='Kho chính')
    image_url = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User')
    transactions = db.relationship('Transaction', backref='device', lazy=True, cascade='all, delete-orphan')

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # --- CẬP NHẬT: Thêm liên kết đến BorrowSlip ---
    borrow_slip_id = db.Column(db.Integer, db.ForeignKey('borrow_slip.id'), nullable=True)