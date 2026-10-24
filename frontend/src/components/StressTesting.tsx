import { useState } from 'react';
import { AlertTriangle, TrendingUp, DollarSign, ShieldAlert } from 'lucide-react';

export function StressTesting() {
  const [repoShockBps, setRepoShockBps] = useState<number>(100);
  const [foirInflationShock, setFoirInflationShock] = useState<number>(8);
  const [unemploymentShock, setUnemploymentShock] = useState<number>(1.5);

  // Baseline Portfolio Metrics (₹50 Cr Portfolio)
  const portfolioSizeCr = 50.0;
  const basePD = 0.038; // 3.8%
  const baseCAR = 16.4; // 16.4% Capital Adequacy Ratio (RBI min is 15%)
  const lgd = 0.45;

  // Stressed Modeling Calculations
  const stressedPD = Math.min(
    0.25,
    basePD + (repoShockBps / 10000) * 0.45 + (foirInflationShock / 100) * 0.12 + (unemploymentShock / 100) * 0.35
  );
  const baseEL_Lakhs = portfolioSizeCr * 100 * basePD * lgd;
  const stressedEL_Lakhs = portfolioSizeCr * 100 * stressedPD * lgd;
  const additionalProvisionsLakhs = Math.max(0, stressedEL_Lakhs - baseEL_Lakhs);

  // CAR Degradation
  const stressedCAR = Math.max(10.0, baseCAR - (additionalProvisionsLakhs / (portfolioSizeCr * 100)) * 12);
  const isCarCompliant = stressedCAR >= 15.0;

  const setScenario = (repo: number, foir: number, unemp: number) => {
    setRepoShockBps(repo);
    setFoirInflationShock(foir);
    setUnemploymentShock(unemp);
  };

  return (
    <section className="panel" style={{ maxWidth: '1000px', margin: '0 auto' }}>
      <div className="panel-heading">
        <div>
          <h2>Macroeconomic Portfolio Stress Testing</h2>
          <p>
            RBI Basel III Supervisory Stress Engine — simulate macro shocks and evaluate capital provision adequacy.
          </p>
        </div>
        <span className="simulation-label" style={{ background: '#fef3c7', color: '#92400e' }}>
          ICAAP Scenario Engine
        </span>
      </div>

      {/* Scenario Presets */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '20px', flexWrap: 'wrap' }}>
        <button
          type="button"
          className="secondary"
          style={{ fontSize: '12px', padding: '6px 12px' }}
          onClick={() => setScenario(50, 4, 0.5)}
        >
          Mild Policy Tightening (+50 bps)
        </button>
        <button
          type="button"
          className="secondary"
          style={{ fontSize: '12px', padding: '6px 12px' }}
          onClick={() => setScenario(150, 10, 2.0)}
        >
          RBI Aggressive Hike (+150 bps)
        </button>
        <button
          type="button"
          className="secondary"
          style={{ fontSize: '12px', padding: '6px 12px', color: '#b91c1c' }}
          onClick={() => setScenario(250, 18, 3.5)}
        >
          Severe Stagflation Shock (+250 bps)
        </button>
      </div>

      {/* Interactive Sliders */}
      <div className="form-grid" style={{ marginBottom: '24px' }}>
        <label>
          RBI Repo Rate Hike ({repoShockBps} bps)
          <input
            type="range"
            min="0"
            max="300"
            step="25"
            value={repoShockBps}
            onChange={e => setRepoShockBps(Number(e.target.value))}
          />
          <small style={{ color: '#64748b' }}>Simulates borrowing cost increase across floating-rate portfolios.</small>
        </label>

        <label>
          Household Cost / FOIR Inflation (+{foirInflationShock}%)
          <input
            type="range"
            min="0"
            max="25"
            step="1"
            value={foirInflationShock}
            onChange={e => setFoirInflationShock(Number(e.target.value))}
          />
          <small style={{ color: '#64748b' }}>Simulates erosion of net disposable income and debt-service capacity.</small>
        </label>

        <label>
          Unemployment Surge (+{unemploymentShock}%)
          <input
            type="range"
            min="0"
            max="5"
            step="0.5"
            value={unemploymentShock}
            onChange={e => setUnemploymentShock(Number(e.target.value))}
          />
          <small style={{ color: '#64748b' }}>Simulates job displacement in salaried and retail borrower segments.</small>
        </label>
      </div>

      {/* Stressed Outcomes Cards */}
      <div className="offer" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', background: '#f8fafc', padding: '20px', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
        <div style={{ background: '#fff', padding: '14px', borderRadius: '8px', border: '1px solid #cbd5e1' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#64748b', fontSize: '12px', fontWeight: 600 }}>
            <TrendingUp size={16} /> Stressed Default Rate (PD)
          </div>
          <div style={{ fontSize: '24px', fontWeight: 700, color: '#dc2626', margin: '6px 0' }}>
            {(stressedPD * 100).toFixed(2)}%
          </div>
          <small style={{ color: '#64748b' }}>Baseline: {(basePD * 100).toFixed(1)}% (+{((stressedPD - basePD) * 100).toFixed(2)} pp spike)</small>
        </div>

        <div style={{ background: '#fff', padding: '14px', borderRadius: '8px', border: '1px solid #cbd5e1' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#64748b', fontSize: '12px', fontWeight: 600 }}>
            <DollarSign size={16} /> Additional Provisions
          </div>
          <div style={{ fontSize: '24px', fontWeight: 700, color: '#0f172a', margin: '6px 0' }}>
            ₹{additionalProvisionsLakhs.toFixed(1)} Lakhs
          </div>
          <small style={{ color: '#64748b' }}>Expected Loss: ₹{stressedEL_Lakhs.toFixed(1)}L (vs ₹{baseEL_Lakhs.toFixed(1)}L)</small>
        </div>

        <div style={{ background: '#fff', padding: '14px', borderRadius: '8px', border: '1px solid #cbd5e1' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#64748b', fontSize: '12px', fontWeight: 600 }}>
            <ShieldAlert size={16} /> Capital Adequacy (CAR)
          </div>
          <div style={{ fontSize: '24px', fontWeight: 700, color: isCarCompliant ? '#16a34a' : '#dc2626', margin: '6px 0' }}>
            {stressedCAR.toFixed(2)}%
          </div>
          <small style={{ color: isCarCompliant ? '#16a34a' : '#dc2626', fontWeight: 600 }}>
            {isCarCompliant ? '✓ Above RBI 15.0% Prudential Floor' : '⚠ Below RBI 15.0% Capital Floor'}
          </small>
        </div>
      </div>

      {/* Advisory Box */}
      <div style={{ marginTop: '20px', padding: '14px 18px', background: isCarCompliant ? '#f0fdf4' : '#fef2f2', border: `1px solid ${isCarCompliant ? '#bbf7d0' : '#fecaca'}`, borderRadius: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600, color: isCarCompliant ? '#166534' : '#991b1b', marginBottom: '4px' }}>
          <AlertTriangle size={18} />
          {isCarCompliant ? 'Supervisory Assessment: Capital Resilient' : 'Supervisory Alert: Capital Buffer Breach Projected'}
        </div>
        <p style={{ margin: 0, fontSize: '13px', color: isCarCompliant ? '#15803d' : '#b91c1c' }}>
          {isCarCompliant
            ? `Under a ${repoShockBps} bps repo shock and ${foirInflationShock}% inflation strain, the institution maintains sufficient risk-weighted capital buffers without requiring tier-1 equity replenishment.`
            : `Projected losses breach the regulatory 15.0% CAR minimum by ${(15.0 - stressedCAR).toFixed(2)} pp. Recommended Action: Tighten FOIR cutoffs from 50% to 42% on new originations and initiate ₹${additionalProvisionsLakhs.toFixed(0)}L in secondary provisioning.`}
        </p>
      </div>
    </section>
  );
}
