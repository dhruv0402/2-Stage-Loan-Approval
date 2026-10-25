from fastapi.testclient import TestClient
from backend.app.main import app, payment
from backend.app.db import init_db

init_db()
client = TestClient(app)
BASE = {'requested_amount': 12000, 'annual_income': 85000, 'dti': 18, 'fico': 720,
        'employment_years': 5, 'term_months': 36, 'purpose': 'debt_consolidation', 'revolving_utilization': 53, 'open_accounts': 11,
        'public_bankruptcies': 0, 'revolving_balance': 11399, 'home_ownership': 'MORTGAGE'}

def test_payment_amortization():
    assert round(payment(12000, .01, 12), 2) == 1066.19

def test_valid_assessment_and_safe_offer():
    r = client.post('/api/assess', json=BASE)
    assert r.status_code == 200
    body = r.json()
    assert 0 <= body['repayment_probability'] <= 1
    assert 0 <= body['probability_of_default'] <= 1
    assert round(body['repayment_probability'] + body['probability_of_default'], 2) == 1.0
    assert 0.0599 <= body['risk_adjusted_apr'] <= 0.3599
    assert 'adverse_action_factors' in body
    assert 'key_strengths' in body
    assert body['offer_amount'] is None or body['offer_amount'] <= BASE['requested_amount']
    if body['offer_amount']:
        assert body['expected_loss'] is not None
        assert body['expected_loss'] >= 0
    assert 'Research simulation' in body['disclaimer']

def test_invalid_request():
    assert client.post('/api/assess', json={**BASE, 'fico': 999}).status_code == 422
    assert client.post('/api/assess', json={**BASE, 'term_months': 48}).status_code == 422

def test_high_debt_blocks_offer():
    r = client.post('/api/assess', json={**BASE, 'dti': 80})
    assert r.status_code == 200
    assert r.json()['offer_amount'] is None

def test_missing_credit_profile_is_rejected():
    incomplete = {key: value for key, value in BASE.items() if key != 'revolving_balance'}
    assert client.post('/api/assess', json=incomplete).status_code == 422

def test_stage_two_is_skipped_below_gate(monkeypatch):
    import numpy as np
    from backend.app import main

    class LowScore:
        def predict_proba(self, frame):
            return np.array([[0.9, 0.1]])

    class MustNotRun:
        def predict(self, frame):
            raise AssertionError('Stage two should not run for a failed gate')

    real = main.bundle()
    monkeypatch.setattr(main, 'bundle', lambda: {**real, 'classifier': LowScore(),
                                              'amount_regressor': MustNotRun()})
    response = client.post('/api/assess', json=BASE)
    assert response.status_code == 200
    assert response.json()['historical_amount_benchmark'] is None

def test_health_and_model_card():
    r_health = client.get('/api/health')
    assert r_health.status_code == 200
    assert r_health.json()['status'] in ('ready', 'untrained')

    r_card = client.get('/api/model-card')
    assert r_card.status_code == 200
    assert 'metrics' in r_card.json()

def test_payment_zero_and_negative_edge_cases():
    assert payment(0, 0.01, 36) == 0.0
    assert payment(-5000, 0.01, 36) == 0.0
    assert round(payment(10000, 0.0, 36), 2) == round(10000 / 36, 2)
    assert payment(10000, 0.01, 0) == 0.0

def test_inr_assessment_with_cibil_and_kfs():
    inr_req = {
        'currency': 'INR',
        'requested_amount': 500000,
        'annual_income': 1200000,
        'dti': 20.0,
        'cibil': 765,
        'employment_years': 4,
        'term_months': 36,
        'purpose': 'debt_consolidation',
        'revolving_utilization': 28.0,
        'open_accounts': 6,
        'public_bankruptcies': 0,
        'revolving_balance': 45000,
        'home_ownership': 'OWN'
    }
    r = client.post('/api/assess', json=inr_req)
    assert r.status_code == 200
    data = r.json()
    assert data['currency'] == 'INR'
    assert data['status'] == 'eligible_for_simulated_offer'
    assert data['offer_amount'] is not None and data['offer_amount'] > 50000
    assert data['key_fact_statement'] is not None
    assert 'net_disbursed_amount' in data['key_fact_statement']
    assert 'monthly_emi' in data['key_fact_statement']
    assert len(data['counterfactual_recourse']) > 0
    assert 'application_id' in data
    assert 'assessment_id' in data

def test_database_persistence_and_listing():
    r = client.get('/api/applications')
    assert r.status_code == 200
    res = r.json()
    assert 'applications' in res
    assert isinstance(res['applications'], list)
    assert len(res['applications']) >= 1
    recent = res['applications'][0]
    assert 'application_id' in recent
    assert 'assessment_id' in recent
    assert 'currency' in recent

def test_drift_endpoint():
    r = client.get('/api/drift')
    assert r.status_code == 200
    report = r.json()
    assert 'overall_status' in report
    assert 'metrics' in report
    assert 'credit_score_psi' in report['metrics']

def test_cash_flow_eval_in_assess():
    req = {
        'currency': 'INR',
        'requested_amount': 500000,
        'annual_income': 1200000,
        'dti': 20.0,
        'cibil': 765,
        'employment_years': 4,
        'term_months': 36,
        'purpose': 'debt_consolidation',
        'revolving_utilization': 28.0,
        'open_accounts': 6,
        'public_bankruptcies': 0,
        'revolving_balance': 45000,
        'home_ownership': 'OWN',
        'nach_bounce_count_last_6m': 2,
        'average_bank_balance': 15000
    }
    r = client.post('/api/assess', json=req)
    assert r.status_code == 200
    data = r.json()
    assert 'cash_flow_assessment' in data
    assert data['cash_flow_assessment']['nach_bounce_penalty_applied'] is True




