import pandas as pd
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .. import admin_required
# Import tất cả model và db
from ..models import db, User, Device, Transaction, BorrowList, ListItem
from sqlalchemy import desc

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    stats = {
        'users': User.query.count(), 
        'devices': Device.query.count(), 
        'transactions': Transaction.query.count(),
        'pending_requests': BorrowList.query.filter_by(status='Submitted').count()
    }
    return render_template('admin/dashboard.html', stats=stats)

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    page = request.args.get('page', 1, type=int)
    users_list = User.query.order_by(User.created_at.desc()).paginate(page=page, per_page=15)
    return render_template('admin/users.html', users=users_list)

@admin_bp.route('/devices')
@login_required
@admin_required
def devices():
    page = request.args.get('page', 1, type=int)
    devices_list = Device.query.order_by(Device.created_at.desc()).paginate(page=page, per_page=15)
    return render_template('admin/devices.html', devices=devices_list)

@admin_bp.route('/transactions')
@login_required
@admin_required
def transactions():
    page = request.args.get('page', 1, type=int)
    transactions_list = Transaction.query.order_by(Transaction.created_at.desc()).paginate(page=page, per_page=20)
    return render_template('admin/transactions.html', transactions=transactions_list)

@admin_bp.route('/user/<int:user_id>')
@login_required
@admin_required
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    transactions = Transaction.query.filter_by(user_id=user.id).order_by(Transaction.created_at.desc()).all()
    return render_template('admin/user_detail.html', user=user, transactions=transactions)


# --- CÁC ROUTE QUẢN LÝ YÊU CẦU ---

@admin_bp.route('/requests')
@login_required
@admin_required
def requests_list():
    submitted_lists = BorrowList.query.filter_by(status='Submitted').order_by(BorrowList.created_at.asc()).all()
    ready_lists = BorrowList.query.filter_by(status='Ready').order_by(BorrowList.created_at.asc()).all()
    
    return render_template('admin_requests.html', 
                           submitted_lists=submitted_lists, 
                           ready_lists=ready_lists)

@admin_bp.route('/request/<int:list_id>')
@login_required
@admin_required
def request_detail(list_id):
    borrow_list = BorrowList.query.get_or_404(list_id)
    return render_template('admin_request_detail.html', borrow_list=borrow_list)

@admin_bp.route('/request/<int:list_id>/ready', methods=['POST'])
@login_required
@admin_required
def mark_as_ready(list_id):
    borrow_list = BorrowList.query.get_or_404(list_id)
    if borrow_list.status == 'Submitted':
        borrow_list.status = 'Ready'
        db.session.commit()
        flash(f'Đã đánh dấu phiếu #{list_id} là Sẵn sàng. Chờ học sinh đến lấy.', 'success')
    else:
        flash('Yêu cầu này không ở trạng thái "Submitted".', 'error')
    return redirect(url_for('admin.request_detail', list_id=list_id))

@admin_bp.route('/request/<int:list_id>/complete', methods=['POST'])
@login_required
@admin_required
def mark_as_completed(list_id):
    borrow_list = BorrowList.query.get_or_404(list_id)
    if borrow_list.status != 'Ready':
        flash('Yêu cầu này không ở trạng thái "Ready".', 'error')
        return redirect(url_for('admin.request_detail', list_id=list_id))

    successful_transactions = []
    for item in borrow_list.items:
        device = item.device
        if device.status == 'Reserved':
            device.status = 'Borrowed'
            device.borrower_id = borrow_list.user_id 
            
            transaction = Transaction(
                device_id=device.id, 
                user_id=borrow_list.user_id, 
                transaction_type='Mượn', 
                notes=f'Mượn theo yêu cầu #{borrow_list.id}'
            )
            db.session.add(transaction)
            successful_transactions.append(transaction)
        
    borrow_list.status = 'Completed'
    db.session.commit()
    
    flash(f'Đã hoàn tất giao {len(successful_transactions)} thiết bị cho phiếu #{list_id}.', 'success')
    return redirect(url_for('admin.requests_list'))

