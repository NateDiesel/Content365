import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
import base64

def send_pdf_email(to_email, pdf_path, topic="AI Content Pack"):
    print(f"📧 Sending email to {to_email} with PDF: {pdf_path}")

    with open(pdf_path, "rb") as f:
        data = f.read()

    encoded_file = base64.b64encode(data).decode()

    message = Mail(
        from_email=os.getenv("SENDGRID_SENDER", "noreply@yourdomain.com"),
        to_emails=to_email,
        subject=f"Your AI Content Pack on {topic}",
        html_content=f"""
        <p>Hi there,</p>
        <p>Your content pack for <strong>{topic}</strong> is ready. Please find it attached.</p>
        <p>Thanks for using our service!</p>
        <p><em>ResumePilot.ai</em></p>
        """
    )

    attachment = Attachment()
    attachment.file_content = FileContent(encoded_file)
    attachment.file_type = FileType("application/pdf")
    attachment.file_name = FileName(os.path.basename(pdf_path))
    attachment.disposition = Disposition("attachment")
    message.attachment = attachment

    try:
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        response = sg.send(message)
        print(f"✅ Email sent! Status code: {response.status_code}")
        return True
    except Exception as e:
        print("❌ SendGrid error:", str(e))
        return False
