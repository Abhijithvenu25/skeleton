import uuid
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict
from app.models.enums import QuotationStatus

class QuotationLineItemBase(BaseModel):
    description: str | None = None
    quantity: float
    unit: str | None = None
    rate: float
    amount: float
    estimated_cost: float | None = 0
    profit_estimator: dict | None = None

class QuotationLineItemCreate(QuotationLineItemBase):
    pass

class QuotationLineItemUpdate(QuotationLineItemBase):
    id: uuid.UUID | None = None

class QuotationLineItemOut(QuotationLineItemBase):
    id: uuid.UUID
    quotation_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class QuotationBase(BaseModel):
    subject: str | None = None
    quotation_date: date | None = None
    valid_until: date | None = None
    enquiry_id: uuid.UUID
    site_visit_id: uuid.UUID | None = None
    subtotal: float | None = 0
    global_discount: float | None = 0
    vat_rate: float | None = 0
    expected_profit: float | None = 0
    total_estimated_cost: float | None = 0
    terms_and_conditions: str | None = None
    remarks: str | None = None
    amount: float | None = 0
    is_draft: bool = True
    version_no: str | None = None

class QuotationCreate(QuotationBase):
    line_items: list[QuotationLineItemCreate] = []

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "subject": "Supply & Installation of FCU Unit Relocation",
                "quotation_date": "2026-08-02",
                "valid_until": "2026-09-02",
                "enquiry_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "site_visit_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "subtotal": 1500.0,
                "global_discount": 100.0,
                "vat_rate": 5.0,
                "expected_profit": 300.0,
                "total_estimated_cost": 1200.0,
                "terms_and_conditions": "1. 100% Payment after work completion.",
                "remarks": "Standard terms apply",
                "amount": 1470.0,
                "is_draft": True,
                "line_items": [
                    {
                        "description": "Carrara Premium Italian Marble",
                        "quantity": 150,
                        "unit": "Sqm",
                        "rate": 10,
                        "amount": 1500,
                        "estimated_cost": 1200,
                        "profit_estimator": {
                            "relocation_cost": 0,
                            "pipe_work_cost": 150,
                            "ceiling_work_cost": 200,
                            "scaffolding_cost": 0,
                            "target_margin": 25
                        }
                    }
                ]
            }
        }
    )

class QuotationUpdate(BaseModel):
    subject: str | None = None
    quotation_date: date | None = None
    valid_until: date | None = None
    site_visit_id: uuid.UUID | None = None
    subtotal: float | None = None
    global_discount: float | None = None
    vat_rate: float | None = None
    expected_profit: float | None = None
    total_estimated_cost: float | None = None
    terms_and_conditions: str | None = None
    remarks: str | None = None
    amount: float | None = None
    is_draft: bool | None = None
    status: QuotationStatus | None = None
    line_items: list[QuotationLineItemUpdate] | None = None

class QuotationOut(QuotationBase):
    id: uuid.UUID
    quotation_number: str
    company_id: uuid.UUID
    executive_id: uuid.UUID | None = None
    version: int
    is_current: bool
    currency: str
    sent_date: date | None = None
    status: QuotationStatus
    enquiry_no: str | None = None
    created_by_id: uuid.UUID
    updated_by_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
    
    line_items: list[QuotationLineItemOut] = []
    
    model_config = ConfigDict(from_attributes=True)
