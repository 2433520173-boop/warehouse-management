import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
# Tải biến môi trường từ file .env (chỉ dùng cho môi trường development)
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    """Cấu hình chung cho tất cả môi trường."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'ban-nen-thay-doi-secret-key-nay'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(basedir, 'app/static/uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('EMAIL_USER')
    MAIL_PASSWORD = os.environ.get('EMAIL_PASS')
    MAIL_DEFAULT_SENDER = os.environ.get('EMAIL_USER')
    HOST_EMAIL = os.environ.get('HOST_EMAIL')

class DevelopmentConfig(Config):
    """Cấu hình cho môi trường phát triển (máy tính cá nhân)."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'warehouse.db')

class ProductionConfig(Config):
    """Cấu hình cho môi trường sản phẩm (trên Render)."""
    DEBUG = False
    # Bắt buộc phải có DATABASE_URL trên môi trường production
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    # Thêm các cấu hình khác cho production nếu cần

# Dictionary để lựa chọn cấu hình
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
