from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict

# Documents
class SchemeDocumentBase(BaseModel):
    name: str
    mandatory: bool = True
    description: Optional[str] = None
    upload_instructions: Optional[str] = None

class SchemeDocumentCreate(SchemeDocumentBase):
    pass

class SchemeDocumentResponse(SchemeDocumentBase):
    id: int
    scheme_id: int
    model_config = ConfigDict(from_attributes=True)

# Sources
class SchemeSourceBase(BaseModel):
    title: str
    url: str
    authority_name: str
    verification_notes: Optional[str] = None
    verified_at: str

class SchemeSourceCreate(SchemeSourceBase):
    pass

class SchemeSourceResponse(SchemeSourceBase):
    id: int
    scheme_id: int
    model_config = ConfigDict(from_attributes=True)

# Eligibility
class SchemeEligibilityBase(BaseModel):
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    gender: Optional[str] = "ALL"
    min_education: Optional[str] = "NONE"
    min_income: Optional[float] = None
    max_income: Optional[float] = None
    caste_categories: List[str] = []
    occupations: List[str] = []
    disability_allowed: bool = True
    min_disability_percentage: int = 0
    rural_urban: Optional[str] = "BOTH"
    special_conditions: Dict[str, Any] = {}
    notes: Optional[str] = None

class SchemeEligibilityCreate(SchemeEligibilityBase):
    pass

class SchemeEligibilityResponse(SchemeEligibilityBase):
    id: int
    scheme_id: int
    model_config = ConfigDict(from_attributes=True)

# Scheme Base
class SchemeBase(BaseModel):
    slug: str
    name: str
    ministry: Optional[str] = None
    department: Optional[str] = None
    level: str = "CENTRAL"
    target_beneficiary: Optional[str] = None
    summary: str
    description: str
    objectives: List[str] = []
    benefits_summary: str
    benefit_type: str = "SUBSIDY"
    financial_details: Dict[str, Any] = {}
    application_mode: str = "ONLINE"
    application_process: List[str] = []
    official_portal: Optional[str] = None
    source_authority: str
    source_url: str
    last_verified_at: datetime
    verification_status: str = "VERIFIED"
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    tags: List[str] = []
    is_active: bool = True

class SchemeCreate(SchemeBase):
    category_slug: Optional[str] = None
    state_code: Optional[str] = None
    district_name: Optional[str] = None
    eligibility: Optional[SchemeEligibilityCreate] = None
    documents: List[SchemeDocumentCreate] = []
    sources: List[SchemeSourceCreate] = []

class SchemeUpdate(BaseModel):
    name: Optional[str] = None
    ministry: Optional[str] = None
    department: Optional[str] = None
    level: Optional[str] = None
    target_beneficiary: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    objectives: Optional[List[str]] = None
    benefits_summary: Optional[str] = None
    benefit_type: Optional[str] = None
    financial_details: Optional[Dict[str, Any]] = None
    application_mode: Optional[str] = None
    application_process: Optional[List[str]] = None
    official_portal: Optional[str] = None
    source_authority: Optional[str] = None
    source_url: Optional[str] = None
    last_verified_at: Optional[datetime] = None
    verification_status: Optional[str] = None
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None

class SchemeListItemResponse(BaseModel):
    id: int
    slug: str
    name: str
    ministry: Optional[str] = None
    level: str = "CENTRAL"
    category_name: Optional[str] = None
    category_slug: Optional[str] = None
    category_icon: Optional[str] = None
    summary: str = ""
    benefits_summary: str = ""
    benefit_type: str = "SUBSIDY"
    application_mode: Optional[str] = "ONLINE"
    official_portal: Optional[str] = None
    source_authority: str = "Government of India"
    last_verified_at: Optional[datetime] = None
    verification_status: str = "VERIFIED"
    state_name: Optional[str] = None
    tags: List[str] = []
    is_active: bool = True
    model_config = ConfigDict(from_attributes=True)

class SchemeDetailResponse(SchemeListItemResponse):
    department: Optional[str] = None
    target_beneficiary: Optional[str] = None
    description: str
    objectives: List[str] = []
    financial_details: Dict[str, Any] = {}
    application_process: List[str] = []
    source_url: str
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    eligibility: Optional[SchemeEligibilityResponse] = None
    documents: List[SchemeDocumentResponse] = []
    sources: List[SchemeSourceResponse] = []
    model_config = ConfigDict(from_attributes=True)

class SchemeListPaginatedResponse(BaseModel):
    items: List[SchemeListItemResponse]
    total: int
    page: int
    size: int
    pages: int
