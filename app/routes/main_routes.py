from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from ..models import db, User, Device, Transaction

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def index():
    stats = {
        'total_devices': Device.query.count(),
        'available_devices': Device.query.filter_by(status='available').count(),
        'borrowed_devices': Device.query.filter_by(status='borrowed').count()
    }
    recent_transactions = Transaction.query.order_by(Transaction.created_at.desc()).limit(5).all()
    return render_template('index.html', stats=stats, recent_transactions=recent_transactions)

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('main.index'))
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.check_password(request.form['password']):
            login_user(user, remember=request.form.get('remember'))
            return redirect(url_for('main.index'))
        flash('Đăng nhập không thành công. Vui lòng kiểm tra lại thông tin.', 'error')
    return render_template('login.html')

@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated: return redirect(url_for('main.index'))
    if request.method == 'POST':
        username, email = request.form['username'], request.form['email']
        if User.query.filter_by(username=username).first():
            flash('Tên đăng nhập đã tồn tại.', 'error')
        elif User.query.filter_by(email=email).first():
            flash('Email đã được sử dụng.', 'error')
        else:
            new_user = User(username=username, email=email, full_name=request.form['full_name'],
                            student_id=request.form['student_id'], class_name=request.form['class_name'])
            new_user.set_password(request.form['password'])
            db.session.add(new_user)
            db.session.commit()
            flash('Đăng ký tài khoản thành công! Vui lòng đăng nhập.', 'success')
            return redirect(url_for('main.login'))
    return render_template('register.html')

@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))

@main_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = User.query.get_or_404(current_user.id)
    if request.method == 'POST':
        user.email = request.form['email']
        user.full_name = request.form['full_name']
        user.student_id = request.form['student_id']
        user.class_name = request.form['class_name']
        
        password = request.form.get('password')
        if password and password == request.form.get('password_confirm'):
            user.set_password(password)
            flash('Mật khẩu đã được cập nhật.', 'success')
        elif password:
            flash('Mật khẩu nhập lại không khớp.', 'error')
        
        db.session.commit()
        flash('Thông tin cá nhân đã được cập nhật.', 'success')
        return redirect(url_for('main.profile'))
    return render_template('profile.html', user=user)
# (Thêm vào cuối file app/routes/main_routes.py)

from ..models import BorrowSlip

@main_bp.route('/my-borrows')
@login_required
def my_borrows():
    # Lấy tất cả các phiếu mượn còn hoạt động của người dùng hiện tại
    active_slips = BorrowSlip.query.filter_by(user_id=current_user.id, is_active=True).order_by(BorrowSlip.created_at.desc()).all()
    return render_template('my_borrows.html', slips=active_slips)