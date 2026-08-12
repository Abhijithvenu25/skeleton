import smtplib
import structlog
from email.message import EmailMessage
from app.core.config import settings

logger = structlog.get_logger(__name__)

def send_email_task(
    to_email: str | list[str], 
    subject: str, 
    body_html: str, 
    attachments: list[tuple[str, str, bytes]] | None = None
) -> None:
    """
    Background task to send an email using SMTP.
    attachments: list of tuples (filename, content_type, file_bytes)
    """
    if not settings.smtp_host or not settings.smtp_user or not settings.smtp_password:
        logger.error("SMTP credentials or host not configured. Skipping email send.")
        return

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = settings.smtp_from_email or settings.smtp_user
    
    if isinstance(to_email, list):
        msg['To'] = ", ".join(to_email)
    else:
        msg['To'] = to_email

    msg.set_content("Please enable HTML to view this email.")
    msg.add_alternative(body_html, subtype='html')

    if attachments:
        for filename, content_type, file_bytes in attachments:
            maintype, _, subtype = content_type.partition('/')
            msg.add_attachment(
                file_bytes, 
                maintype=maintype, 
                subtype=subtype, 
                filename=filename
            )

    try:
        # Use STARTTLS on the configured port (default 587)
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        logger.info("Email sent successfully", to=to_email, subject=subject)
    except Exception as e:
        logger.error("Failed to send email", error=str(e), to=to_email, subject=subject)
