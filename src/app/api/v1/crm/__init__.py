"""CRM router aggregator.

Each resource has its own router file; this package re-exports them so
src/app/api/router.py can do `from app.api.v1 import crm` and include them.
"""

from app.api.v1.crm import (
    company,
    contact,
    enquiry,
    lost_enquiry,
    project,
    quotation,
    quotation_line_item,
    role,
    site_visit,
    staff_profile,
)

__all__ = [
    "company",
    "contact",
    "enquiry",
    "lost_enquiry",
    "project",
    "quotation",
    "quotation_line_item",
    "role",
    "site_visit",
    "staff_profile",
]
