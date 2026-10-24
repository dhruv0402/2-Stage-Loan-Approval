"""Account Aggregator (AA) & Bank Statement Cash Flow Underwriting Engine.
Extracts cash flow stability, Average Bank Balance (ABB), and NACH bounce penalty signals.
"""
from typing import TypedDict

class CashFlowProfile(TypedDict):
    average_bank_balance: float
    monthly_inflow: float
    nach_bounce_count_last_6m: int
    salary_regularity_score: float  # 0.0 to 1.0
    discretionary_expense_ratio: float  # 0.0 to 1.0

class CashFlowAssessment(TypedDict):
    cash_flow_health_score: float  # 0 to 100
    cash_flow_tier: str  # Prime Cash Flow, Stable, High Volatility, Stressed
    nach_bounce_penalty_applied: bool
    recommended_capacity_multiplier: float
    advisory_notes: list[str]

def evaluate_cash_flow(profile: CashFlowProfile, requested_emi: float) -> CashFlowAssessment:
    abb = profile['average_bank_balance']
    inflow = profile['monthly_inflow']
    bounces = profile['nach_bounce_count_last_6m']
    regularity = profile['salary_regularity_score']
    expense_ratio = profile['discretionary_expense_ratio']

    # 1. EMI to Average Bank Balance Coverage Ratio
    coverage_ratio = abb / (requested_emi + 1.0)
    
    # 2. Base Cash Flow Score (0 to 100)
    score = (
        min(40.0, coverage_ratio * 15.0) +
        (regularity * 30.0) +
        max(0.0, (1.0 - expense_ratio) * 30.0)
    )

    advisory_notes = []

    # 3. NACH / ECS Bounce Penalties (Severe credit distress indicator)
    penalty_applied = False
    if bounces > 0:
        penalty_applied = True
        bounce_deduction = min(40.0, bounces * 15.0)
        score = max(10.0, score - bounce_deduction)
        advisory_notes.append(f"Recorded {bounces} NACH/ECS return(s) in last 6 months (-{bounce_deduction:.0f} pts).")
    else:
        advisory_notes.append("Clean 6-month banking record: Zero NACH/inward cheque bounces.")

    if coverage_ratio >= 2.5:
        advisory_notes.append(f"Strong buffer: Average bank balance covers {coverage_ratio:.1f}x the proposed EMI.")
    elif coverage_ratio < 1.0:
        advisory_notes.append("Tight liquidity: Average balance is less than 1 monthly EMI.")

    # 4. Cash Flow Tiering & Sizing Multiplier
    if score >= 75:
        tier = "Prime Cash Flow"
        multiplier = 1.0
    elif score >= 55:
        tier = "Stable Cash Flow"
        multiplier = 0.85
    elif score >= 40:
        tier = "Volatile Cash Flow"
        multiplier = 0.65
    else:
        tier = "High Distress Risk"
        multiplier = 0.0

    return {
        'cash_flow_health_score': round(score, 1),
        'cash_flow_tier': tier,
        'nach_bounce_penalty_applied': penalty_applied,
        'recommended_capacity_multiplier': multiplier,
        'advisory_notes': advisory_notes
    }
