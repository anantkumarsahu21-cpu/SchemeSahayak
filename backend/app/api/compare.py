from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api.deps import get_db
from app.models.scheme import Scheme
from app.schemas.scheme import SchemeDetailResponse
from app.api.schemes import _build_list_item

router = APIRouter(prefix="/compare", tags=["Scheme Comparison"])

class CompareRequest(BaseModel):
    scheme_ids: List[int]

class SchemeComparisonMatrix(BaseModel):
    schemes: List[SchemeDetailResponse]
    comparison_fields: List[str]
    best_fit_summary: str

@router.post("", response_model=SchemeComparisonMatrix)
def compare_schemes(
    req: CompareRequest,
    db: Session = Depends(get_db)
) -> Any:
    if len(req.scheme_ids) < 2:
        raise HTTPException(status_code=400, detail="Please select at least 2 schemes to compare.")

    if len(req.scheme_ids) > 4:
        raise HTTPException(status_code=400, detail="You can compare a maximum of 4 schemes simultaneously.")

    schemes = db.query(Scheme).filter(Scheme.id.in_(req.scheme_ids)).all()
    if not schemes:
        raise HTTPException(status_code=404, detail="Selected schemes not found.")

    details: List[SchemeDetailResponse] = []
    for s in schemes:
        base = _build_list_item(s)
        detail = SchemeDetailResponse(
            **base.model_dump(),
            department=s.department,
            target_beneficiary=s.target_beneficiary,
            description=s.description,
            objectives=s.objectives or [],
            financial_details=s.financial_details or {},
            application_process=s.application_process or [],
            source_url=s.source_url,
            effective_date=s.effective_date,
            expiry_date=s.expiry_date,
            created_at=s.created_at,
            updated_at=s.updated_at,
            eligibility=s.eligibility,
            documents=s.documents or [],
            sources=s.sources or []
        )
        details.append(detail)

    fields = [
        "Category & Level",
        "Target Beneficiary",
        "Financial Benefit / Subsidy",
        "Age Limit",
        "Income Ceiling",
        "Education Requirement",
        "Key Documents",
        "Application Mode",
        "Official Portal"
    ]

    best_fit = f"Comparison generated for {len(details)} government schemes. Review eligibility rules and official documentation."

    return SchemeComparisonMatrix(
        schemes=details,
        comparison_fields=fields,
        best_fit_summary=best_fit
    )
