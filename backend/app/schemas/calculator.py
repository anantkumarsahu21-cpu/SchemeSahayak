from typing import List, Optional, Dict, Any
from pydantic import BaseModel

# EMI Calculator
class EMICalculatorRequest(BaseModel):
    loan_amount: float
    annual_interest_rate: float
    tenure_months: int

class MonthlyScheduleItem(BaseModel):
    month: int
    principal_paid: float
    interest_paid: float
    total_payment: float
    balance_remaining: float

class EMICalculatorResponse(BaseModel):
    monthly_emi: float
    total_interest: float
    total_payment: float
    principal_amount: float
    schedule_summary: List[MonthlyScheduleItem] = []

# Subsidy & PMEGP / Standup Calculator
class SubsidyCalculatorRequest(BaseModel):
    scheme_type: str # PMEGP, MUDRA, STANDUP_INDIA, GENERAL
    business_type: str # MANUFACTURING, SERVICE
    area_type: str # RURAL, URBAN
    category: str # GENERAL, SPECIAL (SC/ST/OBC/Women/Minority/Ex-servicemen/PH)
    project_cost: float
    own_funds: Optional[float] = None

class SubsidyCalculatorResponse(BaseModel):
    project_cost: float
    subsidy_percentage: float
    subsidy_amount: float
    own_contribution_percentage: float
    own_contribution_amount: float
    bank_loan_amount: float
    estimated_monthly_emi: float
    recommended_schemes: List[Dict[str, Any]] = []
    eligibility_notes: str

# Business Funding Gap
class FundingGapRequest(BaseModel):
    project_cost: float
    own_contribution: float
    expected_subsidy_rate: Optional[float] = 0.0
    business_stage: Optional[str] = "NEW"

class FundingGapResponse(BaseModel):
    total_project_cost: float
    promoter_contribution: float
    estimated_subsidy: float
    required_debt_funding: float
    funding_gap: float
    feasibility_status: str # HEALTHY, MODERATE, HIGH_RISK
    suggestions: List[str]
