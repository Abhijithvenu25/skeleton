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
    tender = "Tender"
    other = "Other File"
