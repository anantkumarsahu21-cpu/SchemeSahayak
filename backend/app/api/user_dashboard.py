from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict

from app.api.deps import get_db, get_current_user
from app.models.user import User, UserProfile
from app.models.scheme import Scheme
from app.models.interaction import SavedScheme, UserRoadmap, Notification, RoadmapStatus
from app.api.schemes import _build_list_item
from app.schemas.scheme import SchemeListItemResponse

router = APIRouter(prefix="/user", tags=["User Dashboard & Interactions"])

class SavedSchemeResponse(BaseModel):
    id: int
    scheme: SchemeListItemResponse
    notes: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class RoadmapCreate(BaseModel):
    scheme_id: int

class RoadmapUpdate(BaseModel):
    status: Optional[str] = None
    current_step: Optional[int] = None
    checklist_state: Optional[Dict[str, bool]] = None
    application_reference_no: Optional[str] = None
    notes: Optional[str] = None

class UserRoadmapResponse(BaseModel):
    id: int
    scheme_id: int
    scheme_name: str
    scheme_slug: str
    official_portal: Optional[str] = None
    status: str
    current_step: int
    total_steps: int
    checklist_state: Dict[str, bool] = {}
    application_reference_no: Optional[str] = None
    notes: Optional[str] = None
    application_process: List[str] = []
    required_documents: List[Dict[str, Any]] = []
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    link: Optional[str] = None
    type: str
    is_read: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class DashboardSummaryResponse(BaseModel):
    profile_completion_pct: int
    saved_schemes_count: int
    active_roadmaps_count: int
    unread_notifications_count: int
    profile: Optional[Dict[str, Any]] = None

