import pandas as pd
from backend.ml.train import split_periods


def test_split_periods_obeys_yaml_boundaries():
    dates = pd.date_range('2020-01-01', periods=5, freq='MS')
    frame = pd.DataFrame({'issue_d': dates})
    settings = {'selection_start': '2020-02-01', 'calibration_start': '2020-03-01',
                'internal_check_start': '2020-04-01', 'future_test_start': '2020-05-01'}
    fit, selected, calibrated, checked = split_periods(frame, settings)
    assert [len(group) for group in [fit, selected, calibrated, checked]] == [1, 1, 1, 1]
    assert checked.issue_d.iloc[0] == pd.Timestamp('2020-04-01')
