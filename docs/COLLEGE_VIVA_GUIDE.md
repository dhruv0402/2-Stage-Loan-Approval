# Credence AI — College Demo & Viva Defense Guide

This guide is designed for your **3rd-year college project presentation and viva**. It contains the exact 2-minute elevator pitch, live demo walkthrough steps, and plain-English answers to questions professors will ask.

---

## 1. The 60-Second Elevator Pitch (Start with this)

> "Respected evaluators, today most retail lending either relies on slow manual bank reviews or opaque black-box machine learning models that can't legally explain why an applicant was rejected.
> 
> We built **Credence AI**, an end-to-end autonomous credit decision engine tailored to Indian retail lending under **RBI Digital Lending Guidelines**.
> 
> Instead of a naive single-step model, Credence AI works in **two stages**:
> 1. **Stage 1 (Risk Assessment)** uses calibrated LightGBM with regulatory monotone constraints and native **TreeSHAP** to predict the Probability of Default (PD) and explain top risk drivers.
> 2. **Stage 2 (Credit Sizing & Affordability)** automatically computes debt capacity enforcing the **RBI 50% FOIR cap** and generates an instant **Key Fact Statement (KFS)** with an amortized EMI breakdown.
> 
> The entire system is containerized with Docker, backed by PostgreSQL and Redis for rate-limiting, and features real-time population drift monitoring."

---

## 2. The 3-Step Live Demo Script (Use the new 1-Click Buttons)

During your presentation, navigate to the **Underwriting Workbench** and click each preset button:

### Scenario 1: Click `[Profile A: Prime Salaried]` → Click "Run Assessment"
- **What happens**: The applicant has CIBIL 795, low 16% DTI.
- **What to say**: *"Here is a clean approval. Notice the green sanction card: the borrower requested ₹4,00,000, and our Stage 2 regressor approved ₹4,00,000 at a prime risk-adjusted rate of 12.8%. Below is the mandatory RBI Key Fact Statement showing processing fees, 18% GST, and net disbursement."*

### Scenario 2: Click `[Profile B: Over-leveraged]` → Click "Run Assessment"
- **What happens**: The applicant has CIBIL 685, but high DTI (52%).
- **What to say**: *"Here is a borderline applicant. Their CIBIL is decent, but their existing EMIs exceed the RBI 50% FOIR ceiling. Instead of giving a flat rejection, Credence AI offers **Counterfactual Recourse**—it calculates that reducing monthly debt obligations or tenure can qualify them for safe credit."*

### Scenario 3: Click `[Profile C: High Risk]` → Click "Run Assessment"
- **What happens**: CIBIL 560, high credit card utilization (89%), bankruptcy on record.
- **What to say**: *"Here is a clear default risk. The system immediately rejects the offer, but more importantly, our TreeSHAP explainability engine plots the top adverse action factors—identifying excessive revolving utilization and low bureau score as the primary drags."*

---

## 3. Top 8 Viva Questions & Exact Answers

### Q1: Why did you use a "Two-Stage" model instead of just one model?
**Answer**:
> "In real banking, deciding *whether* to approve someone is a classification problem (Stage 1: will they repay?). Deciding *how much* to lend is a continuous sizing problem constrained by income and cash flow (Stage 2: affordability PV).
> Combining them into a single model causes severe bias—for example, predicting loan amount for people who will default makes no sense. Separating them mimics real bank credit committees."

---

### Q2: Why LightGBM instead of Deep Learning / Neural Networks?
**Answer**:
> "Credit tabular data is structured, heterogenous, and contains strict non-linear thresholds (like CIBIL cutoffs).
> Industry consensus and benchmarks show Gradient Boosted Decision Trees (LightGBM/XGBoost) consistently outperform Neural Networks on tabular data, train in seconds, and natively support **TreeSHAP** marginal attributions and **Monotone Constraints**."

---

### Q3: What is "TreeSHAP" and why not just use standard feature importance?
**Answer**:
> "Standard feature importance only gives a global score for the entire dataset—it doesn't tell you why an *individual* person was rejected.
> TreeSHAP (from cooperative game theory) computes the exact marginal contribution of each feature for a single borrower. This allows us to satisfy RBI and Fair Lending requirements for adverse action notices."

---

### Q4: What is the "Brier Score" and why do you care about Calibration?
**Answer**:
> "Most student ML projects only look at ROC-AUC, which only measures ranking. But banks price loans using *actual probabilities* (e.g. Expected Loss = Exposure × PD × LGD).
> A Brier score measures probability error (like MSE for probabilities). Our model achieved a calibrated Brier score of **0.068**, meaning when the model says someone has an 80% chance of repayment, 8 out of 10 such borrowers actually repay."

---

### Q5: How is your project aligned with the Indian Financial System?
**Answer**:
> "Three major ways:
> 1. We mapped CIBIL scores (300 to 900) to calibrated credit risk percentiles.
> 2. We enforced the **RBI 50% FOIR (Fixed Obligation to Income Ratio)** rule so borrowers cannot be given loans that consume over 50% of their net salary in EMIs.
> 3. We auto-generate the RBI-mandated **Key Fact Statement (KFS)** itemizing the 1.5% origination fee, 18% GST, and net disbursed funds."

---

### Q6: What is "Monotone Constraints"?
**Answer**:
> "Without constraints, decision trees can overfit sample noise—for instance, randomly predicting that a CIBIL score of 710 is riskier than 705.
> We enforced monotonic constraints in LightGBM (`+1` for credit score, `-1` for debt and utilization) ensuring that higher credit score always strictly increases approval probability, which is required for regulatory compliance."

---

### Q7: What is the role of PostgreSQL and Redis in this architecture?
**Answer**:
> "PostgreSQL provides relational ACID persistence for our audit trail, logging every loan evaluation, TreeSHAP values, and timestamps.
> Redis provides sub-millisecond memoized caching for repeat assessments and enforces a sliding-window rate limit (100 requests/minute) to protect the API from automated bot traffic and DoS attacks."

---

### Q8: What is Population Stability Index (PSI) in your Drift endpoint?
**Answer**:
> "Over time, applicant demographics shift (macro inflation, job market changes). PSI measures the divergence between the baseline training distribution and live incoming applicants.
> If PSI is under 0.10, the model is stable. If it crosses 0.25, the system alerts the risk officer that the model must be retrained."