@router.get("/dashboard-summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    profile = current_user.profile
    pct = 0
    if profile:
        fields = [profile.age, profile.gender, profile.state_code, profile.district_name, profile.annual_income, profile.education_level, profile.employment_status, profile.caste_category]
        completed = sum(1 for f in fields if f is not None and f != "" and f != "NONE" and f != 0.0)
        pct = int((completed / len(fields)) * 100)

    saved_count = db.query(SavedScheme).filter(SavedScheme.user_id == current_user.id).count()
    roadmaps_count = db.query(UserRoadmap).filter(UserRoadmap.user_id == current_user.id).count()
    notifs_count = db.query(Notification).filter(Notification.user_id == current_user.id, Notification.is_read == False).count()

    profile_dict = None
    if profile:
        profile_dict = {
            "full_name": current_user.full_name,
            "email": current_user.email,
            "state_code": profile.state_code,
            "district_name": profile.district_name,
            "education_level": profile.education_level,
            "occupation": profile.occupation or profile.employment_status
        }

    return DashboardSummaryResponse(
        profile_completion_pct=pct,
        saved_schemes_count=saved_count,
        active_roadmaps_count=roadmaps_count,
        unread_notifications_count=notifs_count,
        profile=profile_dict
    )

@router.get("/saved", response_model=List[SavedSchemeResponse])
def get_saved_schemes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    saved = db.query(SavedScheme).filter(SavedScheme.user_id == current_user.id).order_by(SavedScheme.created_at.desc()).all()
    results = []
    for s in saved:
        if s.scheme:
            results.append(SavedSchemeResponse(
                id=s.id,
                scheme=_build_list_item(s.scheme),
                notes=s.notes,
                created_at=s.created_at
            ))
    return results

@router.post("/saved/{scheme_id}")
def save_scheme(
    scheme_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    existing = db.query(SavedScheme).filter(SavedScheme.user_id == current_user.id, SavedScheme.scheme_id == scheme_id).first()
    if existing:
        return {"status": "already_saved", "message": "Scheme already bookmarked"}

    scheme = db.query(Scheme).filter(Scheme.id == scheme_id).first()
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")

    new_saved = SavedScheme(user_id=current_user.id, scheme_id=scheme_id)
    db.add(new_saved)
    db.commit()
    return {"status": "saved", "message": f"Saved {scheme.name} to your dashboard"}

@router.delete("/saved/{scheme_id}")
def remove_saved_scheme(
    scheme_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    item = db.query(SavedScheme).filter(SavedScheme.user_id == current_user.id, SavedScheme.scheme_id == scheme_id).first()
    if item:
        db.delete(item)
        db.commit()
    return {"status": "removed", "message": "Scheme removed from bookmarks"}

@router.get("/roadmaps", response_model=List[UserRoadmapResponse])
def get_user_roadmaps(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    roadmaps = db.query(UserRoadmap).filter(UserRoadmap.user_id == current_user.id).order_by(UserRoadmap.updated_at.desc()).all()
    results = []
    for r in roadmaps:
        if r.scheme:
            docs = [{"id": d.id, "name": d.name, "mandatory": d.mandatory} for d in r.scheme.documents]
            process = r.scheme.application_process or [
                "Complete profile and verify eligibility",
                "Gather and self-attest all mandatory documents",
                "Fill online application on the official portal",
                "Submit verification receipt to district nodal office",
                "Track application and receive benefit disbursement"
            ]
            results.append(UserRoadmapResponse(
                id=r.id,
                scheme_id=r.scheme_id,
                scheme_name=r.scheme.name,
                scheme_slug=r.scheme.slug,
                official_portal=r.scheme.official_portal,
                status=r.status,
                current_step=r.current_step,
                total_steps=len(process),
                checklist_state=r.checklist_state or {},
                application_reference_no=r.application_reference_no,
                notes=r.notes,
                application_process=process,
                required_documents=docs,
                updated_at=r.updated_at
            ))
    return results

@router.post("/roadmaps", response_model=UserRoadmapResponse)
def start_roadmap(
    req: RoadmapCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    scheme = db.query(Scheme).filter(Scheme.id == req.scheme_id).first()
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")

    existing = db.query(UserRoadmap).filter(UserRoadmap.user_id == current_user.id, UserRoadmap.scheme_id == req.scheme_id).first()
    if not existing:
        process = scheme.application_process or ["Prepare docs", "Fill portal form", "Submit"]
        existing = UserRoadmap(
            user_id=current_user.id,
            scheme_id=req.scheme_id,
            status=RoadmapStatus.IN_PROGRESS.value,
            current_step=1,
            total_steps=len(process),
            checklist_state={}
        )
        db.add(existing)
        db.commit()
        db.refresh(existing)

    docs = [{"id": d.id, "name": d.name, "mandatory": d.mandatory} for d in scheme.documents]
    return UserRoadmapResponse(
        id=existing.id,
        scheme_id=existing.scheme_id,
        scheme_name=scheme.name,
        scheme_slug=scheme.slug,
        official_portal=scheme.official_portal,
        status=existing.status,
        current_step=existing.current_step,
        total_steps=existing.total_steps,
        checklist_state=existing.checklist_state or {},
        application_reference_no=existing.application_reference_no,
        notes=existing.notes,
        application_process=scheme.application_process or [],
        required_documents=docs,
        updated_at=existing.updated_at
    )

@router.put("/roadmaps/{roadmap_id}", response_model=UserRoadmapResponse)
def update_roadmap(
    roadmap_id: int,
    data: RoadmapUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    roadmap = db.query(UserRoadmap).filter(UserRoadmap.id == roadmap_id, UserRoadmap.user_id == current_user.id).first()
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")

    if data.status is not None:
        roadmap.status = data.status
    if data.current_step is not None:
        roadmap.current_step = data.current_step
    if data.checklist_state is not None:
        roadmap.checklist_state = data.checklist_state
    if data.application_reference_no is not None:
        roadmap.application_reference_no = data.application_reference_no
    if data.notes is not None:
        roadmap.notes = data.notes

    db.commit()
    db.refresh(roadmap)

    scheme = roadmap.scheme
    docs = [{"id": d.id, "name": d.name, "mandatory": d.mandatory} for d in scheme.documents]
    return UserRoadmapResponse(
        id=roadmap.id,
        scheme_id=roadmap.scheme_id,
        scheme_name=scheme.name,
        scheme_slug=scheme.slug,
        official_portal=scheme.official_portal,
        status=roadmap.status,
        current_step=roadmap.current_step,
        total_steps=roadmap.total_steps,
        checklist_state=roadmap.checklist_state or {},
        application_reference_no=roadmap.application_reference_no,
        notes=roadmap.notes,
        application_process=scheme.application_process or [],
        required_documents=docs,
        updated_at=roadmap.updated_at
    )

@router.get("/notifications", response_model=List[NotificationResponse])
def get_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    return db.query(Notification).filter(Notification.user_id == current_user.id).order_by(Notification.created_at.desc()).all()

@router.put("/notifications/{notif_id}/read")
def mark_notification_read(
    notif_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    notif = db.query(Notification).filter(Notification.id == notif_id, Notification.user_id == current_user.id).first()
    if notif:
        notif.is_read = True
        db.commit()
    return {"status": "ok"}
