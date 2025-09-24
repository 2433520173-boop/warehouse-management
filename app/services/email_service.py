from flask import current_app, render_template
from flask_mail import Message
from weasyprint import HTML
from threading import Thread
from .. import mail

def send_async_email(app, msg):
    with app.app_context():
        try:
            mail.send(msg)
        except Exception as e:
            app.logger.error(f"Failed to send email: {e}")

def send_transaction_email(transaction, user, device):
    app = current_app._get_current_object()
    host_email = app.config.get('HOST_EMAIL')
    if not host_email:
        app.logger.warning("HOST_EMAIL is not configured. Cannot send transaction email.")
        return

    try:
        html = render_template('pdf_template.html', transaction=transaction, user=user, device=device)
        pdf = HTML(string=html).write_pdf()
        
        transaction_type_vn = "Mượn" if transaction.transaction_type == 'borrow' else "Trả"
        subject = f"Thông báo {transaction_type_vn} thiết bị - {device.name} (SN: {device.serial})"
        
        msg = Message(subject, recipients=[host_email])
        msg.body = f"Xem chi tiết trong file PDF đính kèm về giao dịch của {user.full_name}."
        msg.attach(f"phieu_{transaction.transaction_type}_{device.serial}.pdf", "application/pdf", pdf)
        
        Thread(target=send_async_email, args=[app, msg]).start()
    except Exception as e:
        app.logger.error(f"Error creating or sending transaction email: {e}")
# (Thêm hàm này vào cuối file app/services/email_service.py)

def send_batch_transaction_email(transactions, user):
    """Gửi một email duy nhất cho một loạt giao dịch."""
    if not transactions:
        return

    app = current_app._get_current_object()
    host_email = app.config.get('HOST_EMAIL')
    if not host_email:
        app.logger.warning("HOST_EMAIL is not configured.")
        return

    try:
        # Xác định loại giao dịch (mượn hay trả)
        transaction_type = transactions[0].transaction_type
        transaction_type_vn = "Mượn" if transaction_type == 'borrow' else "Trả"

        # Render HTML từ template mới
        html = render_template(
            'pdf_batch_template.html', 
            transactions=transactions, 
            user=user, 
            type=transaction_type
        )
        pdf = HTML(string=html).write_pdf()

        subject = f"Thông báo {transaction_type_vn} hàng loạt - {len(transactions)} thiết bị"

        msg = Message(subject, recipients=[host_email])
        msg.body = f"Xin chào Quản trị viên,\n\n{user.full_name} vừa thực hiện giao dịch {transaction_type_vn} hàng loạt với {len(transactions)} thiết bị. Chi tiết được đính kèm trong file PDF."

        msg.attach(
            f"phieu_{transaction_type}_hang_loat.pdf",
            "application/pdf",
            pdf
        )

        Thread(target=send_async_email, args=[app, msg]).start()
    except Exception as e:
        app.logger.error(f"Error creating or sending batch transaction email: {e}")