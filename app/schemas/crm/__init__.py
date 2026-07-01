"""CRM schemas (re-exports for convenience)."""

from app.schemas.crm.company import (
    CompanyIn,
    CompanyOut,
    CompanyPatch,
    CompanyUpdate,
)
from app.schemas.crm.contact import (
    ContactIn,
    ContactOut,
    ContactPatch,
    ContactUpdate,
)
from app.schemas.crm.enquiry import (
    EnquiryIn,
    EnquiryOut,
    EnquiryPatch,
    EnquiryUpdate,
    MarkLostIn,
)
from app.schemas.crm.enums import (
    EnquiryPriority,
    EnquirySource,
    EnquiryStatus,
    LineItemType,
    LostStage,
    ProjectType,
    QuotationStatus,
    RoleName,
    SiteVisitStatus,
)
from app.schemas.crm.lost_enquiry import (
    LostEnquiryIn,
    LostEnquiryOut,
    LostEnquiryPatch,
    LostEnquiryUpdate,
)
from app.schemas.crm.project import (
    ProjectIn,
    ProjectOut,
    ProjectPatch,
    ProjectUpdate,
)
from app.schemas.crm.quotation import (
    QuotationIn,
    QuotationOut,
    QuotationPatch,
    QuotationUpdate,
)
from app.schemas.crm.quotation_version import (
    QuotationLineItemIn,
    QuotationLineItemOut,
    QuotationVersionIn,
    QuotationVersionOut,
)
from app.schemas.crm.role import RoleIn, RoleOut, RolePatch, RoleUpdate
from app.schemas.crm.site_visit import (
    SiteVisitIn,
    SiteVisitOut,
    SiteVisitPatch,
    SiteVisitUpdate,
)
from app.schemas.crm.staff_profile import (
    StaffProfileIn,
    StaffProfileOut,
    StaffProfilePatch,
    StaffProfileUpdate,
)

__all__ = [
    "CompanyIn",
    "CompanyOut",
    "CompanyPatch",
    "CompanyUpdate",
    "ContactIn",
    "ContactOut",
    "ContactPatch",
    "ContactUpdate",
    "EnquiryIn",
    "EnquiryOut",
    "EnquiryPatch",
    "EnquiryPriority",
    "EnquirySource",
    "EnquiryStatus",
    "EnquiryUpdate",
    "LineItemType",
    "LostEnquiryIn",
    "LostEnquiryOut",
    "LostEnquiryPatch",
    "LostEnquiryUpdate",
    "LostStage",
    "MarkLostIn",
    "ProjectIn",
    "ProjectOut",
    "ProjectPatch",
    "ProjectType",
    "ProjectUpdate",
    "QuotationIn",
    "QuotationLineItemIn",
    "QuotationLineItemOut",
    "QuotationOut",
    "QuotationPatch",
    "QuotationStatus",
    "QuotationUpdate",
    "QuotationVersionIn",
    "QuotationVersionOut",
    "RoleIn",
    "RoleName",
    "RoleOut",
    "RolePatch",
    "RoleUpdate",
    "SiteVisitIn",
    "SiteVisitOut",
    "SiteVisitPatch",
    "SiteVisitStatus",
    "SiteVisitUpdate",
    "StaffProfileIn",
    "StaffProfileOut",
    "StaffProfilePatch",
    "StaffProfileUpdate",
]
