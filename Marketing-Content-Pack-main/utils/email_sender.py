import os
import sendgrid
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
import base64

def send_pdf_email(to_email, pdf_path, subject="Your AI Content Pack", content="Please find your generated content pack attached."):
    sg = sendgrid.SendGridAPIClient(api_key=os.getenv("SENDGRID_API_KEY"))
    from_email = os.getenv("FROM_EMAIL")

    with open(pdf_path, 'rb') as f:
        data = f.read()
        encoded = base64.b64encode(data).decode()

    attachment = Attachment(
        FileContent(encoded),
        FileName("content_pack.pdf"),
        FileType("application/pdf"),
        Disposition("attachment")
    )

    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject=subject,
        html_content=content
    )
    message.attachment = attachment

    try:
        response = sg.send(message)
        print(f"Email sent: {response.status_code}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False
