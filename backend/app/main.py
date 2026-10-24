"""Portfolio & Digital Lending Underwriting Simulator API.
Supports multi-currency (INR ₹ with RBI Guidelines & CIBIL, USD $ with FICO),
Basel III Expected Loss modeling, TreeSHAP explainability, and Prescriptive Counterfactual Recourse.
"""
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path
from typing import Literal
import math
import joblib
import pandas as pd
import hashlib
import json
from fastapi import FastAPI, HTTPException, Request, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import os
from backend.ml.features import PURPOSES, HOME_TYPES, clean_frame, FEATURES, AMOUNT_FEATURES
from backend.app.db import init_db, save_application_and_assessment, list_recent_applications
from backend.ml.cashflow import evaluate_cash_flow
from backend.ml.drift import get_drift_report
from backend.app.cache import check_rate_limit, cache_get, cache_set, get_client_identifier


ROOT = Path(__file__).resolve().parents[2]

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title='Credence AI — Autonomous Credit Decision & Risk Engine', version='0.2.0', lifespan=lifespan)

# CORS Configuration: restrict to localhost, internal network, and custom CORS_ORIGINS
_cors_origins_env = os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000')
_allowed_origins = [orig.strip() for orig in _cors_origins_env.split(',') if orig.strip()]

app.add_middleware(CORSMiddleware,
                   allow_origins=_allowed_origins,
                   allow_credentials=True,
                   allow_methods=['GET', 'POST', 'OPTIONS'],
                   allow_headers=['Content-Type', 'Authorization', 'X-API-Key', 'X-Forwarded-For'])

# API Key security scheme for RBAC / internal service integration
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def verify_access_token(api_key: str | None = Security(api_key_header)):
    """Optional API key verification: allows unauthenticated dev access while supporting token authentication in production."""
    required_key = os.getenv('CREDENCE_API_KEY')
    if required_key and api_key != required_key:
        raise HTTPException(status_code=401, detail='Invalid or missing X-API-Key header')
    return api_key or 'anonymous'



PurposeType = Literal['debt_consolidation', 'credit_card', 'home_improvement', 'major_purchase',
                      'small_business', 'medical', 'car', 'other']
HomeOwnershipType = Literal['MORTGAGE', 'RENT', 'OWN']
TermMonthsType = Literal[36, 60]
CurrencyType = Literal['INR', 'USD']

class Application(BaseModel):
    currency: CurrencyType = Field(default='INR', description='Currency: INR (₹) or USD ($)')
    requested_amount: float = Field(ge=1000, le=50000000, description='Requested loan amount')
    annual_income: float = Field(ge=1000, le=500000000, description='Verified annual income')
    dti: float = Field(ge=0, le=100, description='Debt-to-income or FOIR ratio (0-100%)')
    cibil: int | None = Field(default=None, ge=300, le=900, description='CIBIL score (300-900)')
    fico: int | None = Field(default=None, ge=300, le=850, description='FICO score (300-850)')
    employment_years: float = Field(ge=0, le=50, description='Years of employment')
    term_months: TermMonthsType = Field(default=36, description='Loan tenure in months')
    purpose: PurposeType = Field(default='debt_consolidation', description='Stated loan purpose')
    revolving_utilization: float = Field(ge=0, le=250, description='Credit card / line utilization percentage')
    open_accounts: int = Field(ge=0, le=100, description='Number of currently open credit lines')
    public_bankruptcies: int = Field(ge=0, le=20, description='Public bankruptcies / legal suits')
    revolving_balance: float = Field(ge=0, le=100000000, description='Total revolving credit card balance')
    home_ownership: HomeOwnershipType = Field(description='Housing status')
    average_bank_balance: float | None = Field(default=None, ge=0, description='Average Bank Balance (ABB)')
    nach_bounce_count_last_6m: int = Field(default=0, ge=0, le=20, description='Count of NACH/ECS return bounces')
    salary_regularity_score: float = Field(default=0.95, ge=0.0, le=1.0, description='Salary credit regularity index (0 to 1)')
    discretionary_expense_ratio: float = Field(default=0.40, ge=0.0, le=1.0, description='Discretionary expenses ratio')


