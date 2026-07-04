from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import EnquirySource, EnquiryPriority, EnquiryStatus

class EnquiryOut(BaseModel):
    id: uuid.UUID
    enquiry_number: str
    enquiry_date: date
    enquiry_source: EnquirySource | None
    priority: EnquiryPriority
    status: EnquiryStatus
    description: str | None
    remarks: str | None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class AddressOut(BaseModel):
    company_address: str | None = None
    company_city: str | None = None
    company_state: str | None = None
    company_country: str | None = None
    company_pincode: str | None = None

class ProjectDetailsOut(BaseModel):
    project_name: str | None = None
    project_type: str | None = None
    project_location: str | None = None
    estimated_budget: float | None = None
    expected_start_date: date | None = None
    source: EnquirySource | None = None
    priority: EnquiryPriority | None = None
    sales_executive: str | None = None

class DescriptionOut(BaseModel):
    project_description: str | None = None
    remarks: str | None = None

class AttachmentFile(BaseModel):
    id: uuid.UUID
    url: str

class AttachmentsOut(BaseModel):
    boq: list[AttachmentFile] = []
    drawings: list[AttachmentFile] = []
    photos: list[AttachmentFile] = []
    tender_documents: list[AttachmentFile] = []
    other_files: list[AttachmentFile] = []

class EnquiryDetailOut(BaseModel):
    id: uuid.UUID
    enquiry_number: str
    enquiry_date: date
    status: EnquiryStatus
    company_name: str
    company_website: str | None = None
    contact_person: str | None = None
    designation: str | None = None
    mobile: str | None = None
    alternate_mobile: str | None = None
    email: str | None = None
    address: AddressOut
    project_details: ProjectDetailsOut
    description: DescriptionOut
    attachments: AttachmentsOut

    model_config = ConfigDict(from_attributes=True)
