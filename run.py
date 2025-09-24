import os
import click
from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

config_name = os.getenv('FLASK_CONFIG') or 'default'
app = create_app(config_name)

@app.cli.command("init-db")
def init_db_command():
    """Xóa và tạo lại cơ sở dữ liệu với dữ liệu mẫu."""
    db.drop_all()
    db.create_all()

    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin', email='admin@example.com', full_name='Quản Trị Viên',
            student_id='ADMIN001', class_name='ADMIN', is_admin=True
        )
        admin.set_password('admin123')
        db.session.add(admin)

    if not User.query.filter_by(username='user').first():
        user = User(
            username='user', email='user@example.com', full_name='Người Dùng Mẫu',
            student_id='USER001', class_name='USER'
        )
        user.set_password('user123')
        db.session.add(user)

    db.session.commit()
    click.echo('Initialized the database and created sample users.')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)