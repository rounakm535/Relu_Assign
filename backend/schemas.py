from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional
from datetime import datetime

class CompanyEnrichRequest(BaseModel):
    url: str = Field(..., description="The website URL of the company to enrich")
    website_name: Optional[str] = Field(None, description="The custom name of the website/company for record-keeping")

class CompanyResponse(BaseModel):
    website_name: str
    company_name: str
    address: str
    mobile_number: str
    mail: List[str]
    core_service: str
    target_customer: str
    probable_pain_point: str
    outreach_opener: str

    class Config:
        from_attributes = True

class CompanyDBResponse(CompanyResponse):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
