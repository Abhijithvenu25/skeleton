import os
from fastapi import APIRouter, BackgroundTasks, Form, File, UploadFile, status
from pydantic import EmailStr
from app.schemas.common import MessageResponse
from app.services.email import send_email_task

router = APIRouter(prefix="/notifications", tags=["notifications"])

# Path to the email base template
TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "templates", "email_base.html")

@router.post(
    "/email",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Send an email notification",
)
async def send_email_notification(
    background_tasks: BackgroundTasks,
    to_email: EmailStr = Form(...),
    subject: str = Form(...),
    message: str = Form(...),
    attachments: list[UploadFile] | None = File(None),
) -> MessageResponse:
    """
    Triggers a background task to send an email. 
    Accepts Form data to allow multiple file attachments alongside text.
    """
    
    # 1. Load HTML template and inject variables
    body_html = message
    if os.path.exists(TEMPLATE_PATH):
        with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
            template_content = f.read()
            # Basic string replacement
            body_html = template_content.replace("{subject}", subject).replace("{body}", message)
    
    # 2. Read attachments into memory safely before background task executes
    attachment_data: list[tuple[str, str, bytes]] = []
    if attachments:
        for file in attachments:
            if file.filename: # Only process valid files
                content = await file.read()
                attachment_data.append((
                    file.filename,
                    file.content_type or "application/octet-stream",
                    content
                ))
    
    # 3. Schedule the background task
    background_tasks.add_task(
        send_email_task,
        to_email=to_email,
        subject=subject,
        body_html=body_html,
        attachments=attachment_data
    )
    
    return MessageResponse(message="Email queued for delivery.")
