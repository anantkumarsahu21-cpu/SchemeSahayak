import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_admin
from app.models.user import User, UserProfile, AuditLog
from app.models.scheme import Scheme, SchemeEligibility, SchemeDocument, SchemeSource, VerificationStatus
from app.models.category import Category
from app.models.location import State, District
from app.models.chat import ChatMessage
from app.schemas.admin import AnalyticsSummaryResponse, SchemeStatusUpdateRequest, ImportReportResponse
from app.schemas.scheme import SchemeCreate, SchemeUpdate, SchemeDetailResponse
from app.api.schemes import _build_list_item

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin Portal & Data Management"])

@router.get("/analytics", response_model=AnalyticsSummaryResponse)
def get_admin_analytics(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
) -> Any:
    total_schemes = db.query(Scheme).count()
    verified_schemes = db.query(Scheme).filter(Scheme.verification_status == VerificationStatus.VERIFIED.value).count()
    needs_review = db.query(Scheme).filter(Scheme.verification_status == VerificationStatus.NEEDS_REVIEW.value).count()
    expired_schemes = db.query(Scheme).filter(Scheme.verification_status == VerificationStatus.EXPIRED.value).count()
    
    total_users = db.query(User).count()
    total_ai_queries = db.query(ChatMessage).filter(ChatMessage.role == "user").count()

    # Category breakdown
    categories = db.query(Category).all()
    cat_breakdown = []
    for cat in categories:
        cnt = db.query(Scheme).filter(Scheme.category_id == cat.id).count()
        cat_breakdown.append({"category": cat.name, "slug": cat.slug, "count": cnt})

    # Level breakdown
    levels = ["CENTRAL", "STATE", "DISTRICT"]
    level_breakdown = []
    for lvl in levels:
        cnt = db.query(Scheme).filter(Scheme.level == lvl).count()
        level_breakdown.append({"level": lvl, "count": cnt})

    # Recent activity
    recent_schemes = db.query(Scheme).order_by(Scheme.updated_at.desc()).limit(5).all()
    recent_activity = [
        {
            "action": f"Verified Scheme: {s.name}",
            "time": s.last_verified_at,
            "status": s.verification_status
        }
        for s in recent_schemes
    ]

    # Query actual total_matches_run from ChatMessage history
    total_matches_run = db.query(ChatMessage).filter(ChatMessage.role == "assistant").count()
    
    return AnalyticsSummaryResponse(
        total_schemes=total_schemes,
        verified_schemes=verified_schemes,
        needs_review_schemes=needs_review,
        expired_schemes=expired_schemes,
        total_users=total_users,
        total_matches_run=total_matches_run,  # Actual count from database
        total_ai_queries=total_ai_queries,
        categories_breakdown=cat_breakdown,
        level_breakdown=level_breakdown,
        recent_activity=recent_activity
    )

