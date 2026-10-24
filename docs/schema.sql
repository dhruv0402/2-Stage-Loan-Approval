-- Future design only; no database is used by v0.1. Requires consent, auth and retention policy.
CREATE TABLE model_versions (
  id UUID PRIMARY KEY, artifact_sha256 CHAR(64) NOT NULL UNIQUE,
  dataset_sha256 CHAR(64) NOT NULL, config JSONB NOT NULL,
  metrics JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE applications (
  id UUID PRIMARY KEY, subject_pseudonym UUID NOT NULL,
  requested_amount_cents BIGINT NOT NULL CHECK (requested_amount_cents > 0),
  annual_income_cents BIGINT NOT NULL CHECK (annual_income_cents > 0),
  dti_basis_points INT NOT NULL CHECK (dti_basis_points BETWEEN 0 AND 10000),
  fico_score SMALLINT NOT NULL CHECK (fico_score BETWEEN 300 AND 850),
  employment_months SMALLINT NOT NULL CHECK (employment_months BETWEEN 0 AND 600),
  term_months SMALLINT NOT NULL CHECK (term_months IN (36,60)),
  purpose TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  retention_until TIMESTAMPTZ NOT NULL
);
CREATE INDEX applications_subject_created ON applications(subject_pseudonym, created_at DESC);
CREATE TABLE assessments (
  id UUID PRIMARY KEY, application_id UUID NOT NULL REFERENCES applications(id),
  model_version_id UUID NOT NULL REFERENCES model_versions(id),
  status TEXT NOT NULL CHECK(status IN ('eligible_for_simulated_offer','review','outside_demo_policy')),
  repayment_probability NUMERIC(7,6) NOT NULL CHECK(repayment_probability BETWEEN 0 AND 1),
  historical_amount_cents BIGINT NOT NULL, affordability_cap_cents BIGINT NOT NULL,
  offer_amount_cents BIGINT, sensitivity JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX assessments_application_created ON assessments(application_id, created_at DESC);
CREATE TABLE audit_events (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  assessment_id UUID NOT NULL REFERENCES assessments(id), event_type TEXT NOT NULL,
  event_payload JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
