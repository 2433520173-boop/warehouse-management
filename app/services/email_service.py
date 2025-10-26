# app/services/email_service.py

import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
# --- THÊM IMPORT ---
from flask import url_for, render_template
# --- THÊM MỚI: Import model Transaction để lấy thời gian ---
from ..models import Transaction 

def send_email(to_email, subject, html_content):
    """Hàm gửi mail chung sử dụng SendGrid."""

    sendgrid_api_key = os.environ.get('SENDGRID_API_KEY')
    from_email = os.environ.get('EMAIL_USER') # Vẫn dùng email của bạn làm email người gửi

    if not sendgrid_api_key or not from_email:
        print("Lỗi: SENDGRID_API_KEY hoặc EMAIL_USER chưa được thiết lập.")
        return False # Trả về False nếu lỗi cấu hình

    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject=subject,
        html_content=html_content
    )
    try:
        sg = SendGridAPIClient(sendgrid_api_key)
        response = sg.send(message)
        print(f"Email đã được gửi tới {to_email}, status code: {response.status_code}")
        return response.status_code in [200, 202] # Trả về True nếu gửi thành công (status 200 hoặc 202)
    except Exception as e:
        print(f"Lỗi khi gửi email tới {to_email}: {e}")
        return False # Trả về False nếu có lỗi xảy ra

# Các hàm cụ thể vẫn giữ nguyên, chỉ gọi hàm send_email mới
def send_transaction_email(user, device, transaction_type):
    last_transaction = Transaction.query.filter_by(device_id=device.id).order_by(Transaction.created_at.desc()).first()
    transaction_time_str = last_transaction.created_at.strftime('%H:%M %d-%m-%Y') if last_transaction else "N/A"

    subject = f"Thông báo {transaction_type} thiết bị: {device.name}"
    html_content = f"""
    <h3>Xin chào {user.full_name or user.username},</h3>
    <p>Hệ thống ghi nhận bạn đã <strong>{transaction_type}</strong> thiết bị sau:</p>
    <ul>
        <li><strong>Tên thiết bị:</strong> {device.name}</li>
        <li><strong>Serial:</strong> {device.serial}</li>
        <li><strong>Thời gian:</strong> {transaction_type} lúc {transaction_time_str}</li>
    </ul>
    <p>Cảm ơn bạn đã sử dụng hệ thống.</p>
    """
    admin_email = os.environ.get('HOST_EMAIL')
    if admin_email:
        send_email(admin_email, subject, html_content)
    send_email(user.email, subject, html_content)


def send_batch_transaction_email(user, transactions, transaction_type):
    device_list_html = "".join([f"<li>{t.device.name} ({t.device.serial})</li>" for t in transactions])
    subject = f"Thông báo {transaction_type} hàng loạt thiết bị"
    html_content = f"""
    <h3>Xin chào {user.full_name or user.username},</h3>
    <p>Hệ thống ghi nhận bạn đã <strong>{transaction_type}</strong> các thiết bị sau:</p>
    <ul>
        {device_list_html}
    </ul>
    <p>Cảm ơn bạn đã sử dụng hệ thống.</p>
    """
    admin_email = os.environ.get('HOST_EMAIL')
    if admin_email:
        send_email(admin_email, subject, html_content)
    send_email(user.email, subject, html_content)

# --- HÀM MỚI CHO QUÊN MẬT KHẨU ---
def send_password_reset_email(user, token):
    """Gửi email chứa link đặt lại mật khẩu."""
    subject = "[Kho VAA] Yêu cầu đặt lại mật khẩu"
    reset_url = url_for('main.reset_password', token=token, _external=True)
    html_content = render_template('email/reset_password.html', user=user, reset_url=reset_url)
    send_email(user.email, subject, html_content)

# --- THÊM MỚI: HÀM GỬI EMAIL THÔNG BÁO "SẴN SÀNG" ---
def send_request_ready_email(borrow_list):
    """Gửi email thông báo yêu cầu đã sẵn sàng cho sinh viên."""
    if not borrow_list or not borrow_list.user:
        print("Lỗi: Không thể gửi email 'Sẵn sàng' do thiếu thông tin.")
        return False

    user = borrow_list.user
    subject = f"[Kho VAA] Yêu cầu mượn #{borrow_list.id} đã sẵn sàng"

    # Render nội dung email từ template mới
    html_content = render_template('email/request_ready.html',
                                   user=user,
                                   borrow_list=borrow_list,
                                   items=borrow_list.items.all()) # Truyền danh sách items vào template

    print(f"Đang chuẩn bị gửi email 'Sẵn sàng' cho {user.email}...")
    return send_email(user.email, subject, html_content)