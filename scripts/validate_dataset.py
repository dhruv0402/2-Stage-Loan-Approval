"""Comprehensive dataset validation and audit script for credit underwriting data."""
from pathlib import Path
import argparse
import sys
import pandas as pd
import numpy as np

LEAKAGE_CANDIDATES = [
    'sub_grade', 'int_rate', 'installment', 'total_rec_prncp',
    'total_rec_int', 'total_rec_late_fee', 'recoveries',
    'collection_recovery_fee', 'last_pymnt_d', 'last_pymnt_amnt',
    'next_pymnt_d', 'last_credit_pull_d', 'debt_settlement_flag'
]

def validate_dataset(train_path: Path, test_path: Path | None = None) -> dict:
    print(f"Loading {train_path}...")
    df_train = pd.read_csv(train_path)
    
    report = {
        'train_shape': df_train.shape,
        'train_columns': len(df_train.columns),
        'missing_summary': {},
        'leakage_warnings': [],
        'distribution_warnings': [],
        'selection_bias_flag': True
    }
    
    # 1. Check Target
    if 'loan_status' not in df_train.columns:
        report['target_error'] = "Target column 'loan_status' not found in training dataset!"
        return report
        
    target_counts = df_train['loan_status'].value_counts(dropna=False).to_dict()
    report['target_counts'] = target_counts
    
    total_valid = df_train['loan_status'].dropna().count()
    if 1 in target_counts and total_valid > 0:
        pos_rate = target_counts[1] / total_valid
        report['positive_class_prevalence'] = round(pos_rate, 4)
        if pos_rate > 0.8:
            report['distribution_warnings'].append(
                f"Significant class imbalance: {pos_rate:.1%} positive class prevalence. "
                "ROC-AUC may mask precision issues; Precision-Recall AUC (PR-AUC) must be monitored."
            )
            
    # 2. Check for Potential Data Leakage Features
    present_leakage = [col for col in LEAKAGE_CANDIDATES if col in df_train.columns]
    if present_leakage:
        report['leakage_warnings'].append(
            f"Dataset contains post-origination or pricing variables that MUST NOT be used "
            f"as application-time predictors: {present_leakage}."
        )
        
    # 3. Check Date Continuity
    if 'issue_d' in df_train.columns:
        dates = pd.to_datetime(df_train['issue_d'], errors='coerce')
        report['train_date_range'] = [str(dates.min().date()), str(dates.max().date())]
        null_dates = dates.isna().sum()
        if null_dates > 0:
            report['distribution_warnings'].append(f"{null_dates} rows have unparseable 'issue_d' dates.")
            
    # 4. Check Missingness
    missing = df_train.isnull().sum()
    high_missing = missing[missing > (0.1 * len(df_train))]
    if not high_missing.empty:
        report['high_missing_cols'] = high_missing.to_dict()
        
    # 5. Check Test File if provided
    if test_path and test_path.exists():
        print(f"Loading {test_path}...")
        df_test = pd.read_csv(test_path)
        report['test_shape'] = df_test.shape
        test_missing_target = df_test['loan_status'].isna().sum()
        if test_missing_target > 0:
            report['distribution_warnings'].append(
                f"Test set contains {test_missing_target} rows ({test_missing_target/len(df_test):.2%}) "
                "with missing target labels (NaN). These must be cleanly filtered before held-out evaluation."
            )
        if 'issue_d' in df_test.columns and 'issue_d' in df_train.columns:
            test_dates = pd.to_datetime(df_test['issue_d'], errors='coerce')
            report['test_date_range'] = [str(test_dates.min().date()), str(test_dates.max().date())]
            if test_dates.min() < dates.max():
                report['distribution_warnings'].append(
                    f"Temporal overlap detected: test start ({test_dates.min().date()}) is before "
                    f"train max date ({dates.max().date()}). Risk of temporal lookahead leakage."
                )

    # 6. Check Range Sanity
    if 'dti' in df_train.columns:
        invalid_dti = (df_train['dti'] < 0) | (df_train['dti'] > 100)
        if invalid_dti.sum() > 0:
            report['distribution_warnings'].append(
                f"{invalid_dti.sum()} rows with DTI outside standard bounds (0-100%)."
            )
            
    if 'fico_range_low' in df_train.columns:
        invalid_fico = (df_train['fico_range_low'] < 300) | (df_train['fico_range_low'] > 850)
        if invalid_fico.sum() > 0:
            report['distribution_warnings'].append(
                f"{invalid_fico.sum()} rows with FICO score outside standard US range (300-850)."
            )
            
    return report

def main():
    parser = argparse.ArgumentParser(description="Validate underwriting dataset")
    parser.add_argument("--train", type=Path, default=Path("data/raw/train_lending_club.csv"))
    parser.add_argument("--test", type=Path, default=Path("data/raw/test_lending_club.csv"))
    args = parser.parse_args()
    
    res = validate_dataset(args.train, args.test if args.test.exists() else None)
    print("\n" + "="*50)
    print("DATASET VALIDATION SUMMARY")
    print("="*50)
    for k, v in res.items():
        print(f"\n[{k.upper()}]:")
        if isinstance(v, list):
            for item in v:
                print(f"  • {item}")
        elif isinstance(v, dict):
            for sub_k, sub_v in v.items():
                print(f"  • {sub_k}: {sub_v}")
        else:
            print(f"  {v}")

if __name__ == "__main__":
    main()
