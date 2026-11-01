from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from app.schemas.scheme import SchemeListItemResponse, SchemeDocumentResponse

class ProfileMatchRequest(BaseModel):
    age: Optional[int] = None
    gender: Optional[str] = "ALL"
    state_code: Optional[str] = None
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
    funding_needed: Optional[float] = 0.0
    project_cost: Optional[float] = 0.0
    own_contribution: Optional[float] = 0.0
    owns_land: Optional[bool] = False
    target_category_slug: Optional[str] = None

class MatchFactor(BaseModel):
    title: str
    status: str # MATCH, WARNING, FAIL, INFO
    detail: str

class SchemeMatchItem(BaseModel):
    scheme: SchemeListItemResponse
    match_score: int # 0 to 100
    eligibility_status: str # ELIGIBLE, LIKELY_ELIGIBLE, POSSIBLY_ELIGIBLE, NOT_ELIGIBLE, INSUFFICIENT_INFO
    why_matched: List[MatchFactor]
    blockers: List[MatchFactor]
    next_steps: List[str]
    required_documents: List[SchemeDocumentResponse]
    estimated_benefit: str

class MatchResponse(BaseModel):
    total_evaluated: int
    matched_count: int
    results: List[SchemeMatchItem]
