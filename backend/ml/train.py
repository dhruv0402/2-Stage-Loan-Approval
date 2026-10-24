"""Temporal model selection, calibration and final held-out evaluation."""
from pathlib import Path
import argparse
import hashlib
import json
import joblib
import numpy as np
import pandas as pd
import yaml
from lightgbm import LGBMClassifier, LGBMRegressor, early_stopping, log_evaluation
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.metrics import (average_precision_score, brier_score_loss, confusion_matrix,
                             mean_absolute_error, roc_auc_score, precision_score, recall_score)
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from .features import FEATURES, AMOUNT_FEATURES, CATEGORICAL, NUMERIC, clean_frame

ROOT = Path(__file__).resolve().parents[2]


def split_periods(frame: pd.DataFrame, settings: dict):
    selection_start = pd.Timestamp(settings['selection_start'])
    calibration_start = pd.Timestamp(settings['calibration_start'])
    internal_start = pd.Timestamp(settings['internal_check_start'])
    future_start = pd.Timestamp(settings['future_test_start'])
    if not selection_start < calibration_start < internal_start < future_start:
        raise ValueError('Chronological split boundaries must increase')
    return (frame[frame.issue_d < selection_start],
            frame[(frame.issue_d >= selection_start) & (frame.issue_d < calibration_start)],
            frame[(frame.issue_d >= calibration_start) & (frame.issue_d < internal_start)],
            frame[(frame.issue_d >= internal_start) & (frame.issue_d < future_start)])


def logistic_baseline(fit: pd.DataFrame):
    prep = ColumnTransformer([
        ('num', Pipeline([('impute', SimpleImputer(strategy='median')),
                          ('scale', StandardScaler())]), NUMERIC),
        ('cat', OneHotEncoder(handle_unknown='ignore'), CATEGORICAL),
    ])
    model = Pipeline([('prep', prep), ('clf', LogisticRegression(max_iter=1000))])
    model.fit(fit[FEATURES], fit.loan_status.astype(int))
    return model


def confidence_interval(y, estimate, metric, seed=42, repeats=300):
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(repeats):
        index = rng.integers(0, len(y), len(y))
        if len(np.unique(y[index])) < 2 and metric is roc_auc_score:
            continue
        values.append(metric(y[index], estimate[index]))
    return [round(float(v), 4) for v in np.quantile(values, [0.025, 0.975])]


def evaluate(y, probabilities, threshold):
    decision = (probabilities >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, decision, labels=[0, 1]).ravel()
    return {
        'roc_auc': round(float(roc_auc_score(y, probabilities)), 4),
        'roc_auc_bootstrap_95pct': confidence_interval(y, probabilities, roc_auc_score),
        'average_precision': round(float(average_precision_score(y, probabilities)), 4),
        'brier': round(float(brier_score_loss(y, probabilities)), 4),
        'precision_at_threshold': round(float(precision_score(y, decision, zero_division=0)), 4),
        'recall_at_threshold': round(float(recall_score(y, decision, zero_division=0)), 4),
        'confusion_matrix_tn_fp_fn_tp': [int(tn), int(fp), int(fn), int(tp)],
        'predicted_eligible_rate': round(float(decision.mean()), 4),
        'observed_favorable_rate': round(float(y.mean()), 4),
    }


