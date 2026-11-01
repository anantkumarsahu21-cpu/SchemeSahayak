from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, Float, func
from sqlalchemy.orm import relationship
from app.database.base import Base

class SchemeLevel(str, enum.Enum):
    CENTRAL = "CENTRAL"
    STATE = "STATE"
    DISTRICT = "DISTRICT"
    PRIVATE = "PRIVATE"

class VerificationStatus(str, enum.Enum):
    VERIFIED = "VERIFIED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    EXPIRED = "EXPIRED"
    ARCHIVED = "ARCHIVED"

class Scheme(Base):
    __tablename__ = "schemes"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(150), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    
    ministry = Column(String(255), nullable=True)
    department = Column(String(255), nullable=True)
    level = Column(String(50), default=SchemeLevel.CENTRAL.value, nullable=False)
    
    # Location scope
    state_id = Column(Integer, ForeignKey("states.id", ondelete="SET NULL"), nullable=True)
    district_id = Column(Integer, ForeignKey("districts.id", ondelete="SET NULL"), nullable=True)
    
    target_beneficiary = Column(Text, nullable=True)
    summary = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    objectives = Column(JSON, server_default=func.json('[]')) # list of strings
    
    benefits_summary = Column(Text, nullable=False)
    benefit_type = Column(String(100), default="GRANT") # SUBSIDY, LOAN, SCHOLARSHIP, DIRECT_BENEFIT_TRANSFER, HEALTH_INSURANCE, etc.
    financial_details = Column(JSON, server_default=func.json('{}')) # Structured financial details (amounts, %, etc.)
    
    application_mode = Column(String(50), default="ONLINE") # ONLINE, OFFLINE, ONLINE_OFFLINE
    application_process = Column(JSON, server_default=func.json('[]')) # List of step instructions
    official_portal = Column(String(500), nullable=True)
    
    # Verification & Source Integrity
    source_authority = Column(String(255), nullable=False)
    source_url = Column(String(500), nullable=False)
    last_verified_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    verification_status = Column(String(50), default=VerificationStatus.VERIFIED.value, nullable=False)
    effective_date = Column(DateTime, nullable=True)
    expiry_date = Column(DateTime, nullable=True)
    
    tags = Column(JSON, server_default=func.json('[]'))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    category = relationship("Category", back_populates="schemes")
    state = relationship("State", back_populates="schemes")
    district = relationship("District", back_populates="schemes")
    eligibility = relationship("SchemeEligibility", back_populates="scheme", uselist=False, cascade="all, delete-orphan")
    documents = relationship("SchemeDocument", back_populates="scheme", cascade="all, delete-orphan")
    sources = relationship("SchemeSource", back_populates="scheme", cascade="all, delete-orphan")
    saved_by = relationship("SavedScheme", back_populates="scheme", cascade="all, delete-orphan")
    roadmaps = relationship("UserRoadmap", back_populates="scheme", cascade="all, delete-orphan")

class SchemeEligibility(Base):
    __tablename__ = "scheme_eligibility"

    id = Column(Integer, primary_key=True, index=True)
    scheme_id = Column(Integer, ForeignKey("schemes.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    min_age = Column(Integer, nullable=True)
    max_age = Column(Integer, nullable=True)
    gender = Column(String(50), default="ALL") # ALL, FEMALE, MALE, TRANSGENDER
    min_education = Column(String(100), default="NONE") # NONE, 8TH_PASS, 10TH_PASS, 12TH_PASS, GRADUATE, etc.
    min_income = Column(Float, nullable=True)
    max_income = Column(Float, nullable=True)
    
    caste_categories = Column(JSON, server_default=func.json('[]')) # ["GENERAL", "OBC", "SC", "ST", "MINORITY", "EWS"]
    occupations = Column(JSON, server_default=func.json('[]')) # ["STUDENT", "FARMER", "ENTREPRENEUR", "ARTISAN", "UNEMPLOYED", "ALL"]
    
    disability_allowed = Column(Boolean, default=True)
    min_disability_percentage = Column(Integer, default=0)
    rural_urban = Column(String(50), default="BOTH") # RURAL, URBAN, BOTH
    
    special_conditions = Column(JSON, server_default=func.json('{}'))
    notes = Column(Text, nullable=True)

    scheme = relationship("Scheme", back_populates="eligibility")

class SchemeDocument(Base):
    __tablename__ = "scheme_documents"

    id = Column(Integer, primary_key=True, index=True)
    scheme_id = Column(Integer, ForeignKey("schemes.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    mandatory = Column(Boolean, default=True)
    description = Column(Text, nullable=True)
    upload_instructions = Column(Text, nullable=True)

    scheme = relationship("Scheme", back_populates="documents")

class SchemeSource(Base):
    __tablename__ = "scheme_sources"

    id = Column(Integer, primary_key=True, index=True)
    scheme_id = Column(Integer, ForeignKey("schemes.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    authority_name = Column(String(255), nullable=False)
    verification_notes = Column(Text, nullable=True)
    verified_at = Column(String(50), nullable=False)

    scheme = relationship("Scheme", back_populates="sources")
