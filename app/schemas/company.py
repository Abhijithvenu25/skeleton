import uuid
from pydantic import BaseModel, ConfigDict

class CompanyListOut(BaseModel):
    company_name: str
    company_id: uuid.UUID
    enquiry_id: uuid.UUID | None
    
    model_config = ConfigDict(from_attributes=True)
