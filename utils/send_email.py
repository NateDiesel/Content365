# utils/send_email.py
import os
from typing import Optional

def send_pdf_email(to_email: str, pdf_path: str, subject: str, body_text: Optional[str] = None) -> bool:
    """
    Sends the generated PDF as an attachment via SendGrid.
    Returns True on success, False on failure or if config missing.
    """
    api_key = os.getenv("SENDGRID_API_KEY", "").strip()
    from_email = os.getenv("FROM_EMAIL", "").strip()
    from_name = os.getenv("FROM_NAME", "Content365").strip()

    if not (api_key and from_email and to_email and pdf_path and os.path.exists(pdf_path)):
        return False

    try:
        import base64
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail, Email, To, Attachment, FileContent, FileName, FileType, Disposition

        with open(pdf_path, "rb") as f:
            data = f.read()
        encoded = base64.b64encode(data).decode()

        attachment = Attachment(
            FileContent(encoded),
            FileName(os.path.basename(pdf_path)),
            FileType("application/pdf"),
            Disposition("attachment"),
        )

        subject_line = subject or "Your Content365 Marketing Pack"
        body = body_text or (
            "Thanks for using Content365!\n\n"
            "Your marketing content pack PDF is attached.\n\n"
            "â€” The Content365 Team"
        )
        message = Mail(
            from_email=Email(from_email, from_name),
            to_emails=To(to_email),
            subject=subject_line,
            plain_text_content=body
        )
        message.attachment = attachment

        sg = SendGridAPIClient(api_key)
        resp = sg.send(message)
        return resp.status_code < 300
    except Exception:
        return False