@router.post("/schemes", response_model=SchemeDetailResponse)
def create_scheme(
    scheme_in: SchemeCreate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
) -> Any:
    existing = db.query(Scheme).filter(Scheme.slug == scheme_in.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Scheme with this slug already exists.")

    category_id = None
    if scheme_in.category_slug:
        cat = db.query(Category).filter(Category.slug == scheme_in.category_slug).first()
        if cat:
            category_id = cat.id

    state_id = None
    if scheme_in.state_code:
        st = db.query(State).filter(State.code == scheme_in.state_code.upper()).first()
        if st:
            state_id = st.id

    district_id = None
    if scheme_in.district_name and state_id:
        dt = db.query(District).filter(District.state_id == state_id, District.name.ilike(f"%{scheme_in.district_name}%")).first()
        if dt:
            district_id = dt.id

    scheme = Scheme(
        slug=scheme_in.slug,
        name=scheme_in.name,
        category_id=category_id,
        ministry=scheme_in.ministry,
        department=scheme_in.department,
        level=scheme_in.level,
        state_id=state_id,
        district_id=district_id,
        target_beneficiary=scheme_in.target_beneficiary,
        summary=scheme_in.summary,
        description=scheme_in.description,
        objectives=scheme_in.objectives,
        benefits_summary=scheme_in.benefits_summary,
        benefit_type=scheme_in.benefit_type,
        financial_details=scheme_in.financial_details,
        application_mode=scheme_in.application_mode,
        application_process=scheme_in.application_process,
        official_portal=scheme_in.official_portal,
        source_authority=scheme_in.source_authority,
        source_url=scheme_in.source_url,
        last_verified_at=scheme_in.last_verified_at or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        verification_status=scheme_in.verification_status,
        effective_date=scheme_in.effective_date,
        expiry_date=scheme_in.expiry_date,
        tags=scheme_in.tags,
        is_active=scheme_in.is_active
    )
    db.add(scheme)
    db.commit()
    db.refresh(scheme)

    # Add Eligibility
    if scheme_in.eligibility:
        elig = SchemeEligibility(
            scheme_id=scheme.id,
            **scheme_in.eligibility.model_dump()
        )
        db.add(elig)

    # Add Documents
    for doc in scheme_in.documents:
        d = SchemeDocument(scheme_id=scheme.id, **doc.model_dump())
        db.add(d)

    # Add Sources
    for src in scheme_in.sources:
        s = SchemeSource(scheme_id=scheme.id, **src.model_dump())
        db.add(s)

    db.commit()
    db.refresh(scheme)

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

@router.put("/schemes/{scheme_id}/status")
def update_scheme_status(
    scheme_id: int,
    req: SchemeStatusUpdateRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
) -> Any:
    scheme = db.query(Scheme).filter(Scheme.id == scheme_id).first()
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")

    scheme.verification_status = req.verification_status.upper()
    scheme.last_verified_at = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # Audit log
    log = AuditLog(
        user_id=current_admin.id,
        action=f"STATUS_UPDATE_{req.verification_status.upper()}",
        entity_type="Scheme",
        entity_id=str(scheme.id),
        details=req.verification_notes or f"Updated status to {req.verification_status.upper()}"
    )
    db.add(log)
    db.commit()

    return {"status": "success", "message": f"Updated {scheme.name} to {req.verification_status}"}

@router.delete("/schemes/{scheme_id}")
def delete_scheme(
    scheme_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
) -> Any:
    scheme = db.query(Scheme).filter(Scheme.id == scheme_id).first()
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")

    db.delete(scheme)
    db.commit()
    return {"status": "deleted", "message": f"Scheme {scheme_id} deleted successfully"}

@router.post("/import", response_model=ImportReportResponse)
async def import_schemes_json(
    file: UploadFile = File(...),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
) -> Any:
    contents = await file.read()
    try:
        data = json.loads(contents.decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON format: {e}")

    if not isinstance(data, list):
        data = [data]

    imported = 0
    updated = 0
    rejected = 0
    duplicate = 0
    errors = []

    for item in data:
        slug = item.get("slug")
        name = item.get("name")
        if not slug or not name:
            rejected += 1
            errors.append(f"Skipped item without name or slug: {item}")
            continue

        existing = db.query(Scheme).filter(Scheme.slug == slug).first()
        try:
            category_id = None
            if item.get("category_slug"):
                cat = db.query(Category).filter(Category.slug == item["category_slug"]).first()
                if cat:
                    category_id = cat.id

            state_id = None
            if item.get("state_code"):
                st = db.query(State).filter(State.code == item["state_code"].upper()).first()
                if st:
                    state_id = st.id

            if existing:
                # Update existing
                existing.name = name
                existing.category_id = category_id or existing.category_id
                existing.ministry = item.get("ministry", existing.ministry)
                existing.department = item.get("department", existing.department)
                existing.summary = item.get("summary", existing.summary)
                existing.description = item.get("description", existing.description)
                existing.benefits_summary = item.get("benefits_summary", existing.benefits_summary)
                existing.official_portal = item.get("official_portal", existing.official_portal)
                existing.source_authority = item.get("source_authority", existing.source_authority)
                existing.source_url = item.get("source_url", existing.source_url)
                existing.last_verified_at = item.get("last_verified_at", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
                existing.verification_status = item.get("verification_status", "VERIFIED")
                updated += 1
            else:
                new_scheme = Scheme(
                    slug=slug,
                    name=name,
                    category_id=category_id,
                    ministry=item.get("ministry"),
                    department=item.get("department"),
                    level=item.get("level", "CENTRAL"),
                    state_id=state_id,
                    target_beneficiary=item.get("target_beneficiary"),
                    summary=item.get("summary", name),
                    description=item.get("description", name),
                    objectives=item.get("objectives", []),
                    benefits_summary=item.get("benefits_summary", "Government Support"),
                    benefit_type=item.get("benefit_type", "SUBSIDY"),
                    financial_details=item.get("financial_details", {}),
                    application_mode=item.get("application_mode", "ONLINE"),
                    application_process=item.get("application_process", []),
                    official_portal=item.get("official_portal"),
                    source_authority=item.get("source_authority", "Government of India"),
                    source_url=item.get("source_url", "https://myscheme.gov.in"),
                    last_verified_at=item.get("last_verified_at", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
                    verification_status=item.get("verification_status", "VERIFIED"),
                    tags=item.get("tags", [])
                )
                db.add(new_scheme)
                db.commit()
                db.refresh(new_scheme)

                # Add Eligibility
                elig_data = item.get("eligibility_criteria", {})
                if elig_data:
                    elig = SchemeEligibility(
                        scheme_id=new_scheme.id,
                        min_age=elig_data.get("min_age"),
                        max_age=elig_data.get("max_age"),
                        gender=elig_data.get("gender", "ALL"),
                        min_education=elig_data.get("min_education", "NONE"),
                        min_income=elig_data.get("min_income"),
                        max_income=elig_data.get("max_income"),
                        caste_categories=elig_data.get("caste_categories", []),
                        occupations=elig_data.get("occupations", []),
                        disability_allowed=elig_data.get("disability_allowed", True),
                        rural_urban=elig_data.get("rural_urban", "BOTH"),
                        notes=elig_data.get("notes")
                    )
                    db.add(elig)

                # Add Documents
                for doc in item.get("required_documents", []):
                    d = SchemeDocument(
                        scheme_id=new_scheme.id,
                        name=doc.get("name", "ID Proof"),
                        mandatory=doc.get("mandatory", True),
                        description=doc.get("description")
                    )
                    db.add(d)

                imported += 1

            db.commit()
        except Exception as err:
            db.rollback()
            rejected += 1
            errors.append(f"Error importing {slug}: {str(err)}")

    return ImportReportResponse(
        imported_count=imported,
        updated_count=updated,
        rejected_count=rejected,
        duplicate_count=duplicate,
        errors=errors
    )
