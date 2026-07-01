"""CRM schemas (re-exports for convenience)."""

from app.schemas.crm.company import CompanyIn, CompanyOut, CompanyPatch
from app.schemas.crm.contact import ContactIn, ContactOut, ContactPatch
from app.schemas.crm.enquiry import (
    EnquiryIn,
    EnquiryOut,
    EnquiryPatch,
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
)
from app.schemas.crm.project import ProjectIn, ProjectOut, ProjectPatch
from app.schemas.crm.quotation import QuotationIn, QuotationOut, QuotationPatch
from app.schemas.crm.quotation_version import (
    QuotationLineItemOut,
    QuotationVersionIn,
    QuotationVersionOut,
)
from app.schemas.crm.role import RoleIn, RoleOut, RolePatch
from app.schemas.crm.site_visit import (
    SiteVisitIn,
    SiteVisitOut,
    SiteVisitPatch,
)
from app.schemas.crm.staff_profile import (
    StaffProfileIn,
    StaffProfileOut,
    StaffProfilePatch,
    UserRolesIn,
    UserRolesOut,
)

__all__ = [
    "CompanyIn",
    "CompanyOut",
    "CompanyPatch",
    "ContactIn",
    "ContactOut",
    "ContactPatch",
    "EnquiryIn",
    "EnquiryOut",
    "EnquiryPatch",
    "EnquiryPriority",
    "EnquirySource",
    "EnquiryStatus",
    "LineItemType",
    "LostEnquiryIn",
    "LostEnquiryOut",
    "LostEnquiryPatch",
    "LostStage",
    "MarkLostIn",
    "ProjectIn",
    "ProjectOut",
    "ProjectPatch",
    "ProjectType",
    "QuotationIn",
    "QuotationLineItemOut",
    "QuotationOut",
    "QuotationPatch",
    "QuotationStatus",
    "QuotationVersionIn",
    "QuotationVersionOut",
    "RoleIn",
    "RoleName",
    "RoleOut",
    "RolePatch",
    "SiteVisitIn",
    "SiteVisitOut",
    "SiteVisitPatch",
    "SiteVisitStatus",
    "StaffProfileIn",
    "StaffProfileOut",
    "StaffProfilePatch",
    "UserRolesIn",
    "UserRolesOut",
]
