"""Dual-engine Database layer: PostgreSQL for high-throughput production & SQLite for local development."""
import os
from pathlib import Path
import json
import uuid
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / 'data/underwrite.db'
DATABASE_URL = os.getenv('DATABASE_URL', '')

IS_POSTGRES = bool(DATABASE_URL and (DATABASE_URL.startswith('postgres://') or DATABASE_URL.startswith('postgresql://')))

# Threaded connection pool for PostgreSQL
_pg_pool = None

def get_connection():
    global _pg_pool
    if IS_POSTGRES:
        import psycopg2
        from psycopg2.pool import SimpleConnectionPool
        from psycopg2.extras import RealDictCursor
        if _pg_pool is None:
            # Pool with min 2, max 20 connections
            _pg_pool = SimpleConnectionPool(2, 20, DATABASE_URL, cursor_factory=RealDictCursor)
        return _pg_pool.getconn()
    else:
        import sqlite3
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

def release_connection(conn):
    """Safely return connection to pool or close if SQLite."""
    global _pg_pool
    if IS_POSTGRES and _pg_pool is not None:
        try:
            _pg_pool.putconn(conn)
        except Exception:
            conn.close()
    else:
        try:
            conn.close()
        except Exception:
            pass


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    if IS_POSTGRES:
        print(f"✓ Initializing PostgreSQL database from DATABASE_URL")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id VARCHAR(64) PRIMARY KEY,
            created_at VARCHAR(64) NOT NULL,
            currency VARCHAR(10) NOT NULL,
            requested_amount DOUBLE PRECISION NOT NULL,
            annual_income DOUBLE PRECISION NOT NULL,
            dti DOUBLE PRECISION NOT NULL,
            credit_score INTEGER NOT NULL,
            score_type VARCHAR(20) NOT NULL,
            employment_years DOUBLE PRECISION NOT NULL,
            term_months INTEGER NOT NULL,
            purpose VARCHAR(64) NOT NULL,
            revolving_utilization DOUBLE PRECISION NOT NULL,
            open_accounts INTEGER NOT NULL,
            public_bankruptcies INTEGER NOT NULL,
            revolving_balance DOUBLE PRECISION NOT NULL,
            home_ownership VARCHAR(32) NOT NULL
        );

        CREATE TABLE IF NOT EXISTS assessments (
            id VARCHAR(64) PRIMARY KEY,
            application_id VARCHAR(64) NOT NULL REFERENCES applications(id),
            created_at VARCHAR(64) NOT NULL,
            status VARCHAR(64) NOT NULL,
            repayment_probability DOUBLE PRECISION NOT NULL,
            probability_of_default DOUBLE PRECISION NOT NULL,
            offer_amount DOUBLE PRECISION,
            risk_adjusted_apr DOUBLE PRECISION NOT NULL,
            monthly_emi DOUBLE PRECISION,
            expected_loss DOUBLE PRECISION,
            kfs_json TEXT,
            shap_json TEXT,
            recourse_json TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_applications_created ON applications(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_assessments_created ON assessments(created_at DESC);
        """)
    else:
        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS applications (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            currency TEXT NOT NULL,
            requested_amount REAL NOT NULL,
            annual_income REAL NOT NULL,
            dti REAL NOT NULL,
            credit_score INTEGER NOT NULL,
            score_type TEXT NOT NULL,
            employment_years REAL NOT NULL,
            term_months INTEGER NOT NULL,
            purpose TEXT NOT NULL,
            revolving_utilization REAL NOT NULL,
            open_accounts INTEGER NOT NULL,
            public_bankruptcies INTEGER NOT NULL,
            revolving_balance REAL NOT NULL,
            home_ownership TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS assessments (
            id TEXT PRIMARY KEY,
            application_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL,
            repayment_probability REAL NOT NULL,
            probability_of_default REAL NOT NULL,
            offer_amount REAL,
            risk_adjusted_apr REAL NOT NULL,
            monthly_emi REAL,
            expected_loss REAL,
            kfs_json TEXT,
            shap_json TEXT,
            recourse_json TEXT,
            FOREIGN KEY(application_id) REFERENCES applications(id)
        );

        CREATE INDEX IF NOT EXISTS idx_applications_created ON applications(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_assessments_created ON assessments(created_at DESC);
        """)
    conn.commit()
    release_connection(conn)

def save_application_and_assessment(app_data: dict, result_data: dict) -> tuple[str, str]:
    app_id = str(uuid.uuid4())
    assessment_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    conn = get_connection()
    cursor = conn.cursor()

    score_val = app_data.get('cibil') if app_data.get('cibil') is not None else app_data.get('fico', 720)
    score_type = 'CIBIL' if app_data.get('cibil') is not None or app_data.get('currency') == 'INR' else 'FICO'

    ph = '%s' if IS_POSTGRES else '?'

    app_sql = f"""
        INSERT INTO applications (
            id, created_at, currency, requested_amount, annual_income, dti,
            credit_score, score_type, employment_years, term_months, purpose,
            revolving_utilization, open_accounts, public_bankruptcies, revolving_balance,
            home_ownership
        ) VALUES ({', '.join([ph]*16)})
    """
    cursor.execute(app_sql, (
        app_id, now, app_data.get('currency', 'INR'),
        app_data['requested_amount'], app_data['annual_income'], app_data['dti'],
        score_val, score_type, app_data['employment_years'], app_data['term_months'],
        app_data['purpose'], app_data['revolving_utilization'], app_data['open_accounts'],
        app_data['public_bankruptcies'], app_data['revolving_balance'], app_data['home_ownership']
    ))

    assess_sql = f"""
        INSERT INTO assessments (
            id, application_id, created_at, status, repayment_probability,
            probability_of_default, offer_amount, risk_adjusted_apr, monthly_emi,
            expected_loss, kfs_json, shap_json, recourse_json
        ) VALUES ({', '.join([ph]*13)})
    """
    cursor.execute(assess_sql, (
        assessment_id, app_id, now, result_data['status'],
        result_data['repayment_probability'], result_data['probability_of_default'],
        result_data.get('offer_amount'), result_data.get('risk_adjusted_apr', 0.12),
        result_data.get('illustrative_monthly_payment'), result_data.get('expected_loss'),
        json.dumps(result_data.get('key_fact_statement')),
        json.dumps({
            'adverse': result_data.get('adverse_action_factors', []),
            'strengths': result_data.get('key_strengths', [])
        }),
        json.dumps(result_data.get('counterfactual_recourse', []))
    ))

    conn.commit()
    release_connection(conn)
    return app_id, assessment_id

def list_recent_applications(limit: int = 50) -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    ph = '%s' if IS_POSTGRES else '?'
    sql = f"""
        SELECT a.id as application_id, a.created_at, a.currency, a.requested_amount,
               a.annual_income, a.dti, a.credit_score, a.score_type, a.purpose,
               s.id as assessment_id, s.status, s.repayment_probability, s.offer_amount,
               s.risk_adjusted_apr, s.monthly_emi, s.expected_loss
        FROM applications a
        JOIN assessments s ON s.application_id = a.id
        ORDER BY a.created_at DESC
        LIMIT {ph}
    """
    cursor.execute(sql, (limit,))
    rows = cursor.fetchall()
    release_connection(conn)
    return [dict(row) for row in rows]
