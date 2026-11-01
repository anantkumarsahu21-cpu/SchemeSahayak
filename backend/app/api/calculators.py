from typing import Any
from fastapi import APIRouter
from app.schemas.calculator import (
    EMICalculatorRequest, EMICalculatorResponse,
    SubsidyCalculatorRequest, SubsidyCalculatorResponse,
    FundingGapRequest, FundingGapResponse
)
from app.services.calculator_service import CalculatorService

router = APIRouter(prefix="/calculators", tags=["Financial & Subsidy Calculators"])

@router.post("/emi", response_model=EMICalculatorResponse)
def calculate_emi(data: EMICalculatorRequest) -> Any:
    return CalculatorService.calculate_emi(data)

@router.post("/subsidy", response_model=SubsidyCalculatorResponse)
def calculate_subsidy(data: SubsidyCalculatorRequest) -> Any:
    return CalculatorService.calculate_subsidy(data)

@router.post("/funding-gap", response_model=FundingGapResponse)
def calculate_funding_gap(data: FundingGapRequest) -> Any:
    return CalculatorService.calculate_funding_gap(data)
