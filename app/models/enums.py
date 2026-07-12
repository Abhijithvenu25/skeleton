from enum import Enum

class UserRole(str, Enum):
    admin = "admin"
    sales_executive = "sales_executive"
    engineer = "engineer"
    manager = "manager"

class EnquiryStatus(str, Enum):
    enquiry = "enquiry"
    site_visit = "site_visit"
    quotation = "quotation"
    accepted = "accepted"
    lost = "lost"

class EnquiryAuditAction(str, Enum):
    enquiry_created = "enquiry_created"
    site_visit_scheduled = "site_visit_scheduled"
    enquiry_lost = "enquiry_lost"
    enquiry_reinstated = "enquiry_reinstated"

class EnquiryPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"

class EnquirySource(str, Enum):
    email = "email"
    whatsapp = "whatsapp"
    instagram = "instagram"
    facebook = "facebook"
    linkedin = "linkedin"
    website = "website"
    direct_call = "direct_call"
    referral = "referral"
    tender = "tender"
    other = "other"

class SiteVisitStatus(str, Enum):
    scheduled = "scheduled"
    completed = "completed"
    cancelled = "cancelled"

class QuotationStatus(str, Enum):
    draft = "draft"
    sent = "sent"
    accepted = "accepted"
    rejected = "rejected"

class AttachmentDocumentType(str, Enum):
    boq = "BOQ"
    drawings = "Drawings"
    photos = "Photos"
    videos = "Videos"
    measurement_sheets = "Measurement Sheets"
    tender = "Tender"
    other = "Other File"
