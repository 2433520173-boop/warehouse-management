import pandas as pd
# --- THÊM MỚI: Import datetime ---
from datetime import datetime, timedelta, date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .. import admin_required
# Import tất cả model và db
from ..models import db, User, Device, Transaction, BorrowList, ListItem
# --- THÊM MỚI: Import hàm gửi email thông báo sẵn sàng ---
from ..services.email_service import send_request_ready_email # Đảm bảo import dòng này
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
        'pending_requests': BorrowList.query.filter_by(status='Submitted').count(),
        'overdue_count': BorrowList.query.filter(
            BorrowList.status == 'Completed',
            BorrowList.returned_at == None,
            BorrowList.return_deadline < date.today()
        ).count()
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
        try:
            db.session.commit() # Lưu thay đổi trạng thái trước
            flash(f'Đã đánh dấu phiếu #{list_id} là Sẵn sàng.', 'success')

            # --- Gửi email thông báo ---
            # Gọi hàm gửi email SAU KHI commit thành công
            email_sent = send_request_ready_email(borrow_list) # Gọi hàm đã import
            if email_sent:
                flash(f'Đã gửi email thông báo cho sinh viên {borrow_list.user.email}.', 'info')
            else:
                # Lỗi gửi email không làm ảnh hưởng đến việc đổi status
                flash(f'LỖI khi gửi email thông báo cho sinh viên {borrow_list.user.email}. Vui lòng kiểm tra log hoặc cấu hình SendGrid.', 'danger')
            # --- (Kết thúc gửi email) ---

        except Exception as e:
            db.session.rollback() # Hoàn tác nếu có lỗi commit
            flash(f'Lỗi khi cập nhật trạng thái hoặc gửi email: {e}', 'danger')

    else:
        flash('Yêu cầu này không ở trạng thái "Submitted".', 'warning')

    # Luôn chuyển hướng về trang chi tiết
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
    current_time = datetime.utcnow()
    for item in borrow_list.items:
        device = item.device
        if device and device.status == 'Reserved': # Kiểm tra device tồn tại
            device.status = 'Borrowed'; device.borrower_id = borrow_list.user_id
            transaction = Transaction(device_id=device.id, user_id=borrow_list.user_id, transaction_type='Mượn', notes=f'Mượn theo yêu cầu #{borrow_list.id}', created_at=current_time)
            db.session.add(transaction); successful_transactions.append(transaction)
        elif device: # Nếu device tồn tại nhưng không phải Reserved
             flash(f'Cảnh báo: Thiết bị "{device.name}" (Serial: {device.serial}) không ở trạng thái "Reserved". Bỏ qua.', 'warning')
        # Bỏ qua nếu item.device không tồn tại (đã bị xóa?)
    borrow_list.status = 'Completed'; borrow_list.borrowed_at = current_time; borrow_list.return_deadline = (current_time + timedelta(days=30)).date()
    db.session.commit()
    flash(f'Đã hoàn tất giao {len(successful_transactions)} thiết bị cho phiếu #{list_id}. Hạn trả là {borrow_list.return_deadline.strftime("%d-%m-%Y")}.', 'success')
    return redirect(url_for('admin.requests_list'))

@admin_bp.route('/request/<int:list_id>/cancel', methods=['POST'])
@login_required
@admin_required
def cancel_request(list_id):
    borrow_list = BorrowList.query.get_or_404(list_id)
    if borrow_list.status not in ['Submitted', 'Ready']:
        flash('Không thể hủy yêu cầu này.', 'error'); return redirect(url_for('admin.request_detail', list_id=list_id))
    items_released = 0
    for item in borrow_list.items:
        if item.device and item.device.status == 'Reserved':
            item.device.status = 'Available'; items_released += 1
    borrow_list.status = 'Cancelled'
    db.session.commit()
    flash(f'Đã hủy yêu cầu #{list_id}. Đã trả {items_released} thiết bị về kho.', 'success')
    # (TODO: Có thể gửi email thông báo hủy cho sinh viên)
    return redirect(url_for('admin.requests_list'))

# --- ROUTE QUẢN LÝ QUÁ HẠN ---

@admin_bp.route('/overdue')
@login_required
@admin_required
def overdue_list():
    today = date.today()
    overdue_borrow_lists = BorrowList.query.filter(BorrowList.status == 'Completed', BorrowList.returned_at == None, BorrowList.return_deadline < today).order_by(BorrowList.return_deadline.asc()).all()
    return render_template('admin_overdue.html', overdue_lists=overdue_borrow_lists, today=today)

