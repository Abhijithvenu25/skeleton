"""CRM-domain enums (mirror the CHECK constraints in 0003_crm_module.py)."""

from __future__ import annotations

from enum import Enum


class RoleName(str, Enum):
    SALES_EXECUTIVE = "sales_executive"
    ENGINEER = "engineer"
    ADMIN = "admin"
    OWNER = "owner"


class ProjectType(str, Enum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    RENOVATION = "renovation"
    OTHER = "other"


class EnquirySource(str, Enum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    LINKEDIN = "linkedin"
    WEBSITE = "website"
    DIRECT_CALL = "direct_call"
    REFERRAL = "referral"
    TENDER = "tender"
    OTHER = "other"


class EnquiryPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EnquiryStatus(str, Enum):
    ENQUIRY = "enquiry"
    SITE_VISIT = "site_visit"
    QUOTATION = "quotation"
    ACCEPTED = "accepted"
    LOST = "lost"


class SiteVisitStatus(str, Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"


class QuotationStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class LineItemType(str, Enum):
    MATERIAL = "material"
    LABOUR = "labour"
    TAX = "tax"
    OTHER = "other"


class LostStage(str, Enum):
    ENQUIRY = "enquiry"
    SITE_VISIT = "site_visit"
    QUOTATION = "quotation"
