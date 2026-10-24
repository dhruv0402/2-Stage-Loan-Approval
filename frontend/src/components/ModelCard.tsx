export type ModelInfo = {
  threshold: number;
  limitations: string[];
  metrics: {
    source_rows: number; train_rows: number; selection_rows: number; calibration_rows: number;
    internal_check_rows: number; test_rows: number;
    test_date_range: string[];
    model_selection: {logistic_selection_roc_auc: number; boosted_selection_roc_auc: number};
    internal_check_roc_auc: number;
    repayment: {roc_auc: number; roc_auc_bootstrap_95pct: number[]; average_precision: number;
      brier: number; precision_at_threshold: number; recall_at_threshold: number; observed_favorable_rate: number};
    by_issue_year: Record<string, {rows: number; roc_auc: number; brier: number}>;
    amount_historical_mae_usd: number; amount_historical_median_baseline_mae_usd: number;
  };
};

export function ModelCard({card}:{card:ModelInfo|null}) {
  const metrics=card?.metrics;
  return <section className="info-page"><h1>Model card</h1><p>The measured performance and limitations behind each assessment.</p>
    {metrics?<>
      <div className="model-feature"><div><small>Future-period ROC AUC</small><strong>{metrics.repayment.roc_auc.toFixed(3)}</strong><span>95% bootstrap interval {metrics.repayment.roc_auc_bootstrap_95pct.join('–')}</span></div><p>{metrics.test_rows.toLocaleString()} labeled funded loans from {metrics.test_date_range[0]} to {metrics.test_date_range[1]}. Historical outcomes only; this is not approval accuracy.</p></div>
      <div className="metrics"><div><small>Average precision</small><strong>{metrics.repayment.average_precision.toFixed(3)}</strong></div><div><small>Brier score ↓</small><strong>{metrics.repayment.brier.toFixed(3)}</strong></div><div><small>Historical amount MAE ↓</small><strong>${Math.round(metrics.amount_historical_mae_usd).toLocaleString()}</strong></div><div><small>Median baseline MAE</small><strong>${Math.round(metrics.amount_historical_median_baseline_mae_usd).toLocaleString()}</strong></div></div>
      <div className="info-block"><h2>Out-of-time performance</h2><p>Selection AUC: boosted {metrics.model_selection.boosted_selection_roc_auc.toFixed(3)} vs logistic {metrics.model_selection.logistic_selection_roc_auc.toFixed(3)}. The earlier April–June check scored {metrics.internal_check_roc_auc.toFixed(3)} AUC.</p><div className="year-bars">{Object.entries(metrics.by_issue_year).map(([year,row])=><div className="year-row" key={year}><b>{year}</b><div className="year-track"><span style={{width:`${row.roc_auc*100}%`}}/></div><strong>{row.roc_auc.toFixed(3)}</strong><small>{row.rows.toLocaleString()} loans</small></div>)}</div><p className="metric-note">AUC fell across the three future years. Outcome maturity and dataset selection can affect this comparison.</p></div>
      <div className="info-block"><h2>Two-stage method</h2><p><b>1. Outcome estimate:</b> LightGBM chosen on Jan–Feb 2016, then calibrated on March 2016. It estimates the derived favorable label among previously funded loans.</p><p><b>2. Historical amount:</b> another LightGBM model runs only for eligible scenarios. A documented affordability formula caps its amount estimate.</p><p>Fit: {metrics.train_rows.toLocaleString()} rows; selection: {metrics.selection_rows.toLocaleString()}; calibration: {metrics.calibration_rows.toLocaleString()}; earlier check: {metrics.internal_check_rows.toLocaleString()}.</p><h2>Limitations</h2><ul>{card?.limitations.map(item=><li key={item}>{item}</li>)}</ul></div>
    </>:<div className="info-block"><p>The model card is unavailable. Start the API and load the trained bundle to inspect measured results.</p></div>}</section>
}