@admin_bp.route('/mark_returned/<int:list_id>', methods=['POST'])
@login_required
@admin_required
def mark_as_returned(list_id):
    borrow_list = BorrowList.query.get_or_404(list_id)
    if borrow_list.status != 'Completed':
        flash('Phiếu này chưa hoàn tất giao đồ.', 'error'); return redirect(request.referrer or url_for('admin.overdue_list'))
    if borrow_list.returned_at is not None:
        flash('Phiếu này đã được trả.', 'info'); return redirect(request.referrer or url_for('admin.overdue_list'))
    returned_time = datetime.utcnow(); successful_returns = 0; errors = []
    for item in borrow_list.items:
        device = item.device
        if device:
            if device.status == 'Borrowed' and device.borrower_id == borrow_list.user_id:
                device.status = 'Available'; device.borrower_id = None
                return_transaction = Transaction(device_id=device.id, user_id=current_user.id, transaction_type='Trả', notes=f'Trả theo phiếu #{borrow_list.id} bởi admin {current_user.username}', created_at=returned_time)
                db.session.add(return_transaction); successful_returns += 1
            elif device.status != 'Borrowed' and device.borrower_id == borrow_list.user_id:
                 errors.append(f'Thiết bị "{device.name}" ({device.serial}) không ở trạng thái "Borrowed".')
            # Bỏ qua nếu borrower_id không khớp (có thể đã được admin khác xử lý?)
        else: errors.append(f'Thiết bị trong phiếu không tồn tại.')
    borrow_list.returned_at = returned_time
    try:
        db.session.commit()
        flash(f'Đã ghi nhận trả {successful_returns} thiết bị cho phiếu #{list_id}.', 'success')
        if errors:
            for error in errors: flash(error, 'warning')
    except Exception as e:
         db.session.rollback()
         flash(f'Lỗi khi ghi nhận trả: {e}', 'danger')

    return redirect(request.referrer or url_for('admin.overdue_list'))

# --- ROUTE UPLOAD EXCEL ---
@admin_bp.route('/upload-devices', methods=['GET', 'POST'])
@login_required
@admin_required
def upload_devices():
    if request.method == 'POST':
        if 'file' not in request.files: flash('Không tìm thấy file.', 'error'); return redirect(request.url)
        file = request.files['file'];
        if file.filename == '': flash('Không có file nào được chọn.', 'info'); return redirect(request.url)
        if file and (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
            try:
                # Đọc file và kiểm tra cột bắt buộc
                df = pd.read_excel(file, engine='openpyxl')
                required_columns = ['name', 'serial']
                df_columns_lower = [str(c).lower() for c in df.columns]
                if not all(col.lower() in df_columns_lower for col in required_columns):
                    flash(f'File Excel phải có các cột bắt buộc: {", ".join(required_columns)}', 'error'); return redirect(request.url)
                df.columns = df_columns_lower # Chuẩn hóa tên cột

                added_count, error_serials, missing_data_rows = 0, [], 0
                processed_serials_in_file = set() # Kiểm tra trùng trong file

                for index, row in df.iterrows():
                    # Lấy và làm sạch dữ liệu
                    name = str(row.get('name', '')).strip()
                    serial_raw = row.get('serial')
                    serial = str(serial_raw).strip().upper() if not pd.isna(serial_raw) else None

                    if not name or not serial: missing_data_rows += 1; continue # Bỏ qua nếu thiếu

                    # Kiểm tra trùng lặp
                    if serial in processed_serials_in_file:
                        error_serials.append(f"{serial} (trùng trong file)"); continue
                    processed_serials_in_file.add(serial)
                    if Device.query.filter_by(serial=serial).first():
                        error_serials.append(f"{serial} (đã có trong CSDL)"); continue

                    # Lấy và chuẩn hóa dữ liệu tùy chọn
                    category = str(row.get('category', 'Other')).strip(); description = str(row.get('description', '')).strip(); location = str(row.get('location', 'Kho chính')).strip(); unit = str(row.get('unit', 'Cái')).strip()
                    category = 'Other' if pd.isna(row.get('category')) or not category else category
                    description = '' if pd.isna(row.get('description')) else description
                    location = 'Kho chính' if pd.isna(row.get('location')) or not location else location
                    unit = 'Cái' if pd.isna(row.get('unit')) or not unit else unit

                    # Tạo đối tượng Device
                    new_device = Device(name=name, serial=serial, category=category, description=description, location=location, unit=unit, created_by_id=current_user.id, status='Available')
                    db.session.add(new_device); added_count += 1

                # Lưu vào CSDL
                db.session.commit()

                # Flash thông báo kết quả
                if added_count > 0: flash(f'Đã thêm thành công {added_count} thiết bị mới.', 'success')
                if not error_serials and not missing_data_rows and added_count == 0: flash('Không có thiết bị nào được thêm (file rỗng hoặc chỉ chứa serial đã tồn tại/trùng lặp).', 'info')
                if error_serials: flash(f'Các serial sau bị lỗi hoặc đã tồn tại và bị bỏ qua: {", ".join(error_serials)}', 'warning')
                if missing_data_rows > 0: flash(f'Đã bỏ qua {missing_data_rows} dòng do thiếu Tên hoặc Serial.', 'info')

                return redirect(url_for('admin.upload_devices'))
            except Exception as e:
                db.session.rollback(); flash(f'Đã xảy ra lỗi nghiêm trọng khi xử lý file: {e}. Đã hoàn tác mọi thay đổi.', 'danger'); return redirect(request.url)
        else: flash('Định dạng file không hợp lệ. Vui lòng chỉ upload file .xlsx hoặc .xls.', 'error'); return redirect(request.url)
    return render_template('admin_upload.html')