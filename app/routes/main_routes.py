import re # --- THÊM MỚI: Import thư viện Regular Expression ---
# --- THÊM MỚI: Import datetime để xử lý ngày ---
from datetime import datetime 
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
# --- THAY ĐỔI: Thêm BorrowList, ListItem ---
from ..models import db, User, Device, Transaction, BorrowList, ListItem
# --- THÊM MỚI: Import hàm gửi email reset ---
from ..services.email_service import send_password_reset_email

main_bp = Blueprint('main', __name__)

# --- THÊM MỚI: Tự động truyền số lượng giỏ hàng vào mọi template ---
@main_bp.app_context_processor
def inject_pending_list_count():
    """Injects pending list item count for the current user into all templates."""
    if current_user.is_authenticated and not current_user.is_admin:
        pending_list = BorrowList.query.filter_by(user_id=current_user.id, status='Pending').first()
        if pending_list:
            return dict(pending_list_count=pending_list.items.count())
    return dict(pending_list_count=0)


@main_bp.route('/')
@login_required
def index():
    # --- THAY ĐỔI: Thêm trạng thái 'Reserved' vào thống kê ---
    stats = {
        'total_devices': Device.query.count(),
        'available_devices': Device.query.filter_by(status='Available').count(),
        'borrowed_devices': Device.query.filter_by(status='Borrowed').count(),
        'reserved_devices': Device.query.filter_by(status='Reserved').count() # Mới
    }
    recent_transactions = Transaction.query.order_by(Transaction.created_at.desc()).limit(20).all()
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
        username = request.form['username'].strip()
        email = request.form['email'].strip().lower() # Lấy email và chuyển sang chữ thường

        # --- THÊM MỚI: Kiểm tra định dạng email ---
        # Định dạng: 10 chữ số, theo sau là @vaa.edu.vn
        email_pattern = r'^\d{10}@vaa\.edu\.vn$'
        if not re.match(email_pattern, email):
            flash('Email không hợp lệ. Vui lòng sử dụng email của trường.', 'error')
            return render_template('register.html', form=request.form)
        # --- (Kết thúc kiểm tra email) ---

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

# --- GIAI ĐOẠN 3: CÁC ROUTE MỚI CHO "GIỎ HÀNG" ---

@main_bp.route('/my-list')
@login_required
def my_list():
    """Hiển thị trang "giỏ hàng" (Danh sách mượn) của sinh viên."""
    if current_user.is_admin:
        flash('Admin không có danh sách mượn.', 'error')
        return redirect(url_for('main.index'))
    borrow_list = BorrowList.query.filter_by(user_id=current_user.id, status='Pending').first()
    list_items = []
    if borrow_list:
        list_items = borrow_list.items.order_by(ListItem.id.desc()).all()
    return render_template('my_list.html', list_items=list_items, borrow_list=borrow_list)

@main_bp.route('/remove-from-list/<int:item_id>', methods=['POST'])
@login_required
def remove_from_list(item_id):
    """(Sinh viên) Xóa một món đồ khỏi giỏ hàng."""
    if current_user.is_admin:
        return redirect(url_for('main.index'))
    item = ListItem.query.get_or_404(item_id)
    if item.borrow_list.user_id != current_user.id or item.borrow_list.status != 'Pending':
        flash('Bạn không có quyền xóa vật phẩm này.', 'error')
        return redirect(url_for('main.my_list'))
    device = item.device
    device.status = 'Available'
    db.session.delete(item)
    db.session.commit()
    flash(f'Đã xóa "{device.name}" khỏi danh sách.', 'success')
    return redirect(url_for('main.my_list'))

@main_bp.route('/submit-list', methods=['POST'])
@login_required
def submit_list():
    """(Sinh viên) Gửi "giỏ hàng" cho Admin."""
    if current_user.is_admin:
        return redirect(url_for('main.index'))
    borrow_list = BorrowList.query.filter_by(user_id=current_user.id, status='Pending').first()
    if not borrow_list or not borrow_list.items.count():
        flash('Danh sách mượn của bạn đang trống.', 'error')
        return redirect(url_for('main.my_list'))

    # --- THÊM MỚI: Lấy và lưu ngày dự kiến ---
    expected_date_str = request.form.get('expected_borrow_date')
    if expected_date_str:
        try:
            # Chuyển đổi chuỗi YYYY-MM-DD thành đối tượng date
            borrow_list.expected_borrow_date = datetime.strptime(expected_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Định dạng ngày dự kiến không hợp lệ.', 'error')
            return redirect(url_for('main.my_list'))
    else:
        # Nếu không chọn ngày, có thể báo lỗi hoặc để trống tùy ý
        flash('Vui lòng chọn ngày dự kiến nhận thiết bị.', 'error')
        return redirect(url_for('main.my_list'))
        # borrow_list.expected_borrow_date = None # Hoặc cho phép để trống
    # --- (Kết thúc thêm ngày dự kiến) ---

    borrow_list.status = 'Submitted'
    db.session.commit()
    # (TODO: Gửi email cho admin báo có yêu cầu mới)
    flash('Đã gửi yêu cầu mượn thành công! Admin sẽ sớm soạn đồ cho bạn.', 'success')
    return redirect(url_for('main.index'))

# --- TÍNH NĂNG MỚI: QUÊN MẬT KHẨU ---

@main_bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    """Trang yêu cầu đặt lại mật khẩu."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            token = user.get_reset_token()
            send_password_reset_email(user, token)
            flash('Một email hướng dẫn đặt lại mật khẩu đã được gửi đến địa chỉ email của bạn.', 'info')
            return redirect(url_for('main.login'))
        else:
            flash('Không tìm thấy tài khoản nào với địa chỉ email này.', 'warning')
    return render_template('reset_password_request.html')

@main_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Trang đặt lại mật khẩu sau khi nhấp link trong email."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('Token không hợp lệ hoặc đã hết hạn.', 'warning')
        return redirect(url_for('main.reset_password_request'))

    if request.method == 'POST':
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        if password and password == password_confirm:
            user.set_password(password)
            db.session.commit()
            flash('Mật khẩu của bạn đã được cập nhật thành công! Vui lòng đăng nhập.', 'success')
            return redirect(url_for('main.login'))
        else:
            flash('Mật khẩu nhập lại không khớp.', 'error')

    return render_template('reset_password.html', token=token)