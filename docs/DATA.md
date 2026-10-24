# Dataset provenance and audit

Source: Deepchecks' modified Lending Club dataset on Figshare, version 4, DOI https://doi.org/10.6084/m9.figshare.22121477 (page states CC0). The repository contains a checksummed download script and does not commit raw loan rows. The downloadable train and test files are a **funded-loan derived subset**, despite the source page's description of accepted and rejected data. They have no actual approval flag and no requested-versus-offered amount pair.

| Snapshot | Dates | Raw rows | Usable labeled rows | SHA-256 |
| --- | --- | ---: | ---: | --- |
| `train_lending_club.csv` | Jan 2014–Jun 2016 | 236,846 | 236,846 | `8efebed1a9cbaba1edb511f9026732244c2a97497c73a8eb42d1f7864c77d8c1` |
| `test_lending_club.csv` | Jul 2016–Dec 2018 | 95,019 | 93,607, through Nov 2018 | `51dbe82c70c98a53802dfd585182f14842228a13061b29c3ebc21e880139805c` |

The source's `loan_status` is encoded 0/1 without a codebook in these CSVs. Label 1 is *inferred* to mean a favorable repayment outcome because it has higher average FICO (696.3 vs 684.8), lower interest (11.87 vs 16.20) and lower DTI (17.98 vs 21.27) in the training snapshot. This inference needs confirmation against the original transformation. The test file has missing labels, which are excluded. Future-period category missingness is handled by LightGBM. Outcome maturity/censoring and funded-only selection bias remain unresolved.

Chronological fit Jan 2014–Dec 2015; selection Jan–Feb 2016; calibration Mar 2016; internal check Apr–Jun 2016. The separate test snapshot covers Jul 2016–Nov 2018 after dropping missing targets. No test rows are used for fitting, candidate selection or calibration. Source loan amount is historically listed/funded amount, **not an observed optimal offer**.

Only application-time inputs are retained. Source fields `sub_grade`, `int_rate`, `installment`, `initial_list_status`, `loan_status` and issue date are not predictors. Missing feature values in future cohorts are modeled as missing; user input is explicitly validated. Data are historical US peer-to-peer loans and do not represent current lending or Indian borrowers.

Alternative UCI South German Credit (DOI 10.24432/C5X89F) contains 1,000 1970s credit contracts, a corrected risk label and transformed amount, but no modern income, actual approval or optimal offer target. It was unsuitable as the main source.
