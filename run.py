import os
import click
from app import create_app, db
from app.models import User

# Đọc biến môi trường để quyết định cấu hình
config_name = os.getenv('FLASK_CONFIG') or 'default'
app = create_app(config_name)

# --- Lệnh khởi tạo CSDL mới ---
@app.cli.command("init-db")
def init_db_command():
    """Xóa và tạo lại cơ sở dữ liệu với dữ liệu mẫu."""
    # Đặt lệnh echo VÀO TRONG hàm
    click.echo("Bắt đầu quá trình khởi tạo cơ sở dữ liệu...")
    
    db.drop_all()
    db.create_all()

    # Tạo tài khoản admin
    admin = User(
        username='admin', email='admin@example.com', full_name='Quản Trị Viên',
        is_admin=True
    )
    admin.set_password('admin123')
    db.session.add(admin)

    # Tạo tài khoản user mẫu
    user = User(
        username='user', email='user@example.com', full_name='Người Dùng Mẫu'
    )
    user.set_password('user123')
    db.session.add(user)

    db.session.commit()
    click.echo('🎉 Khởi tạo cơ sở dữ liệu và tạo tài khoản mẫu thành công!')


# --- Logic chạy ứng dụng ---
if __name__ == '__main__':
    # Lấy giá trị DEBUG từ file config thay vì đặt cứng là True
    app.run(host='0.0.0.0', debug=app.config.get('DEBUG', False))