@lru_cache
def bundle():
    path = ROOT / 'models/bundle.joblib'
    if not path.exists():
        raise HTTPException(status_code=503, detail='Model bundle missing. Run python -m backend.ml.train first.')
    return joblib.load(path)


def payment(principal: float | None, monthly_rate: float, months: int) -> float:
    if not principal or principal <= 0 or months <= 0:
        return 0.0
    if monthly_rate <= 0:
        return principal / months
    denom = 1 - (1 + monthly_rate) ** (-months)
    return principal * monthly_rate / denom if denom != 0 else principal / months


def row_for(amount: float, annual_inc: float, dti: float, fico: int, emp_length: float,
            term_months: int, purpose: str, revol_util: float, open_acc: int,
            pub_rec_bankruptcies: int, revol_bal: float, home_ownership: str) -> pd.DataFrame:
    return clean_frame(pd.DataFrame([dict(
        loan_amnt=amount, annual_inc=annual_inc, dti=dti,
        fico_range_low=fico, emp_length=emp_length,
        term=f'{term_months} months', purpose=purpose, revol_util=revol_util,
        open_acc=open_acc, pub_rec_bankruptcies=pub_rec_bankruptcies,
        revol_bal=revol_bal, home_ownership=home_ownership
    )]))


FEATURE_LABELS = {
    'fico_range_low': 'Credit Score (CIBIL / FICO)',
    'dti': 'Debt-to-Income / FOIR Ratio',
    'annual_inc': 'Annual Net Take-Home Income',
    'emp_length': 'Employment Stability (Years)',
    'loan_amnt': 'Requested Loan Principal',
    'revol_util': 'Revolving Card Line Utilization',
    'open_acc': 'Active Credit Tradelines',
    'pub_rec_bankruptcies': 'Public Bankruptcies / Derogatory Records',
    'revol_bal': 'Total Outstanding Revolving Balance',
    'purpose': 'Stated Borrowing Purpose',
    'term': 'Loan Repayment Tenure',
    'home_ownership': 'Residential Ownership Status'
}


def compute_kfs(offer: float, apr: float, term_months: int, currency: str) -> dict:
    if not offer or offer <= 0:
        return {}
    processing_fee_rate = 0.015  # 1.5% upfront processing fee
    processing_fee = round(offer * processing_fee_rate, 2)
    gst_on_fee = round(processing_fee * 0.18, 2)  # 18% GST on financial processing
    net_disbursed = round(offer - (processing_fee + gst_on_fee), 2)
    rate = apr / 12
    emi = round(payment(offer, rate, term_months), 2)
    total_repayment = round(emi * term_months, 2)
    total_interest = round(total_repayment - offer, 2)
    return {
        'sanctioned_amount': offer,
        'processing_fee_rate_pct': 1.5,
        'processing_fee': processing_fee,
        'gst_on_processing_fee': gst_on_fee,
        'net_disbursed_amount': net_disbursed,
        'monthly_emi': emi,
        'tenure_months': term_months,
        'annualized_percentage_rate_pct': round(apr * 100, 2),
        'total_interest_payable': total_interest,
        'total_repayment_amount': total_repayment,
        'regulatory_standard': 'RBI Digital Lending Guidelines (KFS Framework)' if currency == 'INR' else 'CFPB Truth in Lending (TILA)'
    }


