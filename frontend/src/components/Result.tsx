export type ShapFactor = {
  feature: string;
  label: string;
  shap_value: number;
  direction: 'positive' | 'negative';
};

export type KeyFactStatement = {
  sanctioned_amount: number;
  processing_fee_rate_pct: number;
  processing_fee: number;
  gst_on_processing_fee: number;
  net_disbursed_amount: number;
  monthly_emi: number;
  tenure_months: number;
  annualized_percentage_rate_pct: number;
  total_interest_payable: number;
  total_repayment_amount: number;
  regulatory_standard: string;
};

export type RecourseAction = {
  action: string;
  rationale: string;
  projected_impact: string;
  category: string;
};

export type Assessment = {
  status: string;
  currency: 'INR' | 'USD';
  repayment_probability: number;
  probability_of_default?: number;
  historical_amount_benchmark: number | null;
  affordability_cap: number;
  offer_amount: number | null;
  illustrative_monthly_payment: number | null;
  assumed_apr: number;
  risk_adjusted_apr?: number;
  loss_given_default?: number;
  expected_loss?: number | null;
  key_fact_statement?: KeyFactStatement | null;
  counterfactual_recourse?: RecourseAction[];
  adverse_action_factors?: ShapFactor[];
  key_strengths?: ShapFactor[];
  scenario_sensitivity: { feature: string; reference_value: number; probability_change_if_reference: number }[];
  model_version: string;
  disclaimer: string;
};

const formatMoney = (n: number, currency: 'INR' | 'USD' = 'INR') =>
  new Intl.NumberFormat(currency === 'INR' ? 'en-IN' : 'en-US', {
    style: 'currency',
    currency: currency,
    maximumFractionDigits: 0
  }).format(n);

const labels: Record<string, string> = {
  fico_range_low: 'Credit Score',
  dti: 'Debt-to-income / FOIR',
  annual_inc: 'Annual income',
  emp_length: 'Employment years',
  loan_amnt: 'Requested amount',
  revol_util: 'Card utilization',
  pub_rec_bankruptcies: 'Legal suits / Bankruptcies',
  revol_bal: 'Revolving card balance'
};

