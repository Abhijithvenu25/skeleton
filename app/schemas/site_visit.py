from pydantic import BaseModel, ConfigDict
import uuid
from datetime import datetime
from app.models.enums import SiteVisitStatus
from app.schemas.enquiry import AttachmentFile

class SiteVisitOut(BaseModel):
    id: uuid.UUID
    visit_number: str
    enquiry_id: uuid.UUID
    company_id: uuid.UUID
    engineer: str | None = None
    sales_executive: str | None = None
    visit_date: datetime
    status: SiteVisitStatus
    notes: str | None = None
    attachments: list[AttachmentFile] = []

    model_config = ConfigDict(from_attributes=True)
