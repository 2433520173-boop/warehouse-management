from flask import Blueprint, render_template, request
from flask_login import login_required
from .. import admin_required
from ..models import User, Device, Transaction
from sqlalchemy import desc

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    stats = {
        'users': User.query.count(), 
        'devices': Device.query.count(), 
        'transactions': Transaction.query.count()
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

# --- PHẦN MỚI ĐƯỢC THÊM VÀO ---
@admin_bp.route('/user/<int:user_id>')
@login_required
@admin_required
def user_detail(user_id):
    """
    Route để xem thông tin chi tiết của một người dùng
    và lịch sử giao dịch của họ.
    """
    user = User.query.get_or_404(user_id)
    transactions = Transaction.query.filter_by(user_id=user.id).order_by(Transaction.created_at.desc()).all()
    return render_template('admin/user_detail.html', user=user, transactions=transactions)