# app/services/email_service.py

import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def send_email(to_email, subject, html_content):
    """Hàm gửi mail chung sử dụng SendGrid."""
    
    # Lấy API Key và email người gửi từ biến môi trường
    sendgrid_api_key = os.environ.get('SENDGRID_API_KEY')
    from_email = os.environ.get('EMAIL_USER') # Vẫn dùng email của bạn làm email người gửi

    if not sendgrid_api_key or not from_email:
        print("Lỗi: SENDGRID_API_KEY hoặc EMAIL_USER chưa được thiết lập.")
        return

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
    except Exception as e:
        print(f"Lỗi khi gửi email: {e}")

# Các hàm cụ thể vẫn giữ nguyên, chỉ gọi hàm send_email mới
def send_transaction_email(user, device, transaction_type):
    subject = f"Thông báo mượn/trả thiết bị: {device.name}"
    html_content = f"""
    <h3>Xin chào {user.full_name},</h3>
    <p>Hệ thống ghi nhận bạn đã <strong>{transaction_type}</strong> thiết bị sau:</p>
    <ul>
        <li><strong>Tên thiết bị:</strong> {device.name}</li>
        <li><strong>Serial:</strong> {device.serial}</li>
        <li><strong>Thời gian:</strong> {transaction_type} lúc {device.last_transaction_time.strftime('%H:%M %d-%m-%Y')}</li>
    </ul>
    <p>Cảm ơn bạn đã sử dụng hệ thống.</p>
    """
    admin_email = os.environ.get('HOST_EMAIL')
    # Gửi cho cả admin và người dùng
    if admin_email:
        send_email(admin_email, subject, html_content)
    send_email(user.email, subject, html_content)


def send_batch_transaction_email(user, devices, transaction_type):
    device_list_html = "".join([f"<li>{d.name} ({d.serial})</li>" for d in devices])
    subject = f"Thông báo {transaction_type} hàng loạt thiết bị"
    html_content = f"""
    <h3>Xin chào {user.full_name},</h3>
    <p>Hệ thống ghi nhận bạn đã <strong>{transaction_type}</strong> các thiết bị sau:</p>
    <ul>
        {device_list_html}
    </ul>
    <p>Cảm ơn bạn đã sử dụng hệ thống.</p>
    """
    admin_email = os.environ.get('HOST_EMAIL')
    # Gửi cho cả admin và người dùng
    if admin_email:
        send_email(admin_email, subject, html_content)
    send_email(user.email, subject, html_content)