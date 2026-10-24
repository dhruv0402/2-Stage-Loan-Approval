"""Multi-table Relational Feature Engineering & Model Training on Home Credit Default Risk."""
from pathlib import Path
import json
import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier, early_stopping, log_evaluation
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss
from sklearn.model_selection import StratifiedKFold

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / 'data/home_credit'
OUTPUT_DIR = ROOT / 'models'

def build_bureau_features(bureau_path: Path) -> pd.DataFrame:
    if not bureau_path.exists():
        return pd.DataFrame()
    print("Aggregating bureau tradelines...")
    df = pd.read_parquet(bureau_path, columns=[
        'SK_ID_CURR', 'CREDIT_ACTIVE', 'CREDIT_DAY_OVERDUE',
        'AMT_CREDIT_SUM', 'AMT_CREDIT_SUM_DEBT', 'AMT_CREDIT_SUM_OVERDUE'
    ])
    
    agg = df.groupby('SK_ID_CURR').agg(
        bureau_loan_count=('CREDIT_ACTIVE', 'count'),
        bureau_active_count=('CREDIT_ACTIVE', lambda x: (x == 'Active').sum()),
        bureau_max_overdue_days=('CREDIT_DAY_OVERDUE', 'max'),
        bureau_total_debt=('AMT_CREDIT_SUM_DEBT', 'sum'),
        bureau_overdue_debt=('AMT_CREDIT_SUM_OVERDUE', 'sum'),
        bureau_total_credit=('AMT_CREDIT_SUM', 'sum')
    ).reset_index()
    return agg

def build_prev_app_features(prev_paths: list[Path]) -> pd.DataFrame:
    dfs = [pd.read_parquet(p, columns=['SK_ID_CURR', 'NAME_CONTRACT_STATUS', 'AMT_APPLICATION', 'AMT_CREDIT']) 
           for p in prev_paths if p.exists()]
    if not dfs:
        return pd.DataFrame()
    print("Aggregating previous applications (Reject Inference)...")
    df = pd.concat(dfs, ignore_index=True)
    agg = df.groupby('SK_ID_CURR').agg(
        prev_app_count=('NAME_CONTRACT_STATUS', 'count'),
        prev_refused_count=('NAME_CONTRACT_STATUS', lambda x: (x == 'Refused').sum()),
        prev_approved_count=('NAME_CONTRACT_STATUS', lambda x: (x == 'Approved').sum()),
        prev_avg_requested=('AMT_APPLICATION', 'mean'),
        prev_avg_sanctioned=('AMT_CREDIT', 'mean')
    ).reset_index()
    agg['prev_refusal_rate'] = agg['prev_refused_count'] / (agg['prev_app_count'] + 1e-5)
    return agg

def train_home_credit():
    app_path = DATA_DIR / 'application_train.parquet'
    if not app_path.exists():
        raise FileNotFoundError(f"{app_path} not found. Run scripts/download_home_credit.py first.")
    
    print(f"Loading primary application table from {app_path}...")
    core_cols = [
        'SK_ID_CURR', 'TARGET', 'AMT_INCOME_TOTAL', 'AMT_CREDIT', 'AMT_ANNUITY',
        'DAYS_BIRTH', 'DAYS_EMPLOYED', 'EXT_SOURCE_1', 'EXT_SOURCE_2', 'EXT_SOURCE_3',
        'DAYS_ID_PUBLISH', 'OWN_CAR_AGE', 'REGION_RATING_CLIENT'
    ]
    app_df = pd.read_parquet(app_path)
    available_cols = [c for c in core_cols if c in app_df.columns]
    df = app_df[available_cols].copy()
    
    # Feature Engineering on application table
    df['age_years'] = -df['DAYS_BIRTH'] / 365.25 if 'DAYS_BIRTH' in df else np.nan
    df['emp_years'] = -df['DAYS_EMPLOYED'] / 365.25 if 'DAYS_EMPLOYED' in df else np.nan
    df['emp_years'] = df['emp_years'].apply(lambda x: np.nan if x < 0 else x)
    df['credit_to_income'] = df['AMT_CREDIT'] / (df['AMT_INCOME_TOTAL'] + 1)
    df['annuity_to_income'] = df['AMT_ANNUITY'] / (df['AMT_INCOME_TOTAL'] + 1)
    
    # External bureau aggregation
    bureau_agg = build_bureau_features(DATA_DIR / 'bureau.parquet')
    if not bureau_agg.empty:
        df = df.merge(bureau_agg, on='SK_ID_CURR', how='left')
        
    # Previous applications aggregation
    prev_agg = build_prev_app_features([
        DATA_DIR / 'previous_application_0.parquet',
        DATA_DIR / 'previous_application_1.parquet'
    ])
    if not prev_agg.empty:
        df = df.merge(prev_agg, on='SK_ID_CURR', how='left')
        
    features = [c for c in df.columns if c not in ('SK_ID_CURR', 'TARGET')]
    print(f"Engineered dataset shape: {df.shape}. Features count: {len(features)}")
    
    X = df[features]
    y = df['TARGET'].astype(int)
    
    # 5-Fold Stratified Split for Validation
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    train_idx, val_idx = next(skf.split(X, y))
    
    X_train, y_train = X.iloc[train_idx], y.iloc[train_idx]
    X_val, y_val = X.iloc[val_idx], y.iloc[val_idx]
    
    print("Training calibrated LightGBM classifier on relational features...")
    model = LGBMClassifier(
        n_estimators=600,
        learning_rate=0.03,
        num_leaves=31,
        min_child_samples=300,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
        verbosity=-1
    )
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        eval_metric='auc',
        callbacks=[early_stopping(30, verbose=False), log_evaluation(0)]
    )
    
    # Probability Calibration
    calibrated = CalibratedClassifierCV(FrozenEstimator(model), method='sigmoid')
    calibrated.fit(X_val, y_val)
    
    val_probs = calibrated.predict_proba(X_val)[:, 1]
    auc = float(roc_auc_score(y_val, val_probs))
    pr_auc = float(average_precision_score(y_val, val_probs))
    brier = float(brier_score_loss(y_val, val_probs))
    
    metrics = {
        'dataset': 'Home Credit Default Risk (Multi-Table Relational)',
        'records_trained': len(X_train),
        'records_validated': len(X_val),
        'features_count': len(features),
        'features': features,
        'val_roc_auc': round(auc, 4),
        'val_pr_auc': round(pr_auc, 4),
        'val_brier_score': round(brier, 4),
        'target_default_rate': round(float(y.mean()), 4)
    }
    print(json.dumps(metrics, indent=2))
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({'model': calibrated, 'features': features, 'metrics': metrics}, OUTPUT_DIR / 'home_credit_bundle.joblib')
    (OUTPUT_DIR / 'home_credit_metrics.json').write_text(json.dumps(metrics, indent=2))
    print(f"Saved model and metrics to {OUTPUT_DIR}")

if __name__ == '__main__':
    train_home_credit()
