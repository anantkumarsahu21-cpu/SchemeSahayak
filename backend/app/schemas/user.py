from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict

# Token
class Token(BaseModel):
    access_token: str
    token_type: str
    user: "UserResponse"

class TokenPayload(BaseModel):
    sub: Optional[str] = None

# User Profile
class UserProfileBase(BaseModel):
    age: Optional[int] = None
    gender: Optional[str] = "ALL"
    state_code: Optional[str] = None
    state_name: Optional[str] = None
    district_name: Optional[str] = None
    area_type: Optional[str] = "RURAL"
    caste_category: Optional[str] = "GENERAL"
    annual_income: Optional[float] = 0.0
    is_disabled: Optional[bool] = False
    disability_percentage: Optional[int] = 0
    education_level: Optional[str] = "NONE"
    employment_status: Optional[str] = "UNEMPLOYED"
    occupation: Optional[str] = None
    business_type: Optional[str] = None
    business_stage: Optional[str] = None
    business_registered: Optional[bool] = False
    registration_type: Optional[str] = None
    funding_needed: Optional[float] = 0.0
    project_cost: Optional[float] = 0.0
    own_contribution: Optional[float] = 0.0
    owns_land: Optional[bool] = False
    land_area_acres: Optional[float] = 0.0

class UserProfileCreate(UserProfileBase):
    pass

class UserProfileUpdate(UserProfileBase):
    pass

class UserProfileResponse(UserProfileBase):
    id: int
    user_id: int
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

# User
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    preferred_language: Optional[str] = "en"

class UserCreate(UserBase):
    password: str
    role: Optional[str] = "USER"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: int
    role: str
    is_active: bool
    created_at: datetime
    profile: Optional[UserProfileResponse] = None
    model_config = ConfigDict(from_attributes=True)

Token.model_rebuild()
