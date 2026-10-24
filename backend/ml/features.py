"""Shared application-time feature contract and source normalization."""
import pandas as pd

CATEGORICAL = ['purpose', 'term', 'home_ownership']
NUMERIC = ['annual_inc', 'dti', 'fico_range_low', 'emp_length', 'loan_amnt',
           'revol_util', 'open_acc', 'pub_rec_bankruptcies', 'revol_bal']
FEATURES = NUMERIC + CATEGORICAL
AMOUNT_FEATURES = [name for name in FEATURES if name != 'loan_amnt']
PURPOSES = ['debt_consolidation', 'credit_card', 'home_improvement', 'major_purchase',
            'small_business', 'medical', 'car', 'other']
HOME_TYPES = ['MORTGAGE', 'RENT', 'OWN']


def clean_frame(data: pd.DataFrame) -> pd.DataFrame:
    x = data.copy()
    x['term'] = x['term'].astype(str).str.extract(r'(36|60)', expand=False).fillna('36')
    x['purpose'] = x['purpose'].where(x['purpose'].isin(PURPOSES), 'other')
    x['home_ownership'] = x['home_ownership'].where(x['home_ownership'].isin(HOME_TYPES))
    for column in NUMERIC:
        x[column] = pd.to_numeric(x[column], errors='coerce')
    x['term'] = pd.Categorical(x['term'], categories=['36', '60'])
    x['purpose'] = pd.Categorical(x['purpose'], categories=PURPOSES)
    x['home_ownership'] = pd.Categorical(x['home_ownership'], categories=HOME_TYPES)
    return x
