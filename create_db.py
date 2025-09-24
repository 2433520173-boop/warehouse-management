# create_db.py
import os
from app import create_app, db
from app.models import User

# Tạo một instance của ứng dụng để có context
app = create_app()

# Chạy trong application context
with app.app_context():
    print("Bắt đầu quá trình khởi tạo cơ sở dữ liệu...")

    # Xóa tất cả các bảng cũ (nếu có) để làm sạch
    db.drop_all()
    print("Đã xóa các bảng cũ (nếu có).")

    # Tạo tất cả các bảng mới dựa trên models.py
    db.create_all()
    print("Đã tạo thành công tất cả các bảng mới (user, device, transaction).")

    # Thêm tài khoản admin
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@example.com', full_name='Quản Trị Viên', is_admin=True)
        admin.set_password('admin123')
        db.session.add(admin)
        print("Đã thêm tài khoản admin.")

    # Thêm tài khoản user mẫu
    if not User.query.filter_by(username='user').first():
        user = User(username='user', email='user@example.com', full_name='Người Dùng Mẫu')
        user.set_password('user123')
        db.session.add(user)
        print("Đã thêm tài khoản user mẫu.")

    # Lưu thay đổi vào cơ sở dữ liệu
    db.session.commit()
    print("\n🎉 Khởi tạo cơ sở dữ liệu và tạo tài khoản mẫu thành công!")