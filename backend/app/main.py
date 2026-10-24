"""Portfolio simulator API. No credit decisions or applicant PII storage."""
from functools import lru_cache
from pathlib import Path
import math
import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from backend.ml.features import PURPOSES, HOME_TYPES, clean_frame, FEATURES, AMOUNT_FEATURES

ROOT = Path(__file__).resolve().parents[2]
app = FastAPI(title='Underwrite simulator', version='0.1.0')
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
                   allow_credentials=False, allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])

class Application(BaseModel):
    requested_amount: float = Field(ge=1000, le=40000)
    annual_income: float = Field(ge=1000, le=10000000)
    dti: float = Field(ge=0, le=100)
    fico: int = Field(ge=300, le=850)
    employment_years: float = Field(ge=0, le=50)
    term_months: int = Field(default=36)
    purpose: str = Field(default='debt_consolidation')
    revolving_utilization: float = Field(ge=0, le=250)
    open_accounts: int = Field(ge=0, le=100)
    public_bankruptcies: int = Field(ge=0, le=20)
    revolving_balance: float = Field(ge=0, le=1000000)
    home_ownership: str

@lru_cache
def bundle():
    path = ROOT / 'models/bundle.joblib'
    if not path.exists():
        raise HTTPException(status_code=503, detail='Model bundle missing. Run python -m backend.ml.train first.')
    return joblib.load(path)


def payment(principal: float, monthly_rate: float, months: int) -> float:
    return principal * monthly_rate / (1 - (1 + monthly_rate) ** (-months)) if monthly_rate else principal / months


def row_for(a: Application, amount: float) -> pd.DataFrame:
    return clean_frame(pd.DataFrame([dict(loan_amnt=amount, annual_inc=a.annual_income, dti=a.dti,
                                     fico_range_low=a.fico, emp_length=a.employment_years,
                                     term=f'{a.term_months} months', purpose=a.purpose, revol_util=a.revolving_utilization,
                                     open_acc=a.open_accounts, pub_rec_bankruptcies=a.public_bankruptcies,
                                     revol_bal=a.revolving_balance, home_ownership=a.home_ownership)]))


@app.get('/api/health')
def health():
    return {'status': 'ready' if (ROOT / 'models/bundle.joblib').exists() else 'untrained'}


@app.get('/api/model-card')
def model_card():
    b = bundle()
    return {'metrics': b['metrics'], 'threshold': b['config']['model']['decision_threshold'],
            'assumed_apr': b['config']['policy']['assumed_apr'],
            'limitations': ['Funded-loan repayment probability is not an approval probability.',
                            'Historical amount regression is not an optimal amount label.',
                            'The policy and 12% APR are illustrative US dollar assumptions.']}


@app.post('/api/assess')
def assess(a: Application):
    if a.term_months not in (36, 60) or a.purpose not in PURPOSES or a.home_ownership not in HOME_TYPES:
        raise HTTPException(422, 'term, purpose or home ownership is unsupported')
    b = bundle()
    cfg = b['config']['policy']
    threshold = b['config']['model']['decision_threshold']
    margin = b['config']['model']['review_margin']
    row = row_for(a, a.requested_amount)
    repayment_probability = float(b['classifier'].predict_proba(row[FEATURES])[0, 1])
    monthly_income = a.annual_income / 12
    max_payment = max(0.0, min(cfg['max_payment_share_of_monthly_income'] * monthly_income,
                                (0.36 - a.dti / 100) * monthly_income))
    rate = cfg['assumed_apr'] / 12
    annuity_factor = ((1 + rate) ** a.term_months - 1) / (rate * (1 + rate) ** a.term_months) if rate else a.term_months
    affordability_cap = max_payment * annuity_factor
    historical_amount = None
    offer = None
    if repayment_probability < threshold - margin or affordability_cap < cfg['min_offer']:
        status = 'outside_demo_policy'
    elif repayment_probability < threshold:
        status = 'review'
    else:
        historical_amount = float(b['amount_regressor'].predict(row[AMOUNT_FEATURES])[0])
        candidate = math.floor(min(a.requested_amount, historical_amount, affordability_cap, cfg['max_offer']) / 50) * 50
        if candidate < cfg['min_offer']:
            status = 'outside_demo_policy'
        else:
            status = 'eligible_for_simulated_offer'
            offer = candidate
    payment_amount = round(payment(offer, rate, a.term_months), 2) if offer else None
    # One-factor reference probes are scenarios, not regulatory adverse-action reasons.
    references = {'fico_range_low': 700, 'dti': 18, 'annual_inc': 75000, 'emp_length': 5, 'loan_amnt': 15000, 'revol_util': 53, 'pub_rec_bankruptcies': 0, 'revol_bal': 11399}
    sensitivity = []
    for feature, reference in references.items():
        probe = row.copy(); probe.loc[0, feature] = reference
        alternative = float(b['classifier'].predict_proba(probe[FEATURES])[0, 1])
        sensitivity.append({'feature': feature, 'reference_value': reference,
                            'probability_change_if_reference': round(alternative - repayment_probability, 4)})
    sensitivity.sort(key=lambda item: abs(item['probability_change_if_reference']), reverse=True)
    return {'status': status, 'repayment_probability': round(repayment_probability, 4),
            'historical_amount_benchmark': round(historical_amount, 0) if historical_amount is not None else None,
            'affordability_cap': round(affordability_cap, 0), 'offer_amount': offer,
            'illustrative_monthly_payment': payment_amount, 'assumed_apr': cfg['assumed_apr'],
            'scenario_sensitivity': sensitivity[:5], 'model_version': b['metrics']['dataset_sha256'][:12],
            'disclaimer': 'Research simulation for funded US loans. Not a real credit decision, approval probability, APR quote, or adverse-action notice.'}

