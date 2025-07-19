import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
import base64

def send_pdf_email(recipient_email, file_path, topic="AI Content Pack"):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        encoded_file = base64.b64encode(data).decode()

        message = Mail(
            from_email=os.getenv("EMAIL_FROM"),
            to_emails=recipient_email,
            subject=os.getenv("EMAIL_SUBJECT", "Your Content Pack is Ready!"),
            html_content=f"<p>Your AI Content Pack on <strong>{topic}</strong> is attached.</p>"
        )
        attached_file = Attachment(
            FileContent(encoded_file),
            FileName(os.path.basename(file_path)),
            FileType("application/pdf"),
            Disposition("attachment")
        )
        message.attachment = attached_file

        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        sg.send(message)
        print(f"📧 Sent to {recipient_email}")
    except Exception as e:
        print("❌ Email send failed:", e)
