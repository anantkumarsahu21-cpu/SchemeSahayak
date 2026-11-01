import math
from typing import Dict, Any, List
from app.schemas.calculator import (
    EMICalculatorRequest, EMICalculatorResponse, MonthlyScheduleItem,
    SubsidyCalculatorRequest, SubsidyCalculatorResponse,
    FundingGapRequest, FundingGapResponse
)

class CalculatorService:
    @staticmethod
    def calculate_emi(data: EMICalculatorRequest) -> EMICalculatorResponse:
        P = float(data.loan_amount)
        annual_rate = float(data.annual_interest_rate)
        n = int(data.tenure_months)

        if P <= 0 or n <= 0:
            return EMICalculatorResponse(
                monthly_emi=0.0,
                total_interest=0.0,
                total_payment=0.0,
                principal_amount=P,
                schedule_summary=[]
            )

        monthly_rate = (annual_rate / 12.0) / 100.0

        if monthly_rate == 0:
            emi = P / n
            total_interest = 0.0
            total_payment = P
        else:
            # EMI = [P x R x (1+R)^N]/[(1+R)^N-1]
            emi = (P * monthly_rate * math.pow(1 + monthly_rate, n)) / (math.pow(1 + monthly_rate, n) - 1)
            total_payment = emi * n
            total_interest = total_payment - P

        # Generate amortisation schedule summary (e.g. sample intervals or first 12 months)
        schedule = []
        balance = P
        sample_step = max(1, n // 10)

        for month in range(1, n + 1):
            interest_for_month = balance * monthly_rate if monthly_rate > 0 else 0
            principal_for_month = emi - interest_for_month
            balance = max(0.0, balance - principal_for_month)

            if month % sample_step == 0 or month == 1 or month == n:
                schedule.append(MonthlyScheduleItem(
                    month=month,
                    principal_paid=round(principal_for_month, 2),
                    interest_paid=round(interest_for_month, 2),
                    total_payment=round(emi, 2),
                    balance_remaining=round(balance, 2)
                ))

        return EMICalculatorResponse(
            monthly_emi=round(emi, 2),
            total_interest=round(total_interest, 2),
            total_payment=round(total_payment, 2),
            principal_amount=round(P, 2),
            schedule_summary=schedule
        )

    @staticmethod
    def calculate_subsidy(data: SubsidyCalculatorRequest) -> SubsidyCalculatorResponse:
        cost = float(data.project_cost)
        is_special = data.category.upper() in ["SPECIAL", "SC", "ST", "OBC", "WOMEN", "MINORITY", "PH", "EX_SERVICEMEN"]
        is_rural = data.area_type.upper() == "RURAL"
        is_mfg = data.business_type.upper() == "MANUFACTURING"

        subsidy_pct = 15.0
        own_contrib_pct = 10.0
        notes = "Standard credit-linked subsidy rules apply."

        if data.scheme_type.upper() == "PMEGP" or data.scheme_type.upper() == "GENERAL":
            # Cap check for PMEGP: Mfg max 50L, Service max 20L
            max_cost = 5000000.0 if is_mfg else 2000000.0
            effective_cost = min(cost, max_cost)

            if is_special:
                own_contrib_pct = 5.0
                subsidy_pct = 35.0 if is_rural else 25.0
                notes = f"Special Category (Rural: 35%, Urban: 25% subsidy, 5% own contribution). Eligible project cost capped at ₹{int(max_cost/100000)} Lakhs."
            else:
                own_contrib_pct = 10.0
                subsidy_pct = 25.0 if is_rural else 15.0
                notes = f"General Category (Rural: 25%, Urban: 15% subsidy, 10% own contribution). Eligible project cost capped at ₹{int(max_cost/100000)} Lakhs."
            
            subsidy_amount = (effective_cost * subsidy_pct) / 100.0
            own_contribution_amount = (cost * own_contrib_pct) / 100.0
            bank_loan = max(0.0, cost - own_contribution_amount - subsidy_amount)
        
        elif data.scheme_type.upper() == "STANDUP_INDIA":
            # Stand-up India covers up to 85% composite loan for Women / SC / ST
            subsidy_pct = 0.0 # It's a composite loan + credit guarantee
            own_contrib_pct = 15.0
            subsidy_amount = 0.0
            own_contribution_amount = (cost * 15.0) / 100.0
            bank_loan = min(10000000.0, max(0.0, cost * 0.85))
            notes = "Stand-Up India provides up to 85% bank loan (₹10 Lakhs to ₹1 Crore) with 15% promoter margin."

        else: # MUDRA / MICRO
            subsidy_pct = 0.0
            own_contrib_pct = 10.0
            subsidy_amount = 0.0
            own_contribution_amount = (cost * 10.0) / 100.0
            bank_loan = min(2000000.0, cost * 0.90)
            notes = "Pradhan Mantri MUDRA Yojana provides collateral-free institutional credit up to ₹20 Lakhs."

        # Estimate standard 5-year EMI for the bank loan portion at ~9.5% p.a.
        rate_monthly = (9.5 / 12.0) / 100.0
        tenure = 60
        if bank_loan > 0:
            est_emi = (bank_loan * rate_monthly * math.pow(1 + rate_monthly, tenure)) / (math.pow(1 + rate_monthly, tenure) - 1)
        else:
            est_emi = 0.0

        recommended_schemes = [
            {"name": "Prime Minister's Employment Generation Programme (PMEGP)", "slug": "pmegp", "type": "Subsidy + Loan"},
            {"name": "Pradhan Mantri MUDRA Yojana (PMMY)", "slug": "pm-mudra-yojana", "type": "Collateral-Free Loan"},
            {"name": "Stand-Up India Scheme", "slug": "stand-up-india", "type": "Greenfield Enterprise Loan"}
        ]

        return SubsidyCalculatorResponse(
            project_cost=round(cost, 2),
            subsidy_percentage=round(subsidy_pct, 1),
            subsidy_amount=round(subsidy_amount, 2),
            own_contribution_percentage=round(own_contrib_pct, 1),
            own_contribution_amount=round(own_contribution_amount, 2),
            bank_loan_amount=round(bank_loan, 2),
            estimated_monthly_emi=round(est_emi, 2),
            recommended_schemes=recommended_schemes,
            eligibility_notes=notes
        )

    @staticmethod
    def calculate_funding_gap(data: FundingGapRequest) -> FundingGapResponse:
        total = float(data.project_cost)
        promoter = float(data.own_contribution)
        subsidy_rate = float(data.expected_subsidy_rate or 0.0)

        subsidy = (total * subsidy_rate) / 100.0
        covered = promoter + subsidy
        required_debt = max(0.0, total - covered)
        gap = max(0.0, total - promoter - subsidy)

        promoter_pct = (promoter / total * 100.0) if total > 0 else 0

        suggestions = []
        if promoter_pct < 10.0:
            feasibility = "HIGH_RISK"
            suggestions.append("Banks typically require at least 10% to 15% own contribution as promoter equity.")
            suggestions.append("Consider pitching for angel/incubator grants or pooling family funds.")
        elif promoter_pct < 20.0:
            feasibility = "MODERATE"
            suggestions.append("Promoter equity is sufficient for standard schemes like PMEGP and MUDRA.")
            suggestions.append("Ensure your credit score (CIBIL) is above 700 for smooth loan appraisal.")
        else:
            feasibility = "HEALTHY"
            suggestions.append("Strong promoter stake (>20%) significantly improves bank sanction probability.")
            suggestions.append("You qualify for competitive interest rates and faster credit approval.")

        if subsidy > 0:
            suggestions.append(f"Applying under a credit-linked subsidy scheme saves approx ₹{subsidy:,.0f} in capital repayment.")

        return FundingGapResponse(
            total_project_cost=round(total, 2),
            promoter_contribution=round(promoter, 2),
            estimated_subsidy=round(subsidy, 2),
            required_debt_funding=round(required_debt, 2),
            funding_gap=round(gap, 2),
            feasibility_status=feasibility,
            suggestions=suggestions
        )
