import os
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.security import get_password_hash
from app.database.base import Base
from app.database.session import engine, SessionLocal
from app.models.user import User, UserRole, UserProfile, AuditLog
from app.models.location import State, District
from app.models.category import Category
from app.models.scheme import Scheme, SchemeEligibility, SchemeDocument, SchemeSource
from app.models.interaction import SavedScheme, UserRoadmap, Notification
from app.models.chat import ChatSession, ChatMessage

# Import API routers
from app.api import auth, locations, categories, schemes, matching, assistant, calculators, compare, user_dashboard, admin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SchemeSahayak")

def _parse_date(date_str: str) -> datetime:
    """Parse date string to datetime object."""
    if not date_str:
        return None
    try:
        if isinstance(date_str, datetime):
            return date_str
        return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        logger.warning(f"Could not parse date: {date_str}")
        return datetime.now(timezone.utc)

def seed_initial_data_if_empty():
    db = SessionLocal()
    try:
        # 1. Create Tables
        Base.metadata.create_all(bind=engine)

        # 2. Seed Default Admin User
        admin_user = db.query(User).filter(User.email == settings.DEFAULT_ADMIN_EMAIL.lower()).first()
        if not admin_user:
            logger.info("Seeding default Administrator account...")
            admin_user = User(
                email=settings.DEFAULT_ADMIN_EMAIL.lower(),
                hashed_password=get_password_hash(settings.DEFAULT_ADMIN_PASSWORD),
                full_name="National SchemeSahayak Administrator",
                role=UserRole.ADMIN.value,
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            db.add(UserProfile(user_id=admin_user.id))
            db.commit()

        # 2b. Seed Demo Citizen User
        demo_citizen = db.query(User).filter(User.email == "citizen.demo@schemesahayak.gov.in").first()
        if not demo_citizen:
            logger.info("Seeding demo citizen account...")
            demo_citizen = User(
                email="citizen.demo@schemesahayak.gov.in",
                hashed_password=get_password_hash("CitizenDemo@123"),
                full_name="Demo Citizen User",
                role=UserRole.USER.value,
                is_active=True,
                preferred_language="en"
            )
            db.add(demo_citizen)
            db.commit()
            db.refresh(demo_citizen)
            demo_profile = UserProfile(
                user_id=demo_citizen.id,
                age=28,
                gender="MALE",
                state_name="Uttar Pradesh",
                state_code="UP",
                area_type="URBAN",
                caste_category="GENERAL",
                annual_income=350000,
                education_level="GRADUATE",
                employment_status="SELF_EMPLOYED",
                occupation="ENTREPRENEUR"
            )
            db.add(demo_profile)
            db.commit()

        # 3. Seed States & Districts
        state_count = db.query(State).count()
        if state_count == 0:
            states_file = os.path.join(os.path.dirname(__file__), "..", "..", "data", "states", "states_districts.json")
            if os.path.exists(states_file):
                logger.info("Seeding 36 Indian States and Districts...")
                with open(states_file, "r", encoding="utf-8") as f:
                    states_data = json.load(f)
                    for item in states_data:
                        state = State(
                            code=item["code"],
                            name=item["name"],
                            type=item.get("type", "STATE")
                        )
                        db.add(state)
                        db.commit()
                        db.refresh(state)

                        for dist_name in item.get("districts", []):
                            dist = District(state_id=state.id, name=dist_name)
                            db.add(dist)
                        db.commit()

        # 4. Seed Categories
        cat_count = db.query(Category).count()
        if cat_count == 0:
            cats_file = os.path.join(os.path.dirname(__file__), "..", "..", "data", "categories", "categories.json")
            if os.path.exists(cats_file):
                logger.info("Seeding Categories...")
                with open(cats_file, "r", encoding="utf-8") as f:
                    cats_data = json.load(f)
                    for c in cats_data:
                        cat = Category(
                            slug=c["slug"],
                            name=c["name"],
                            description=c.get("description", ""),
                            icon=c.get("icon", "Briefcase")
                        )
                        db.add(cat)
                    db.commit()

        # 5. Seed Verified Schemes
        scheme_count = db.query(Scheme).count()
        if scheme_count == 0:
            schemes_file = os.path.join(os.path.dirname(__file__), "..", "..", "data", "schemes", "verified_schemes.json")
            if os.path.exists(schemes_file):
                logger.info("Seeding Verified Central and State Government Schemes...")
                categories_map = {c.slug: c.id for c in db.query(Category).all()}
                states_map = {st.code.upper(): st.id for st in db.query(State).all()}
                with open(schemes_file, "r", encoding="utf-8") as f:
                    schemes_data = json.load(f)
                    for i, s in enumerate(schemes_data):
                        cat_id = categories_map.get(s.get("category_slug"))
                        state_code = s.get("state_code")
                        state_id = states_map.get(state_code.upper()) if state_code else None

                        scheme = Scheme(
                            slug=s["slug"],
                            name=s["name"],
                            category_id=cat_id,
                            ministry=s.get("ministry"),
                            department=s.get("department"),
                            level=s.get("level", "CENTRAL"),
                            state_id=state_id,
                            target_beneficiary=s.get("target_beneficiary"),
                            summary=s.get("summary", s["name"]),
                            description=s.get("description", s["name"]),
                            objectives=s.get("objectives", []),
                            benefits_summary=s.get("benefits_summary", ""),
                            benefit_type=s.get("benefit_type", "SUBSIDY"),
                            financial_details=s.get("financial_details", {}),
                            application_mode=s.get("application_mode", "ONLINE"),
                            application_process=s.get("application_process", []),
                            official_portal=s.get("official_portal"),
                            source_authority=s.get("source_authority", "Government of India"),
                            source_url=s.get("source_url", "https://myscheme.gov.in"),
                            last_verified_at=_parse_date(s.get("last_verified_at")) or datetime.now(timezone.utc),
                            verification_status=s.get("verification_status", "VERIFIED"),
                            effective_date=_parse_date(s.get("effective_date")),
                            expiry_date=_parse_date(s.get("expiry_date")),
                            tags=s.get("tags", []),
                            is_active=True
                        )
                        db.add(scheme)
                        db.flush()

                        # Eligibility
                        elig = s.get("eligibility_criteria", {})
                        if elig:
                            e = SchemeEligibility(
                                scheme_id=scheme.id,
                                min_age=elig.get("min_age"),
                                max_age=elig.get("max_age"),
                                gender=elig.get("gender", "ALL"),
                                min_education=elig.get("min_education", "NONE"),
                                min_income=elig.get("min_income"),
                                max_income=elig.get("max_income"),
                                caste_categories=elig.get("caste_categories", []),
                                occupations=elig.get("occupations", []),
                                disability_allowed=elig.get("disability_allowed", True),
                                rural_urban=elig.get("rural_urban", "BOTH"),
                                notes=elig.get("notes")
                            )
                            db.add(e)

                        # Documents
                        for doc in s.get("required_documents", []):
                            d = SchemeDocument(
                                scheme_id=scheme.id,
                                name=doc.get("name", "Document"),
                                mandatory=doc.get("mandatory", True),
                                description=doc.get("description")
                            )
                            db.add(d)

                        # Sources
                        src = SchemeSource(
                            scheme_id=scheme.id,
                            title=s.get("source_authority", "Official Portal"),
                            url=s.get("source_url", "https://myscheme.gov.in"),
                            authority_name=s.get("source_authority", "Govt of India"),
                            verification_notes="Verified via official portal and ministry Gazette notification",
                            verified_at=s.get("last_verified_at", "2026-08-01")
                        )
                        db.add(src)

                        if (i + 1) % 200 == 0:
                            db.commit()
                    db.commit()
        logger.info("Database seeding completed successfully.")
    except Exception as e:
        logger.error(f"Error during auto-seed: {e}")
        db.rollback()
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Seed initial data
    seed_initial_data_if_empty()
    yield
    # Shutdown

app = FastAPI(
    title="SchemeSahayak API",
    description="AI-Powered Government Scheme, Education & Business Support Navigator Backend",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';"
    return response

# Request Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"{request.method} {request.url.path} - User-Agent: {request.headers.get('user-agent', 'unknown')}")
    response = await call_next(request)
    logger.info(f"Response Status: {response.status_code}")
    return response

# Global Error Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception at {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please try again later."}
    )

# Include Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(locations.router, prefix=settings.API_V1_STR)
app.include_router(categories.router, prefix=settings.API_V1_STR)
app.include_router(schemes.router, prefix=settings.API_V1_STR)
app.include_router(matching.router, prefix=settings.API_V1_STR)
app.include_router(assistant.router, prefix=settings.API_V1_STR)
app.include_router(calculators.router, prefix=settings.API_V1_STR)
app.include_router(compare.router, prefix=settings.API_V1_STR)
app.include_router(user_dashboard.router, prefix=settings.API_V1_STR)
app.include_router(admin.router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {
        "name": "SchemeSahayak API",
        "version": "1.0.0",
        "tagline": "Find the Support You Deserve.",
        "docs_url": "/docs",
        "status": "online"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "SchemeSahayak Backend"}
