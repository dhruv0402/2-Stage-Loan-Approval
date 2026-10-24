from fastapi.testclient import TestClient
from backend.app.main import app, payment

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
    assert body['offer_amount'] is None or body['offer_amount'] <= BASE['requested_amount']
    assert 'Not a real credit decision' in body['disclaimer']

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
