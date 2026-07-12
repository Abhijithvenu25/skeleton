from datetime import datetime
import uuid
from pydantic import BaseModel, ConfigDict
from app.models.enums import EnquiryAuditAction

class EnquiryAuditLogOut(BaseModel):
    id: uuid.UUID
    enquiry_id: uuid.UUID
    action: EnquiryAuditAction
    action_date: datetime
    description: str | None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