def compute_counterfactual_recourse(b, row, current_prob: float, currency: str, term_months: int,
                                   current_fico: int, revol_util: float, dti: float) -> list[dict]:
    recourse = []
    symbol = '₹' if currency == 'INR' else '$'
    
    # Action 1: Tenure extension (36 -> 60)
    if term_months == 36:
        probe_term = row.copy()
        probe_term['term'] = pd.Categorical(['60'], categories=['36', '60'])
        prob_term = float(b['classifier'].predict_proba(probe_term[FEATURES])[0, 1])
        recourse.append({
            'action': 'Extend Tenure to 60 Months',
            'rationale': f'Spreads repayment burden, reducing monthly obligation ratio and expanding borrowing capacity under {"RBI 50% FOIR" if currency == "INR" else "CFPB ATR"}.',
            'projected_impact': f"{(prob_term - current_prob) * 100:+.1f} pp eligibility score",
            'category': 'Tenure'
        })

    # Action 2: Revolving Utilization Reduction
    if revol_util > 30:
        probe_util = row.copy()
        probe_util['revol_util'] = 25.0
        prob_util = float(b['classifier'].predict_proba(probe_util[FEATURES])[0, 1])
        diff = round((prob_util - current_prob) * 100, 1)
        recourse.append({
            'action': 'Pay Down Card Balance to under 30% Utilization',
            'rationale': f'Current card usage is {revol_util:.0f}%. Dropping usage to 25% sharply improves creditworthiness and unlocks lower interest spreads.',
            'projected_impact': f"{diff:+.1f} pp eligibility score",
            'category': 'Card Utilization'
        })

    # Action 3: Credit Score Tier Upgrade
    if current_fico < 750:
        probe_fico = row.copy()
        probe_fico['fico_range_low'] = min(850.0, current_fico + 35)
        prob_fico = float(b['classifier'].predict_proba(probe_fico[FEATURES])[0, 1])
        diff_fico = round((prob_fico - current_prob) * 100, 1)
        score_label = 'CIBIL' if currency == 'INR' else 'FICO'
        recourse.append({
            'action': f'Improve {score_label} by ~35 Points',
            'rationale': f'Resolving any contested tradelines and maintaining consecutive on-time payments elevates your credit tier to Prime status.',
            'projected_impact': f"{diff_fico:+.1f} pp eligibility score",
            'category': 'Credit Bureau'
        })
        
    return recourse[:3]


@app.get('/api/health')
def health():
    return {'status': 'ready' if (ROOT / 'models/bundle.joblib').exists() else 'untrained'}


@app.get('/api/model-card')
def model_card():
    b = bundle()
    return {'metrics': b['metrics'],
            'threshold': b['config']['model']['decision_threshold'],
            'assumed_apr': b['config']['policy']['assumed_apr'],
            'supported_currencies': ['INR', 'USD'],
            'regulatory_standards': ['RBI Digital Lending Guidelines (India)', 'Basel III Internal Ratings-Based (IRB) Expected Loss', 'Equal Credit Opportunity Act (ECOA)'],
            'limitations': ['Funded-loan repayment probability is not an approval probability.',
                            'Historical amount regression is an empirical benchmark, not an optimal offer label.',
                            'Pricing incorporates Probability of Default (PD) and Expected Loss (EL) modeling under institutional risk spreads.']}


