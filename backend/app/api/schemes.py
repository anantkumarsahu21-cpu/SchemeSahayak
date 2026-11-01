import math
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.api.deps import get_db
from app.models.scheme import Scheme, SchemeEligibility, SchemeDocument, SchemeSource, SchemeLevel, VerificationStatus
from app.models.category import Category
from app.models.location import State, District
from app.schemas.scheme import SchemeListItemResponse, SchemeDetailResponse, SchemeListPaginatedResponse

router = APIRouter(prefix="/schemes", tags=["Schemes"])

def _build_list_item(s: Scheme) -> SchemeListItemResponse:
    return SchemeListItemResponse(
        id=s.id,
        slug=s.slug,
        name=s.name,
        ministry=s.ministry,
        level=s.level or "CENTRAL",
        category_name=s.category.name if s.category else "General Support",
        category_slug=s.category.slug if s.category else "general",
        category_icon=s.category.icon if s.category else "Briefcase",
        summary=s.summary or s.name,
        benefits_summary=s.benefits_summary or "",
        benefit_type=s.benefit_type or "GRANT",
        application_mode=s.application_mode or "ONLINE",
        official_portal=s.official_portal,
        source_authority=s.source_authority or "Government of India",
        last_verified_at=s.last_verified_at,
        verification_status=s.verification_status or "VERIFIED",
        state_name=s.state.name if s.state else "All India",
        tags=s.tags or [],
        is_active=s.is_active if s.is_active is not None else True
    )

@router.get("", response_model=SchemeListPaginatedResponse)
def list_schemes(
    q: Optional[str] = None,
    category: Optional[str] = None,
    level: Optional[str] = None,
    state: Optional[str] = None,
    benefit_type: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(12, ge=1, le=100),
    db: Session = Depends(get_db)
) -> Any:
    query = db.query(Scheme).filter(Scheme.is_active == True)

    if q:
        search_pattern = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Scheme.name.ilike(search_pattern),
                Scheme.summary.ilike(search_pattern),
                Scheme.description.ilike(search_pattern),
                Scheme.target_beneficiary.ilike(search_pattern),
                Scheme.source_authority.ilike(search_pattern)
            )
        )

    if category:
        cat = db.query(Category).filter(or_(Category.slug == category, Category.name.ilike(f"%{category}%"))).first()
        if cat:
            query = query.filter(Scheme.category_id == cat.id)

    if level and level.upper() != "ALL":
        if level.upper() == "GOVERNMENT":
            query = query.filter(Scheme.level.in_([SchemeLevel.CENTRAL.value, SchemeLevel.STATE.value, SchemeLevel.DISTRICT.value]))
        else:
            query = query.filter(Scheme.level == level.upper())

    if state and state.upper() not in ["ALL", "CENTRAL"]:
        # Match central/national schemes OR specific state schemes
        st = db.query(State).filter(or_(State.code == state.upper(), State.name.ilike(f"%{state}%"))).first()
        if st:
            query = query.filter(
                or_(
                    Scheme.level.in_([SchemeLevel.CENTRAL.value, SchemeLevel.PRIVATE.value]),
                    Scheme.state_id == st.id,
                    Scheme.state_id.is_(None)
                )
            )

    if benefit_type and benefit_type.upper() != "ALL":
        query = query.filter(Scheme.benefit_type.ilike(f"%{benefit_type}%"))

    if status:
        query = query.filter(Scheme.verification_status == status.upper())

    total = query.count()
    pages = math.ceil(total / limit) if total > 0 else 1
    offset = (page - 1) * limit
    schemes = (
        query.options(joinedload(Scheme.category), joinedload(Scheme.state))
        .order_by(Scheme.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = [_build_list_item(s) for s in schemes]

    return SchemeListPaginatedResponse(
        items=items,
        total=total,
        page=page,
        size=limit,
        pages=pages
    )

@router.get("/featured", response_model=List[SchemeListItemResponse])
def get_featured_schemes(db: Session = Depends(get_db)) -> Any:
    schemes = (
        db.query(Scheme)
        .options(joinedload(Scheme.category), joinedload(Scheme.state))
        .filter(Scheme.is_active == True, Scheme.verification_status == VerificationStatus.VERIFIED.value)
        .limit(6)
        .all()
    )
    return [_build_list_item(s) for s in schemes]

@router.get("/education", response_model=List[SchemeListItemResponse])
def get_education_schemes(
    education_level: Optional[str] = None,
    caste: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
) -> Any:
    cat = db.query(Category).filter(Category.slug == "education-scholarships").first()
    query = db.query(Scheme).filter(Scheme.is_active == True)
    if cat:
        query = query.filter(Scheme.category_id == cat.id)
    schemes = query.options(joinedload(Scheme.category), joinedload(Scheme.state)).limit(limit).all()
    return [_build_list_item(s) for s in schemes]

@router.get("/business", response_model=List[SchemeListItemResponse])
def get_business_schemes(
    funding_type: Optional[str] = None,
    sector: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
) -> Any:
    cat = db.query(Category).filter(Category.slug == "business-msme").first()
    query = db.query(Scheme).filter(Scheme.is_active == True)
    if cat:
        query = query.filter(Scheme.category_id == cat.id)
    if sector and sector.upper() != "ALL":
        if sector.upper() == "GOVERNMENT":
            query = query.filter(Scheme.level.in_([SchemeLevel.CENTRAL.value, SchemeLevel.STATE.value, SchemeLevel.DISTRICT.value]))
        elif sector.upper() == "PRIVATE":
            query = query.filter(Scheme.level == SchemeLevel.PRIVATE.value)
    if funding_type and funding_type.upper() != "ALL":
        query = query.filter(Scheme.benefit_type.ilike(f"%{funding_type}%"))
    if q:
        query = query.filter(
            or_(
                Scheme.name.ilike(f"%{q}%"),
                Scheme.summary.ilike(f"%{q}%"),
                Scheme.description.ilike(f"%{q}%"),
                Scheme.source_authority.ilike(f"%{q}%")
            )
        )
    schemes = query.options(joinedload(Scheme.category), joinedload(Scheme.state)).order_by(Scheme.id.desc()).limit(limit).all()
    return [_build_list_item(s) for s in schemes]

@router.get("/{slug_or_id}", response_model=SchemeDetailResponse)
def get_scheme_detail(slug_or_id: str, db: Session = Depends(get_db)) -> Any:
    if slug_or_id.isdigit():
        scheme = db.query(Scheme).filter(Scheme.id == int(slug_or_id)).first()
    else:
        scheme = db.query(Scheme).filter(Scheme.slug == slug_or_id).first()

    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")

    base = _build_list_item(scheme)
    return SchemeDetailResponse(
        **base.model_dump(),
        department=scheme.department,
        target_beneficiary=scheme.target_beneficiary,
        description=scheme.description,
        objectives=scheme.objectives or [],
        financial_details=scheme.financial_details or {},
        application_process=scheme.application_process or [],
        source_url=scheme.source_url,
        effective_date=scheme.effective_date,
        expiry_date=scheme.expiry_date,
        created_at=scheme.created_at,
        updated_at=scheme.updated_at,
        eligibility=scheme.eligibility,
        documents=scheme.documents or [],
        sources=scheme.sources or []
    )
