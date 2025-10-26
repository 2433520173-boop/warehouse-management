from . import db, login_manager
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
# --- THÊM IMPORT ---
# --- SỬA LẠI: Import Date từ datetime ---
from datetime import datetime, timedelta, timezone, date
from flask import current_app
from itsdangerous import URLSafeTimedSerializer as Serializer
# --- (Kết thúc thêm import) ---

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
    borrow_lists = db.relationship('BorrowList', backref='user', lazy=True)


    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # --- PHƯƠNG THỨC MỚI CHO RESET MẬT KHẨU ---
    def get_reset_token(self, expires_sec=1800):
        """Tạo token reset mật khẩu, hết hạn sau expires_sec giây (mặc định 30 phút)."""
        s = Serializer(current_app.config['SECRET_KEY'])
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_sec)
        payload = {'user_id': self.id, 'exp': expires_at.timestamp()}
        return s.dumps(payload)

    @staticmethod
    def verify_reset_token(token, leeway=10):
        """Xác thực token reset. Trả về User nếu hợp lệ, None nếu không."""
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            payload = s.loads(token, max_age=None)
            user_id = payload.get('user_id')
            exp_timestamp = payload.get('exp')
            if exp_timestamp is None or datetime.now(timezone.utc).timestamp() > exp_timestamp + leeway:
                 return None
            if user_id is None:
                return None
        except Exception:
            return None
        return User.query.get(user_id)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    serial = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), default='Other')
    unit = db.Column(db.String(30), default='Cái')
    status = db.Column(db.String(50), default='Available', nullable=False) # Available, Reserved, Borrowed, Maintenance
    location = db.Column(db.String(100), default='Kho chính')
    image_url = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    borrower_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    borrower = db.relationship('User', foreign_keys=[borrower_id])
    transactions = db.relationship('Transaction', backref='device', lazy=True, cascade='all, delete-orphan')

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False) # Mượn, Trả
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class BorrowList(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(50), default='Pending', nullable=False) # Pending, Submitted, Ready, Completed, Cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expected_borrow_date = db.Column(db.Date, nullable=True)

    # --- THÊM MỚI: Các cột cho quản lý quá hạn ---
    borrowed_at = db.Column(db.DateTime, nullable=True) # Thời điểm giao đồ (hoàn tất)
    return_deadline = db.Column(db.Date, nullable=True) # Hạn trả = borrowed_at + 30 days
    returned_at = db.Column(db.DateTime, nullable=True) # Thời điểm trả thực tế (null nếu chưa trả)

    items = db.relationship('ListItem', backref='borrow_list', lazy='dynamic', cascade="all, delete-orphan")

    # --- THÊM MỚI: Property để kiểm tra quá hạn ---
    @property
    def is_overdue(self):
        """Kiểm tra xem phiếu mượn này có bị quá hạn không."""
        # Chỉ kiểm tra nếu phiếu đã hoàn tất, chưa trả, và có hạn trả
        if self.status == 'Completed' and self.returned_at is None and self.return_deadline:
            return date.today() > self.return_deadline
        return False


class ListItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    list_id = db.Column(db.Integer, db.ForeignKey('borrow_list.id'), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=False)
    device = db.relationship('Device')