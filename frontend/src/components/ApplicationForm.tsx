import type { FormEvent } from 'react';

export type Input = {
  currency: 'INR' | 'USD';
  requested_amount: number;
  annual_income: number;
  dti: number;
  cibil?: number;
  fico?: number;
  employment_years: number;
  term_months: number;
  purpose: string;
  revolving_utilization: number;
  open_accounts: number;
  public_bankruptcies: number;
  revolving_balance: number;
  home_ownership: string;
};

export const initialINR: Input = {
  currency: 'INR',
  requested_amount: 500000,
  annual_income: 1200000,
  dti: 20,
  cibil: 760,
  employment_years: 4,
  term_months: 36,
  purpose: 'debt_consolidation',
  revolving_utilization: 28,
  open_accounts: 7,
  public_bankruptcies: 0,
  revolving_balance: 35000,
  home_ownership: 'OWN'
};

export const initialUSD: Input = {
  currency: 'USD',
  requested_amount: 12000,
  annual_income: 85000,
  dti: 18,
  fico: 720,
  employment_years: 5,
  term_months: 36,
  purpose: 'debt_consolidation',
  revolving_utilization: 53,
  open_accounts: 11,
  public_bankruptcies: 0,
  revolving_balance: 11399,
  home_ownership: 'MORTGAGE'
};

export const initial: Input = initialINR;

