# Technical requirements — Credence AI v0.2

## Stack

React 19, TypeScript and Vite; FastAPI/Pydantic; pandas, LightGBM, scikit-learn calibration, joblib and YAML. API: `GET /api/health`, `GET /api/model-card`, `POST /api/assess`. Vite proxies `/api` to local FastAPI. CORS is limited to local development origins.

## Models and data contract

`clean_frame` normalizes term, purpose and home ownership with fixed categories and converts numeric fields. The 12 predictor fields are `annual_inc`, `dti`, `fico_range_low`, `emp_length`, `loan_amnt`, `revol_util`, `open_acc`, `pub_rec_bankruptcies`, `revol_bal`, `purpose`, `term`, and `home_ownership`. LightGBM handles missing categorical values; the API requires all scenario inputs. `loan_amnt` is omitted from amount regression predictors. Loan grade, assigned interest, installment and later performance are barred from predictors to prevent downstream leakage.

Stage 1 compares a logistic baseline with regularized LightGBM candidates with 7, 15 and 31 leaves; selects on Jan–Feb 2016 ROC AUC; fits sigmoid probability calibration on March 2016. Stage 2 compares three LightGBM regressors using Jan–Feb 2016 MAE. Models fit only on 2014–15 funded-loan rows. April–June 2016 is a temporal check. A separate July 2016–November 2018 snapshot is the final future-period evaluation. `models/metrics.json` reports ROC AUC, bootstrap 95% interval, AP, Brier, precision, recall, confusion counts, MAE versus a training-median baseline and year-by-year drift.

## Policy calculation

Monthly payment capacity = `max(0, min(0.12 × annual_income/12, (0.36 − DTI/100) × annual_income/12))`. Principal affordability cap is the present value of that payment at a **12% assumed APR** for 36 or 60 months. Score <0.65, or cap under $1,000, yields no offer; 0.65–0.70 yields review; ≥0.70 may yield an offer. Offered amount is floored to $50 and capped at request, historical amount benchmark, affordability and $40,000. The threshold and formula are illustrative configuration values, not validated lender policy.

## API and operations

Request example:

```json
{"requested_amount":12000,"annual_income":85000,"dti":18,"fico":720,"employment_years":5,"term_months":36,"purpose":"debt_consolidation","revolving_utilization":53,"open_accounts":11,"public_bankruptcies":0,"revolving_balance":11399,"home_ownership":"MORTGAGE"}
```

Response includes status, probability, benchmark, affordability cap, nullable offer/payment, reference-probe sensitivity, model version and disclaimer. The fitted bundle contains preprocessing category metadata, both models, configuration and metrics. `scripts/download_data.py` verifies fixed source SHA-256 values. The API loads once per worker via a cached function and stores no application record.

## Future persistence and deployment

`schema.sql` provides a versioned, pseudonymous PostgreSQL design, unused in v0.2. Any public deployment requires identity controls, encrypted data handling, retention, rate limits, monitoring and human review. CI should run API tests, TypeScript/build and a reproducible training check on the fixed snapshots. A production model needs validated target definitions and fair-lending review before any decision support use.