@app.post('/api/assess')
def assess(a: Application, request: Request, auth_token: str = Depends(verify_access_token)):
    client_id = get_client_identifier(request)
    if not check_rate_limit(client_id, max_requests=100, window_seconds=60):
        raise HTTPException(429, 'Rate limit exceeded: Too many evaluation requests. Please wait 1 minute.')

    cache_key = f"assess:{hashlib.md5(a.model_dump_json().encode()).hexdigest()}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    if a.term_months not in (36, 60) or a.purpose not in PURPOSES or a.home_ownership not in HOME_TYPES:
        raise HTTPException(422, 'term, purpose or home ownership is unsupported')

    
    # Resolve Credit Score (CIBIL 300-900 or FICO 300-850)
    if a.cibil is not None:
        effective_fico = round(300 + (a.cibil - 300) * (550 / 600))
    elif a.fico is not None:
        effective_fico = a.fico
    else:
        # Default prime credit score if omitted
        effective_fico = 720

    b = bundle()
    cfg = b['config']['policy']
    threshold = b['config']['model']['decision_threshold']
    margin = b['config']['model']['review_margin']

    # Currency normalization for model inference scale
    FX = 80.0 if a.currency == 'INR' else 1.0
    min_offer = cfg['min_offer'] * FX
    max_offer = cfg['max_offer'] * FX
    step_size = 5000 if a.currency == 'INR' else 50

    model_amount = a.requested_amount / FX
    model_income = a.annual_income / FX
    model_revol = a.revolving_balance / FX

    row = row_for(model_amount, model_income, a.dti, effective_fico, a.employment_years,
                  a.term_months, a.purpose, a.revolving_utilization, a.open_accounts,
                  a.public_bankruptcies, model_revol, a.home_ownership)
                  
    repayment_probability = float(b['classifier'].predict_proba(row[FEATURES])[0, 1])
    probability_of_default = round(1.0 - repayment_probability, 4)

    # Institutional Risk-Adjusted Pricing
    if a.currency == 'INR':
        # RBI Repo Rate (6.5%) + Bank Cost of Funds/OpEx (4.0%) = 10.5% Prime Base
        base_rate = 0.105
        risk_spread = probability_of_default * 0.18
        risk_adjusted_apr = round(min(0.24, max(0.105, base_rate + risk_spread)), 4)
        # RBI FOIR Guideline: 50% max permissible debt-service ratio
        monthly_income = a.annual_income / 12
        max_payment = max(0.0, min(0.50 * monthly_income, (0.50 - a.dti / 100) * monthly_income))
    else:
        # US Fed Funds Base + Prime Spread
        base_rate = cfg['assumed_apr'] * 0.70
        risk_spread = probability_of_default * 0.25
        risk_adjusted_apr = round(min(0.3599, max(0.0599, base_rate + risk_spread)), 4)
        monthly_income = a.annual_income / 12
        max_payment = max(0.0, min(cfg['max_payment_share_of_monthly_income'] * monthly_income,
                                    (0.36 - a.dti / 100) * monthly_income))

    rate = risk_adjusted_apr / 12
    annuity_factor = ((1 + rate) ** a.term_months - 1) / (rate * (1 + rate) ** a.term_months) if rate else a.term_months
    affordability_cap = max_payment * annuity_factor

    historical_amount = None
    offer = None
    if repayment_probability < threshold - margin or affordability_cap < min_offer:
        status = 'outside_demo_policy'
    elif repayment_probability < threshold:
        status = 'review'
    else:
        model_hist_amount = float(b['amount_regressor'].predict(row[AMOUNT_FEATURES])[0])
        historical_amount = model_hist_amount * FX
        candidate = math.floor(min(a.requested_amount, historical_amount, affordability_cap, max_offer) / step_size) * step_size
        if candidate < min_offer:
            status = 'outside_demo_policy'
        else:
            status = 'eligible_for_simulated_offer'
            offer = candidate

    # Account Aggregator Cash Flow Assessment
    monthly_inflow = a.annual_income / 12
    abb = a.average_bank_balance if a.average_bank_balance is not None else monthly_inflow * 0.40
    cf_profile = {
        'average_bank_balance': abb,
        'monthly_inflow': monthly_inflow,
        'nach_bounce_count_last_6m': a.nach_bounce_count_last_6m,
        'salary_regularity_score': a.salary_regularity_score,
        'discretionary_expense_ratio': a.discretionary_expense_ratio
    }
    candidate_emi = (offer * (rate / (1 - (1 + rate)**(-a.term_months)))) if offer and rate else (a.requested_amount / a.term_months)
    cash_flow_eval = evaluate_cash_flow(cf_profile, candidate_emi)
    if offer and cash_flow_eval['recommended_capacity_multiplier'] < 1.0:
        if cash_flow_eval['recommended_capacity_multiplier'] == 0.0:
            status = 'outside_demo_policy'
            offer = None
        else:
            offer = math.floor((offer * cash_flow_eval['recommended_capacity_multiplier']) / step_size) * step_size

    payment_amount = round(payment(offer, rate, a.term_months), 2) if offer else None

    # Basel II/III Expected Loss (EL = PD * EAD * LGD, LGD=45%)
    loss_given_default = 0.45
    expected_loss = round(offer * probability_of_default * loss_given_default, 2) if offer else None

    # RBI Key Fact Statement (KFS)
    kfs = compute_kfs(offer, risk_adjusted_apr, a.term_months, a.currency) if offer else None

    # TreeSHAP Factor Extraction
    adverse_action_factors = []
    key_strengths = []
    try:
        base_estimator = b['classifier'].calibrated_classifiers_[0].estimator
        if hasattr(base_estimator, 'estimator'):
            base_estimator = base_estimator.estimator
        booster = base_estimator.booster_
        contribs = booster.predict(row[FEATURES], pred_contrib=True)[0][:-1]
        shap_factors = []
        for feat, impact in zip(FEATURES, contribs):
            val = float(impact)
            shap_factors.append({
                'feature': feat,
                'label': FEATURE_LABELS.get(feat, feat),
                'shap_value': round(val, 4),
                'direction': 'positive' if val > 0 else 'negative'
            })
        adverse_action_factors = sorted([f for f in shap_factors if f['direction'] == 'negative'],
                                        key=lambda x: x['shap_value'])[:4]
        key_strengths = sorted([f for f in shap_factors if f['direction'] == 'positive'],
                               key=lambda x: x['shap_value'], reverse=True)[:4]
    except Exception:
        pass

    # Prescriptive Counterfactual Recourse
    counterfactual_recourse = compute_counterfactual_recourse(
        b, row, repayment_probability, a.currency, a.term_months, effective_fico,
        a.revolving_utilization, a.dti
    )

    # Vectorized sensitivity probes
    references = {'fico_range_low': 700, 'dti': 18, 'annual_inc': 75000, 'emp_length': 5,
                  'loan_amnt': 15000, 'revol_util': 53, 'pub_rec_bankruptcies': 0, 'revol_bal': 11399}
    probe_rows = [row.assign(**{feature: reference}) for feature, reference in references.items()]
    batch = pd.concat(probe_rows, ignore_index=True)
    alternative_probs = b['classifier'].predict_proba(batch[FEATURES])[:, 1]
    
    sensitivity = []
    for (feature, reference), alt_prob in zip(references.items(), alternative_probs):
        sensitivity.append({'feature': feature, 'reference_value': reference,
                            'probability_change_if_reference': round(float(alt_prob) - repayment_probability, 4)})
    sensitivity.sort(key=lambda item: abs(item['probability_change_if_reference']), reverse=True)

    res = {
        'status': status,
        'currency': a.currency,
        'repayment_probability': round(repayment_probability, 4),
        'probability_of_default': probability_of_default,
        'historical_amount_benchmark': round(historical_amount, 0) if historical_amount is not None else None,
        'affordability_cap': round(affordability_cap, 0),
        'offer_amount': offer,
        'illustrative_monthly_payment': payment_amount,
        'assumed_apr': cfg['assumed_apr'],
        'risk_adjusted_apr': risk_adjusted_apr,
        'loss_given_default': loss_given_default,
        'expected_loss': expected_loss,
        'key_fact_statement': kfs,
        'cash_flow_assessment': cash_flow_eval,
        'counterfactual_recourse': counterfactual_recourse,
        'adverse_action_factors': adverse_action_factors,
        'key_strengths': key_strengths,
        'scenario_sensitivity': sensitivity[:5],
        'model_version': b['metrics']['dataset_sha256'][:12],
        'disclaimer': 'Research simulation calibrated to institutional underwriting standards. Includes RBI KFS compliance, Cash Flow AA, and TreeSHAP explainability.'
    }
    try:
        app_id, assess_id = save_application_and_assessment(a.model_dump(), res)
        res['application_id'] = app_id
        res['assessment_id'] = assess_id
    except Exception:
        pass
    cache_set(cache_key, res, ttl_seconds=600)
    return res



@app.get('/api/applications')
def get_applications(limit: int = 50, auth_token: str = Depends(verify_access_token)):
    return {'applications': list_recent_applications(limit)}


@app.get('/api/drift')
def drift_report():
    return get_drift_report()


