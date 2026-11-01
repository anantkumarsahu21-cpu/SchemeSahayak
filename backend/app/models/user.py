from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, Enum
from sqlalchemy.orm import relationship
from app.database.base import Base

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    DATA_MANAGER = "DATA_MANAGER"
    USER = "USER"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    phone_number = Column(String(30), nullable=True)
    role = Column(String(50), default=UserRole.USER.value, nullable=False)
    is_active = Column(Boolean, default=True)
    preferred_language = Column(String(10), default="en")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    saved_schemes = relationship("SavedScheme", back_populates="user", cascade="all, delete-orphan")
    roadmaps = relationship("UserRoadmap", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    # Demographics
    age = Column(Integer, nullable=True)
    gender = Column(String(20), default="ALL")  # MALE, FEMALE, TRANSGENDER, ALL
    state_code = Column(String(10), nullable=True)
    state_name = Column(String(100), nullable=True)
    district_name = Column(String(100), nullable=True)
    area_type = Column(String(20), default="RURAL")  # RURAL, URBAN
    
    # Socio-economic
    caste_category = Column(String(50), default="GENERAL")  # GENERAL, OBC, SC, ST, MINORITY, EWS
    annual_income = Column(Float, default=0.0)
    is_disabled = Column(Boolean, default=False)
    disability_percentage = Column(Integer, default=0)
    
    # Education & Employment
    education_level = Column(String(100), nullable=True)  # NONE, 8TH_PASS, 10TH_PASS, 12TH_PASS, ITI, DIPLOMA, GRADUATE, POST_GRADUATE, PHD
    employment_status = Column(String(100), nullable=True) # STUDENT, UNEMPLOYED, SELF_EMPLOYED, EMPLOYED, FARMER, ARTISAN, RETIRED
    occupation = Column(String(100), nullable=True) # FARMER, ARTISAN, VENDOR, ENTREPRENEUR, STUDENT, TEACHER, etc.
    
    # Business Profile (for MSME / startup discovery)
    business_type = Column(String(100), nullable=True) # MANUFACTURING, SERVICE, TRADING, AGRI_ALLIED, TECH_STARTUP
    business_stage = Column(String(50), nullable=True) # IDEA, EARLY_STAGE, OPERATIONAL, EXPANSION
    business_registered = Column(Boolean, default=False)
    registration_type = Column(String(50), nullable=True) # UDYAM, GST, PRIVATE_LIMITED, PROPRIETORSHIP
    funding_needed = Column(Float, default=0.0)
    project_cost = Column(Float, default=0.0)
    own_contribution = Column(Float, default=0.0)

    # Agriculture profile
    owns_land = Column(Boolean, default=False)
    land_area_acres = Column(Float, default=0.0)

    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="profile")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(String(100), nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