export function Result({ data, error }: { data: Assessment | null; error: string }) {
  const isINR = data?.currency === 'INR';
  const curr = data?.currency ?? 'INR';

  return (
    <section className="panel result-panel">
      <div className="panel-heading">
        <div>
          <h2>Decision Result & Term Sheet</h2>
          <p>
            {isINR
              ? 'Institutional underwriting term sheet under RBI Digital Lending Guidelines.'
              : 'Institutional underwriting term sheet under US Consumer Credit Standards.'}
          </p>
        </div>
        {data && data.offer_amount && (
          <button
            type="button"
            className="secondary"
            onClick={() => window.print()}
            style={{ fontSize: '12px', padding: '6px 12px', display: 'flex', alignItems: 'center', gap: '4px' }}
          >
            🖨️ Print Sanction Letter
          </button>
        )}
      </div>

      {error ? (
        <div role="alert" className="error">
          {error}
        </div>
      ) : data ? (
        <>
          {/* Main Decision Badge */}
          <div
            className={`status ${
              data.status === 'eligible_for_simulated_offer'
                ? 'positive'
                : data.status === 'review'
                ? 'review'
                : 'negative'
            }`}
          >
            <div className="status-icon">
              {data.status === 'eligible_for_simulated_offer' ? '✓' : data.status === 'review' ? '…' : '×'}
            </div>
            <div>
              <strong>
                {data.status === 'eligible_for_simulated_offer'
                  ? 'Sanctioned for Loan Offer'
                  : data.status === 'review'
                  ? 'Manual Credit Committee Review'
                  : 'Declined — Outside Risk Appetite'}
              </strong>
              <span>
                Repayment Probability: {(data.repayment_probability * 100).toFixed(1)}% · Probability of Default (PD):{' '}
                {((data.probability_of_default ?? (1 - data.repayment_probability)) * 100).toFixed(1)}%
              </span>
            </div>
          </div>

          {/* Sanctioned Offer Overview */}
          <div className="offer">
            <div>
              <small>Sanctioned Loan Facility</small>
              <strong>{data.offer_amount ? formatMoney(data.offer_amount, curr) : 'No Offer'}</strong>
              <span>
                {data.offer_amount
                  ? `Optimized within ${isINR ? 'RBI 50% FOIR limit' : 'CFPB 36% DTI limit'} and credit capacity.`
                  : 'Debt burden exceeds permissible debt-service coverage ratios.'}
              </span>
            </div>
            <div className="offer-details">
              <div>
                <span>Risk-Adjusted APR</span>
                <b>
                  {data.risk_adjusted_apr
                    ? `${(data.risk_adjusted_apr * 100).toFixed(2)}%`
                    : `${(data.assumed_apr * 100).toFixed(1)}%`}
                </b>
              </div>
              <div>
                <span>Max Affordability Cap</span>
                <b>{formatMoney(data.affordability_cap, curr)}</b>
              </div>
              <div>
                <span>Monthly Installment (EMI)</span>
                <b>{data.illustrative_monthly_payment ? formatMoney(data.illustrative_monthly_payment, curr) : '—'}</b>
              </div>
              <div>
                <span>Expected Credit Loss (EL)</span>
                <b>
                  {data.expected_loss !== undefined && data.expected_loss !== null
                    ? formatMoney(data.expected_loss, curr)
                    : '—'}
                </b>
              </div>
            </div>
          </div>

          {/* RBI Key Fact Statement (KFS) */}
          {data.key_fact_statement && (
            <div className="factor-section" style={{ background: '#f8fafc', padding: '16px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <h3 style={{ margin: 0 }}>Key Fact Statement (KFS)</h3>
                <span style={{ fontSize: '11px', background: '#e0e7ff', color: '#3730a3', padding: '2px 8px', borderRadius: '4px', fontWeight: 600 }}>
                  {data.key_fact_statement.regulatory_standard}
                </span>
              </div>
              <p style={{ margin: '0 0 12px 0', fontSize: '12px', color: '#64748b' }}>
                Standardized mandatory disclosure of total loan cost, upfront deductions, and net disbursal.
              </p>
              <div className="offer-details" style={{ marginTop: '8px' }}>
                <div>
                  <span>Net Disbursed to Bank</span>
                  <b style={{ color: '#047857' }}>{formatMoney(data.key_fact_statement.net_disbursed_amount, curr)}</b>
                </div>
                <div>
                  <span>Processing Fee (1.5% + GST)</span>
                  <b>{formatMoney(data.key_fact_statement.processing_fee + data.key_fact_statement.gst_on_processing_fee, curr)}</b>
                </div>
                <div>
                  <span>Total Interest Payable</span>
                  <b>{formatMoney(data.key_fact_statement.total_interest_payable, curr)}</b>
                </div>
                <div>
                  <span>Total Repayment Amount</span>
                  <b>{formatMoney(data.key_fact_statement.total_repayment_amount, curr)}</b>
                </div>
              </div>
            </div>
          )}

          {/* Actionable Counterfactual Recourse */}
          {data.counterfactual_recourse && data.counterfactual_recourse.length > 0 && (
            <div className="factor-section">
              <h3>Actionable Borrower Recourse (Prescriptive Plan)</h3>
              <p>Optimization-backed steps to expand borrowing capacity and reduce interest spread.</p>
              {data.counterfactual_recourse.map((r, idx) => (
                <div
                  className="factor"
                  key={idx}
                  style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: '4px', padding: '10px 12px' }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
                    <strong style={{ fontSize: '13px', color: '#0f172a' }}>{r.action}</strong>
                    <span style={{ fontSize: '11px', background: '#dcfce7', color: '#15803d', padding: '2px 8px', borderRadius: '4px', fontWeight: 600 }}>
                      {r.projected_impact}
                    </span>
                  </div>
                  <span style={{ fontSize: '12px', color: '#64748b' }}>{r.rationale}</span>
                </div>
              ))}
            </div>
          )}

          {/* TreeSHAP Feature Attributions */}
          {((data.adverse_action_factors && data.adverse_action_factors.length > 0) ||
            (data.key_strengths && data.key_strengths.length > 0)) && (
            <div className="factor-section">
              <h3>TreeSHAP Feature Attributions</h3>
              <p>Exact contribution to log-odds score (Regulatory Adverse Action & Credit Strengths).</p>

              {data.key_strengths && data.key_strengths.length > 0 && (
                <div style={{ marginBottom: '12px' }}>
                  <small style={{ fontWeight: 600, color: '#16a34a', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    Top Credit Strengths
                  </small>
                  {data.key_strengths.map(s => (
                    <div className="factor" key={`pos-${s.feature}`}>
                      <span>{s.label}</span>
                      <b className="up">+{s.shap_value.toFixed(3)}</b>
                    </div>
                  ))}
                </div>
              )}

              {data.adverse_action_factors && data.adverse_action_factors.length > 0 && (
                <div>
                  <small style={{ fontWeight: 600, color: '#dc2626', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    Adverse Action Factors (Risk Drags)
                  </small>
                  {data.adverse_action_factors.map(s => (
                    <div className="factor" key={`neg-${s.feature}`}>
                      <span>{s.label}</span>
                      <b className="down">{s.shap_value.toFixed(3)}</b>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Scenario Sensitivity Probes */}
          <div className="factor-section">
            <h3>Scenario Sensitivity Probes</h3>
            <p>Empirical one-factor perturbations evaluated against reference portfolio medians.</p>
            {data.scenario_sensitivity.map(s => (
              <div className="factor" key={s.feature}>
                <span>
                  {labels[s.feature] || s.feature} → {s.reference_value.toLocaleString()}
                </span>
                <b className={s.probability_change_if_reference > 0 ? 'up' : 'down'}>
                  {s.probability_change_if_reference > 0 ? '+' : ''}
                  {(s.probability_change_if_reference * 100).toFixed(1)} pp
                </b>
              </div>
            ))}
          </div>

          <p className="fineprint">{data.disclaimer}</p>
        </>
      ) : (
        <div className="empty">
          <div className="empty-symbol">◎</div>
          <h3>Ready for an Assessment</h3>
          <p>Configure the applicant details in INR (₹) or USD ($) to run the underwriting engine.</p>
          <div className="empty-lines">
            <span />
            <span />
            <span />
          </div>
        </div>
      )}
    </section>
  );
}