@admin_bp.route('/request/<int:list_id>/cancel', methods=['POST'])
@login_required
@admin_required
def cancel_request(list_id):
    borrow_list = BorrowList.query.get_or_404(list_id)
    if borrow_list.status not in ['Submitted', 'Ready']:
        flash('Không thể hủy một yêu cầu đã hoàn tất.', 'error')
        return redirect(url_for('admin.request_detail', list_id=list_id))

    for item in borrow_list.items:
        if item.device.status == 'Reserved':
            item.device.status = 'Available'
            
    borrow_list.status = 'Cancelled'
    db.session.commit()
    flash(f'Đã hủy yêu cầu #{list_id}. Các thiết bị đã được trả về kho.', 'success')
    return redirect(url_for('admin.requests_list'))


# --- TÍNH NĂNG MỚI: UPLOAD EXCEL ---

@admin_bp.route('/upload-devices', methods=['GET', 'POST'])
@login_required
@admin_required
def upload_devices():
    if request.method == 'POST':
        # 1. Kiểm tra file
        if 'file' not in request.files:
            flash('Không tìm thấy file. Vui lòng chọn file để upload.', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('Không có file nào được chọn.', 'info')
            return redirect(request.url)
        
        # 2. Đọc file bằng Pandas
        if file and (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
            try:
                df = pd.read_excel(file, engine='openpyxl')
                
                # 3. Kiểm tra các cột bắt buộc
                required_columns = ['name', 'serial']
                if not all(col.lower() in [c.lower() for c in df.columns] for col in required_columns):
                    flash(f'File Excel phải có các cột bắt buộc: {", ".join(required_columns)}', 'error')
                    return redirect(request.url)
                
                # Chuẩn hóa tên cột về chữ thường
                df.columns = [col.lower() for col in df.columns]

                added_count = 0
                error_serials = []
                missing_data_rows = 0

                # 4. Lặp qua từng dòng để thêm
                for index, row in df.iterrows():
                    name = row['name']
                    serial = row.get('serial')

                    # Bỏ qua dòng nếu thiếu Tên hoặc Serial
                    if pd.isna(name) or pd.isna(serial):
                        missing_data_rows += 1
                        continue
                    
                    serial = str(serial).strip().upper()

                    # Kiểm tra serial trùng lặp trong CSDL
                    if Device.query.filter_by(serial=serial).first():
                        error_serials.append(serial)
                        continue

                    # Lấy các cột tùy chọn (nếu có)
                    category = row.get('category', 'Other')
                    description = row.get('description', '')
                    location = row.get('location', 'Kho chính')
                    
                    # Xử lý giá trị rỗng (NaN) từ Excel
                    category = 'Other' if pd.isna(category) else category
                    description = '' if pd.isna(description) else description
                    location = 'Kho chính' if pd.isna(location) else location

                    new_device = Device(
                        name=name,
                        serial=serial,
                        category=category,
                        description=description,
                        location=location,
                        created_by_id=current_user.id,
                        status='Available' # Mặc định là có sẵn
                    )
                    db.session.add(new_device)
                    added_count += 1
                
                # 5. Lưu vào CSDL
                db.session.commit()

                # 6. Flash thông báo kết quả
                if added_count > 0:
                    flash(f'Đã thêm thành công {added_count} thiết bị mới.', 'success')
                if not error_serials and not missing_data_rows and added_count == 0:
                    flash('Không có thiết bị nào được thêm (có thể file rỗng).', 'info')
                if error_serials:
                    flash(f'Các serial sau đã tồn tại và bị bỏ qua: {", ".join(error_serials)}', 'warning')
                if missing_data_rows > 0:
                    flash(f'Đã bỏ qua {missing_data_rows} dòng do thiếu Tên hoặc Serial.', 'info')

                return redirect(url_for('admin.upload_devices'))

            except Exception as e:
                db.session.rollback()
                flash(f'Đã xảy ra lỗi khi xử lý file: {e}', 'error')
                return redirect(request.url)
        else:
            flash('Định dạng file không hợp lệ. Vui lòng chỉ upload file .xlsx hoặc .xls.', 'error')
            return redirect(request.url)
            
    # --- Trang GET ---
    return render_template('admin_upload.html')