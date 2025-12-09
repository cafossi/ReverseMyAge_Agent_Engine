# app/sub_agents/nbot/reports/sections.py
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, List

from app.utils.utils import get_env_var
from google.adk.tools.bigquery.client import get_bigquery_client
from google.cloud import bigquery

__all__ = [
    "compute_workforce_scope",
    "compute_nbot_contribution",
    "ContributionRow",
]

# -----------------------------------------------------------------------------
# Environment / FQN resolution
# -----------------------------------------------------------------------------

_DATA_PROJECT = get_env_var("BQ_DATA_PROJECT_ID")
_DATASET = get_env_var("BQ_DATASET_ID")

# May be a bare table, dataset.table, or project.dataset.table
_RAW_TABLE = os.getenv("APEX_COUNTERS_TABLE", "APEX_Counters").strip()

def _resolve_table_fqn(raw: str) -> str:
    """
    Resolve table name into a fully-qualified identifier:
      - project.dataset.table  -> use as-is
      - dataset.table          -> prefix project
      - table                  -> prefix project + dataset
    """
    parts = [p for p in raw.split(".") if p]
    if len(parts) >= 3:
        # Already project.dataset.table
        return raw
    if len(parts) == 2:
        # dataset.table -> prefix project
        return f"{_DATA_PROJECT}.{raw}"
    # just table -> prefix project + dataset
    return f"{_DATA_PROJECT}.{_DATASET}.{raw}"

_TABLE_FQN = _resolve_table_fqn(_RAW_TABLE)

# Preferred location column, can be overridden via env.
LOCATION_COL = os.getenv("APEX_LOCATION_COL", "location_number")

print(f"[NBOT] Using table FQN: `{_TABLE_FQN}`")

# -----------------------------------------------------------------------------
# Client & Schema helpers
# -----------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _client() -> bigquery.Client:
    # ADK helper expects a keyword-only 'credentials' arg
    return get_bigquery_client(
        project=get_env_var("BQ_COMPUTE_PROJECT_ID"),
        credentials=None,
    )

@lru_cache(maxsize=1)
def _table_columns() -> List[str]:
    """Lower-cased column names for the target table."""
    tbl = _client().get_table(_TABLE_FQN)
    return [f.name.lower() for f in tbl.schema]

def _location_expr() -> str:
    """
    SELECT expression for Location No.
    Uses LOCATION_COL (default: location_number) if present; otherwise NULL.
    """
    col = LOCATION_COL.lower()
    if col in _table_columns():
        return f"CAST({col} AS STRING) AS location_no"
    print(f"[NBOT] WARNING: column {LOCATION_COL!r} not found in `{_TABLE_FQN}`; using NULL.")
    return "CAST(NULL AS STRING) AS location_no"

def _like_param(customer_name: str) -> str:
    # Case-insensitive contains match
    return f"%{customer_name.strip()}%"

# -----------------------------------------------------------------------------
# NBOT rules (SQL fragments)
# -----------------------------------------------------------------------------

_OT_CASE = """
CASE
  WHEN counter_type IN (
    'Daily Overtime','Weekly Overtime','Daily Double Time',
    'Holiday Worked','Consecutive Day OT','Consecutive Day DT'
  ) OR LOWER(counter_type) LIKE '%overtime%'
  THEN counter_hours ELSE 0
END
"""

# -----------------------------------------------------------------------------
# Workforce Scope
# -----------------------------------------------------------------------------

def compute_workforce_scope(customer_name: str, start_date: str, end_date: str) -> Dict[str, Any]:
    """
    Returns:
      {
        "total_hours": float,
        "nbot_hours": float,
        "nbot_pct": float
      }
    """
    sql = f"""
    SELECT
      SUM(counter_hours) AS total_hours,
      SUM({_OT_CASE})   AS nbot_hours
    FROM `{_TABLE_FQN}`
    WHERE LOWER(customer_name) LIKE LOWER(@customer_like)
      AND counter_date BETWEEN @start_date AND @end_date
    """
    job = _client().query(
        sql,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("customer_like", "STRING", _like_param(customer_name)),
                bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
                bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
            ]
        ),
    )
    row = list(job.result())[0]
    total = float(row["total_hours"] or 0.0)
    nbot = float(row["nbot_hours"] or 0.0)
    nbot_pct = 0.0 if total == 0.0 else (nbot / total) * 100.0
    return {
        "total_hours": round(total, 2),
        "nbot_hours": round(nbot, 2),
        "nbot_pct": round(nbot_pct, 2),
    }

# -----------------------------------------------------------------------------
# NBOT Contribution (Location No., City, State)
# -----------------------------------------------------------------------------

@dataclass
class ContributionRow:
    location_no: str | None
    city: str | None
    state: str | None
    total_hours: float
    nbot_hours: float
    nbot_pct: float
    nbot_contrib_pct: float
    cumulative_contrib_pct: float

def compute_nbot_contribution(customer_name: str, start_date: str, end_date: str) -> List[ContributionRow]:
    """
    Contribution % of NBOT by (Location No., City, State),
    sorted high→low by NBOT Contribution %, with cumulative %.
    """
    location_expr = _location_expr()

    sql = f"""
    WITH base AS (
      SELECT
        {location_expr},
        city,
        state,
        SUM(counter_hours) AS total_hours,
        SUM({_OT_CASE})    AS nbot_hours
      FROM `{_TABLE_FQN}`
      WHERE LOWER(customer_name) LIKE LOWER(@customer_like)
        AND counter_date BETWEEN @start_date AND @end_date
      GROUP BY 1, 2, 3
    ),
    tot AS (
      SELECT SUM(nbot_hours) AS total_nbot FROM base
    )
    SELECT
      b.location_no,
      b.city,
      b.state,
      b.total_hours,
      b.nbot_hours,
      SAFE_MULTIPLY(SAFE_DIVIDE(b.nbot_hours, NULLIF(b.total_hours, 0)), 100) AS nbot_pct,
      SAFE_MULTIPLY(SAFE_DIVIDE(b.nbot_hours, NULLIF(t.total_nbot, 0)), 100) AS nbot_contrib_pct,
      -- Repeat the ratio inside the window to avoid alias issues
      SUM(SAFE_MULTIPLY(SAFE_DIVIDE(b.nbot_hours, NULLIF(t.total_nbot, 0)), 100))
        OVER (
          ORDER BY SAFE_DIVIDE(b.nbot_hours, NULLIF(t.total_nbot, 0)) DESC,
                   b.nbot_hours DESC, b.total_hours DESC, b.city
        ) AS cumulative_contrib_pct
    FROM base b
    CROSS JOIN tot t
    ORDER BY nbot_contrib_pct DESC, b.nbot_hours DESC, b.total_hours DESC, b.city
    """
    job = _client().query(
        sql,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("customer_like", "STRING", _like_param(customer_name)),
                bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
                bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
            ]
        ),
    )

    rows: List[ContributionRow] = []
    for r in job.result():
        rows.append(
            ContributionRow(
                location_no=r["location_no"],
                city=r["city"],
                state=r["state"],
                total_hours=round(float(r["total_hours"] or 0.0), 2),
                nbot_hours=round(float(r["nbot_hours"] or 0.0), 2),
                nbot_pct=round(float(r["nbot_pct"] or 0.0), 2),
                nbot_contrib_pct=round(float(r["nbot_contrib_pct"] or 0.0), 2),
                cumulative_contrib_pct=round(float(r["cumulative_contrib_pct"] or 0.0), 2),
            )
        )
    return rows