export function ApplicationForm({
  value,
  onChange,
  onSubmit,
  onClear,
  busy
}: {
  value: Input;
  onChange: (v: Input) => void;
  onSubmit: (e: FormEvent) => void;
  onClear: () => void;
  busy: boolean;
}) {
  const isINR = value.currency === 'INR';
  const sym = isINR ? '₹' : '$';

  const handleCurrencyToggle = (curr: 'INR' | 'USD') => {
    if (curr === value.currency) return;
    onChange(curr === 'INR' ? initialINR : initialUSD);
  };

  return (
    <section className="panel form-panel">
      <div className="panel-heading">
        <div>
          <h2>Application details</h2>
          <p>
            {isINR
              ? 'Institutional underwriting simulator under RBI Digital Lending Guidelines & CIBIL.'
              : 'Institutional underwriting simulator under US CFPB ATR Rules & FICO.'}
          </p>
        </div>
        <div style={{ display: 'flex', gap: '6px' }}>
          <button
            type="button"
            className={isINR ? 'primary' : 'secondary'}
            style={{ padding: '4px 10px', fontSize: '12px' }}
            onClick={() => handleCurrencyToggle('INR')}
          >
            ₹ INR (India / CIBIL)
          </button>
          <button
            type="button"
            className={!isINR ? 'primary' : 'secondary'}
            style={{ padding: '4px 10px', fontSize: '12px' }}
            onClick={() => handleCurrencyToggle('USD')}
          >
            $ USD (Global / FICO)
          </button>
        </div>
      </div>

      <form onSubmit={onSubmit}>
        <div className="form-grid">
          <label>
            Requested amount ({sym})
            <input
              type="number"
              required
              min={isINR ? 10000 : 1000}
              max={isINR ? 10000000 : 40000}
              step={isINR ? 5000 : 50}
              value={value.requested_amount}
              onChange={e => onChange({ ...value, requested_amount: Number(e.target.value) })}
            />
          </label>

          <label>
            Annual Net Income ({sym})
            <input
              type="number"
              required
              min={isINR ? 50000 : 1000}
              max={isINR ? 50000000 : 10000000}
              step={isINR ? 10000 : 100}
              value={value.annual_income}
              onChange={e => onChange({ ...value, annual_income: Number(e.target.value) })}
            />
          </label>

          <label>
            {isINR ? 'Existing EMIs / Obligations (FOIR %)' : 'Existing Debt-to-Income (DTI %)'}
            <input
              type="number"
              required
              min="0"
              max="100"
              step="0.1"
              value={value.dti}
              onChange={e => onChange({ ...value, dti: Number(e.target.value) })}
            />
          </label>

          {isINR ? (
            <label>
              CIBIL Credit Score (300-900)
              <input
                type="number"
                required
                min="300"
                max="900"
                step="1"
                value={value.cibil ?? 750}
                onChange={e => onChange({ ...value, cibil: Number(e.target.value), fico: undefined })}
              />
            </label>
          ) : (
            <label>
              FICO Credit Score (300-850)
              <input
                type="number"
                required
                min="300"
                max="850"
                step="1"
                value={value.fico ?? 720}
                onChange={e => onChange({ ...value, fico: Number(e.target.value), cibil: undefined })}
              />
            </label>
          )}

          <label>
            Employment stability (years)
            <input
              type="number"
              required
              min="0"
              max="50"
              step="0.5"
              value={value.employment_years}
              onChange={e => onChange({ ...value, employment_years: Number(e.target.value) })}
            />
          </label>

          <label>
            Loan tenure
            <select
              value={value.term_months}
              onChange={e => onChange({ ...value, term_months: Number(e.target.value) })}
            >
              <option value={36}>36 months (3 Years)</option>
              <option value={60}>60 months (5 Years)</option>
            </select>
          </label>

          <label className="wide">
            Borrowing purpose
            <select
              value={value.purpose}
              onChange={e => onChange({ ...value, purpose: e.target.value })}
            >
              {[
                ['debt_consolidation', 'Debt consolidation'],
                ['credit_card', 'Credit card refinance'],
                ['home_improvement', 'Home renovation / improvement'],
                ['major_purchase', 'Major purchase'],
                ['small_business', 'Business / Working capital'],
                ['medical', 'Medical emergency'],
                ['car', 'Vehicle purchase'],
                ['other', 'Personal / Other']
              ].map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="credit-profile">
          <h3>Bureau Tradelines & Stability</h3>
          <p>
            {isINR
              ? 'Key credit bureau and banking tradelines verified through Account Aggregator (AA) and CIBIL report.'
              : 'Credit profile features calibrated against historical loan underwriting cohorts.'}
          </p>
          <div className="form-grid">
            <label>
              Credit line utilization (%)
              <input
                type="number"
                required
                min="0"
                max="250"
                step="0.1"
                value={value.revolving_utilization}
                onChange={e => onChange({ ...value, revolving_utilization: Number(e.target.value) })}
              />
            </label>

            <label>
              Active credit lines
              <input
                type="number"
                required
                min="0"
                max="100"
                value={value.open_accounts}
                onChange={e => onChange({ ...value, open_accounts: Number(e.target.value) })}
              />
            </label>

            <label>
              {isINR ? 'Default suits / Write-offs' : 'Public bankruptcies'}
              <input
                type="number"
                required
                min="0"
                max="20"
                value={value.public_bankruptcies}
                onChange={e => onChange({ ...value, public_bankruptcies: Number(e.target.value) })}
              />
            </label>

            <label>
              Outstanding credit balance ({sym})
              <input
                type="number"
                required
                min="0"
                max={isINR ? 50000000 : 1000000}
                step="1"
                value={value.revolving_balance}
                onChange={e => onChange({ ...value, revolving_balance: Number(e.target.value) })}
              />
            </label>

            <label className="wide">
              Residential status
              <select
                value={value.home_ownership}
                onChange={e => onChange({ ...value, home_ownership: e.target.value })}
              >
                <option value="OWN">Self-Owned Property</option>
                <option value="MORTGAGE">Home Loan / Mortgaged</option>
                <option value="RENT">Rented Accommodation</option>
              </select>
            </label>
          </div>
        </div>

        <div className="form-actions">
          <button className="primary" type="submit" disabled={busy}>
            {busy ? 'Evaluating Credit Profile…' : 'Run Underwriting Engine'}
          </button>
          <button className="secondary" type="button" onClick={onClear}>
            Reset Defaults
          </button>
        </div>
      </form>
    </section>
  );
}
