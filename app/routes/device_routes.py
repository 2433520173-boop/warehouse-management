from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, Response
from flask_login import login_required, current_user
from ..models import db, Device, Transaction, User, BorrowSlip
from ..services.email_service import send_transaction_email, send_batch_transaction_email
from sqlalchemy import or_, desc
from werkzeug.utils import secure_filename
import os, uuid, csv
from io import StringIO
from .. import admin_required

# --- KHỞI TẠO BLUEPRINT ---
device_bp = Blueprint('device', __name__)

def allowed_file(filename):
    """Kiểm tra file có phần mở rộng hợp lệ không."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

# --- CÁC ROUTE CHÍNH VỀ THIẾT BỊ ---

@device_bp.route('/devices')
@login_required
def devices():
    """Hiển thị danh sách thiết bị với chức năng tìm kiếm nâng cao."""
    query_string = request.args.get('query', '').strip()
    devices_query = Device.query

    if query_string:
        normalized_query = query_string.replace(',', '\n')
        search_terms = [term.strip().upper() for term in normalized_query.splitlines() if term.strip()]
        
        if search_terms:
            if len(search_terms) == 1:
                search_term_single = f"%{search_terms[0]}%"
                devices_query = devices_query.filter(or_(Device.name.ilike(search_term_single), Device.serial.ilike(search_term_single)))
            else:
                devices_query = devices_query.filter(Device.serial.in_(search_terms))

    devices_list = devices_query.order_by(Device.name).all()
    return render_template('devices.html', devices=devices_list, query=query_string)

@device_bp.route('/device/<int:device_id>')
@login_required
def device_detail(device_id):
    """Hiển thị trang chi tiết của một thiết bị."""
    device = Device.query.get_or_404(device_id)
    transactions = Transaction.query.filter_by(device_id=device_id).order_by(desc(Transaction.created_at)).all()
    return render_template('device_detail.html', device=device, transactions=transactions)

# --- CÁC ROUTE QUẢN LÝ (YÊU CẦU ADMIN) ---

@device_bp.route('/add-device', methods=['GET', 'POST'])
@login_required
@admin_required
def add_device():
    """Thêm một hoặc nhiều thiết bị mới."""
    if request.method == 'POST':
        name, serials_input = request.form['name'].strip(), request.form['serials'].strip()
        if not name or not serials_input:
            flash('Tên thiết bị và Serial không được để trống!', 'error'); return render_template('add_device.html', form=request.form)

        serials = [s.strip().upper() for s in serials_input.splitlines() if s.strip()]
        image_filename = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                unique_filename = str(uuid.uuid4()) + "_" + secure_filename(file.filename)
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)); image_filename = unique_filename
        
        added_count, error_serials = 0, []
        for serial in serials:
            if Device.query.filter_by(serial=serial).first(): error_serials.append(serial); continue
            new_device = Device(name=name, serial=serial, category=request.form.get('category'), description=request.form.get('description'),
                                location=request.form.get('location'), image_url=image_filename, created_by_id=current_user.id)
            db.session.add(new_device); added_count += 1
        
        if error_serials: flash(f'Các serial sau đã tồn tại: {", ".join(error_serials)}', 'warning')
        if added_count > 0:
            db.session.commit(); flash(f'Đã thêm thành công {added_count} thiết bị!', 'success'); return redirect(url_for('device.devices'))
        flash('Không có thiết bị nào được thêm.', 'info')
    return render_template('add_device.html')

@device_bp.route('/edit-device/<int:device_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_device(device_id):
    """Chỉnh sửa thông tin một thiết bị."""
    device = Device.query.get_or_404(device_id)
    if request.method == 'POST':
        device.name, device.serial, device.category, device.description, device.location, device.status = \
            request.form['name'], request.form['serial'], request.form['category'], request.form['description'], request.form['location'], request.form['status']
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                if device.image_url:
                    old_path = os.path.join(current_app.config['UPLOAD_FOLDER'], device.image_url)
                    if os.path.exists(old_path): os.remove(old_path)
                unique_filename = str(uuid.uuid4()) + "_" + secure_filename(file.filename)
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)); device.image_url = unique_filename
        db.session.commit(); flash('Cập nhật thiết bị thành công!', 'success')
        return redirect(url_for('device.device_detail', device_id=device.id))
    return render_template('edit_device.html', device=device)

@device_bp.route('/delete-device/<int:device_id>', methods=['POST'])
@login_required
@admin_required
def delete_device(device_id):
    """Xóa một thiết bị."""
    device = Device.query.get_or_404(device_id)
    if device.image_url:
        image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], device.image_url)
        if os.path.exists(image_path): os.remove(image_path)
    db.session.delete(device); db.session.commit()
    flash('Đã xóa thiết bị thành công!', 'success')
    return redirect(url_for('device.devices'))

# --- CÁC ROUTE GIAO DỊCH (MƯỢN/TRẢ) ---

@device_bp.route('/borrow/<int:device_id>', methods=['POST'])
@login_required
def borrow_device(device_id):
    """Mượn một thiết bị duy nhất."""
    device = Device.query.get_or_404(device_id)
    if device.status == 'available':
        device.status = 'borrowed'
        transaction = Transaction(device_id=device.id, user_id=current_user.id, transaction_type='borrow', notes=request.form.get('notes'))
        db.session.add(transaction); db.session.commit()
        send_transaction_email(transaction, current_user, device)
        flash(f'Bạn đã mượn "{device.name}" thành công!', 'success')
    else: flash('Thiết bị này không có sẵn để mượn.', 'error')
    return redirect(url_for('device.device_detail', device_id=device_id))

@device_bp.route('/return/<int:device_id>', methods=['POST'])
@login_required
def return_device(device_id):
    """Trả một thiết bị duy nhất."""
    device = Device.query.get_or_404(device_id)
    if device.status == 'borrowed':
        device.status = 'available'
        transaction = Transaction(device_id=device.id, user_id=current_user.id, transaction_type='return', notes=request.form.get('notes'))
        db.session.add(transaction); db.session.commit()
        send_transaction_email(transaction, current_user, device)
        flash(f'Bạn đã trả "{device.name}" thành công!', 'success')
    else: flash('Thiết bị này không ở trạng thái đang được mượn.', 'error')
    return redirect(url_for('device.device_detail', device_id=device_id))

@device_bp.route('/borrow-multiple', methods=['POST'])
@login_required
def borrow_multiple():
    """Mượn nhiều thiết bị cùng lúc, tạo ra một Phiếu mượn."""
    device_ids = request.form.getlist('device_ids')
    if not device_ids: flash('Bạn chưa chọn thiết bị nào để mượn.', 'info'); return redirect(url_for('device.devices'))

    successful_transactions, error_devices = [], []
    new_slip = BorrowSlip(user_id=current_user.id)
    db.session.add(new_slip); db.session.flush()

    for device_id in device_ids:
        device = Device.query.get(device_id)
        if device and device.status == 'available':
            device.status = 'borrowed'
            transaction = Transaction(device_id=device.id, user_id=current_user.id, transaction_type='borrow', notes=f'Phiếu mượn #{new_slip.id}', borrow_slip_id=new_slip.id)
            db.session.add(transaction); successful_transactions.append(transaction)
        elif device: error_devices.append(device.name)
    
    if successful_transactions:
        db.session.commit(); send_batch_transaction_email(successful_transactions, current_user)
        flash(f'Đã mượn thành công {len(successful_transactions)} thiết bị (Phiếu mượn #{new_slip.id}).', 'success')
    else: db.session.rollback(); flash('Không có thiết bị nào được mượn.', 'error')

    if error_devices: flash(f'Không thể mượn các thiết bị sau: {", ".join(error_devices)}', 'error')
    return redirect(url_for('device.devices'))

@device_bp.route('/return-multiple', methods=['POST'])
@login_required
def return_multiple():
    """Trả nhiều thiết bị được chọn tự do."""
    device_ids = request.form.getlist('device_ids')
    if not device_ids: flash('Bạn chưa chọn thiết bị nào để trả.', 'info'); return redirect(url_for('device.devices'))

    successful_transactions, error_devices = [], []
    for device_id in device_ids:
        device = Device.query.get(device_id)
        if device and device.status == 'borrowed':
            last_borrow = Transaction.query.filter_by(device_id=device.id, transaction_type='borrow').order_by(desc(Transaction.created_at)).first()
            if current_user.is_admin or (last_borrow and last_borrow.user_id == current_user.id):
                device.status = 'available'
                transaction = Transaction(device_id=device.id, user_id=current_user.id, transaction_type='return', notes='Trả nhiều mục')
                db.session.add(transaction); successful_transactions.append(transaction)
            else: error_devices.append(f"{device.name} (không có quyền trả)")
        elif device: error_devices.append(f"{device.name} (trạng thái không hợp lệ)")
    
    if successful_transactions:
        db.session.commit(); send_batch_transaction_email(successful_transactions, current_user)
        flash(f'Đã trả thành công {len(successful_transactions)} thiết bị.', 'success')

    if error_devices: flash(f'Không thể trả các thiết bị sau: {", ".join(error_devices)}', 'error')
    return redirect(url_for('device.devices'))

@device_bp.route('/return-slip/<int:slip_id>', methods=['POST'])
@login_required
def return_slip(slip_id):
    """Trả toàn bộ thiết bị theo một Phiếu mượn."""
    slip = BorrowSlip.query.get_or_404(slip_id)
    if slip.user_id != current_user.id and not current_user.is_admin:
        flash('Bạn không có quyền trả phiếu mượn này.', 'error'); return redirect(url_for('main.my_borrows'))
    if not slip.is_active:
        flash('Phiếu này đã được trả trước đó.', 'info'); return redirect(url_for('main.my_borrows'))

    devices_to_return = [trans.device for trans in slip.transactions if trans.transaction_type == 'borrow']
    successful_transactions = []
    for device in devices_to_return:
        device.status = 'available'
        transaction = Transaction(device_id=device.id, user_id=current_user.id, transaction_type='return', notes=f'Trả theo phiếu mượn #{slip.id}', borrow_slip_id=slip.id)
        db.session.add(transaction); successful_transactions.append(transaction)

    slip.is_active = False; db.session.commit()
    send_batch_transaction_email(successful_transactions, current_user)
    flash(f'Đã trả thành công {len(successful_transactions)} thiết bị từ phiếu mượn #{slip.id}.', 'success')
    return redirect(url_for('main.my_borrows'))

# --- EXPORT ---

@device_bp.route('/export/devices.csv')
@login_required
@admin_required
def export_devices_csv():
    """Xuất danh sách thiết bị ra file CSV."""
    si = StringIO(); cw = csv.writer(si)
    headers = ['ID', 'Name', 'Serial', 'Category', 'Status', 'Location', 'Created At']
    cw.writerow(headers)
    for device in Device.query.all():
        cw.writerow([device.id, device.name, device.serial, device.category, device.status, device.location, device.created_at.strftime('%Y-%m-%d')])
    return Response(si.getvalue(), mimetype="text/csv", headers={"Content-disposition": "attachment; filename=devices_export.csv"})