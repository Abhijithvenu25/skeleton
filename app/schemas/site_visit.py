from pydantic import BaseModel, ConfigDict
import uuid
from datetime import datetime
from app.models.enums import SiteVisitStatus
from app.schemas.enquiry import AttachmentFile

class SiteVisitAttachmentsOut(BaseModel):
    photos: list[AttachmentFile] = []
    videos: list[AttachmentFile] = []
    drawings: list[AttachmentFile] = []
    measurement_sheets: list[AttachmentFile] = []

class SiteVisitOut(BaseModel):
    id: uuid.UUID
    visit_number: str
    visit_count: int
    enquiry_id: uuid.UUID
    company_id: uuid.UUID
    engineer: str | None = None
    sales_executive: str | None = None
    visit_date: datetime
    status: SiteVisitStatus
    client_representative: str | None = None
    client_representative_no: str | None = None
    notes: str | None = None
    requirements: str | None = None
    measurements: str | None = None
    existing_conditions: str | None = None
    challenges: str | None = None
    recommendation: str | None = None
    attachments: SiteVisitAttachmentsOut

    model_config = ConfigDict(from_attributes=True)
