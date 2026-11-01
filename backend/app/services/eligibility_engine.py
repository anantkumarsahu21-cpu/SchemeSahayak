from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session, joinedload, selectinload
from app.models.scheme import Scheme, SchemeEligibility, SchemeDocument, SchemeLevel
from app.models.location import State
from app.schemas.matching import ProfileMatchRequest, SchemeMatchItem, MatchFactor
from app.schemas.scheme import SchemeListItemResponse, SchemeDocumentResponse

EDUCATION_RANK = {
    "NONE": 0,
    "8TH_PASS": 1,
    "8TH_PASS_FOR_LARGE_PROJECTS": 1,
    "10TH_PASS": 2,
    "12TH_PASS": 3,
    "ITI": 3,
    "DIPLOMA": 4,
    "GRADUATE": 5,
    "POST_GRADUATE": 6,
    "PHD": 7
}

class EligibilityEngine:
    @staticmethod
    def evaluate_scheme(
        scheme: Scheme,
        profile: ProfileMatchRequest,
        db_state_code_map: Dict[int, str]
    ) -> SchemeMatchItem:
        score = 100
        why_matched: List[MatchFactor] = []
        blockers: List[MatchFactor] = []
        is_hard_disqualified = False
        insufficient_info = False

        eligibility: SchemeEligibility = scheme.eligibility

        # 1. State / Geographic Match
        if scheme.level == SchemeLevel.STATE.value and scheme.state_id:
            scheme_state_code = db_state_code_map.get(scheme.state_id, "")
            if profile.state_code:
                if profile.state_code.upper() == scheme_state_code.upper():
                    why_matched.append(MatchFactor(
                        title="State Residency",
                        status="MATCH",
                        detail=f"You reside in {profile.state_code.upper()}, which matches this state-level scheme."
                    ))
                else:
                    is_hard_disqualified = True
                    score -= 80
                    blockers.append(MatchFactor(
                        title="State Boundary",
                        status="FAIL",
                        detail=f"This scheme is exclusively for residents of state ({scheme_state_code.upper()}). Your profile indicates {profile.state_code.upper()}."
                    ))
            else:
                insufficient_info = True
                score -= 15
                blockers.append(MatchFactor(
                    title="State Not Specified",
                    status="WARNING",
                    detail="Please specify your State in your profile to confirm geographic eligibility."
                ))
        elif scheme.level == SchemeLevel.CENTRAL.value:
            why_matched.append(MatchFactor(
                title="Pan-India Central Scheme",
                status="MATCH",
                detail="This is a Central Government scheme available to eligible citizens across all States and UTs."
            ))

        # 2. Age Check
        if eligibility and (eligibility.min_age is not None or eligibility.max_age is not None):
            if profile.age is not None and profile.age > 0:
                if eligibility.min_age and profile.age < eligibility.min_age:
                    is_hard_disqualified = True
                    score -= 40
                    blockers.append(MatchFactor(
                        title="Minimum Age Requirement",
                        status="FAIL",
                        detail=f"Minimum age required is {eligibility.min_age} years. Your age is {profile.age} years."
                    ))
                elif eligibility.max_age and profile.age > eligibility.max_age:
                    is_hard_disqualified = True
                    score -= 40
                    blockers.append(MatchFactor(
                        title="Maximum Age Limit",
                        status="FAIL",
                        detail=f"Maximum age limit is {eligibility.max_age} years. Your age is {profile.age} years."
                    ))
                else:
                    age_str = f"Between {eligibility.min_age or 0} and {eligibility.max_age or 'No limit'} years"
                    why_matched.append(MatchFactor(
                        title="Age Criteria",
                        status="MATCH",
                        detail=f"Your age ({profile.age} years) satisfies the required age criteria ({age_str})."
                    ))
            else:
                insufficient_info = True
                score -= 10
                blockers.append(MatchFactor(
                    title="Age Not Provided",
                    status="WARNING",
                    detail="Please provide your age to verify age-based criteria."
                ))

        # 3. Gender Check
        if eligibility and eligibility.gender and eligibility.gender.upper() != "ALL":
            required_gender = eligibility.gender.upper()
            user_gender = (profile.gender or "ALL").upper()

            if user_gender != "ALL" and user_gender != required_gender:
                is_hard_disqualified = True
                score -= 60
                blockers.append(MatchFactor(
                    title="Gender Eligibility",
                    status="FAIL",
                    detail=f"This scheme is specifically dedicated to {required_gender.lower()} beneficiaries."
                ))
            elif user_gender == required_gender:
                why_matched.append(MatchFactor(
                    title="Gender Match",
                    status="MATCH",
                    detail=f"Scheme specifically supports {required_gender.lower()} applicants."
                ))

        # 4. Income Ceiling Check
        if eligibility and eligibility.max_income is not None:
            if profile.annual_income is not None:
                if profile.annual_income > eligibility.max_income:
                    is_hard_disqualified = True
                    score -= 50
                    blockers.append(MatchFactor(
                        title="Income Ceiling Exceeded",
                        status="FAIL",
                        detail=f"Maximum family income allowed is ₹{eligibility.max_income:,.0f}/year. Your declared income is ₹{profile.annual_income:,.0f}/year."
                    ))
                else:
                    why_matched.append(MatchFactor(
                        title="Income Criteria Satisfied",
                        status="MATCH",
                        detail=f"Your annual income (₹{profile.annual_income:,.0f}) is within the scheme limit of ₹{eligibility.max_income:,.0f}."
                    ))
            else:
                insufficient_info = True
                score -= 10
                blockers.append(MatchFactor(
                    title="Income Certificate Required",
                    status="WARNING",
                    detail=f"Income must be under ₹{eligibility.max_income:,.0f}/year. Income certificate will be required."
                ))

        # 5. Caste / Social Category Check
        if eligibility and eligibility.caste_categories:
            valid_castes = [c.upper() for c in eligibility.caste_categories]
            user_caste = (profile.caste_category or "GENERAL").upper()

            if "ALL" not in valid_castes:
                if user_caste in valid_castes:
                    why_matched.append(MatchFactor(
                        title="Category Eligibility",
                        status="MATCH",
                        detail=f"Your category ({user_caste}) is eligible for this scheme."
                    ))
                else:
                    is_hard_disqualified = True
                    score -= 50
                    blockers.append(MatchFactor(
                        title="Category Restriction",
                        status="FAIL",
                        detail=f"This scheme is specifically designated for {', '.join(valid_castes)} categories. Your selected category is {user_caste}."
                    ))

        # 6. Occupation / Target Role Match
        if eligibility and eligibility.occupations:
            valid_occupations = [o.upper() for o in eligibility.occupations]
            user_occ = (profile.occupation or profile.employment_status or "").upper()

            if "ALL" in valid_occupations:
                why_matched.append(MatchFactor(
                    title="Target Group",
                    status="MATCH",
                    detail="Open to all citizen occupations."
                ))
            elif any(occ in user_occ for occ in valid_occupations):
                why_matched.append(MatchFactor(
                    title="Occupation Match",
                    status="MATCH",
                    detail=f"Your occupation profile matches target beneficiaries ({', '.join(valid_occupations)})."
                ))
            elif user_occ:
                # Soft penalty for mismatched role
                score -= 20
                blockers.append(MatchFactor(
                    title="Target Occupation",
                    status="WARNING",
                    detail=f"Scheme primarily targets {', '.join(valid_occupations)}. Your current occupation is listed as {user_occ}."
                ))

        # 7. Education Level Check
        if eligibility and eligibility.min_education and eligibility.min_education != "NONE":
            req_rank = EDUCATION_RANK.get(eligibility.min_education, 0)
            user_rank = EDUCATION_RANK.get((profile.education_level or "NONE").upper(), 0)

            if user_rank < req_rank:
                score -= 25
                blockers.append(MatchFactor(
                    title="Educational Requirement",
                    status="WARNING",
                    detail=f"Scheme requires minimum education: {eligibility.min_education.replace('_', ' ')}."
                ))
            else:
                why_matched.append(MatchFactor(
                    title="Educational Qualification",
                    status="MATCH",
                    detail=f"Your qualification meets or exceeds the required level ({eligibility.min_education.replace('_', ' ')})."
                ))

        # 8. Area Type (Rural / Urban)
        if eligibility and eligibility.rural_urban and eligibility.rural_urban.upper() != "BOTH":
            req_area = eligibility.rural_urban.upper()
            user_area = (profile.area_type or "RURAL").upper()
            if req_area != user_area:
                score -= 25
                blockers.append(MatchFactor(
                    title="Location Scope",
                    status="WARNING",
                    detail=f"Scheme is specifically intended for {req_area.lower()} areas. Your profile is set to {user_area.lower()}."
                ))

        # Ensure bounds on final score
        final_score = max(0, min(100, score))
        if is_hard_disqualified:
            final_score = min(final_score, 35)

        # Determine status label
        if is_hard_disqualified:
            status = "NOT_ELIGIBLE"
        elif final_score >= 85:
            status = "ELIGIBLE"
        elif final_score >= 70:
            status = "LIKELY_ELIGIBLE"
        elif final_score >= 45:
            status = "POSSIBLY_ELIGIBLE"
        elif insufficient_info:
            status = "INSUFFICIENT_INFO"
        else:
            status = "NOT_ELIGIBLE"

        # Construct Next Steps
        next_steps = [
            f"Review official guidelines and verified terms from {scheme.source_authority}.",
            "Verify all required identity, income, and category documents in original.",
            f"Submit digital or offline application through {scheme.official_portal or 'authorized district center'}."
        ]

        # Construct Document list
        docs = [
            SchemeDocumentResponse(
                id=doc.id,
                scheme_id=scheme.id,
                name=doc.name,
                mandatory=doc.mandatory,
                description=doc.description,
                upload_instructions=doc.upload_instructions
            )
            for doc in scheme.documents
        ]

        # Construct Scheme list item summary
        scheme_summary = SchemeListItemResponse(
            id=scheme.id,
            slug=scheme.slug,
            name=scheme.name,
            ministry=scheme.ministry,
            level=scheme.level,
            category_name=scheme.category.name if scheme.category else "General Support",
            category_slug=scheme.category.slug if scheme.category else "general",
            category_icon=scheme.category.icon if scheme.category else "Briefcase",
            summary=scheme.summary,
            benefits_summary=scheme.benefits_summary or "Financial support assistance",
            benefit_type=scheme.benefit_type or "SUBSIDY",
            application_mode=scheme.application_mode or "ONLINE",
            official_portal=scheme.official_portal,
            source_authority=scheme.source_authority or "Government of India",
            last_verified_at=scheme.last_verified_at or datetime.now(timezone.utc),
            verification_status=scheme.verification_status or "VERIFIED",
            state_name=scheme.state.name if scheme.state else "All India",
            tags=scheme.tags or [],
            is_active=scheme.is_active
        )

        return SchemeMatchItem(
            scheme=scheme_summary,
            match_score=final_score,
            eligibility_status=status,
            why_matched=why_matched,
            blockers=blockers,
            next_steps=next_steps,
            required_documents=docs,
            estimated_benefit=scheme.benefits_summary
        )

    @classmethod
    def match_all(cls, db: Session, profile: ProfileMatchRequest) -> List[SchemeMatchItem]:
        query = db.query(Scheme).filter(Scheme.is_active == True).options(
            joinedload(Scheme.category),
            joinedload(Scheme.state),
            joinedload(Scheme.eligibility),
            selectinload(Scheme.documents)
        )
        schemes = query.all()

        states = db.query(State).all()
        state_map = {s.id: s.code for s in states}

        results: List[SchemeMatchItem] = []
        for scheme in schemes:
            match_item = cls.evaluate_scheme(scheme, profile, state_map)
            results.append(match_item)

        # Sort results by match_score descending
        results.sort(key=lambda x: x.match_score, reverse=True)
        return results
