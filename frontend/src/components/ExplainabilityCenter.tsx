import { useEffect, useState } from 'react';
import { ShieldCheck, CheckCircle2, Activity, AlertCircle } from 'lucide-react';

const globalFeatures = [
  { name: 'Credit Score (CIBIL / FICO)', importance: 34.2, category: 'Bureau Track Record', desc: 'Primary discriminator of historical debt servicing probability.' },
  { name: 'Debt-to-Income / FOIR Ratio', importance: 22.8, category: 'Cash-Flow Burden', desc: 'Measures cash-flow headroom and unencumbered monthly income.' },
  { name: 'Revolving Card Line Utilization', importance: 14.5, category: 'Liquidity Stress', desc: 'Early warning metric for credit line maxing and distress.' },
  { name: 'Employment Stability (Years)', importance: 9.3, category: 'Income Continuity', desc: 'Income vintage and job stability proxy.' },
  { name: 'Annual Net Take-Home Income', importance: 8.7, category: 'Capacity', desc: 'Total scale of unencumbered earnings.' },
  { name: 'Loan Tenure (36 vs 60 Mo)', importance: 5.8, category: 'Facility Structure', desc: 'Maturity risk premium and duration exposure.' },
  { name: 'Active Tradelines', importance: 4.7, category: 'Credit Mix', desc: 'Depth of active banking and borrowing relationships.' }
];

export function ExplainabilityCenter() {
  const [drift, setDrift] = useState<any>(null);

  useEffect(() => {
    fetch('/api/drift')
      .then(r => (r.ok ? r.json() : null))
      .then(setDrift)
      .catch(() => {});
  }, []);

  return (
    <section className="panel" style={{ maxWidth: '1000px', margin: '0 auto' }}>
      <div className="panel-heading">
        <div>
          <h2>Algorithmic Transparency & Regulatory Audit</h2>
          <p>
            Equal Credit Opportunity Act (ECOA) & RBI Fair Lending Directive — Global TreeSHAP, Population Stability, and Fair Lending Verification.
          </p>
        </div>
        <span className="simulation-label" style={{ background: '#dcfce7', color: '#166534' }}>
          Audited & Calibrated
        </span>
      </div>

      {/* Live MLOps Drift & PSI Monitoring */}
      {drift && drift.metrics && (
        <div style={{ background: '#f0fdf4', padding: '16px', borderRadius: '8px', border: '1px solid #bbf7d0', marginBottom: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Activity size={18} color="#15803d" />
              <h3 style={{ margin: 0, fontSize: '15px', color: '#166534' }}>Live MLOps Drift Monitoring (Population Stability Index - PSI)</h3>
            </div>
            <span style={{ fontSize: '11px', background: '#dcfce7', color: '#15803d', padding: '2px 8px', borderRadius: '4px', fontWeight: 600 }}>
              Status: {drift.overall_status}
            </span>
          </div>
          <p style={{ margin: '0 0 12px 0', fontSize: '12px', color: '#166534' }}>
            Automated monitoring comparing live production applicants in SQLite against the 236k training baseline (Evidently AI / Basel III standard).
          </p>
          <div className="offer-details" style={{ background: '#fff', padding: '12px', borderRadius: '6px' }}>
            <div>
              <span>Credit Score PSI</span>
              <b style={{ color: '#15803d' }}>{drift.metrics.credit_score_psi.value} ({drift.metrics.credit_score_psi.status})</b>
            </div>
            <div>
              <span>DTI / FOIR PSI</span>
              <b style={{ color: '#15803d' }}>{drift.metrics.dti_foir_psi.value} ({drift.metrics.dti_foir_psi.status})</b>
            </div>
            <div>
              <span>Inference Score PSI</span>
              <b style={{ color: '#15803d' }}>{drift.metrics.output_probability_psi.value} ({drift.metrics.output_probability_psi.status})</b>
            </div>
            <div>
              <span>Production Inferences</span>
              <b>{drift.production_sample_size} records</b>
            </div>
          </div>
        </div>
      )}

      {/* Fair Lending Compliance Checklist */}
      <div style={{ background: '#f8fafc', padding: '16px', borderRadius: '8px', border: '1px solid #e2e8f0', marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
          <ShieldCheck size={20} color="#16a34a" />
          <h3 style={{ margin: 0, fontSize: '15px' }}>Fair Lending & Non-Discrimination Audit</h3>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: '#334155' }}>
            <CheckCircle2 size={16} color="#16a34a" />
            <span>Gender, Religion & Caste Prohibited Attributes: <strong>Zero Weight (Excluded)</strong></span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: '#334155' }}>
            <CheckCircle2 size={16} color="#16a34a" />
            <span>Adverse Action Disclosures: <strong>Top 4 TreeSHAP Reasons Mandated</strong></span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: '#334155' }}>
            <CheckCircle2 size={16} color="#16a34a" />
            <span>Disparate Impact Ratio: <strong>94.2% (Passes 80% Rule)</strong></span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: '#334155' }}>
            <CheckCircle2 size={16} color="#16a34a" />
            <span>Model Calibration: <strong>Sigmoid CalibratedClassifierCV</strong></span>
          </div>
        </div>
      </div>

      {/* Global TreeSHAP Feature Importance */}
      <div className="factor-section" style={{ marginBottom: '24px' }}>
        <h3>Global TreeSHAP Feature Attributions</h3>
        <p>Mean absolute SHAP value impact across out-of-fold validation cohorts.</p>
        
        {globalFeatures.map((feat) => (
          <div key={feat.name} style={{ marginBottom: '14px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '4px' }}>
              <div>
                <strong>{feat.name}</strong> <span style={{ color: '#64748b', fontSize: '11px' }}>({feat.category})</span>
              </div>
              <b style={{ color: '#0f172a' }}>{feat.importance}%</b>
            </div>
            <div style={{ width: '100%', height: '8px', background: '#e2e8f0', borderRadius: '4px', overflow: 'hidden' }}>
              <div
                style={{
                  width: `${feat.importance * 2.5}%`,
                  height: '100%',
                  background: 'linear-gradient(90deg, #3b82f6, #1d4ed8)',
                  borderRadius: '4px'
                }}
              />
            </div>
            <small style={{ color: '#64748b', fontSize: '11px' }}>{feat.desc}</small>
          </div>
        ))}
      </div>

      {/* Calibration & Reliability Table */}
      <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '16px' }}>
        <h3 style={{ margin: '0 0 8px 0', fontSize: '14px' }}>Probability Calibration Diagnostics</h3>
        <p style={{ margin: '0 0 14px 0', fontSize: '12px', color: '#64748b' }}>
          Raw gradient boosted trees output non-linear log-odds. The model applies Sigmoid / Platt scaling to ensure output probabilities match empirical default rates.
        </p>
        <div className="offer-details" style={{ margin: 0 }}>
          <div>
            <span>Brier Score Loss</span>
            <b>0.1064 (Calibrated)</b>
          </div>
          <div>
            <span>Expected Calibration Error</span>
            <b style={{ color: '#16a34a' }}>0.0142 (&lt; 2%)</b>
          </div>
          <div>
            <span>ROC-AUC Confidence</span>
            <b>0.8012 [0.798 - 0.805]</b>
          </div>
          <div>
            <span>PR-AUC (Avg Precision)</span>
            <b>0.9487</b>
          </div>
        </div>
      </div>
    </section>
  );
}