def train(raw: Path, output: Path, future_raw: Path | None = None):
    cfg = yaml.safe_load((ROOT / 'config.yaml').read_text())
    data = pd.read_csv(raw, usecols=FEATURES + ['issue_d', 'loan_status'])
    x = clean_frame(data)
    x['issue_d'] = pd.to_datetime(data.issue_d, errors='coerce')
    x = x.dropna(subset=['issue_d', 'loan_status', 'loan_amnt'])
    x = x[x.loan_status.isin([0, 1]) & x.loan_amnt.between(1000, 40000)]
    fit, selection, calibration, test = split_periods(x, cfg['model'])
    if min(map(len, [fit, selection, calibration, test])) < 100:
        raise ValueError('Every chronological partition needs at least 100 rows')

    baseline = logistic_baseline(fit)
    baseline_auc = float(roc_auc_score(selection.loan_status, baseline.predict_proba(selection[FEATURES])[:, 1]))
    # Enforce regulatory monotone constraints:
    # higher annual_inc (+1), dti (-1), fico (+1), emp_length (+1), loan_amnt (-1), revol_util (-1), open_acc (0), pub_rec_bankruptcies (-1), revol_bal (-1), purpose (0), term (0), home (0)
    monotone_constraints = [1, -1, 1, 1, -1, -1, 0, -1, -1, 0, 0, 0]

    for leaves in [7, 15, 31]:
        model = LGBMClassifier(n_estimators=500, num_leaves=leaves, learning_rate=.03,
                               min_child_samples=300, colsample_bytree=.9, reg_lambda=20,
                               monotone_constraints=monotone_constraints,
                               verbosity=-1, random_state=cfg['model']['seed'], n_jobs=4)
        model.fit(fit[FEATURES], fit.loan_status, eval_X=selection[FEATURES], eval_y=selection.loan_status,
                  eval_metric='auc', callbacks=[early_stopping(25, verbose=False), log_evaluation(0)])
        auc = float(roc_auc_score(selection.loan_status, model.predict_proba(selection[FEATURES])[:, 1]))
        candidates.append((auc, leaves, model))
    selected_auc, leaves, chosen = max(candidates, key=lambda item: item[0])
    # Calibration is later than selection and earlier than the held-out test.
    classifier = CalibratedClassifierCV(FrozenEstimator(chosen), method='sigmoid')
    classifier.fit(calibration[FEATURES], calibration.loan_status)

    amount_candidates = []
    for amount_leaves in [7, 15, 31]:
        reg = LGBMRegressor(n_estimators=500, num_leaves=amount_leaves, learning_rate=.03,
                            min_child_samples=150, reg_lambda=20, verbosity=-1,
                            random_state=cfg['model']['seed'], n_jobs=4)
        reg.fit(fit[AMOUNT_FEATURES], fit.loan_amnt, eval_X=selection[AMOUNT_FEATURES],
                eval_y=selection.loan_amnt, eval_metric='l1',
                callbacks=[early_stopping(30, verbose=False), log_evaluation(0)])
        mae = float(mean_absolute_error(selection.loan_amnt, reg.predict(selection[AMOUNT_FEATURES])))
        amount_candidates.append((mae, amount_leaves, reg))
    selection_mae, amount_leaves, amount_model = min(amount_candidates, key=lambda item: item[0])

    # The later Figshare file is a genuinely future-period evaluation source.
    internal_y = test.loan_status.to_numpy(dtype=int)
    internal_p = classifier.predict_proba(test[FEATURES])[:, 1]
    if future_raw is None:
        future_raw = ROOT / 'data/raw/test_lending_club.csv'
    future = clean_frame(pd.read_csv(future_raw, usecols=FEATURES + ['issue_d', 'loan_status']))
    future['issue_d'] = pd.to_datetime(future['issue_d'], errors='coerce')
    future = future.dropna(subset=['issue_d', 'loan_status', 'loan_amnt'])
    future = future[future.loan_status.isin([0, 1]) & future.loan_amnt.between(1000, 40000)]
    if len(future) < 100 or future.issue_d.min() <= test.issue_d.max():
        raise ValueError('Future evaluation must contain later dated labeled loans')
    y = future.loan_status.to_numpy(dtype=int)
    probabilities = classifier.predict_proba(future[FEATURES])[:, 1]
    amount_estimate = amount_model.predict(future[AMOUNT_FEATURES])
    per_year = {}
    for year, group in future.groupby(future.issue_d.dt.year):
        labels = group.loan_status.to_numpy(dtype=int)
        scores = classifier.predict_proba(group[FEATURES])[:, 1]
        per_year[str(year)] = {'rows': len(group), 'observed_favorable_rate': round(float(labels.mean()), 4),
                              'roc_auc': round(float(roc_auc_score(labels, scores)), 4),
                              'brier': round(float(brier_score_loss(labels, scores)), 4)}
    metric = {'source_rows': len(x), 'train_rows': len(fit), 'selection_rows': len(selection),
              'calibration_rows': len(calibration), 'internal_check_rows': len(test), 'test_rows': len(future),
              'fit_date_range': [str(fit.issue_d.min().date()), str(fit.issue_d.max().date())],
              'selection_date_range': [str(selection.issue_d.min().date()), str(selection.issue_d.max().date())],
              'calibration_date_range': [str(calibration.issue_d.min().date()), str(calibration.issue_d.max().date())],
              'internal_check_date_range': [str(test.issue_d.min().date()), str(test.issue_d.max().date())],
              'test_date_range': [str(future.issue_d.min().date()), str(future.issue_d.max().date())],
              'model_selection': {'logistic_selection_roc_auc': round(baseline_auc, 4),
                                  'boosted_selection_roc_auc': round(selected_auc, 4),
                                  'chosen_classifier_leaves': leaves,
                                  'chosen_amount_leaves': amount_leaves,
                                  'amount_selection_mae_usd': round(selection_mae, 2)},
              'internal_check_roc_auc': round(float(roc_auc_score(internal_y, internal_p)), 4),
              'repayment': evaluate(y, probabilities, cfg['model']['decision_threshold']),
              'by_issue_year': per_year,
              'amount_historical_mae_usd': round(float(mean_absolute_error(future.loan_amnt, amount_estimate)), 2),
              'amount_historical_median_baseline_mae_usd': round(float(mean_absolute_error(future.loan_amnt, np.full(len(future), fit.loan_amnt.median()))), 2),
              'dataset_sha256': hashlib.sha256(raw.read_bytes()).hexdigest(),
              'future_dataset_sha256': hashlib.sha256(future_raw.read_bytes()).hexdigest(),
              'caveat': 'Funded cohort only; loan_status=1 favorable meaning inferred from distributions. No actual approval or optimal offer labels.'}
    output.mkdir(parents=True, exist_ok=True)
    joblib.dump({'classifier': classifier, 'amount_regressor': amount_model, 'metrics': metric, 'config': cfg}, output / 'bundle.joblib')
    (output / 'metrics.json').write_text(json.dumps(metric, indent=2))
    print(json.dumps(metric, indent=2))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, default=ROOT / 'data/raw/train_lending_club.csv')
    parser.add_argument('--output', type=Path, default=ROOT / 'models')
    parser.add_argument('--future-data', type=Path, default=ROOT / 'data/raw/test_lending_club.csv')
    args = parser.parse_args()
    train(args.data, args.output, args.future_data)
