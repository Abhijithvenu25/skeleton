from app.models.enquiry import Enquiry
from app.models.enums import AttachmentDocumentType
from app.schemas.enquiry import (
    AddressOut,
    AttachmentsOut,
    AttachmentFile,
    DescriptionOut,
    EnquiryDetailOut,
    ProjectDetailsOut,
)


def build_enquiry_detail_out(enquiry: Enquiry) -> EnquiryDetailOut:
    boq = []
    drawings = []
    photos = []
    tender = []
    other = []

    for att in enquiry.attachments:
        item = AttachmentFile(id=att.id, url=att.file)
        if att.document_type == AttachmentDocumentType.boq:
            boq.append(item)
        elif att.document_type == AttachmentDocumentType.drawings:
            drawings.append(item)
        elif att.document_type == AttachmentDocumentType.photos:
            photos.append(item)
        elif att.document_type == AttachmentDocumentType.tender:
            tender.append(item)
        elif att.document_type == AttachmentDocumentType.other:
            other.append(item)
        else:
            other.append(item)

    address = AddressOut(
        company_address=enquiry.company.address_line1 if enquiry.company else None,
        company_city=enquiry.company.city if enquiry.company else None,
        company_state=enquiry.company.state if enquiry.company else None,
        company_country=enquiry.company.country if enquiry.company else None,
        company_pincode=enquiry.company.pincode if enquiry.company else None,
    )

    project_details = ProjectDetailsOut(
        project_name=enquiry.project.project_name if enquiry.project else None,
        project_type=enquiry.project.project_type.type_name if enquiry.project and enquiry.project.project_type else None,
        project_location=enquiry.project.project_location if enquiry.project else None,
        estimated_budget=float(enquiry.project.estimated_budget) if enquiry.project and enquiry.project.estimated_budget is not None else None,
        expected_start_date=enquiry.project.expected_start_date if enquiry.project else None,
        source=enquiry.enquiry_source,
        priority=enquiry.priority,
        sales_executive=enquiry.sales_executive.full_name if enquiry.sales_executive else None,
    )

    description = DescriptionOut(
        project_description=enquiry.description,
        remarks=enquiry.remarks,
    )

    attachments = AttachmentsOut(
        boq=boq,
        drawings=drawings,
        photos=photos,
        tender_documents=tender,
        other_files=other,
    )
    
    # client fields: client_contact, alternate_contact, client_designation in Client model
    contact = enquiry.client.client_contact if enquiry.client else None
    alt_contact = enquiry.client.alternate_contact if enquiry.client else None
    
    return EnquiryDetailOut(
        id=enquiry.id,
        enquiry_number=enquiry.enquiry_number,
        enquiry_date=enquiry.enquiry_date,
        status=enquiry.status,
        company_name=enquiry.company.company_name if enquiry.company else "Unknown",
        company_website=enquiry.company.company_website if enquiry.company else None,
        contact_person=enquiry.client.client_name if enquiry.client else None, # Assuming client_name is contact_person
        designation=enquiry.client.client_designation if enquiry.client else None,
        mobile=contact,
        alternate_mobile=alt_contact,
        email=enquiry.client.email if enquiry.client else None,
        address=address,
        project_details=project_details,
        description=description,
        attachments=attachments,
    )
