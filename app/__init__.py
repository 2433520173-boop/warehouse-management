from flask import Flask, flash, redirect, url_for, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_mail import Mail
# Sửa lại import ở đây
from config import config
from functools import wraps
import os
from datetime import datetime, timedelta

db = SQLAlchemy()
mail = Mail()
login_manager = LoginManager()
login_manager.login_view = 'main.login'
login_manager.login_message_category = 'info'

def format_to_local_time(utc_dt):
    if utc_dt is None: return ""
    local_dt = utc_dt + timedelta(hours=7)
    return local_dt.strftime('%H:%M ngày %d-%m-%Y')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Bạn cần quyền admin để truy cập trang này!', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

# Cập nhật hàm create_app
def create_app(config_name):
    app = Flask(__name__)
    # Áp dụng cấu hình được chọn
    app.config.from_object(config[config_name])

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)

    app.jinja_env.filters['localtime'] = format_to_local_time

    from .routes.main_routes import main_bp
    app.register_blueprint(main_bp)
    from .routes.device_routes import device_bp
    app.register_blueprint(device_bp)
    from .routes.admin_routes import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    @app.errorhandler(404)
    def page_not_found(e): return render_template('errors/404.html'), 404
    @app.errorhandler(403)
    def forbidden(e): return render_template('errors/403.html'), 403

    return app