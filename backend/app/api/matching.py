from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_optional_current_user
from app.models.user import User, UserProfile
from app.schemas.matching import ProfileMatchRequest, MatchResponse
from app.services.eligibility_engine import EligibilityEngine

router = APIRouter(prefix="/match", tags=["Eligibility Matching Engine"])

@router.post("", response_model=MatchResponse)
def match_schemes(
    profile_data: ProfileMatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_current_user)
) -> Any:
    # If user is logged in and some fields were empty, we can blend stored profile
    if current_user and current_user.profile:
        p: UserProfile = current_user.profile
        if not profile_data.state_code and p.state_code:
            profile_data.state_code = p.state_code
        if not profile_data.age and p.age:
            profile_data.age = p.age
        if (not profile_data.gender or profile_data.gender == "ALL") and p.gender:
            profile_data.gender = p.gender
        if not profile_data.annual_income and p.annual_income:
            profile_data.annual_income = p.annual_income
        if (not profile_data.caste_category or profile_data.caste_category == "GENERAL") and p.caste_category:
            profile_data.caste_category = p.caste_category

    matched_items = EligibilityEngine.match_all(db, profile_data)

    # Filter by category if requested
    if profile_data.target_category_slug:
        matched_items = [item for item in matched_items if item.scheme.category_slug == profile_data.target_category_slug]

    total_eval = len(matched_items)
    matched_cnt = len([i for i in matched_items if i.match_score >= 50])

    return MatchResponse(
        total_evaluated=total_eval,
        matched_count=matched_cnt,
        results=matched_items
    )
