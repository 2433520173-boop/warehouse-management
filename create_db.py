import os
from app import create_app, db
from app.models import User

# Đọc biến môi trường FLASK_CONFIG để chọn đúng CSDL
config_name = os.getenv('FLASK_CONFIG') or 'default'
app = create_app(config_name)

with app.app_context():
    print(f"Bắt đầu quá trình khởi tạo cơ sở dữ liệu cho môi trường '{config_name}'...")
    # (Phần còn lại giữ nguyên)
    db.drop_all()
    print("Đã xóa các bảng cũ (nếu có).")
    db.create_all()
    print("Đã tạo thành công tất cả các bảng mới.")

    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@example.com', full_name='Quản Trị Viên', is_admin=True)
        admin.set_password('admin123')
        db.session.add(admin)
        print("Đã thêm tài khoản admin.")

    if not User.query.filter_by(username='user').first():
        user = User(username='user', email='user@example.com', full_name='Người Dùng Mẫu')
        user.set_password('user123')
        db.session.add(user)
        print("Đã thêm tài khoản user mẫu.")

    db.session.commit()
    print("\n🎉 Khởi tạo cơ sở dữ liệu và tạo tài khoản mẫu thành công!")
