from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class AnalyticsSummaryResponse(BaseModel):
    total_schemes: int
    verified_schemes: int
    needs_review_schemes: int
    expired_schemes: int
    total_users: int
    total_matches_run: int
    total_ai_queries: int
    categories_breakdown: List[Dict[str, Any]]
    level_breakdown: List[Dict[str, Any]]
    recent_activity: List[Dict[str, Any]]

class SchemeStatusUpdateRequest(BaseModel):
    verification_status: str # VERIFIED, NEEDS_REVIEW, EXPIRED, ARCHIVED
    verification_notes: Optional[str] = None

class ImportReportResponse(BaseModel):
    imported_count: int
    updated_count: int
    rejected_count: int
    duplicate_count: int
    errors: List[str]
