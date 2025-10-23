from . import db, login_manager
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime

# --- (BỎ HOÀN TOÀN) class BorrowSlip(db.Model) ---
# Chúng ta thay thế nó bằng 2 class mới: BorrowList và ListItem

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    full_name = db.Column(db.String(100))
    student_id = db.Column(db.String(20), unique=True)
    class_name = db.Column(db.String(50))
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Quan hệ
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    
    # --- THÊM MỚI: Liên kết đến các "phiếu mượn" của user ---
    borrow_lists = db.relationship('BorrowList', backref='user', lazy=True)


    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id): return User.query.get(int(user_id))

class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    serial = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), default='Other')
    
    # --- THAY ĐỔI: Thay thế cột 'status' cũ bằng cột 'status' chi tiết hơn ---
    # Trạng thái mới: 'Available', 'Reserved', 'Borrowed', 'Maintenance'
    status = db.Column(db.String(50), default='Available', nullable=False)
    
    # --- (BỎ) Cột 'quantity' ---
    # Bỏ vì chúng ta theo dõi từng thiết bị riêng lẻ qua 'serial'
    
    location = db.Column(db.String(100), default='Kho chính')
    image_url = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    
    # --- THÊM MỚI: Theo dõi ai đang mượn thiết bị này ---
    borrower_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    borrower = db.relationship('User', foreign_keys=[borrower_id])
    
    # Quan hệ
    transactions = db.relationship('Transaction', backref='device', lazy=True, cascade='all, delete-orphan')

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # --- (BỎ) Cột 'borrow_slip_id' ---
    # Chúng ta không dùng BorrowSlip cũ nữa


# --- MODEL MỚI 1: BORROW LIST (GIỎ HÀNG/PHIẾU YÊU CẦU) ---
class BorrowList(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Trạng thái phiếu: 'Pending' (đang thêm đồ), 'Submitted' (đã gửi admin), 
    # 'Ready' (admin đã soạn), 'Completed' (đã mượn), 'Cancelled' (đã hủy)
    status = db.Column(db.String(50), default='Pending', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Quan hệ: Một phiếu có nhiều món đồ
    items = db.relationship('ListItem', backref='borrow_list', lazy='dynamic', cascade="all, delete-orphan")

# --- MODEL MỚI 2: LIST ITEM (CÁC MÓN ĐỒ TRONG GIỎ) ---
class ListItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    list_id = db.Column(db.Integer, db.ForeignKey('borrow_list.id'), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=False)
    
    # Quan hệ
    device = db.relationship('Device')