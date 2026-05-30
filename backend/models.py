from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from .database import Base

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    website_url = Column(String, unique=True, index=True, nullable=False)
    website_name = Column(String, nullable=True)
    company_name = Column(String, nullable=True)
    address = Column(String, nullable=True)
    mobile_number = Column(String, nullable=True)
    mail = Column(JSON, nullable=True)  # List of emails
    core_service = Column(Text, nullable=True)
    target_customer = Column(Text, nullable=True)
    probable_pain_point = Column(Text, nullable=True)
    outreach_opener = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
