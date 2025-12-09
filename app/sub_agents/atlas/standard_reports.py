# ============================================================
# EPC • NBOT Standard Reports (worked time)
# Env vars:
#   BQ_DATA_PROJECT_ID
#   BQ_DATASET_ID
#   BQ_COMPUTE_PROJECT_ID
# Dataset used: APEX_Performance_DataMart.APEX_Counters
# ============================================================

from jinja2 import Template
from typing import Optional, Dict, Any, List, Tuple
import os
from google.cloud import bigquery
import datetime 



# ============================================================
# clean_site_manager_name
# ============================================================

def clean_site_manager_name(manager_name: str) -> str:
    """
    Clean site manager name by removing everything after the first '('.
    
    Example:
        Input: "Diego Altamirano (M-1 West Coast (AZ,CA,ID,NM,NV,OR,WA)) (209290)"
        Output: "Diego Altamirano"
    
    Args:
        manager_name: Full site manager string from database
    
    Returns:
        Cleaned manager name (first name + last name only)
    """
    if not manager_name:
        return "Unassigned"
    
    manager_name = str(manager_name).strip()
    
    # Extract only the name before the first "("
    if '(' in manager_name:
        return manager_name.split('(')[0].strip()
    
    return manager_name


def clean_site_manager_in_rows(rows: list, field_name: str = 'site_manager') -> None:
    """
    Clean site manager names in a list of dictionaries (in-place).
    
    Args:
        rows: List of dictionaries containing site manager data
        field_name: Name of the field containing site manager info (default: 'site_manager')
    """
    for row in rows:
        if field_name in row:
            row[field_name] = clean_site_manager_name(row[field_name])


# ------------------------------------------------------------
# Helpers (env + customer resolver)
# ------------------------------------------------------------
def _env() -> Tuple[str, str, str, Optional[str]]:
    project = os.getenv("BQ_DATA_PROJECT_ID")
    dataset = os.getenv("BQ_DATASET_ID")
    compute_project = os.getenv("BQ_COMPUTE_PROJECT_ID")
    err = None
    if not all([project, dataset, compute_project]):
        err = ("Missing required environment variables. Please set "
               "BQ_DATA_PROJECT_ID, BQ_DATASET_ID, BQ_COMPUTE_PROJECT_ID.")
    return project, dataset, compute_project, err


def _resolve_customer_code(
    *,
    customer_code: Optional[int],
    customer_name: Optional[str],
    project: str,
    dataset: str,
    compute_project: str
) -> Tuple[Optional[int], Optional[str]]:
    """
    Resolve a customer_code from either the provided code or a fuzzy customer_name.
    Returns (code, error_message). If ambiguous, returns an error with options.
    """
    if customer_code is not None:
        try:
            return int(customer_code), None
        except Exception:
            return None, "Invalid customer_code format. Please provide an integer."

    if not customer_name:
        return None, "Please provide either customer_code or customer_name."

    client = bigquery.Client(project=compute_project)
    
    sql = f"""
        SELECT DISTINCT customer_code, customer_name
        FROM `{project}.{dataset}.APEX_Counters`
        WHERE LOWER(customer_name) LIKE LOWER(@pattern)
        ORDER BY customer_name
        LIMIT 50
    """
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("pattern", "STRING", f"%{customer_name}%")
        ]
    )
    
    rows = list(client.query(sql, job_config=job_config).result())

    if not rows:
        return None, f"No customers matched '{customer_name}'. Please provide the customer_code directly."

    if len(rows) == 1:
        return int(rows[0]["customer_code"]), None

    opts = [f"  • {r['customer_name']} (code: {r['customer_code']})" for r in rows]
    msg = (
        f"Found {len(rows)} customers matching '{customer_name}':\n\n"
        + "\n".join(opts) +
        f"\n\nPlease specify the exact customer_code."
    )
    return None, msg


# ------------------------------------------------------------
# Public entrypoint / Dispatcher
# ------------------------------------------------------------
def generate_standard_report(
    report_id: str,
    customer_code: Optional[int] = None,
    customer_name: Optional[str] = None,
    location_number: Optional[str] = None,
    region: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> str:
    """
    NBOT standard reports on worked time (APEX_Counters).
    Route by report_id and return a fully-rendered Markdown string.

    report_id options:
      - "nbot_site_analysis"
      - "nbot_region_analysis"
      - "nbot_customer_analysis"
      - "nbot_company_by_region"
      - "nbot_company_by_customer"
      - "nbot_company_4week_snapshot"  # Now supports region, customer, or site scope 
    """
    project, dataset, compute_project, env_err = _env()
    if env_err:
        return env_err

    if report_id == "nbot_site_analysis":
        code, err = _resolve_customer_code(
            customer_code=customer_code,
            customer_name=customer_name,
            project=project, dataset=dataset, compute_project=compute_project,
        )
        if err:
            return f"❌ Customer Resolution Error:\n\n{err}"
        missing = []
        if not location_number: missing.append("location_number")
        if not start_date:      missing.append("start_date")
        if not end_date:        missing.append("end_date")
        if missing:
            return "Missing required parameters: " + ", ".join(missing)
        return _generate_nbot_site_analysis(
            code, location_number, start_date, end_date, project, dataset, compute_project
        )

    if report_id == "nbot_region_analysis":
        if not all([region, start_date, end_date]):
            return "Missing required parameters: region, start_date, end_date"
        return _generate_nbot_region_analysis(
            region, start_date, end_date, project, dataset, compute_project
        )

    if report_id == "nbot_customer_analysis":
        code, err = _resolve_customer_code(
            customer_code=customer_code,
            customer_name=customer_name,
            project=project, dataset=dataset, compute_project=compute_project,
        )
        if err:
            return f"❌ Customer Resolution Error:\n\n{err}"
        if not all([code, start_date, end_date]):
            return "Missing required parameters: customer_code|customer_name, start_date, end_date"
        return _generate_nbot_customer_analysis(
            code, start_date, end_date, project, dataset, compute_project
        )

    if report_id == "nbot_company_by_region":
        if not all([start_date, end_date]):
            return "Missing required parameters: start_date, end_date"
        return _generate_nbot_company_by_region(
            start_date, end_date, project, dataset, compute_project
        )

    if report_id == "nbot_company_by_customer":
        if not all([start_date, end_date]):
            return "Missing required parameters: start_date, end_date"
        return _generate_nbot_company_by_customer(
            start_date, end_date, project, dataset, compute_project
        )


    if report_id == "nbot_region_analysis_by_site":
        if not all([region, start_date, end_date]):
            return "Missing required parameters: region, start_date, end_date"
        return _generate_nbot_region_analysis_by_site(
            region, start_date, end_date, project, dataset, compute_project
        )


    if report_id == "nbot_company_4week_snapshot":
        # Support optional scope: company-wide, region, customer, or site
        resolved_customer_code = None
        if customer_code or customer_name:
            resolved_customer_code, err = _resolve_customer_code(
                customer_code=customer_code,
                customer_name=customer_name,
                project=project, dataset=dataset, compute_project=compute_project,
            )
            if err:
                return f"❌ Customer Resolution Error:\n\n{err}"
        
        if not end_date:
            # Default to last Saturday
            from datetime import datetime, timedelta
            today = datetime.now().date()
            days_since_saturday = (today.weekday() + 2) % 7
            last_saturday = today - timedelta(days=days_since_saturday)
            end_date = last_saturday.strftime('%Y-%m-%d')
        
        return _generate_nbot_company_4week_snapshot(
            end_date=end_date,
            project=project,
            dataset=dataset,
            compute_project=compute_project,
            region=region,
            customer_code=resolved_customer_code,
            location_number=location_number
        )

    return (
        f"Report '{report_id}' not implemented.\n\n"
        "Available: nbot_site_analysis, nbot_region_analysis, nbot_region_analysis_by_site, "
        "nbot_customer_analysis, nbot_company_by_region, nbot_company_by_customer, nbot_company_4week_snapshot"
    )


# ------------------------------------------------------------
# 1) NBOT Site Analysis
# ------------------------------------------------------------

def _generate_nbot_site_analysis(
    customer_code: int,
    location_number: str,
    start_date: str,
    end_date: str,
    project: str,
    dataset: str,
    compute_project: str
) -> str:
    """
    Generates the NBOT Site Analysis report with:
      - Pay Type breakdown (Hourly/Salaried/1099/Unknown) with totals
      - Hourly-only counter-type breakdown with totals
      - OT composition (Hourly OT categories), Billable OT (premium-anywhere), and NBOT derived by counter type (totals)
      - Workforce analytics + regional/company benchmarks (utilization + sick/unpaid)
      - Call-out event tracking (sick and unpaid time off events) by site, all sites, and 4-week rolling
    """
    if not all([customer_code, location_number, start_date, end_date]):
        return "Missing required parameters: customer_code, location_number, start_date, end_date"

    from jinja2 import Template
    from google.cloud import bigquery
    from zoneinfo import ZoneInfo
    import datetime

    customer_code_str = str(customer_code)
    report_ts = datetime.datetime.now(ZoneInfo("America/Chicago")).strftime("%Y-%m-%d")

    # --------------------------
    # EMPLOYEES AT SITE (meta) - WITH CALL OUT COUNTS (THIS SITE + ALL SITES + 4-WEEK ROLLING)
    # --------------------------
    emp_sql = f"""
WITH EmployeesAtSite AS (
  SELECT DISTINCT employee_id
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE CAST(customer_code AS STRING) = '{customer_code_str}'
    AND CAST(location_number AS STRING) = '{location_number}'
    AND DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
),
FourWeekCallOuts AS (
  SELECT
    employee_id,
    COUNTIF(LOWER(TRIM(counter_type)) = 'sick' 
            OR LOWER(TRIM(counter_type)) LIKE '%unpaid time off%') AS call_outs_4week
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE_SUB(DATE('{end_date}'), INTERVAL 28 DAY) AND DATE('{end_date}')
  GROUP BY employee_id
),
EmployeeAgg AS (
  SELECT
    employee_id,
    ANY_VALUE(employee_name) AS employee_name,
    ANY_VALUE(employee_status) AS employee_status,
    SAFE.PARSE_DATE('%m/%d/%Y', ANY_VALUE(CAST(employee_date_started AS STRING))) AS ed_start_str,
    SAFE_CAST(ANY_VALUE(employee_date_started) AS DATE) AS ed_start_date,
    ANY_VALUE(customer_name) AS customer_name,
    ANY_VALUE(state) AS state,
    ANY_VALUE(region) AS region,
    ANY_VALUE(city) AS city,
    ANY_VALUE(site_manager) AS site_manager,
    SUM(IF(CAST(location_number AS STRING) = '{location_number}', counter_hours, 0)) AS hours_this_site,
    SUM(counter_hours) AS hours_all_sites,
    COUNTIF(CAST(location_number AS STRING) = '{location_number}' 
            AND (LOWER(TRIM(counter_type)) = 'sick' 
                 OR LOWER(TRIM(counter_type)) LIKE '%unpaid time off%')) AS call_outs_this_site,
    COUNTIF(LOWER(TRIM(counter_type)) = 'sick' 
            OR LOWER(TRIM(counter_type)) LIKE '%unpaid time off%') AS call_outs_all_sites
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
    AND employee_id IN (SELECT employee_id FROM EmployeesAtSite)
  GROUP BY employee_id
),
EmployeeFinal AS (
  SELECT
    ea.employee_id,
    ea.employee_name,
    ea.employee_status,
    COALESCE(ea.ed_start_date, ea.ed_start_str) AS employee_date_started,
    ea.customer_name, ea.state, ea.region, ea.city, ea.site_manager,
    ea.hours_this_site,
    ea.hours_all_sites,
    ea.call_outs_this_site,
    ea.call_outs_all_sites,
    COALESCE(fw.call_outs_4week, 0) AS call_outs_4week,
    DATE_DIFF(CURRENT_DATE(), COALESCE(ea.ed_start_date, ea.ed_start_str), DAY) AS tenure_days
  FROM EmployeeAgg ea
  LEFT JOIN FourWeekCallOuts fw ON ea.employee_id = fw.employee_id
)
SELECT * FROM EmployeeFinal
ORDER BY hours_this_site DESC
"""

    # --------------------------
    # TOTALS (incl unpaid/sick + EVENT COUNTS)
    #   FIX: billable_ot_hours = ANY row with is_billable_overtime='OT' (premium-anywhere)
    #   NBOT stays confined to OT-like counters with NON-OT flag
    # --------------------------
    totals_sql = f"""
WITH Base AS (
  SELECT
    LOWER(TRIM(counter_type)) AS counter_type,
    SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours,
    COALESCE(NULLIF(TRIM(is_billable_overtime), ''), 'UNKNOWN') AS is_billable_ot
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE CAST(customer_code AS STRING) = '{customer_code_str}'
    AND CAST(location_number AS STRING) = '{location_number}'
    AND DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
),
Totals AS (
  SELECT
    SUM(counter_hours) AS total_hours,

    -- NBOT (non-billable overtime) - only OT-like counters
    SUM(CASE
          WHEN (counter_type IN ('daily overtime','daily ot','weekly overtime','weekly ot','holiday worked')
                OR counter_type LIKE 'consecutive day ot%%'
                OR counter_type LIKE 'consecutive day dt%%'
                OR counter_type LIKE '%%double time%%'
                OR counter_type LIKE '%%overtime%%')
               AND is_billable_ot = 'NON-OT'
          THEN counter_hours ELSE 0 END
    ) AS nbot_hours,

    -- Billable OT (premium-anywhere): ANY row marked OT, regardless of counter_type
    SUM(CASE WHEN is_billable_ot = 'OT' THEN counter_hours ELSE 0 END) AS billable_ot_hours,

    -- Unpaid & Sick totals
    SUM(CASE WHEN counter_type LIKE '%%unpaid time off%%' THEN counter_hours ELSE 0 END) AS unpaid_time_off_hours_total,
    SUM(CASE WHEN counter_type = 'sick' THEN counter_hours ELSE 0 END) AS sick_hours_total,
    
    -- Event counts
    COUNTIF(counter_type LIKE '%%unpaid time off%%') AS unpaid_events_total,
    COUNTIF(counter_type = 'sick') AS sick_events_total
  FROM Base
),
Regular AS (
  SELECT 'Regular' AS category,
         SUM(counter_hours) AS hours
  FROM Base
  WHERE NOT (
    counter_type IN ('daily overtime','daily ot','weekly overtime','weekly ot','holiday worked')
    OR counter_type LIKE 'consecutive day ot%%'
    OR counter_type LIKE 'consecutive day dt%%'
    OR counter_type LIKE '%%double time%%'
    OR counter_type LIKE '%%overtime%%'
  )
)
SELECT
  (SELECT total_hours FROM Totals) AS total_hours,
  (SELECT nbot_hours FROM Totals) AS nbot_hours,
  (SELECT billable_ot_hours FROM Totals) AS billable_ot_hours,
  (SELECT unpaid_time_off_hours_total FROM Totals) AS unpaid_time_off_hours_total,
  (SELECT sick_hours_total FROM Totals) AS sick_hours_total,
  (SELECT unpaid_events_total FROM Totals) AS unpaid_events_total,
  (SELECT sick_events_total FROM Totals) AS sick_events_total,

  SAFE_DIVIDE((SELECT nbot_hours FROM Totals),(SELECT total_hours FROM Totals)) * 100 AS nbot_pct,
  SAFE_DIVIDE((SELECT billable_ot_hours FROM Totals),(SELECT total_hours FROM Totals)) * 100 AS billable_ot_pct,
  SAFE_DIVIDE((SELECT nbot_hours FROM Totals) + (SELECT billable_ot_hours FROM Totals),(SELECT total_hours FROM Totals)) * 100 AS total_ot_pct,

  SAFE_DIVIDE((SELECT unpaid_time_off_hours_total FROM Totals),(SELECT total_hours FROM Totals)) * 100 AS unpaid_pct_total,
  SAFE_DIVIDE((SELECT sick_hours_total FROM Totals),(SELECT total_hours FROM Totals)) * 100 AS sick_pct_total,

  (SELECT category FROM Regular) AS regular_label,
  (SELECT hours FROM Regular) AS regular_hours
"""

    # ----------------------------------
    # OT breakdown rows (plus unpaid/sick)
    # (category view keeps OT-like counters grouped; used for display)
    # ----------------------------------
    ot_breakdown_sql = f"""
WITH Base AS (
  SELECT
    LOWER(TRIM(counter_type)) AS counter_type,
    SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours,
    COALESCE(NULLIF(TRIM(is_billable_overtime), ''), 'UNKNOWN') AS is_billable_ot
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE CAST(customer_code AS STRING) = '{customer_code_str}'
    AND CAST(location_number AS STRING) = '{location_number}'
    AND DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
)
-- Overtime categories
SELECT
  CASE
    WHEN counter_type IN ('daily overtime','daily ot') THEN 'Daily Overtime'
    WHEN counter_type IN ('weekly overtime','weekly ot') THEN 'Weekly Overtime'
    WHEN counter_type LIKE '%%double time%%' THEN 'Daily Double Time'
    WHEN counter_type LIKE 'consecutive day ot%%' THEN 'Consecutive Day OT'
    WHEN counter_type LIKE 'consecutive day dt%%' THEN 'Consecutive Day DT'
    ELSE 'Other OT'
  END AS ot_category,
  SUM(CASE WHEN is_billable_ot = 'NON-OT' THEN counter_hours ELSE 0 END) AS nbot_hours,
  SUM(CASE WHEN is_billable_ot = 'OT' THEN counter_hours ELSE 0 END) AS billable_hours,
  SUM(counter_hours) AS total_ot_hours
FROM Base
WHERE (counter_type IN ('daily overtime','daily ot','weekly overtime','weekly ot')
       OR counter_type LIKE 'consecutive day ot%%'
       OR counter_type LIKE 'consecutive day dt%%'
       OR counter_type LIKE '%%double time%%'
       OR counter_type LIKE '%%overtime%%')
GROUP BY ot_category

UNION ALL
-- Unpaid Time Off Request (as its own row)
SELECT
  'Unpaid Time Off Request' AS ot_category,
  0 AS nbot_hours,
  0 AS billable_hours,
  SUM(CASE WHEN counter_type LIKE '%%unpaid time off%%' THEN counter_hours ELSE 0 END) AS total_ot_hours
FROM Base
WHERE counter_type LIKE '%%unpaid time off%%'

UNION ALL
-- Sick (as its own row)
SELECT
  'Sick' AS ot_category,
  0 AS nbot_hours,
  0 AS billable_hours,
  SUM(CASE WHEN counter_type = 'sick' THEN counter_hours ELSE 0 END) AS total_ot_hours
FROM Base
WHERE counter_type = 'sick'
"""

    # --------------------------
    # Pay type totals (Hourly/Salaried/1099/Unknown)
    # --------------------------
    pay_type_totals_sql = f"""
WITH Base AS (
  SELECT
    SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours,
    LOWER(TRIM(counter_type)) AS counter_type,
    LOWER(TRIM(COALESCE(CAST(pay_type AS STRING), ''))) AS pay_type_raw
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE CAST(customer_code AS STRING) = '{customer_code_str}'
    AND CAST(location_number AS STRING) = '{location_number}'
    AND DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
),
Norm AS (
  SELECT
    counter_hours,
    counter_type,
    CASE
      WHEN pay_type_raw IN ('hourly','h','non-exempt','nonexempt') THEN 'Hourly'
      WHEN pay_type_raw IN ('salaried','salary','exempt')          THEN 'Salaried'
      WHEN pay_type_raw IN ('1099','contractor','independent','ic') THEN '1099'
      ELSE 'Unknown'
    END AS pay_type
  FROM Base
),
Agg AS (
  SELECT
    SUM(counter_hours) AS total_counter_hours,
    SUM(CASE WHEN pay_type = 'Hourly'   THEN counter_hours ELSE 0 END) AS hourly_hours,
    SUM(CASE WHEN pay_type = 'Salaried' THEN counter_hours ELSE 0 END) AS salaried_hours,
    SUM(CASE WHEN pay_type = '1099'     THEN counter_hours ELSE 0 END) AS contractor_1099_hours,
    SUM(CASE WHEN pay_type = 'Unknown'  THEN counter_hours ELSE 0 END) AS unknown_hours
  FROM Norm
)
SELECT
  total_counter_hours,
  hourly_hours,
  salaried_hours,
  contractor_1099_hours,
  unknown_hours,
  SAFE_DIVIDE(hourly_hours,   total_counter_hours) * 100 AS hourly_pct,
  SAFE_DIVIDE(salaried_hours, total_counter_hours) * 100 AS salaried_pct,
  SAFE_DIVIDE(contractor_1099_hours, total_counter_hours) * 100 AS contractor_1099_pct,
  SAFE_DIVIDE(unknown_hours,  total_counter_hours) * 100 AS unknown_pct
FROM Agg
"""

    # --------------------------
    # Hourly-only breakdown
    # --------------------------
    hourly_ct_breakdown_sql = f"""
WITH Base AS (
  SELECT
    SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours,
    LOWER(TRIM(counter_type)) AS counter_type,
    LOWER(TRIM(COALESCE(CAST(pay_type AS STRING), ''))) AS pay_type_raw
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE CAST(customer_code AS STRING) = '{customer_code_str}'
    AND CAST(location_number AS STRING) = '{location_number}'
    AND DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
),
Hourly AS (
  SELECT counter_type, counter_hours
  FROM Base
  WHERE pay_type_raw IN ('hourly','h','non-exempt','nonexempt')
),
Agg AS (
  SELECT
    CASE
      WHEN counter_type IN ('daily overtime','daily ot')     THEN 'Daily Overtime'
      WHEN counter_type IN ('weekly overtime','weekly ot')   THEN 'Weekly Overtime'
      WHEN counter_type LIKE '%%double time%%'               THEN 'Daily Double Time'
      WHEN counter_type = 'holiday worked'                   THEN 'Holiday Worked'
      WHEN counter_type LIKE 'consecutive day ot%%'          THEN 'Consecutive Day OT'
      WHEN counter_type LIKE 'consecutive day dt%%'          THEN 'Consecutive Day DT'
      WHEN counter_type LIKE '%%unpaid time off%%'           THEN 'Unpaid Time Off'
      WHEN counter_type = 'sick'                             THEN 'Sick'
      ELSE 'Regular / Other'
    END AS category,
    SUM(counter_hours) AS hours
  FROM Hourly
  GROUP BY category
),
Total AS ( SELECT SUM(hours) AS total_hourly_worked FROM Agg )
SELECT
  category,
  hours,
  SAFE_DIVIDE(hours, (SELECT total_hourly_worked FROM Total)) * 100 AS pct_of_hourly
FROM Agg
ORDER BY hours DESC
"""

    # --------------------------
    # OT composition (Hourly-only; OT-like)
    # --------------------------
    ot_composition_sql = f"""
WITH Base AS (
  SELECT
    SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours,
    LOWER(TRIM(counter_type)) AS counter_type,
    LOWER(TRIM(COALESCE(CAST(pay_type AS STRING), ''))) AS pay_type_raw,
    COALESCE(NULLIF(TRIM(is_billable_overtime), ''), 'UNKNOWN') AS is_billable_ot
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE CAST(customer_code AS STRING) = '{customer_code_str}'
    AND CAST(location_number AS STRING) = '{location_number}'
    AND DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
),
HourlyOT AS (
  SELECT counter_hours, counter_type, is_billable_ot
  FROM Base
  WHERE pay_type_raw IN ('hourly','h','non-exempt','nonexempt')
    AND (counter_type IN ('daily overtime','daily ot','weekly overtime','weekly ot')
         OR counter_type LIKE 'consecutive day ot%%'
         OR counter_type LIKE 'consecutive day dt%%'
         OR counter_type LIKE '%%double time%%'
         OR counter_type LIKE '%%overtime%%')
),
Agg AS (
  SELECT
    CASE
      WHEN counter_type IN ('daily overtime','daily ot') THEN 'Daily Overtime'
      WHEN counter_type IN ('weekly overtime','weekly ot') THEN 'Weekly Overtime'
      WHEN counter_type LIKE '%%double time%%' THEN 'Daily Double Time'
      WHEN counter_type LIKE 'consecutive day ot%%' THEN 'Consecutive Day OT'
      WHEN counter_type LIKE 'consecutive day dt%%' THEN 'Consecutive Day DT'
      ELSE 'Other OT'
    END AS ot_category,
    SUM(counter_hours) AS ot_hours
  FROM HourlyOT
  GROUP BY ot_category
),
Total AS ( SELECT SUM(ot_hours) AS total_ot FROM Agg )
SELECT
  ot_category,
  ot_hours,
  SAFE_DIVIDE(ot_hours, (SELECT total_ot FROM Total)) * 100 AS pct_of_ot
FROM Agg
ORDER BY ot_hours DESC
"""

    # --------------------------
    # Billable Premium (Hourly-only; premium-anywhere)
    # --------------------------
    billable_ot_sql = f"""
WITH Base AS (
  SELECT
    SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours,
    LOWER(TRIM(counter_type)) AS counter_type,
    LOWER(TRIM(COALESCE(CAST(pay_type AS STRING), ''))) AS pay_type_raw,
    COALESCE(NULLIF(TRIM(is_billable_overtime), ''), 'UNKNOWN') AS is_billable_ot
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE CAST(customer_code AS STRING) = '{customer_code_str}'
    AND CAST(location_number AS STRING) = '{location_number}'
    AND DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
),
Billable AS (
  SELECT
    CASE
      WHEN counter_type IN ('daily overtime','daily ot')      THEN 'Daily Overtime'
      WHEN counter_type IN ('weekly overtime','weekly ot')    THEN 'Weekly Overtime'
      WHEN counter_type LIKE '%%double time%%'                THEN 'Daily Double Time'
      WHEN counter_type = 'holiday worked'                    THEN 'Holiday Worked'
      WHEN counter_type LIKE 'consecutive day ot%%'           THEN 'Consecutive Day OT'
      WHEN counter_type LIKE 'consecutive day dt%%'           THEN 'Consecutive Day DT'
      WHEN counter_type LIKE '%%unpaid time off%%'            THEN 'Unpaid Time Off'
      WHEN counter_type = 'sick'                              THEN 'Sick'
      ELSE 'Regular / Other'
    END AS ot_category,
    SUM(counter_hours) AS billable_hours
  FROM Base
  WHERE pay_type_raw IN ('hourly','h','non-exempt','nonexempt')
    AND is_billable_ot = 'OT'
  GROUP BY ot_category
),
Total AS ( SELECT SUM(billable_hours) AS total_billable_ot FROM Billable )
SELECT
  ot_category,
  billable_hours,
  SAFE_DIVIDE(billable_hours, (SELECT total_billable_ot FROM Total)) * 100 AS pct_of_ot
FROM Billable
ORDER BY billable_hours DESC
"""

    # --------------------------
    # Region/Company benchmarks (with event counts) - FIXED
    # --------------------------
    region_bench_sql = f"""
WITH SiteMeta AS (
  SELECT
    ANY_VALUE(state) AS state,
    COALESCE(ANY_VALUE(region), ANY_VALUE(state)) AS region_key
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE CAST(customer_code AS STRING) = '{customer_code_str}'
    AND CAST(location_number AS STRING) = '{location_number}'
    AND DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
),
Pool AS (
  SELECT
    COALESCE(region, state) AS region_key,
    CONCAT(CAST(customer_code AS STRING), '-', CAST(location_number AS STRING)) AS site_key,
    SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours,
    LOWER(TRIM(counter_type)) AS counter_type
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
),
SiteAgg AS (
  SELECT
    region_key,
    site_key,
    AVG(counter_hours) AS avg_utilization,
    SUM(CASE WHEN counter_type = 'sick' THEN counter_hours ELSE 0 END) /
      NULLIF(SUM(counter_hours),0) * 100 AS sick_pct,
    SUM(CASE WHEN counter_type LIKE '%%unpaid time off%%' THEN counter_hours ELSE 0 END) /
      NULLIF(SUM(counter_hours),0) * 100 AS unpaid_pct,
    COUNTIF(counter_type = 'sick') AS sick_events,
    COUNTIF(counter_type LIKE '%%unpaid time off%%') AS unpaid_events
  FROM Pool
  GROUP BY region_key, site_key
),
Agg AS (
  SELECT
    region_key,
    AVG(avg_utilization) AS avg_utilization,
    AVG(sick_pct) AS sick_pct,
    AVG(unpaid_pct) AS unpaid_pct,
    AVG(sick_events) AS avg_sick_events,
    AVG(unpaid_events) AS avg_unpaid_events
  FROM SiteAgg
  GROUP BY region_key
)
SELECT a.*, sm.region_key AS site_region_key
FROM Agg a
JOIN SiteMeta sm ON a.region_key = sm.region_key
"""

    company_bench_sql = f"""
WITH Pool AS (
  SELECT
    CONCAT(CAST(customer_code AS STRING), '-', CAST(location_number AS STRING)) AS site_key,
    SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours,
    LOWER(TRIM(counter_type)) AS counter_type
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
),
SiteAgg AS (
  SELECT
    site_key,
    AVG(counter_hours) AS avg_utilization,
    SUM(CASE WHEN counter_type = 'sick' THEN counter_hours ELSE 0 END) /
      NULLIF(SUM(counter_hours),0) * 100 AS sick_pct,
    SUM(CASE WHEN counter_type LIKE '%%unpaid time off%%' THEN counter_hours ELSE 0 END) /
      NULLIF(SUM(counter_hours),0) * 100 AS unpaid_pct,
    COUNTIF(counter_type = 'sick') AS sick_events,
    COUNTIF(counter_type LIKE '%%unpaid time off%%') AS unpaid_events
  FROM Pool
  GROUP BY site_key
),
Agg AS (
  SELECT
    AVG(avg_utilization) AS avg_utilization_company,
    AVG(sick_pct) AS sick_pct_company,
    AVG(unpaid_pct) AS unpaid_pct_company,
    AVG(sick_events) AS avg_sick_events_company,
    AVG(unpaid_events) AS avg_unpaid_events_company
  FROM SiteAgg
)
SELECT * FROM Agg
"""

    # --------------------------
    # RUN QUERIES
    # --------------------------
    try:
        client = bigquery.Client(project=compute_project)
        emp_rows = client.query(emp_sql).to_dataframe().to_dict(orient="records")
        tot = client.query(totals_sql).to_dataframe().to_dict(orient="records")
        ot_breakdown_rows = client.query(ot_breakdown_sql).to_dataframe().to_dict(orient="records")
        pay_type_totals = client.query(pay_type_totals_sql).to_dataframe().to_dict(orient="records")
        hourly_ct_rows  = client.query(hourly_ct_breakdown_sql).to_dataframe().to_dict(orient="records")
        ot_comp_rows    = client.query(ot_composition_sql).to_dataframe().to_dict(orient="records")
        billable_rows   = client.query(billable_ot_sql).to_dataframe().to_dict(orient="records")
        region_bench    = client.query(region_bench_sql).to_dataframe().to_dict(orient="records")
        company_bench   = client.query(company_bench_sql).to_dataframe().to_dict(orient="records")
    except Exception as e:
        return (
            f"Query failed: {str(e)}\n\nEMP_SQL:\n{emp_sql}\n\nTOTALS_SQL:\n{totals_sql}\n\n"
            f"OT_BREAKDOWN_SQL:\n{ot_breakdown_sql}\n\n"
            f"PAY_TYPE_TOTALS_SQL:\n{pay_type_totals_sql}\n\n"
            f"HOURLY_CT_BREAKDOWN_SQL:\n{hourly_ct_breakdown_sql}\n\n"
            f"OT_COMPOSITION_SQL:\n{ot_composition_sql}\n\n"
            f"BILLABLE_OT_SQL:\n{billable_ot_sql}\n\n"
            f"REGION_BENCH_SQL:\n{region_bench_sql}\n\n"
            f"COMPANY_BENCH_SQL:\n{company_bench_sql}"
        )

    if not tot:
        return f"No data found for customer_code={customer_code}, location_number={location_number}, dates={start_date} to {end_date}"

    # --------------------------
    # UNPACK TOTALS & METRICS
    # --------------------------
    totals = tot[0]
    total_hours = float(totals.get("total_hours") or 0)
    nbot_hours = float(totals.get("nbot_hours") or 0)
    billable_ot_hours = float(totals.get("billable_ot_hours") or 0)
    total_ot_hours = nbot_hours + billable_ot_hours

    unpaid_time_off_hours_total = float(totals.get("unpaid_time_off_hours_total") or 0)
    sick_hours_total = float(totals.get("sick_hours_total") or 0)
    unpaid_events_total = int(totals.get("unpaid_events_total") or 0)
    sick_events_total = int(totals.get("sick_events_total") or 0)
    total_call_outs = sick_events_total + unpaid_events_total
    
    unpaid_pct_total = round(float(totals.get("unpaid_pct_total") or 0), 2)
    sick_pct_total = round(float(totals.get("sick_pct_total") or 0), 2)

    nbot_pct = round(float(totals.get("nbot_pct") or 0), 2)
    billable_ot_pct = round(float(totals.get("billable_ot_pct") or 0), 2)
    total_ot_pct = round(float(totals.get("total_ot_pct") or 0), 2)

    regular_hours = float(totals.get("regular_hours") or 0)
    regular_pct = round((regular_hours / total_hours * 100) if total_hours else 0, 1)
    fte_needed = int((total_hours + 35.9999) // 36) if total_hours else 0

    def usage_label(h_all):
        if h_all is None: return "Unknown"
        if h_all < 25: return "🔴 Critical (Under)"
        if 25 <= h_all <= 31: return "🟡 Sub-Optimal"
        if 32 <= h_all <= 40: return "🟢 Optimal"
        if h_all > 40: return "🔴 Critical (Over)"
        return "Unknown"

    def tenure_label(days):
        if days is None: return "Unknown"
        if days <= 90: return "🔴 Critical Risk"
        if 91 <= days <= 179: return "🟠 High Risk"
        if 180 <= days <= 365: return "🟡 Medium Risk"
        return "🟢 Low Risk"

    for r in emp_rows:
        r["usage_status"] = usage_label(r.get("hours_all_sites"))
        r["tenure_status"] = tenure_label(r.get("tenure_days"))
        r["call_outs_this_site"] = int(r.get("call_outs_this_site") or 0)
        r["call_outs_all_sites"] = int(r.get("call_outs_all_sites") or 0)
        r["call_outs_4week"] = int(r.get("call_outs_4week") or 0)

    for r in ot_breakdown_rows:
        r["nbot_hours"] = float(r.get("nbot_hours") or 0)
        r["billable_hours"] = float(r.get("billable_hours") or 0)
        r["total_ot_hours"] = float(r.get("total_ot_hours") or 0)
        r["nbot_pct_of_twh"] = round((r["nbot_hours"] / total_hours * 100) if total_hours else 0, 2)
        r["billable_pct_of_twh"] = round((r["billable_hours"] / total_hours * 100) if total_hours else 0, 2)
        r["total_ot_pct_of_twh"] = round((r["total_ot_hours"] / total_hours * 100) if total_hours else 0, 2)

    # --------------------------
    # Helpers: totals row builder
    # --------------------------
    def _with_totals(rows, hours_key, pct_keys=None, label_key=None, total_label="Total"):
        out = [dict(r) for r in rows] if rows else []
        total_row = {}
        total_hours_local = round(sum(float(r.get(hours_key, 0) or 0) for r in rows), 2) if rows else 0.0
        if rows:
            for k in rows[0].keys():
                total_row[k] = ""
            lk = label_key or (rows and list(rows[0].keys())[0]) or "category"
            total_row[lk] = total_label
        total_row[hours_key] = total_hours_local
        if pct_keys:
            for pk in pct_keys:
                total_row[pk] = round(sum(float(r.get(pk, 0) or 0) for r in rows), 2)
        out.append(total_row)
        return out

    # --------------------------
    # Derive OT / Billable / NBOT tables with totals
    # --------------------------
    total_ot_from_comp = sum(float(r.get("ot_hours", 0) or 0) for r in ot_comp_rows) if ot_comp_rows else 0.0
    for r in (ot_comp_rows or []):
        r["ot_hours"] = float(r.get("ot_hours") or 0)
        r["pct_of_ot"] = round(float(r.get("pct_of_ot") or 0), 2)
    ot_comp_rows = _with_totals(ot_comp_rows, "ot_hours", ["pct_of_ot"], label_key="ot_category")

    for r in (billable_rows or []):
        r["billable_hours"] = float(r.get("billable_hours") or 0)
        r["pct_of_ot"] = round(float(r.get("pct_of_ot") or 0), 2)
    billable_rows = _with_totals(billable_rows, "billable_hours", ["pct_of_ot"], label_key="ot_category")

    bill_map = {r.get("ot_category"): float(r.get("billable_hours") or 0) for r in (billable_rows[:-1] if billable_rows else [])}
    nbot_rows = []
    for r in (ot_comp_rows[:-1] if ot_comp_rows else []):
        cat = r.get("ot_category")
        ot_h = float(r.get("ot_hours") or 0)
        bill_h = bill_map.get(cat, 0.0)
        nbot_h = max(ot_h - bill_h, 0.0)
        nbot_rows.append({
            "ot_category": cat,
            "nbot_hours": nbot_h,
            "pct_of_ot": round((nbot_h / total_ot_from_comp * 100) if total_ot_from_comp else 0.0, 2),
            "pct_of_twh": round((nbot_h / total_hours * 100) if total_hours else 0.0, 2),
        })
    nbot_rows = _with_totals(nbot_rows, "nbot_hours", ["pct_of_ot","pct_of_twh"], label_key="ot_category")

    # Pay type unpack
    pt = pay_type_totals[0] if pay_type_totals else {}
    total_counter_hours_all     = float(pt.get("total_counter_hours") or 0.0)
    hourly_hours_total          = float(pt.get("hourly_hours") or 0.0)
    salaried_hours_total        = float(pt.get("salaried_hours") or 0.0)
    contractor_1099_hours_total = float(pt.get("contractor_1099_hours") or 0.0)
    unknown_hours_total         = float(pt.get("unknown_hours") or 0.0)

    hourly_pct          = round(float(pt.get("hourly_pct") or 0.0), 2)
    salaried_pct        = round(float(pt.get("salaried_pct") or 0.0), 2)
    contractor_1099_pct = round(float(pt.get("contractor_1099_pct") or 0.0), 2)
    unknown_pct         = round(float(pt.get("unknown_pct") or 0.0), 2)

    for r in (hourly_ct_rows or []):
        r["hours"] = float(r.get("hours") or 0)
        r["pct_of_hourly"] = round(float(r.get("pct_of_hourly") or 0), 2)
    hourly_ct_rows = _with_totals(hourly_ct_rows, "hours", ["pct_of_hourly"], label_key="category")

    # --------------------------
    # Executive summary flags
    # --------------------------
    if nbot_pct < 3:
        nbot_status_color = "🟢"; nbot_status_text = "Excellent — Under target"
    elif 3 <= nbot_pct <= 5:
        nbot_status_color = "🟡"; nbot_status_text = "Acceptable — Monitor closely"
    else:
        nbot_status_color = "🔴"; nbot_status_text = "Critical — Immediate action required"

    ot_breakdown = []
    if nbot_hours > 0:
        for r in ot_breakdown_rows:
            if r.get("nbot_hours", 0) > 0:
                pct_of_nbot = round((float(r["nbot_hours"]) / nbot_hours * 100), 1)
                ot_breakdown.append({"label": r["ot_category"], "pct_of_nbot": pct_of_nbot})

    avg_util_this_site = round((total_hours / len(emp_rows)) if emp_rows else 0, 1)
    total_hours_all_sites = sum(float(e.get('hours_all_sites', 0)) for e in emp_rows)
    avg_util_all_sites = round((total_hours_all_sites / len(emp_rows)) if emp_rows else 0, 1)

    underutilized = sum(1 for e in emp_rows if (e.get('hours_all_sites') or 0) < 25)
    underutilized_pct = round((underutilized / len(emp_rows) * 100) if emp_rows else 0, 1)

    overutilized_this_site = sum(1 for e in emp_rows if (e.get('hours_this_site') or 0) > 40)
    overutilized_this_site_pct = round((overutilized_this_site / len(emp_rows) * 100) if emp_rows else 0, 1)

    overutilized_all_sites = sum(1 for e in emp_rows if (e.get('hours_all_sites') or 0) > 40)
    overutilized_all_sites_pct = round((overutilized_all_sites / len(emp_rows) * 100) if emp_rows else 0, 1)

    critical_risks = sum(1 for e in emp_rows if (e.get("tenure_days") or 0) <= 90)
    high_risk_tenure = sum(1 for e in emp_rows if 91 <= (e.get('tenure_days') or 0) <= 179)
    high_risk_tenure_pct = round((high_risk_tenure / len(emp_rows) * 100) if emp_rows else 0, 1)

    # Call-out rate calculations
    employees_with_callouts = sum(1 for e in emp_rows if e.get("call_outs_all_sites", 0) > 0)
    callout_rate = round((employees_with_callouts / len(emp_rows) * 100) if emp_rows else 0, 1)

    if nbot_pct > 5 or (len(emp_rows) > 0 and critical_risks > len(emp_rows) * 0.4):
        site_health_status = "🔴 Needs Attention"
    elif nbot_pct > 3 or (len(emp_rows) > 0 and critical_risks > len(emp_rows) * 0.2):
        site_health_status = "🟡 Monitor"
    else:
        site_health_status = "🟢 Healthy"

    risk_flags = []
    if nbot_pct > 5:
        risk_flags.append(f"🔴 High NBOT ({nbot_pct:.1f}%) — Exceeds 5% threshold")
    if underutilized > 0:
        risk_flags.append(f"🟡 Underutilization — {underutilized} employees ({underutilized_pct}%) below optimal hours (< 25 hrs/week)")
    if overutilized_this_site > 0:
        risk_flags.append(f"🔴 Overutilization (This Site) — {overutilized_this_site} employees ({overutilized_this_site_pct}%) working > 40 hrs/week at this location")
    if overutilized_all_sites > 0:
        risk_flags.append(f"🔴 Burnout Risk — {overutilized_all_sites} employees ({overutilized_all_sites_pct}%) working > 40 hrs/week across all sites")
    if critical_risks > 0:
        critical_risks_pct = round((critical_risks / len(emp_rows) * 100) if emp_rows else 0, 1)
        risk_flags.append(f"🔴 Critical Tenure Risk — {critical_risks} employees ({critical_risks_pct}%) under 90 days tenure")
    if high_risk_tenure > 0:
        risk_flags.append(f"🟠 High Risk Tenure — {high_risk_tenure} employees ({high_risk_tenure_pct}%) between 91-179 days tenure")
    if fte_needed > len(emp_rows) * 1.1:
        risk_flags.append(f"⚠️ Staffing Gap — Need {fte_needed} FTE, have {len(emp_rows)} employees")
    if sick_events_total >= 3:
        risk_flags.append(f"🟠 High Sick Call-Out Rate — {sick_events_total} events affecting {sick_pct_total:.2f}% of hours")
    if callout_rate > 50:
        risk_flags.append(f"🟡 Elevated Call-Out Rate — {callout_rate}% of workforce ({employees_with_callouts} employees) had call-outs")
    if unpaid_events_total >= 5:
        risk_flags.append(f"🟡 High Unpaid Time Off — {unpaid_events_total} events affecting {unpaid_pct_total:.2f}% of hours")

    recommendations = []
    if nbot_pct > 5 and len(ot_breakdown_rows) > 0:
        top_nbot_category = max(ot_breakdown_rows, key=lambda x: float(x.get("nbot_hours", 0)))
        if top_nbot_category.get("nbot_hours", 0) > 0:
            recommendations.append(
                f"**Reduce {top_nbot_category['ot_category']}** (NBOT) — Accounts for "
                f"{(top_nbot_category.get('nbot_hours', 0)/total_hours*100 if total_hours else 0):.2f}% of total hours"
            )
    if critical_risks > 5:
        recommendations.append(
            f"**Retention Focus** — {critical_risks} employees < 90 days tenure. Add onboarding support & mentorship."
        )
    if underutilized > 0 and overutilized_this_site > 0:
        recommendations.append(
            f"**Balance Workload** — {overutilized_this_site} overutilized vs {underutilized} underutilized. Rebalance shifts."
        )
    elif len(emp_rows) > 0 and underutilized > len(emp_rows) * 0.2:
        recommendations.append("**Optimize Scheduling** — High underutilization; review shift allocation and cross-training.")
    if overutilized_all_sites_pct > 30:
        recommendations.append("**Address Burnout** — Many employees >40 hrs across sites; cap multi-site workloads.")
    if fte_needed > len(emp_rows):
        gap = fte_needed - len(emp_rows)
        recommendations.append(f"**Increase Headcount** — Add {gap} FTE to meet demand without excessive OT.")
    if len(emp_rows) > 0 and fte_needed < len(emp_rows) * 0.9:
        recommendations.append("**Review Staffing Levels** — Headcount likely exceeds need; consider reallocation.")
    if sick_events_total >= 3 or callout_rate > 50:
        recommendations.append(f"**Address Absenteeism** — {total_call_outs} total call-outs; review attendance policies and employee wellness programs.")
    if not recommendations:
        recommendations.append("✅ Site is operating efficiently — Continue current practices")

    header_customer = emp_rows[0]["customer_name"] if emp_rows else ""
    header_state = emp_rows[0]["state"] if emp_rows else ""
    header_region = emp_rows[0].get("region") if emp_rows and emp_rows[0].get("region") else header_state
    header_city = emp_rows[0].get("city", "") if emp_rows else ""
    header_manager = emp_rows[0]["site_manager"] if emp_rows else ""

    # --- Region/Company benchmark unpack
    region_row = region_bench[0] if region_bench else {}
    company_row = company_bench[0] if company_bench else {}
    site_avg_util = avg_util_this_site
    reg_avg_util = float(region_row.get("avg_utilization") or 0.0)
    co_avg_util  = float(company_row.get("avg_utilization_company") or 0.0)
    
    sick_pct_reg   = round(float(region_row.get("sick_pct") or 0.0), 2)
    unpaid_pct_reg = round(float(region_row.get("unpaid_pct") or 0.0), 2)
    sick_pct_co    = round(float(company_row.get("sick_pct_company") or 0.0), 2)
    unpaid_pct_co  = round(float(company_row.get("unpaid_pct_company") or 0.0), 2)
    
    avg_sick_events_reg = round(float(region_row.get("avg_sick_events") or 0.0), 1)
    avg_unpaid_events_reg = round(float(region_row.get("avg_unpaid_events") or 0.0), 1)
    avg_sick_events_co = round(float(company_row.get("avg_sick_events_company") or 0.0), 1)
    avg_unpaid_events_co = round(float(company_row.get("avg_unpaid_events_company") or 0.0), 1)
    
    delta_util_vs_reg = round(site_avg_util - reg_avg_util, 2)
    delta_util_vs_co  = round(site_avg_util - co_avg_util, 2)

    context = {
        "customer_name": header_customer,
        "location_number": location_number,
        "state": header_state,
        "region": header_region or "",
        "site_manager": header_manager,
        "start_date": start_date,
        "end_date": end_date,
        "total_hours": f"{total_hours:,.2f}",
        "employee_count": len(emp_rows),
        "nbot_hours": f"{nbot_hours:,.2f}",
        "billable_ot_hours": f"{billable_ot_hours:,.2f}",
        "total_ot_hours": f"{total_ot_hours:,.2f}",
        "nbot_pct": nbot_pct,
        "billable_ot_pct": billable_ot_pct,
        "total_ot_pct": total_ot_pct,
        "fte_needed": fte_needed,
        "regular_hours": f"{regular_hours:,.2f}",
        "regular_pct": f"{regular_pct:.1f}",
        "ot_breakdown_rows": ot_breakdown_rows,
        "employees": emp_rows,
        "site_health_status": site_health_status,
        "nbot_status_color": nbot_status_color,
        "nbot_status_text": nbot_status_text,
        "ot_breakdown": ot_breakdown,
        "risk_flags": risk_flags,
        "recommendations": recommendations,
        "avg_util_this_site": avg_util_this_site,
        "avg_util_all_sites": avg_util_all_sites,
        "unpaid_time_off_hours_total": f"{unpaid_time_off_hours_total:,.2f}",
        "unpaid_pct_total": unpaid_pct_total,
        "sick_hours_total": f"{sick_hours_total:,.2f}",
        "sick_pct_total": sick_pct_total,
        "unpaid_events_total": unpaid_events_total,
        "sick_events_total": sick_events_total,
        "total_call_outs": total_call_outs,
        "total_counter_hours_all": f"{total_counter_hours_all:,.2f}",
        "hourly_hours_total": f"{hourly_hours_total:,.2f}",
        "salaried_hours_total": f"{salaried_hours_total:,.2f}",
        "unknown_hours_total": f"{unknown_hours_total:,.2f}",
        "hourly_pct": hourly_pct,
        "salaried_pct": salaried_pct,
        "unknown_pct": unknown_pct,
        "hourly_ct_rows": hourly_ct_rows,
        "ot_comp_rows": ot_comp_rows,
        "billable_rows": billable_rows,
        "nbot_rows": nbot_rows,
        "reg_avg_util": reg_avg_util,
        "co_avg_util": co_avg_util,
        "delta_util_vs_reg": delta_util_vs_reg,
        "delta_util_vs_co": delta_util_vs_co,
        "sick_pct_reg": sick_pct_reg,
        "unpaid_pct_reg": unpaid_pct_reg,
        "sick_pct_co": sick_pct_co,
        "unpaid_pct_co": unpaid_pct_co,
        "avg_sick_events_reg": avg_sick_events_reg,
        "avg_unpaid_events_reg": avg_unpaid_events_reg,
        "avg_sick_events_co": avg_sick_events_co,
        "avg_unpaid_events_co": avg_unpaid_events_co,
        "city": header_city,
        "report_ts": report_ts,
        "contractor_1099_hours_total": f"{contractor_1099_hours_total:,.2f}",
        "contractor_1099_pct": contractor_1099_pct,
    }

    template = Template("""# 🌐 Excellence Performance Center 🌐
## NBOT Site Analysis | {{ report_ts }}
**{{ customer_name }} – Location {{ location_number }}** | **City:** {{ city }} | **State:** {{ state }} | **Region:** {{ region }} | **Site Manager:** {{ site_manager }} | **Week:** {{ start_date }} – {{ end_date }}

---

## 📋 EXECUTIVE SUMMARY

**Site Health:** {{ site_health_status }}

### Key Findings

- **NBOT Performance:** {{ "%.2f"|format(nbot_pct) }}% ({{ nbot_status_color }}) — {{ nbot_status_text }}
- **Billable OT (Includes OT and Regular Hours Billed at OT Rate):** {{ "%.2f"|format(billable_ot_pct) }}% | **Total OT:** {{ "%.2f"|format(total_ot_pct) }}%
- **Unpaid Time Off:** {{ "%.2f"|format(unpaid_pct_total) }}% ({{ unpaid_time_off_hours_total }} hours) - **{{ unpaid_events_total }} events**
- **Sick:** {{ "%.2f"|format(sick_pct_total) }}% ({{ sick_hours_total }} hours) - **{{ sick_events_total }} events**
- **Workforce Utilization:** {{ employee_count }} employees worked {{ total_hours }} hours
- **Average Utilization (This Site):** {{ "%.1f"|format(avg_util_this_site) }} hours/week
- **Average Utilization (All Sites):** {{ "%.1f"|format(avg_util_all_sites) }} hours/week
- **Coverage Status (This Site):** {{ fte_needed }} FTE needed vs {{ employee_count }} employees deployed

**NBOT Thresholds:** 🟢 GREEN < 3% · 🟡 YELLOW 3–5% · 🔴 RED > 5%


{% if risk_flags and risk_flags|length > 0 -%}
### ⚠️ Risk Indicators
{% for flag in risk_flags -%}
- {{ flag }}
{% endfor -%}
{% endif %}

{% if recommendations and recommendations|length > 0 -%}
### ▶️Recommendations
{% for rec in recommendations -%}
- {{ rec }}
{% endfor -%}
{% endif %}

---

## 📊 Key Metrics
| Metric | Value |
|:----------------------|----------:|
| Total Hours Counters | {{ total_hours }} |
| Total Hours | Hourly Employees    | {{ hourly_hours_total }} |
| Total OT Hours | {{ total_ot_hours }} |
| Total OT % | {{ "%.2f"|format(total_ot_pct) }}% |
| Billable OT Hours (OT or Regular Hours Billed at OT Rate) | {{ billable_ot_hours }} |
| Billable OT % (OT or Regular Hours Billed at OT Rate) | {{ "%.2f"|format(billable_ot_pct) }}% |
| NBOT Hours | {{ nbot_hours }} |
| NBOT % | {{ "%.2f"|format(nbot_pct) }}% |
| Employees | {{ employee_count }} |
| FTE Needed (36 Hrs) | {{ fte_needed }} |
| **Sick Events** | **{{ sick_events_total }}** |
| **Unpaid Time Off Events** | **{{ unpaid_events_total }}** |

---

## 🧮 Total Hours | Pay Type Breakdown
**Total Counter Hours (All counters):** {{ total_counter_hours_all }}

| Pay Type  | Hours | % of Total |
|:----------|------:|-----------:|
| Hourly    | {{ hourly_hours_total }} | {{ "%.2f"|format(hourly_pct) }}% |
| Salaried  | {{ salaried_hours_total }} | {{ "%.2f"|format(salaried_pct) }}% |
| 1099      | {{ contractor_1099_hours_total }} | {{ "%.2f"|format(contractor_1099_pct) }}% |
| **Total** | **{{ total_counter_hours_all }}** | **{{ "%.2f"|format(hourly_pct + salaried_pct + contractor_1099_pct) }}%** |

> **Note:** Only **Hourly** hours are used for OT/NBOT calculation and compliance exposure.

---

## 🧩 Hourly Worked Hours | by Counter Type
| Category | Hours | % of Hourly |
|:---------|------:|------------:|
{% for r in hourly_ct_rows -%}
| {{ r.category }} | {{ "%.2f"|format(r.hours or 0) }} | {{ "%.2f"|format(r.pct_of_hourly or 0) }}% |
{% endfor -%}

---

## 🔧 OT Breakdown | by Counter Type (Hourly Only)
| OT Counter Type | OT Hours | % of OT |
|:----------------|---------:|--------:|
{% for r in ot_comp_rows -%}
| {{ r.ot_category }} | {{ "%.2f"|format(r.ot_hours or 0) }} | {{ "%.2f"|format(r.pct_of_ot or 0) }}% |
{% endfor -%}

---

## 💸 Billable OT (OT and Regular Hours Charged at OT Rate)
| Counter Type | Billable Premium Hours | % of Premium |
|:-------------|-----------------------:|-------------:|
{% for r in billable_rows -%}
| {{ r.ot_category }} | {{ "%.2f"|format(r.billable_hours or 0) }} | {{ "%.2f"|format(r.pct_of_ot or 0) }}% |
{% endfor -%}

---

##  NBOT (Non-Billable Overtime) | by Counter Type
| OT Counter Type | NBOT Hours | % of OT | % of TWH |
|:----------------|-----------:|--------:|---------:|
{% for r in nbot_rows -%}
| {{ r.ot_category }} | {{ "%.2f"|format(r.nbot_hours or 0) }} | {{ "%.2f"|format(r.pct_of_ot or 0) }}% | {{ "%.2f"|format(r.pct_of_twh or 0) }}% |
{% endfor -%}

---

## ⚙️ Workforce Analytics | Site vs Benchmarks

### Sick & Unpaid Time Off Benchmark | Total Site Call Outs: **{{ total_call_outs }}**
| Metric | Site | Region | Company | Δ vs Region | Δ vs Company |
|:--|--:|--:|--:|--:|--:|
| Sick % | {{ "%.2f"|format(sick_pct_total) }}% | {{ "%.2f"|format(sick_pct_reg) }}% | {{ "%.2f"|format(sick_pct_co) }}% | {{ "%.2f"|format(sick_pct_total - sick_pct_reg) }} pp | {{ "%.2f"|format(sick_pct_total - sick_pct_co) }} pp |
| Sick Events | {{ sick_events_total }} | {{ "%.1f"|format(avg_sick_events_reg) }} avg | {{ "%.1f"|format(avg_sick_events_co) }} avg | {{ "%.1f"|format(sick_events_total - avg_sick_events_reg) }} | {{ "%.1f"|format(sick_events_total - avg_sick_events_co) }} |
| Unpaid % | {{ "%.2f"|format(unpaid_pct_total) }}% | {{ "%.2f"|format(unpaid_pct_reg) }}% | {{ "%.2f"|format(unpaid_pct_co) }}% | {{ "%.2f"|format(unpaid_pct_total - unpaid_pct_reg) }} pp | {{ "%.2f"|format(unpaid_pct_total - unpaid_pct_co) }} pp |
| Unpaid Events | {{ unpaid_events_total }} | {{ "%.1f"|format(avg_unpaid_events_reg) }} avg | {{ "%.1f"|format(avg_unpaid_events_co) }} avg | {{ "%.1f"|format(unpaid_events_total - avg_unpaid_events_reg) }} | {{ "%.1f"|format(unpaid_events_total - avg_unpaid_events_co) }} |

---

## 📅 HOURS BREAKDOWN BY CATEGORY

| Category | NBOT Hours | Billable OT | Total Hours | % of TWH | Visual Impact |
|:---------|----------:|------------:|------------:|---------:|:--------------|
| Regular (NON-OT) | — | — | — | {{ regular_pct }}% | ████████████████████ |
{% for row in ot_breakdown_rows -%}
| {{ row.ot_category }} | {{ "%.2f"|format(row.nbot_hours or 0) }} | {{ "%.2f"|format(row.billable_hours or 0) }} | {{ "%.2f"|format(row.total_ot_hours or 0) }} | {{ "%.2f"|format(row.total_ot_pct_of_twh or 0) }}% | {% if row.total_ot_pct_of_twh > 5 %}██████░░░░░░░░░░░░░░{% elif row.total_ot_pct_of_twh > 2 %}███░░░░░░░░░░░░░░░░░{% else %}█░░░░░░░░░░░░░░░░░░░{% endif %} |
{% endfor %}

{% if ot_breakdown and ot_breakdown|length > 0 -%}
**▶️ Key Insight:** {{ ot_breakdown[0].label }} represents {{ "%.1f"|format(ot_breakdown[0].pct_of_nbot) }}% of NBOT → Primary reduction target
{% endif %}

---

## 👮 Employee Utilization Analysis
| Employee ID | Name | Tenure Days | Tenure Status | Employee Status | Call Outs (This Site) | Call Outs (All Sites) | Call Outs (Last 4 Weeks) | Hours (This Site) | Hours (All Sites) | Usage Status |
|:-----------:|:-----|:------------:|:--------------|:---------------:|:---------------------:|:---------------------:|:------------------------:|------------------:|------------------:|:-------------|
{% for e in employees -%}
| {{ e.employee_id }} | {{ e.employee_name }} | {{ e.tenure_days or '' }} | {{ e.tenure_status }} | {{ e.employee_status }} | {{ e.call_outs_this_site }} | {{ e.call_outs_all_sites }} | {{ e.call_outs_4week }} | {{ "%.2f"|format(e.hours_this_site or 0) }} | {{ "%.2f"|format(e.hours_all_sites or 0) }} | {{ e.usage_status }} |
{% endfor %}
""")
    return template.render(**context)


# ------------------------------------------------------------
# 2) NBOT Region Analysis (Pareto by Customer)
# ------------------------------------------------------------


# ------------------------------------------------------------
# 2) NBOT Region Analysis (Pareto by Customer)
# ------------------------------------------------------------


def _generate_nbot_region_analysis(
    region: str,
    start_date: str,
    end_date: str,
    project: str,
    dataset: str,
    compute_project: str
) -> str:
    if not all([region, start_date, end_date]):
        return "Missing required parameters: region, start_date, end_date"

    from jinja2 import Template
    from google.cloud import bigquery
    import datetime

    # Date-only report stamp
    report_ts = datetime.datetime.now().strftime("%Y-%m-%d")

    # ---------------------------
    # Customers Pareto (region) with event counts
    # - Total OT Hours: Sum of ALL OT counter type hours (regardless of billing)
    # - Billable OT: ANY counter with is_billable_overtime = 'OT' (includes regular)
    # - NBOT: Total OT Hours - Billable OT Hours
    # ---------------------------
    customers_sql = f"""
WITH Base AS (
  SELECT
    customer_code,
    COALESCE(NULLIF(TRIM(customer_name), ''), 'Unassigned') AS customer_name,
    LOWER(TRIM(counter_type)) AS counter_type,
    SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours,
    COALESCE(NULLIF(TRIM(is_billable_overtime), ''), 'UNKNOWN') AS is_billable_ot
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
    AND TRIM(region) = '{region}'
),
Agg AS (
  SELECT
    customer_code, customer_name,
    SUM(counter_hours) AS total_hours,
    
    -- Total OT Hours: Sum of ALL OT counter type hours (regardless of billing)
    SUM(
      CASE 
        WHEN (counter_type IN ('daily overtime','daily ot','weekly overtime','weekly ot','holiday worked')
              OR counter_type LIKE 'consecutive day ot%%'
              OR counter_type LIKE 'consecutive day dt%%'
              OR counter_type LIKE '%%double time%%'
              OR counter_type LIKE '%%overtime%%')
        THEN counter_hours ELSE 0 END
    ) AS total_ot_hours,
    
    -- Billable OT (premium anywhere: OT AND regular)
    SUM(CASE WHEN is_billable_ot = 'OT' THEN counter_hours ELSE 0 END) AS billable_ot_hours,
    
    -- Regular hours billed at OT rate
    SUM(
      CASE 
        WHEN counter_type NOT IN ('daily overtime','daily ot','weekly overtime','weekly ot','holiday worked')
             AND counter_type NOT LIKE 'consecutive day ot%%'
             AND counter_type NOT LIKE 'consecutive day dt%%'
             AND counter_type NOT LIKE '%%double time%%'
             AND counter_type NOT LIKE '%%overtime%%'
             AND is_billable_ot = 'OT'
        THEN counter_hours ELSE 0 END
    ) AS regular_billed_at_ot_hours,
    
    -- Event counts
    COUNTIF(counter_type = 'sick') AS sick_events,
    COUNTIF(counter_type LIKE '%%unpaid time off%%') AS unpaid_events,
    
    -- Event hours
    SUM(CASE WHEN counter_type = 'sick' THEN counter_hours ELSE 0 END) AS sick_hours,
    SUM(CASE WHEN counter_type LIKE '%%unpaid time off%%' THEN counter_hours ELSE 0 END) AS unpaid_hours
  FROM Base
  GROUP BY customer_code, customer_name
),
WithPct AS (
  SELECT
    customer_code, customer_name, total_hours, total_ot_hours, billable_ot_hours, regular_billed_at_ot_hours,
    sick_events, unpaid_events, sick_hours, unpaid_hours,
    -- NBOT = Total OT Hours - Billable OT Hours
    (total_ot_hours - billable_ot_hours) AS nbot_hours,
    SAFE_DIVIDE(total_ot_hours, total_hours) * 100 AS total_ot_pct,
    SAFE_DIVIDE((total_ot_hours - billable_ot_hours), total_hours) * 100 AS nbot_pct,
    SAFE_DIVIDE(billable_ot_hours, total_hours) * 100 AS billable_ot_pct,
    SAFE_DIVIDE(sick_hours, total_hours) * 100 AS sick_pct,
    SAFE_DIVIDE(unpaid_hours, total_hours) * 100 AS unpaid_pct
  FROM Agg
),
Pareto AS (
  SELECT
    *,
    RANK() OVER (ORDER BY nbot_hours DESC) AS nbot_rank,
    SUM(nbot_hours) OVER () AS nbot_total_all,
    SUM(nbot_hours) OVER (ORDER BY nbot_hours DESC
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS nbot_cum,
    SAFE_DIVIDE(
      SUM(nbot_hours) OVER (ORDER BY nbot_hours DESC
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW),
      SUM(nbot_hours) OVER ()
    ) * 100 AS nbot_cum_pct
  FROM WithPct
)
SELECT
  customer_code, customer_name, total_hours, total_ot_hours, nbot_hours, billable_ot_hours, regular_billed_at_ot_hours,
  total_ot_pct, nbot_pct, billable_ot_pct,
  sick_events, unpaid_events, sick_hours, unpaid_hours, sick_pct, unpaid_pct,
  nbot_rank, nbot_cum_pct,
  CASE WHEN nbot_cum_pct <= 80 THEN 'Yes' ELSE 'No' END AS pareto_80_flag
FROM Pareto
ORDER BY nbot_hours DESC
"""

    # ---------------------------
    # Region Totals / % (with corrected NBOT calculation)
    # ---------------------------
    region_totals_sql = f"""
WITH Base AS (
  SELECT
    LOWER(TRIM(counter_type)) AS counter_type,
    SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours,
    COALESCE(NULLIF(TRIM(is_billable_overtime), ''), 'UNKNOWN') AS is_billable_ot
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
    AND TRIM(region) = '{region}'
)
SELECT
  SUM(counter_hours) AS total_hours,

  -- Total OT Hours: Sum of ALL OT counter type hours (regardless of billing)
  SUM(
    CASE 
      WHEN (counter_type IN ('daily overtime','daily ot','weekly overtime','weekly ot','holiday worked')
            OR counter_type LIKE 'consecutive day ot%%'
            OR counter_type LIKE 'consecutive day dt%%'
            OR counter_type LIKE '%%double time%%'
            OR counter_type LIKE '%%overtime%%')
      THEN counter_hours ELSE 0 END
  ) AS total_ot_hours,

  -- Billable OT (premium anywhere: OT AND regular)
  SUM(CASE WHEN is_billable_ot = 'OT' THEN counter_hours ELSE 0 END) AS billable_ot_hours,

  -- Regular hours billed at OT rate
  SUM(
    CASE 
      WHEN counter_type NOT IN ('daily overtime','daily ot','weekly overtime','weekly ot','holiday worked')
           AND counter_type NOT LIKE 'consecutive day ot%%'
           AND counter_type NOT LIKE 'consecutive day dt%%'
           AND counter_type NOT LIKE '%%double time%%'
           AND counter_type NOT LIKE '%%overtime%%'
           AND is_billable_ot = 'OT'
      THEN counter_hours ELSE 0 END
  ) AS regular_billed_at_ot_hours,

  -- Unpaid Time Off + Sick totals
  SUM(CASE WHEN counter_type LIKE '%%unpaid time off%%' THEN counter_hours ELSE 0 END) AS unpaid_time_off_hours_total,
  SUM(CASE WHEN counter_type = 'sick' THEN counter_hours ELSE 0 END) AS sick_hours_total,
  
  -- Event counts
  COUNTIF(counter_type LIKE '%%unpaid time off%%') AS unpaid_events_total,
  COUNTIF(counter_type = 'sick') AS sick_events_total,

  -- Percentages (of total worked hours)
  SAFE_DIVIDE(
    SUM(
      CASE 
        WHEN (counter_type IN ('daily overtime','daily ot','weekly overtime','weekly ot','holiday worked')
              OR counter_type LIKE 'consecutive day ot%%'
              OR counter_type LIKE 'consecutive day dt%%'
              OR counter_type LIKE '%%double time%%'
              OR counter_type LIKE '%%overtime%%')
      THEN counter_hours ELSE 0 END),
    SUM(counter_hours)
  ) * 100 AS total_ot_pct,

  -- NBOT % = (Total OT - Billable OT) / Total Hours
  SAFE_DIVIDE(
    SUM(
      CASE 
        WHEN (counter_type IN ('daily overtime','daily ot','weekly overtime','weekly ot','holiday worked')
              OR counter_type LIKE 'consecutive day ot%%'
              OR counter_type LIKE 'consecutive day dt%%'
              OR counter_type LIKE '%%double time%%'
              OR counter_type LIKE '%%overtime%%')
      THEN counter_hours ELSE 0 END) - SUM(CASE WHEN is_billable_ot = 'OT' THEN counter_hours ELSE 0 END),
    SUM(counter_hours)
  ) * 100 AS nbot_pct,

  SAFE_DIVIDE(
    SUM(CASE WHEN is_billable_ot = 'OT' THEN counter_hours ELSE 0 END),
    SUM(counter_hours)
  ) * 100 AS billable_ot_pct,

  SAFE_DIVIDE(
    SUM(CASE WHEN counter_type LIKE '%%unpaid time off%%' THEN counter_hours ELSE 0 END),
    SUM(counter_hours)
  ) * 100 AS unpaid_pct_total,

  SAFE_DIVIDE(
    SUM(CASE WHEN counter_type = 'sick' THEN counter_hours ELSE 0 END),
    SUM(counter_hours)
  ) * 100 AS sick_pct_total
FROM Base
"""

    # ---------------------------
    # OT breakdown (kept OT categories)
    # ---------------------------
    ot_breakdown_sql = f"""
WITH Base AS (
  SELECT
    LOWER(TRIM(counter_type)) AS counter_type,
    SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours,
    COALESCE(NULLIF(TRIM(is_billable_overtime), ''), 'UNKNOWN') AS is_billable_ot
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
    AND TRIM(region) = '{region}'
)

-- Standard OT categories
SELECT
  CASE
    WHEN counter_type IN ('daily overtime','daily ot') THEN 'Daily Overtime'
    WHEN counter_type IN ('weekly overtime','weekly ot') THEN 'Weekly Overtime'
    WHEN counter_type LIKE '%%double time%%' THEN 'Daily Double Time'
    WHEN counter_type LIKE 'consecutive day ot%%' THEN 'Consecutive Day OT'
    WHEN counter_type LIKE 'consecutive day dt%%' THEN 'Consecutive Day DT'
    ELSE 'Other OT'
  END AS ot_category,
  SUM(CASE WHEN is_billable_ot = 'OT' THEN counter_hours ELSE 0 END) AS billable_hours,
  SUM(counter_hours) AS total_ot_hours,
  SUM(counter_hours) - SUM(CASE WHEN is_billable_ot = 'OT' THEN counter_hours ELSE 0 END) AS nbot_hours
FROM Base
WHERE (counter_type IN ('daily overtime','daily ot','weekly overtime','weekly ot')
       OR counter_type LIKE 'consecutive day ot%%'
       OR counter_type LIKE 'consecutive day dt%%'
       OR counter_type LIKE '%%double time%%'
       OR counter_type LIKE '%%overtime%%')
GROUP BY ot_category

UNION ALL
-- Unpaid Time Off Request (as its own row)
SELECT
  'Unpaid Time Off Request' AS ot_category,
  0 AS billable_hours,
  SUM(CASE WHEN counter_type LIKE '%%unpaid time off%%' THEN counter_hours ELSE 0 END) AS total_ot_hours,
  0 AS nbot_hours
FROM Base
WHERE counter_type LIKE '%%unpaid time off%%'

UNION ALL
-- Sick (as its own row)
SELECT
  'Sick' AS ot_category,
  0 AS billable_hours,
  SUM(CASE WHEN counter_type = 'sick' THEN counter_hours ELSE 0 END) AS total_ot_hours,
  0 AS nbot_hours
FROM Base
WHERE counter_type = 'sick'
ORDER BY total_ot_hours DESC
"""

    # ---------------------------
    # Pay type totals
    # ---------------------------
    pay_type_totals_sql = f"""
WITH Base AS (
  SELECT
    SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours,
    LOWER(TRIM(counter_type)) AS counter_type,
    LOWER(TRIM(COALESCE(CAST(pay_type AS STRING), ''))) AS pay_type_raw
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
    AND TRIM(region) = '{region}'
),
Norm AS (
  SELECT
    counter_hours,
    counter_type,
    CASE
      WHEN pay_type_raw IN ('hourly','h','non-exempt','nonexempt') THEN 'Hourly'
      WHEN pay_type_raw IN ('salaried','salary','exempt')          THEN 'Salaried'
      WHEN pay_type_raw IN ('1099','contractor','independent','ic') THEN '1099'
      ELSE 'Unknown'
    END AS pay_type
  FROM Base
),
Agg AS (
  SELECT
    SUM(counter_hours) AS total_counter_hours,
    SUM(CASE WHEN pay_type = 'Hourly'   THEN counter_hours ELSE 0 END) AS hourly_hours,
    SUM(CASE WHEN pay_type = 'Salaried' THEN counter_hours ELSE 0 END) AS salaried_hours,
    SUM(CASE WHEN pay_type = '1099'     THEN counter_hours ELSE 0 END) AS contractor_1099_hours,
    SUM(CASE WHEN pay_type = 'Unknown'  THEN counter_hours ELSE 0 END) AS unknown_hours
  FROM Norm
)
SELECT
  total_counter_hours,
  hourly_hours,
  salaried_hours,
  contractor_1099_hours,
  unknown_hours,
  SAFE_DIVIDE(hourly_hours,   total_counter_hours) * 100 AS hourly_pct,
  SAFE_DIVIDE(salaried_hours, total_counter_hours) * 100 AS salaried_pct,
  SAFE_DIVIDE(contractor_1099_hours, total_counter_hours) * 100 AS contractor_1099_pct,
  SAFE_DIVIDE(unknown_hours,  total_counter_hours) * 100 AS unknown_pct
FROM Agg
"""

    # ---------------------------
    # Hourly-only breakdown by counter type
    # ---------------------------
    hourly_ct_breakdown_sql = f"""
WITH Base AS (
  SELECT
    SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours,
    LOWER(TRIM(counter_type)) AS counter_type,
    LOWER(TRIM(COALESCE(CAST(pay_type AS STRING), ''))) AS pay_type_raw
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
    AND TRIM(region) = '{region}'
),
Hourly AS (
  SELECT counter_type, counter_hours
  FROM Base
  WHERE pay_type_raw IN ('hourly','h','non-exempt','nonexempt')
),
Agg AS (
  SELECT
    CASE
      WHEN counter_type IN ('daily overtime','daily ot')     THEN 'Daily Overtime'
      WHEN counter_type IN ('weekly overtime','weekly ot')   THEN 'Weekly Overtime'
      WHEN counter_type LIKE '%%double time%%'               THEN 'Daily Double Time'
      WHEN counter_type = 'holiday worked'                   THEN 'Holiday Worked'
      WHEN counter_type LIKE 'consecutive day ot%%'          THEN 'Consecutive Day OT'
      WHEN counter_type LIKE 'consecutive day dt%%'          THEN 'Consecutive Day DT'
      WHEN counter_type LIKE '%%unpaid time off%%'           THEN 'Unpaid Time Off'
      WHEN counter_type = 'sick'                             THEN 'Sick'
      ELSE 'Regular / Other'
    END AS category,
    SUM(counter_hours) AS hours
  FROM Hourly
  GROUP BY category
),
Total AS ( SELECT SUM(hours) AS total_hourly_worked FROM Agg )
SELECT
  category,
  hours,
  SAFE_DIVIDE(hours, (SELECT total_hourly_worked FROM Total)) * 100 AS pct_of_hourly
FROM Agg
ORDER BY hours DESC
"""

    # ---------------------------
    # OT Composition (Hourly only, OT-like counters)
    # ---------------------------
    ot_composition_sql = f"""
WITH Base AS (
  SELECT
    SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours,
    LOWER(TRIM(counter_type)) AS counter_type,
    LOWER(TRIM(COALESCE(CAST(pay_type AS STRING), ''))) AS pay_type_raw,
    COALESCE(NULLIF(TRIM(is_billable_overtime), ''), 'UNKNOWN') AS is_billable_ot
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
    AND TRIM(region) = '{region}'
),
HourlyOT AS (
  SELECT counter_hours, counter_type, is_billable_ot
  FROM Base
  WHERE pay_type_raw IN ('hourly','h','non-exempt','nonexempt')
    AND (counter_type IN ('daily overtime','daily ot','weekly overtime','weekly ot')
         OR counter_type LIKE 'consecutive day ot%%'
         OR counter_type LIKE 'consecutive day dt%%'
         OR counter_type LIKE '%%double time%%'
         OR counter_type LIKE '%%overtime%%')
),
Agg AS (
  SELECT
    CASE
      WHEN counter_type IN ('daily overtime','daily ot') THEN 'Daily Overtime'
      WHEN counter_type IN ('weekly overtime','weekly ot') THEN 'Weekly Overtime'
      WHEN counter_type LIKE '%%double time%%' THEN 'Daily Double Time'
      WHEN counter_type LIKE 'consecutive day ot%%' THEN 'Consecutive Day OT'
      WHEN counter_type LIKE 'consecutive day dt%%' THEN 'Consecutive Day DT'
      ELSE 'Other OT'
    END AS ot_category,
    SUM(counter_hours) AS ot_hours
  FROM HourlyOT
  GROUP BY ot_category
),
Total AS ( SELECT SUM(ot_hours) AS total_ot FROM Agg )
SELECT
  ot_category,
  ot_hours,
  SAFE_DIVIDE(ot_hours, (SELECT total_ot FROM Total)) * 100 AS pct_of_ot
FROM Agg
ORDER BY ot_hours DESC
"""

    # ---------------------------
    # Billable OT by type (Hourly-only; premium anywhere, includes Regular/Other)
    # ---------------------------
    billable_ot_sql = f"""
WITH Base AS (
  SELECT
    SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours,
    LOWER(TRIM(counter_type)) AS counter_type,
    LOWER(TRIM(COALESCE(CAST(pay_type AS STRING), ''))) AS pay_type_raw,
    COALESCE(NULLIF(TRIM(is_billable_overtime), ''), 'UNKNOWN') AS is_billable_ot
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
    AND TRIM(region) = '{region}'
),
Billable AS (
  SELECT
    CASE
      WHEN counter_type IN ('daily overtime','daily ot')   THEN 'Daily Overtime'
      WHEN counter_type IN ('weekly overtime','weekly ot') THEN 'Weekly Overtime'
      WHEN counter_type LIKE '%%double time%%'             THEN 'Daily Double Time'
      WHEN counter_type LIKE 'consecutive day ot%%'        THEN 'Consecutive Day OT'
      WHEN counter_type LIKE 'consecutive day dt%%'        THEN 'Consecutive Day DT'
      WHEN counter_type LIKE '%%unpaid time off%%'         THEN 'Unpaid Time Off'
      WHEN counter_type = 'sick'                           THEN 'Sick'
      ELSE 'Regular / Other'
    END AS ot_category,
    SUM(counter_hours) AS billable_hours
  FROM Base
  WHERE pay_type_raw IN ('hourly','h','non-exempt','nonexempt')
    AND is_billable_ot = 'OT'
  GROUP BY ot_category
),
Total AS ( SELECT SUM(billable_hours) AS total_billable_ot FROM Billable )
SELECT
  ot_category,
  billable_hours,
  SAFE_DIVIDE(billable_hours, (SELECT total_billable_ot FROM Total)) * 100 AS pct_of_ot
FROM Billable
ORDER BY billable_hours DESC
"""

    # ---- Execute queries
    try:
        client = bigquery.Client(project=compute_project)
        cust_rows = client.query(customers_sql).to_dataframe().to_dict(orient="records")
        totals = client.query(region_totals_sql).to_dataframe().to_dict(orient="records")
        ot_breakdown_rows = client.query(ot_breakdown_sql).to_dataframe().to_dict(orient="records")
        pay_type_totals = client.query(pay_type_totals_sql).to_dataframe().to_dict(orient="records")
        hourly_ct_rows  = client.query(hourly_ct_breakdown_sql).to_dataframe().to_dict(orient="records")
        ot_comp_rows    = client.query(ot_composition_sql).to_dataframe().to_dict(orient="records")
        billable_rows   = client.query(billable_ot_sql).to_dataframe().to_dict(orient="records")
    except Exception as e:
        return (
            f"Query failed: {str(e)}\n\n"
            f"CUSTOMERS_SQL:\n{customers_sql}\n\nREGION_TOTALS_SQL:\n{region_totals_sql}\n\n"
            f"OT_BREAKDOWN_SQL:\n{ot_breakdown_sql}\n\nPAY_TYPE_TOTALS_SQL:\n{pay_type_totals_sql}\n\n"
            f"HOURLY_CT_BREAKDOWN_SQL:\n{hourly_ct_breakdown_sql}\n\nOT_COMPOSITION_SQL:\n{ot_composition_sql}\n\n"
            f"BILLABLE_OT_SQL:\n{billable_ot_sql}"
        )

    if not totals:
        return f"No data found for region={region}, dates={start_date} to {end_date}"

    t = totals[0]
    total_hours = float(t.get('total_hours') or 0)
    total_ot_hours = float(t.get('total_ot_hours') or 0)
    billable_ot_hours = float(t.get('billable_ot_hours') or 0)
    regular_billed_at_ot_hours = float(t.get('regular_billed_at_ot_hours') or 0)
    nbot_hours = total_ot_hours - billable_ot_hours

    # Unpaid & Sick totals
    unpaid_time_off_hours_total = float(t.get('unpaid_time_off_hours_total') or 0)
    sick_hours_total = float(t.get('sick_hours_total') or 0)
    unpaid_events_total = int(t.get('unpaid_events_total') or 0)
    sick_events_total = int(t.get('sick_events_total') or 0)
    total_call_outs = sick_events_total + unpaid_events_total
    
    unpaid_pct_total = round(float(t.get('unpaid_pct_total') or 0), 2)
    sick_pct_total = round(float(t.get('sick_pct_total') or 0), 2)

    total_ot_pct = round(float(t.get('total_ot_pct') or 0), 2)
    nbot_pct = round(float(t.get('nbot_pct') or 0), 2)
    billable_ot_pct = round(float(t.get('billable_ot_pct') or 0), 2)

    # Regular hours
    regular_hours = total_hours - total_ot_hours
    regular_pct = round((regular_hours / total_hours * 100) if total_hours else 0, 1)

    # Add % of TWH to each OT breakdown row
    for r in ot_breakdown_rows:
        r["nbot_pct_of_twh"] = round((float(r.get("nbot_hours", 0)) / total_hours * 100) if total_hours else 0, 2)
        r["billable_pct_of_twh"] = round((float(r.get("billable_hours", 0)) / total_hours * 100) if total_hours else 0, 2)
        r["total_ot_pct_of_twh"] = round((float(r.get("total_ot_hours", 0)) / total_hours * 100) if total_hours else 0, 2)

    # Process customer rows
    for c in cust_rows:
        c["total_hours"] = float(c.get("total_hours") or 0)
        c["total_ot_hours"] = float(c.get("total_ot_hours") or 0)
        c["billable_ot_hours"] = float(c.get("billable_ot_hours") or 0)
        c["nbot_hours"] = float(c.get("nbot_hours") or 0)
        c["regular_billed_at_ot_hours"] = float(c.get("regular_billed_at_ot_hours") or 0)
        c["total_ot_pct"] = round(float(c.get("total_ot_pct") or 0), 2)
        c["nbot_pct"] = round(float(c.get("nbot_pct") or 0), 2)
        c["billable_ot_pct"] = round(float(c.get("billable_ot_pct") or 0), 2)
        c["sick_events"] = int(c.get("sick_events") or 0)
        c["unpaid_events"] = int(c.get("unpaid_events") or 0)
        c["total_call_outs"] = c["sick_events"] + c["unpaid_events"]
        c["sick_hours"] = float(c.get("sick_hours") or 0)
        c["unpaid_hours"] = float(c.get("unpaid_hours") or 0)
        c["sick_pct"] = round(float(c.get("sick_pct") or 0), 2)
        c["unpaid_pct"] = round(float(c.get("unpaid_pct") or 0), 2)

    # Executive summary health
    if nbot_pct < 3:
        nbot_status_color = "🟢"; nbot_status_text = "Excellent — Under target"
    elif 3 <= nbot_pct <= 5:
        nbot_status_color = "🟡"; nbot_status_text = "Acceptable — Monitor closely"
    else:
        nbot_status_color = "🔴"; nbot_status_text = "Critical — Immediate action required"

    critical_customers = sum(1 for c in cust_rows if c.get("nbot_pct", 0) > 5)
    if nbot_pct > 5 or (len(cust_rows) > 0 and critical_customers > len(cust_rows) * 0.4):
        region_health_status = "🔴 Needs Attention"
    elif nbot_pct > 3 or (len(cust_rows) > 0 and critical_customers > len(cust_rows) * 0.2):
        region_health_status = "🟡 Monitor"
    else:
        region_health_status = "🟢 Healthy"

    customers_with_ot = sum(1 for c in cust_rows if c.get("total_ot_hours", 0) > 0)
    customers_with_ot_pct = round((customers_with_ot / len(cust_rows) * 100) if cust_rows else 0, 1)

    # Key Insight support list
    ot_breakdown = []
    if nbot_hours > 0:
        for r in ot_breakdown_rows:
            if r.get("nbot_hours", 0) > 0:
                pct_of_nbot = round((float(r["nbot_hours"]) / nbot_hours * 100), 1)
                ot_breakdown.append({"label": r["ot_category"], "pct_of_nbot": pct_of_nbot})

    pareto_customers = [c for c in cust_rows if c.get('pareto_80_flag') == 'Yes']

    # Risk flags
    risk_flags = []
    if nbot_pct > 5:
        risk_flags.append(f"🔴 High Regional NBOT ({nbot_pct:.1f}%) — Exceeds 5% threshold")
    if len(cust_rows) > 0 and critical_customers > len(cust_rows) * 0.3:
        risk_flags.append(f"🟠 Multiple Critical Customers — {critical_customers} of {len(cust_rows)} customers exceed 5% NBOT")
    top_customers = sorted(cust_rows, key=lambda x: float(x.get("nbot_pct", 0)), reverse=True)[:3]
    if top_customers and top_customers[0].get("nbot_pct", 0) > 10:
        risk_flags.append(f"⚠️ Severe Customer Issue — {top_customers[0]['customer_name']} at {top_customers[0].get('nbot_pct', 0):.1f}% NBOT")
    if len(pareto_customers) > 0 and len(cust_rows) > 0:
        concentration_pct = round((len(pareto_customers) / len(cust_rows) * 100), 1)
        if concentration_pct < 30:
            risk_flags.append(f"📊 High Concentration — {len(pareto_customers)} customers ({concentration_pct}%) account for 80% of regional NBOT")
    if total_call_outs >= 10:
        risk_flags.append(f"🟡 Elevated Regional Call-Out Rate — {total_call_outs} events across region")

    # Recommendations
    recommendations = []
    if nbot_pct > 5 and len(ot_breakdown_rows) > 0:
        top_nbot_category = max(ot_breakdown_rows, key=lambda x: float(x.get("nbot_hours", 0)))
        if top_nbot_category.get("nbot_hours", 0) > 0:
            recommendations.append(
                f"**Reduce {top_nbot_category['ot_category']}** (NBOT) across region — Accounts for "
                f"{top_nbot_category.get('nbot_pct_of_twh', 0):.2f}% of total regional hours"
            )
    if len(pareto_customers) > 0:
        pareto_nbot = sum(float(c.get('nbot_hours', 0)) for c in pareto_customers)
        top_3_pareto = [c['customer_name'] for c in pareto_customers[:3]]
        recommendations.append(
            f"**Pareto Strategy** — {len(pareto_customers)} customers drive 80% of regional NBOT ({pareto_nbot:,.0f} hours). "
            f"Focus efforts on: {', '.join(top_3_pareto)}"
        )
    if critical_customers > 0:
        top_3_customers = [c['customer_name'] for c in top_customers[:3] if c.get('nbot_pct', 0) > 5]
        if top_3_customers:
            recommendations.append(
                f"**Focus on High-NBOT Customers** — Prioritize intervention at: {', '.join(top_3_customers)}"
            )
    if len(cust_rows) > 5 and critical_customers > 3:
        recommendations.append(
            "**Regional Review** — High number of customers with NBOT issues suggests regional "
            "operational challenges. Consider region-wide policy and scheduling review."
        )
    if total_call_outs >= 10:
        recommendations.append(
            f"**Address Regional Absenteeism** — {total_call_outs} total call-outs; implement region-wide attendance policies and wellness programs."
        )
    if not recommendations:
        recommendations.append("✅ Region is performing well across all customers — Continue current practices")

    # Helper: add totals rows
    def _with_totals(rows, hours_key, pct_keys=None, label_key=None, total_label="Total"):
        out = [dict(r) for r in rows] if rows else []
        total_row = {}
        total_val = round(sum(float(r.get(hours_key, 0) or 0) for r in rows), 2) if rows else 0.0
        if rows:
            for k in rows[0].keys():
                total_row[k] = ""
            lk = label_key or (rows and list(rows[0].keys())[0]) or "category"
            total_row[lk] = total_label
        total_row[hours_key] = total_val
        if pct_keys:
            for pk in pct_keys:
                total_row[pk] = round(sum(float(r.get(pk, 0) or 0) for r in rows), 2)
        out.append(total_row)
        return out

    # Build OT/Billable/NBOT tables with totals
    total_ot_from_comp = sum(float(r.get("ot_hours", 0) or 0) for r in ot_comp_rows) if ot_comp_rows else 0.0
    for r in (ot_comp_rows or []):
        r["ot_hours"] = float(r.get("ot_hours") or 0)
        r["pct_of_ot"] = round(float(r.get("pct_of_ot") or 0), 2)
    ot_comp_rows = _with_totals(ot_comp_rows, "ot_hours", ["pct_of_ot"], label_key="ot_category")

    for r in (billable_rows or []):
        r["billable_hours"] = float(r.get("billable_hours") or 0)
        r["pct_of_ot"] = round(float(r.get("pct_of_ot") or 0), 2)
    billable_rows = _with_totals(billable_rows, "billable_hours", ["pct_of_ot"], label_key="ot_category")

    # NBOT = Total OT (hourly) – Billable OT (hourly)
    bill_map = {r.get("ot_category"): float(r.get("billable_hours") or 0) for r in (billable_rows[:-1] if billable_rows else [])}
    nbot_rows = []
    for r in (ot_comp_rows[:-1] if ot_comp_rows else []):
        cat = r.get("ot_category")
        ot_h = float(r.get("ot_hours") or 0)
        bill_h = bill_map.get(cat, 0.0)
        nbot_h = max(ot_h - bill_h, 0.0)
        nbot_rows.append({
            "ot_category": cat,
            "nbot_hours": nbot_h,
            "pct_of_ot": round((nbot_h / total_ot_from_comp * 100) if total_ot_from_comp else 0.0, 2),
            "pct_of_twh": round((nbot_h / total_hours * 100) if total_hours else 0.0, 2),
        })
    nbot_rows = _with_totals(nbot_rows, "nbot_hours", ["pct_of_ot","pct_of_twh"], label_key="ot_category")

    # Pay type unpack
    pt = pay_type_totals[0] if pay_type_totals else {}
    total_counter_hours_all     = float(pt.get("total_counter_hours") or 0.0)
    hourly_hours_total          = float(pt.get("hourly_hours") or 0.0)
    salaried_hours_total        = float(pt.get("salaried_hours") or 0.0)
    contractor_1099_hours_total = float(pt.get("contractor_1099_hours") or 0.0)
    unknown_hours_total         = float(pt.get("unknown_hours") or 0.0)

    hourly_pct          = round(float(pt.get("hourly_pct") or 0.0), 2)
    salaried_pct        = round(float(pt.get("salaried_pct") or 0.0), 2)
    contractor_1099_pct = round(float(pt.get("contractor_1099_pct") or 0.0), 2)
    unknown_pct         = round(float(pt.get("unknown_pct") or 0.0), 2)

    for r in (hourly_ct_rows or []):
        r["hours"] = float(r.get("hours") or 0)
        r["pct_of_hourly"] = round(float(r.get("pct_of_hourly") or 0), 2)
    hourly_ct_rows = _with_totals(hourly_ct_rows, "hours", ["pct_of_hourly"], label_key="category")

    context = {
        "region": region,
        "start_date": start_date,
        "end_date": end_date,
        "report_ts": report_ts,
        "total_hours": f"{total_hours:,.2f}",
        "total_ot_hours": f"{total_ot_hours:,.2f}",
        "nbot_hours": f"{nbot_hours:,.2f}",
        "billable_ot_hours": f"{billable_ot_hours:,.2f}",
        "regular_billed_at_ot_hours": f"{regular_billed_at_ot_hours:,.2f}",
        "total_ot_pct": total_ot_pct,
        "nbot_pct": nbot_pct,
        "billable_ot_pct": billable_ot_pct,
        "regular_hours": f"{regular_hours:,.2f}",
        "regular_pct": f"{regular_pct:.1f}",
        "customer_count": len(cust_rows),
        "customers": cust_rows,
        "ot_breakdown_rows": ot_breakdown_rows,
        "region_health_status": region_health_status,
        "nbot_status_color": nbot_status_color,
        "nbot_status_text": nbot_status_text,
        "customers_with_ot": customers_with_ot,
        "customers_with_ot_pct": customers_with_ot_pct,
        "ot_breakdown": ot_breakdown,
        "risk_flags": risk_flags,
        "recommendations": recommendations,
        "unpaid_time_off_hours_total": f"{unpaid_time_off_hours_total:,.2f}",
        "unpaid_pct_total": unpaid_pct_total,
        "sick_hours_total": f"{sick_hours_total:,.2f}",
        "sick_pct_total": sick_pct_total,
        "unpaid_events_total": unpaid_events_total,
        "sick_events_total": sick_events_total,
        "total_call_outs": total_call_outs,
        "total_counter_hours_all": f"{total_counter_hours_all:,.2f}",
        "hourly_hours_total": f"{hourly_hours_total:,.2f}",
        "salaried_hours_total": f"{salaried_hours_total:,.2f}",
        "unknown_hours_total": f"{unknown_hours_total:,.2f}",
        "hourly_pct": hourly_pct,
        "salaried_pct": salaried_pct,
        "unknown_pct": unknown_pct,
        "hourly_ct_rows": hourly_ct_rows,
        "ot_comp_rows": ot_comp_rows,
        "billable_rows": billable_rows,
        "nbot_rows": nbot_rows,
        "contractor_1099_hours_total": f"{contractor_1099_hours_total:,.2f}",
        "contractor_1099_pct": contractor_1099_pct,
    }

    template = Template("""# 🌐 Excellence Performance Center 🌐
## NBOT Region Analysis – {{ region }} | {{ report_ts }}
**Period:** {{ start_date }} – {{ end_date }}

---

## 📋 Executive Summary

**Regional Health:** {{ region_health_status }}

### Key Findings
- **NBOT Performance:** {{ "%.2f"|format(nbot_pct) }}% ({{ nbot_status_color }}) — {{ nbot_status_text }}
- **Billable OT (OT or Regular Hours Billed at OT Rate):** {{ "%.2f"|format(billable_ot_pct) }}% | **Total OT:** {{ "%.2f"|format(total_ot_pct) }}%
- **Customers with OT:** {{ customers_with_ot }} of {{ customer_count }} customers ({{ "%.1f"|format(customers_with_ot_pct) }}%)
- **Unpaid Time Off:** {{ unpaid_events_total }} events ({{ "%.2f"|format(unpaid_pct_total) }}% of hours)
- **Sick:** {{ sick_events_total }} events ({{ "%.2f"|format(sick_pct_total) }}% of hours)
- **Total Call-Outs:** {{ total_call_outs }} events across region

**NBOT Thresholds:** 🟢 GREEN < 3% · 🟡 YELLOW 3–5% · 🔴 RED > 5%

{% if risk_flags and risk_flags|length > 0 -%}
### ⚠️ Risk Indicators
{% for flag in risk_flags -%}
- {{ flag }}
{% endfor -%}
{% endif %}

{% if recommendations and recommendations|length > 0 -%}
### 💡 Recommendations
{% for rec in recommendations -%}
- {{ rec }}
{% endfor -%}
{% endif %}

---

## 📊 Regional Key Metrics

| METRIC | VALUE |
|:-------|------:|
| Total Hours Counters | {{ total_hours }} |
| Total Hours Hourly | {{ hourly_hours_total }} |
| Total OT Hours | {{ total_ot_hours }} |
| Total OT % | {{ "%.2f"|format(total_ot_pct) }}% |
| Billable OT Hours (OT or Regular Hours Billed at OT Rate) | {{ billable_ot_hours }} |
| Billable OT % (OT or Regular Hours Billed at OT Rate) | {{ "%.2f"|format(billable_ot_pct) }}% |
| NBOT Hours | {{ nbot_hours }} |
| NBOT % | {{ "%.2f"|format(nbot_pct) }}% |
| Total Customers | {{ customer_count }} |
| Customers with OT | {{ customers_with_ot }} |
| **Sick Events** | **{{ sick_events_total }}** |
| **Unpaid Time Off Events** | **{{ unpaid_events_total }}** |
| **Total Call-Outs** | **{{ total_call_outs }}** |

> **Note:** Billable OT Hours includes {{ regular_billed_at_ot_hours }} Regular hours billed at OT Rate

---

## 🧮 Total Hours | Pay Type Breakdown
**Total Counter Hours (All counters):** {{ total_counter_hours_all }}

| Pay Type  | Hours | % of Total |
|:----------|------:|-----------:|
| Hourly    | {{ hourly_hours_total }} | {{ "%.2f"|format(hourly_pct) }}% |
| Salaried  | {{ salaried_hours_total }} | {{ "%.2f"|format(salaried_pct) }}% |
| 1099      | {{ contractor_1099_hours_total }} | {{ "%.2f"|format(contractor_1099_pct) }}% |
| **Total** | **{{ total_counter_hours_all }}** | **{{ "%.2f"|format(hourly_pct + salaried_pct + contractor_1099_pct) }}%** |

> **Note:** Only **Hourly** hours are used for OT/NBOT calculation and compliance exposure.

---

## 🧩 Hourly Worked Hours | by Counter Type
| Category | Hours | % of Hourly |
|:---------|------:|------------:|
{% for r in hourly_ct_rows -%}
| {{ r.category }} | {{ "%.2f"|format(r.hours or 0) }} | {{ "%.2f"|format(r.pct_of_hourly or 0) }}% |
{% endfor -%}

---

## 🔧 OT Composition (Hourly Only)
| OT Counter Type | OT Hours | % of OT |
|:----------------|---------:|--------:|
{% for r in ot_comp_rows -%}
| {{ r.ot_category }} | {{ "%.2f"|format(r.ot_hours or 0) }} | {{ "%.2f"|format(r.pct_of_ot or 0) }}% |
{% endfor -%}

---

## 💸 Billable OT (OT and Regular Hours Charged at Premium) — Hourly Only
| Counter Type | Billable Premium Hours | % of Premium |
|:-------------|-----------------------:|-------------:|
{% for r in billable_rows -%}
| {{ r.ot_category }} | {{ "%.2f"|format(r.billable_hours or 0) }} | {{ "%.2f"|format(r.pct_of_ot or 0) }}% |
{% endfor -%}

---

##  NBOT (Non-Billable Overtime) | by Counter Type
| OT Counter Type | NBOT Hours | % of OT | % of TWH |
|:----------------|-----------:|--------:|---------:|
{% for r in nbot_rows -%}
| {{ r.ot_category }} | {{ "%.2f"|format(r.nbot_hours or 0) }} | {{ "%.2f"|format(r.pct_of_ot or 0) }}% | {{ "%.2f"|format(r.pct_of_twh or 0) }}% |
{% endfor -%}

---

## 📅 HOURS BREAKDOWN BY CATEGORY

| Category | NBOT Hours | Billable OT | Total Hours | % of TWH | Visual Impact |
|:---------|----------:|------------:|------------:|---------:|:--------------|
| Regular (NON-OT) | — | — | — | {{ regular_pct }}% | ████████████████████ |
{% for row in ot_breakdown_rows -%}
| {{ row.ot_category }} | {{ "%.2f"|format(row.nbot_hours or 0) }} | {{ "%.2f"|format(row.billable_hours or 0) }} | {{ "%.2f"|format(row.total_ot_hours or 0) }} | {{ "%.2f"|format(row.total_ot_pct_of_twh or 0) }}% | {% if row.total_ot_pct_of_twh > 5 %}██████░░░░░░░░░░░░░░{% elif row.total_ot_pct_of_twh > 2 %}███░░░░░░░░░░░░░░░░░{% else %}█░░░░░░░░░░░░░░░░░░░{% endif %} |
{% endfor %}

{% if ot_breakdown and ot_breakdown|length > 0 -%}
**▶️ Key Insight:** {{ ot_breakdown[0].label }} represents {{ "%.1f"|format(ot_breakdown[0].pct_of_nbot) }}% of NBOT → Primary reduction target
{% endif %}

---

## 📈 Pareto – NBOT by Customer (Region: {{ region }})
| Rank | Customer Code | Customer | Total Hours | Total OT Hours | Total OT % | NBOT Hours | NBOT % | Billable OT Hours | Billable OT % | Sick Events | Unpaid Events | Cum NBOT % | Pareto 80% |
|---:|:--:|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|:--:|
{% for c in customers -%}
| {{ c.nbot_rank }} | {{ c.customer_code or '' }} | {{ c.customer_name }} | {{ "%.2f"|format(c.total_hours or 0) }} | {{ "%.2f"|format(c.total_ot_hours or 0) }} | {{ "%.2f"|format(c.total_ot_pct or 0) }}% | {{ "%.2f"|format(c.nbot_hours or 0) }} | {{ "%.2f"|format(c.nbot_pct or 0) }}% | {{ "%.2f"|format(c.billable_ot_hours or 0) }} | {{ "%.2f"|format(c.billable_ot_pct or 0) }}% | {{ c.sick_events }} | {{ c.unpaid_events }} | {{ "%.2f"|format(c.nbot_cum_pct or 0) }}% | {% if c.pareto_80_flag == 'Yes' %}☑️{% endif %} |
{% endfor %}

---

## 🏥 Regional Sick & Unpaid Time Off Analysis

### Event Summary by Customer
| Rank | Customer | Sick Events | Sick Hours | Sick % | Unpaid Events | Unpaid Hours | Unpaid % | Total Call-Outs |
|---:|:---------|------------:|-----------:|-------:|--------------:|-------------:|---------:|----------------:|
{% for c in customers -%}
| {{ c.nbot_rank }} | {{ c.customer_name }} | {{ c.sick_events }} | {{ "%.2f"|format(c.sick_hours or 0) }} | {{ "%.2f"|format(c.sick_pct or 0) }}% | {{ c.unpaid_events }} | {{ "%.2f"|format(c.unpaid_hours or 0) }} | {{ "%.2f"|format(c.unpaid_pct or 0) }}% | {{ c.total_call_outs }} |
{% endfor %}
""")
    return template.render(**context)







# ------------------------------------------------------------
# 3) NBOT Customer Analysis (across regions, Pareto by Site)
# ------------------------------------------------------------


def _generate_nbot_customer_analysis(
    customer_code: int,
    start_date: str,
    end_date: str,
    project: str,
    dataset: str,
    compute_project: str,
    region: Optional[str] = None
) -> str:
    if not all([customer_code, start_date, end_date]):
        return "Missing required parameters: customer_code, start_date, end_date"

    from jinja2 import Template
    from google.cloud import bigquery
    import datetime

    customer_code_str = str(customer_code)
    
    # Date-only report stamp
    report_ts = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Optional region scope
    region_filter = f"AND TRIM(region) = '{region}'" if region else ""

    # ---------------------------
    # Sites Pareto (customer)
    # - NBOT: Non-billable overtime in OT-like counters
    # - Billable OT: ANY counter with is_billable_overtime = 'OT' (premium regular + OT)
    # ---------------------------
    sites_sql = f"""
WITH Base AS (
  SELECT
    CAST(location_number AS STRING) AS location_number,
    COALESCE(NULLIF(TRIM(region), ''), 'Unassigned') AS region,
    COALESCE(NULLIF(TRIM(state), ''), 'NA') AS state,
    COALESCE(NULLIF(TRIM(customer_name), ''), 'Unassigned') AS customer_name,
    COALESCE(NULLIF(TRIM(site_manager), ''), 'Unassigned') AS site_manager,
    LOWER(TRIM(counter_type)) AS counter_type,
    SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours,
    COALESCE(NULLIF(TRIM(is_billable_overtime), ''), 'UNKNOWN') AS is_billable_ot
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
    AND customer_code = '{customer_code_str}'
    {region_filter}
),
Agg AS (
  SELECT
    location_number, region, state,
    ANY_VALUE(customer_name) AS customer_name,
    ANY_VALUE(site_manager) AS site_manager,
    SUM(counter_hours) AS total_hours,
    -- NBOT: Non-Billable OT only (confined to OT-like counters)
    SUM(
      CASE 
        WHEN (counter_type IN ('daily overtime','daily ot','weekly overtime','weekly ot','holiday worked')
              OR counter_type LIKE 'consecutive day ot%%'
              OR counter_type LIKE 'consecutive day dt%%'
              OR counter_type LIKE '%%double time%%'
              OR counter_type LIKE '%%overtime%%')
             AND is_billable_ot = 'NON-OT'
        THEN counter_hours ELSE 0 END
    ) AS nbot_hours,
    -- Billable OT (premium anywhere: OT AND regular)
    SUM(CASE WHEN is_billable_ot = 'OT' THEN counter_hours ELSE 0 END) AS billable_ot_hours
  FROM Base
  GROUP BY location_number, region, state
),
WithPct AS (
  SELECT
    location_number, region, state, customer_name, site_manager,
    total_hours, nbot_hours, billable_ot_hours,
    SAFE_DIVIDE(nbot_hours, total_hours) * 100 AS nbot_pct,
    SAFE_DIVIDE(billable_ot_hours, total_hours) * 100 AS billable_ot_pct,
    SAFE_DIVIDE(nbot_hours + billable_ot_hours, total_hours) * 100 AS total_ot_pct
  FROM Agg
),
Pareto AS (
  SELECT
    *,
    RANK() OVER (ORDER BY nbot_hours DESC) AS nbot_rank,
    SUM(nbot_hours) OVER () AS nbot_total_all,
    SUM(nbot_hours) OVER (ORDER BY nbot_hours DESC
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS nbot_cum,
    SAFE_DIVIDE(
      SUM(nbot_hours) OVER (ORDER BY nbot_hours DESC
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW),
      SUM(nbot_hours) OVER ()
    ) * 100 AS nbot_cum_pct
  FROM WithPct
)
SELECT
  location_number, region, state, customer_name, site_manager,
  total_hours, nbot_hours, billable_ot_hours,
  nbot_pct, billable_ot_pct, total_ot_pct,
  nbot_rank, nbot_cum_pct,
  CASE WHEN nbot_cum_pct <= 80 THEN 'Yes' ELSE 'No' END AS pareto_80_flag
FROM Pareto
ORDER BY nbot_hours DESC
"""

    # ---------------------------
    # Customer Totals / % (Billable premium anywhere)
    # ---------------------------
    cust_totals_sql = f"""
WITH Base AS (
  SELECT
    customer_name,
    LOWER(TRIM(counter_type)) AS counter_type,
    SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours,
    COALESCE(NULLIF(TRIM(is_billable_overtime), ''), 'UNKNOWN') AS is_billable_ot
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
    AND customer_code = '{customer_code_str}'
    {region_filter}
)
SELECT
  ANY_VALUE(customer_name) AS customer_name,
  SUM(counter_hours) AS total_hours,

  -- NBOT: Non-Billable OT only (confined to OT-like counters)
  SUM(
    CASE 
      WHEN (counter_type IN ('daily overtime','daily ot','weekly overtime','weekly ot','holiday worked')
            OR counter_type LIKE 'consecutive day ot%%'
            OR counter_type LIKE 'consecutive day dt%%'
            OR counter_type LIKE '%%double time%%'
            OR counter_type LIKE '%%overtime%%')
           AND is_billable_ot = 'NON-OT'
      THEN counter_hours ELSE 0 END
  ) AS nbot_hours,

  -- Billable OT (premium anywhere: OT AND regular)
  SUM(CASE WHEN is_billable_ot = 'OT' THEN counter_hours ELSE 0 END) AS billable_ot_hours,

  -- Unpaid Time Off + Sick totals
  SUM(CASE WHEN counter_type LIKE '%%unpaid time off%%' THEN counter_hours ELSE 0 END) AS unpaid_time_off_hours_total,
  SUM(CASE WHEN counter_type = 'sick' THEN counter_hours ELSE 0 END) AS sick_hours_total,

  -- Percentages (of total worked hours)
  SAFE_DIVIDE(
    SUM(
      CASE 
        WHEN (counter_type IN ('daily overtime','daily ot','weekly overtime','weekly ot','holiday worked')
              OR counter_type LIKE 'consecutive day ot%%'
              OR counter_type LIKE 'consecutive day dt%%'
              OR counter_type LIKE '%%double time%%'
              OR counter_type LIKE '%%overtime%%')
             AND is_billable_ot = 'NON-OT'
      THEN counter_hours ELSE 0 END),
    SUM(counter_hours)
  ) * 100 AS nbot_pct,

  SAFE_DIVIDE(
    SUM(CASE WHEN is_billable_ot = 'OT' THEN counter_hours ELSE 0 END),
    SUM(counter_hours)
  ) * 100 AS billable_ot_pct,

  SAFE_DIVIDE(
    SUM(CASE WHEN counter_type LIKE '%%unpaid time off%%' THEN counter_hours ELSE 0 END),
    SUM(counter_hours)
  ) * 100 AS unpaid_pct_total,

  SAFE_DIVIDE(
    SUM(CASE WHEN counter_type = 'sick' THEN counter_hours ELSE 0 END),
    SUM(counter_hours)
  ) * 100 AS sick_pct_total
FROM Base
"""

    # ---------------------------
    # OT breakdown (kept OT categories)
    # ---------------------------
    ot_breakdown_sql = f"""
WITH Base AS (
  SELECT
    LOWER(TRIM(counter_type)) AS counter_type,
    SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours,
    COALESCE(NULLIF(TRIM(is_billable_overtime), ''), 'UNKNOWN') AS is_billable_ot
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
    AND customer_code = '{customer_code_str}'
    {region_filter}
)

-- Standard OT categories
SELECT
  CASE
    WHEN counter_type IN ('daily overtime','daily ot') THEN 'Daily Overtime'
    WHEN counter_type IN ('weekly overtime','weekly ot') THEN 'Weekly Overtime'
    WHEN counter_type LIKE '%%double time%%' THEN 'Daily Double Time'
    WHEN counter_type LIKE 'consecutive day ot%%' THEN 'Consecutive Day OT'
    WHEN counter_type LIKE 'consecutive day dt%%' THEN 'Consecutive Day DT'
    ELSE 'Other OT'
  END AS ot_category,
  SUM(CASE WHEN is_billable_ot = 'NON-OT' THEN counter_hours ELSE 0 END) AS nbot_hours,
  SUM(CASE WHEN is_billable_ot = 'OT' THEN counter_hours ELSE 0 END) AS billable_hours,
  SUM(counter_hours) AS total_ot_hours
FROM Base
WHERE (counter_type IN ('daily overtime','daily ot','weekly overtime','weekly ot')
       OR counter_type LIKE 'consecutive day ot%%'
       OR counter_type LIKE 'consecutive day dt%%'
       OR counter_type LIKE '%%double time%%'
       OR counter_type LIKE '%%overtime%%')
GROUP BY ot_category

UNION ALL
-- Unpaid Time Off Request (as its own row)
SELECT
  'Unpaid Time Off Request' AS ot_category,
  0 AS nbot_hours,
  0 AS billable_hours,
  SUM(CASE WHEN counter_type LIKE '%%unpaid time off%%' THEN counter_hours ELSE 0 END) AS total_ot_hours
FROM Base
WHERE counter_type LIKE '%%unpaid time off%%'

UNION ALL
-- Sick (as its own row)
SELECT
  'Sick' AS ot_category,
  0 AS nbot_hours,
  0 AS billable_hours,
  SUM(CASE WHEN counter_type = 'sick' THEN counter_hours ELSE 0 END) AS total_ot_hours
FROM Base
WHERE counter_type = 'sick'
ORDER BY total_ot_hours DESC
"""

    # ---------------------------
    # Pay type totals (adds 1099; Unknown kept out of the table)
    # ---------------------------
    pay_type_totals_sql = f"""
WITH Base AS (
  SELECT
    SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours,
    LOWER(TRIM(counter_type)) AS counter_type,
    LOWER(TRIM(COALESCE(CAST(pay_type AS STRING), ''))) AS pay_type_raw
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
    AND customer_code = '{customer_code_str}'
    {region_filter}
),
Norm AS (
  SELECT
    counter_hours,
    counter_type,
    CASE
      WHEN pay_type_raw IN ('hourly','h','non-exempt','nonexempt') THEN 'Hourly'
      WHEN pay_type_raw IN ('salaried','salary','exempt')          THEN 'Salaried'
      WHEN pay_type_raw IN ('1099','contractor','independent','ic') THEN '1099'
      ELSE 'Unknown'
    END AS pay_type
  FROM Base
),
Agg AS (
  SELECT
    SUM(counter_hours) AS total_counter_hours,
    SUM(CASE WHEN pay_type = 'Hourly'   THEN counter_hours ELSE 0 END) AS hourly_hours,
    SUM(CASE WHEN pay_type = 'Salaried' THEN counter_hours ELSE 0 END) AS salaried_hours,
    SUM(CASE WHEN pay_type = '1099'     THEN counter_hours ELSE 0 END) AS contractor_1099_hours,
    SUM(CASE WHEN pay_type = 'Unknown'  THEN counter_hours ELSE 0 END) AS unknown_hours
  FROM Norm
)
SELECT
  total_counter_hours,
  hourly_hours,
  salaried_hours,
  contractor_1099_hours,
  unknown_hours,
  SAFE_DIVIDE(hourly_hours,   total_counter_hours) * 100 AS hourly_pct,
  SAFE_DIVIDE(salaried_hours, total_counter_hours) * 100 AS salaried_pct,
  SAFE_DIVIDE(contractor_1099_hours, total_counter_hours) * 100 AS contractor_1099_pct,
  SAFE_DIVIDE(unknown_hours,  total_counter_hours) * 100 AS unknown_pct
FROM Agg
"""

    # ---------------------------
    # Hourly-only breakdown by counter type
    # ---------------------------
    hourly_ct_breakdown_sql = f"""
WITH Base AS (
  SELECT
    SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours,
    LOWER(TRIM(counter_type)) AS counter_type,
    LOWER(TRIM(COALESCE(CAST(pay_type AS STRING), ''))) AS pay_type_raw
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
    AND customer_code = '{customer_code_str}'
    {region_filter}
),
Hourly AS (
  SELECT counter_type, counter_hours
  FROM Base
  WHERE pay_type_raw IN ('hourly','h','non-exempt','nonexempt')
),
Agg AS (
  SELECT
    CASE
      WHEN counter_type IN ('daily overtime','daily ot')     THEN 'Daily Overtime'
      WHEN counter_type IN ('weekly overtime','weekly ot')   THEN 'Weekly Overtime'
      WHEN counter_type LIKE '%%double time%%'               THEN 'Daily Double Time'
      WHEN counter_type = 'holiday worked'                   THEN 'Holiday Worked'
      WHEN counter_type LIKE 'consecutive day ot%%'          THEN 'Consecutive Day OT'
      WHEN counter_type LIKE 'consecutive day dt%%'          THEN 'Consecutive Day DT'
      WHEN counter_type LIKE '%%unpaid time off%%'           THEN 'Unpaid Time Off'
      WHEN counter_type = 'sick'                             THEN 'Sick'
      ELSE 'Regular / Other'
    END AS category,
    SUM(counter_hours) AS hours
  FROM Hourly
  GROUP BY category
),
Total AS ( SELECT SUM(hours) AS total_hourly_worked FROM Agg )
SELECT
  category,
  hours,
  SAFE_DIVIDE(hours, (SELECT total_hourly_worked FROM Total)) * 100 AS pct_of_hourly
FROM Agg
ORDER BY hours DESC
"""

    # ---------------------------
    # OT Composition (Hourly only, OT-like counters)
    # ---------------------------
    ot_composition_sql = f"""
WITH Base AS (
  SELECT
    SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours,
    LOWER(TRIM(counter_type)) AS counter_type,
    LOWER(TRIM(COALESCE(CAST(pay_type AS STRING), ''))) AS pay_type_raw,
    COALESCE(NULLIF(TRIM(is_billable_overtime), ''), 'UNKNOWN') AS is_billable_ot
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
    AND customer_code = '{customer_code_str}'
    {region_filter}
),
HourlyOT AS (
  SELECT counter_hours, counter_type, is_billable_ot
  FROM Base
  WHERE pay_type_raw IN ('hourly','h','non-exempt','nonexempt')
    AND (counter_type IN ('daily overtime','daily ot','weekly overtime','weekly ot')
         OR counter_type LIKE 'consecutive day ot%%'
         OR counter_type LIKE 'consecutive day dt%%'
         OR counter_type LIKE '%%double time%%'
         OR counter_type LIKE '%%overtime%%')
),
Agg AS (
  SELECT
    CASE
      WHEN counter_type IN ('daily overtime','daily ot') THEN 'Daily Overtime'
      WHEN counter_type IN ('weekly overtime','weekly ot') THEN 'Weekly Overtime'
      WHEN counter_type LIKE '%%double time%%' THEN 'Daily Double Time'
      WHEN counter_type LIKE 'consecutive day ot%%' THEN 'Consecutive Day OT'
      WHEN counter_type LIKE 'consecutive day dt%%' THEN 'Consecutive Day DT'
      ELSE 'Other OT'
    END AS ot_category,
    SUM(counter_hours) AS ot_hours
  FROM HourlyOT
  GROUP BY ot_category
),
Total AS ( SELECT SUM(ot_hours) AS total_ot FROM Agg )
SELECT
  ot_category,
  ot_hours,
  SAFE_DIVIDE(ot_hours, (SELECT total_ot FROM Total)) * 100 AS pct_of_ot
FROM Agg
ORDER BY ot_hours DESC
"""

    # ---------------------------
    # Billable OT by type (Hourly-only; premium anywhere, includes Regular/Other)
    # ---------------------------
    billable_ot_sql = f"""
WITH Base AS (
  SELECT
    SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours,
    LOWER(TRIM(counter_type)) AS counter_type,
    LOWER(TRIM(COALESCE(CAST(pay_type AS STRING), ''))) AS pay_type_raw,
    COALESCE(NULLIF(TRIM(is_billable_overtime), ''), 'UNKNOWN') AS is_billable_ot
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
    AND customer_code = '{customer_code_str}'
    {region_filter}
),
Billable AS (
  SELECT
    CASE
      WHEN counter_type IN ('daily overtime','daily ot')   THEN 'Daily Overtime'
      WHEN counter_type IN ('weekly overtime','weekly ot') THEN 'Weekly Overtime'
      WHEN counter_type LIKE '%%double time%%'             THEN 'Daily Double Time'
      WHEN counter_type LIKE 'consecutive day ot%%'        THEN 'Consecutive Day OT'
      WHEN counter_type LIKE 'consecutive day dt%%'        THEN 'Consecutive Day DT'
      WHEN counter_type LIKE '%%unpaid time off%%'         THEN 'Unpaid Time Off'
      WHEN counter_type = 'sick'                           THEN 'Sick'
      ELSE 'Regular / Other'
    END AS ot_category,
    SUM(counter_hours) AS billable_hours
  FROM Base
  WHERE pay_type_raw IN ('hourly','h','non-exempt','nonexempt')
    AND is_billable_ot = 'OT'    -- premium anywhere (includes regular)
  GROUP BY ot_category
),
Total AS ( SELECT SUM(billable_hours) AS total_billable_ot FROM Billable )
SELECT
  ot_category,
  billable_hours,
  SAFE_DIVIDE(billable_hours, (SELECT total_billable_ot FROM Total)) * 100 AS pct_of_ot
FROM Billable
ORDER BY billable_hours DESC
"""

    # ---- Execute queries
    try:
        client = bigquery.Client(project=compute_project)
        site_rows = client.query(sites_sql).to_dataframe().to_dict(orient="records")
        totals = client.query(cust_totals_sql).to_dataframe().to_dict(orient="records")
        ot_breakdown_rows = client.query(ot_breakdown_sql).to_dataframe().to_dict(orient="records")
        pay_type_totals = client.query(pay_type_totals_sql).to_dataframe().to_dict(orient="records")
        hourly_ct_rows  = client.query(hourly_ct_breakdown_sql).to_dataframe().to_dict(orient="records")
        ot_comp_rows    = client.query(ot_composition_sql).to_dataframe().to_dict(orient="records")
        billable_rows   = client.query(billable_ot_sql).to_dataframe().to_dict(orient="records")
    except Exception as e:
        return (
            f"Query failed: {str(e)}\n\n"
            f"SITES_SQL:\n{sites_sql}\n\nCUSTOMER_TOTALS_SQL:\n{cust_totals_sql}\n\n"
            f"OT_BREAKDOWN_SQL:\n{ot_breakdown_sql}\n\nPAY_TYPE_TOTALS_SQL:\n{pay_type_totals_sql}\n\n"
            f"HOURLY_CT_BREAKDOWN_SQL:\n{hourly_ct_breakdown_sql}\n\nOT_COMPOSITION_SQL:\n{ot_composition_sql}\n\n"
            f"BILLABLE_OT_SQL:\n{billable_ot_sql}"
        )

    # Clean manager names
    clean_site_manager_in_rows(site_rows)

    if not totals:
        region_msg = f" in region '{region}'" if region else ""
        return f"No data found for customer_code={customer_code}{region_msg}, dates={start_date} to {end_date}"

    t = totals[0]
    total_hours = float(t.get('total_hours') or 0)
    nbot_hours = float(t.get('nbot_hours') or 0)
    billable_ot_hours = float(t.get('billable_ot_hours') or 0)
    total_ot_hours = nbot_hours + billable_ot_hours

    # Unpaid & Sick totals
    unpaid_time_off_hours_total = float(t.get('unpaid_time_off_hours_total') or 0)
    sick_hours_total = float(t.get('sick_hours_total') or 0)
    unpaid_pct_total = round(float(t.get('unpaid_pct_total') or 0), 2)
    sick_pct_total = round(float(t.get('sick_pct_total') or 0), 2)

    nbot_pct = round(float(t.get('nbot_pct') or 0), 2)
    billable_ot_pct = round(float(t.get('billable_ot_pct') or 0), 2)
    total_ot_pct = round((total_ot_hours / total_hours * 100) if total_hours else 0, 2)

    # Regular hours
    regular_hours = total_hours - total_ot_hours
    regular_pct = round((regular_hours / total_hours * 100) if total_hours else 0, 1)

    # Add % of TWH to each OT breakdown row
    for r in ot_breakdown_rows:
        r["nbot_pct_of_twh"] = round((float(r.get("nbot_hours", 0)) / total_hours * 100) if total_hours else 0, 2)
        r["billable_pct_of_twh"] = round((float(r.get("billable_hours", 0)) / total_hours * 100) if total_hours else 0, 2)
        r["total_ot_pct_of_twh"] = round((float(r.get("total_ot_hours", 0)) / total_hours * 100) if total_hours else 0, 2)

    # Executive summary health
    if nbot_pct < 3:
        nbot_status_color = "🟢"; nbot_status_text = "Excellent — Under target"
    elif 3 <= nbot_pct <= 5:
        nbot_status_color = "🟡"; nbot_status_text = "Acceptable — Monitor closely"
    else:
        nbot_status_color = "🔴"; nbot_status_text = "Critical — Immediate action required"

    critical_sites = sum(1 for s in site_rows if s.get("nbot_pct", 0) > 5)
    if nbot_pct > 5 or (len(site_rows) > 0 and critical_sites > len(site_rows) * 0.4):
        customer_health_status = "🔴 Needs Attention"
    elif nbot_pct > 3 or (len(site_rows) > 0 and critical_sites > len(site_rows) * 0.2):
        customer_health_status = "🟡 Monitor"
    else:
        customer_health_status = "🟢 Healthy"

    sites_with_ot = sum(1 for s in site_rows if (s.get("nbot_hours", 0) + s.get("billable_ot_hours", 0)) > 0)
    sites_with_ot_pct = round((sites_with_ot / len(site_rows) * 100) if site_rows else 0, 1)

    # Key Insight support list
    ot_breakdown = []
    if nbot_hours > 0:
        for r in ot_breakdown_rows:
            if r.get("nbot_hours", 0) > 0:
                pct_of_nbot = round((float(r["nbot_hours"]) / nbot_hours * 100), 1)
                ot_breakdown.append({"label": r["ot_category"], "pct_of_nbot": pct_of_nbot})

    pareto_sites = [s for s in site_rows if s.get('pareto_80_flag') == 'Yes']

    # Risk flags
    risk_flags = []
    region_scope = f" (Region: {region})" if region else ""
    if nbot_pct > 5:
        risk_flags.append(f"🔴 High Customer NBOT ({nbot_pct:.1f}%){region_scope} — Exceeds 5% threshold")
    if len(site_rows) > 0 and critical_sites > len(site_rows) * 0.3:
        risk_flags.append(f"🟠 Multiple Critical Sites — {critical_sites} of {len(site_rows)} sites exceed 5% NBOT")
    
    top_sites = sorted(site_rows, key=lambda x: float(x.get("nbot_pct", 0)), reverse=True)[:3]
    if top_sites and top_sites[0].get("nbot_pct", 0) > 10:
        risk_flags.append(f"⚠️ Severe Site Issue — Location {top_sites[0]['location_number']} at {top_sites[0].get('nbot_pct', 0):.1f}% NBOT")
    
    if len(pareto_sites) > 0 and len(site_rows) > 0:
        concentration_pct = round((len(pareto_sites) / len(site_rows) * 100), 1)
        if concentration_pct < 30:
            risk_flags.append(f"📊 High Concentration — {len(pareto_sites)} sites ({concentration_pct}%) account for 80% of customer NBOT")

    # Recommendations
    recommendations = []
    if nbot_pct > 5 and len(ot_breakdown_rows) > 0:
        top_nbot_category = max(ot_breakdown_rows, key=lambda x: float(x.get("nbot_hours", 0)))
        if top_nbot_category.get("nbot_hours", 0) > 0:
            scope_text = f"across {region} region sites" if region else "across all sites"
            recommendations.append(
                f"**Reduce {top_nbot_category['ot_category']}** (NBOT) {scope_text} — Accounts for "
                f"{top_nbot_category.get('nbot_pct_of_twh', 0):.2f}% of total customer hours"
            )
    
    if len(pareto_sites) > 0:
        pareto_nbot = sum(float(s.get('nbot_hours', 0)) for s in pareto_sites)
        top_3_pareto = [f"Location {s['location_number']}" for s in pareto_sites[:3]]
        recommendations.append(
            f"**Pareto Strategy** — {len(pareto_sites)} sites drive 80% of customer NBOT ({pareto_nbot:,.0f} hours). "
            f"Focus efforts on: {', '.join(top_3_pareto)}"
        )
    
    if critical_sites > 0:
        top_3_sites = [f"Location {s['location_number']}" for s in top_sites[:3] if s.get('nbot_pct', 0) > 5]
        if top_3_sites:
            recommendations.append(
                f"**Focus on High-NBOT Sites** — Prioritize intervention at: {', '.join(top_3_sites)}"
            )
    
    if len(site_rows) > 5 and critical_sites > 3:
        scope_text = "regional" if region else "customer-wide"
        recommendations.append(
            f"**{scope_text.title()} Review** — High number of sites with NBOT issues suggests {scope_text} "
            f"operational challenges. Consider {scope_text} policy and scheduling review."
        )
    
    if not recommendations:
        recommendations.append("✅ Customer is performing well across all sites — Continue current practices")

    # Helper: add totals rows
    def _with_totals(rows, hours_key, pct_keys=None, label_key=None, total_label="Total"):
        out = [dict(r) for r in rows] if rows else []
        total_row = {}
        total_val = round(sum(float(r.get(hours_key, 0) or 0) for r in rows), 2) if rows else 0.0
        if rows:
            for k in rows[0].keys():
                total_row[k] = ""
            lk = label_key or (rows and list(rows[0].keys())[0]) or "category"
            total_row[lk] = total_label
        total_row[hours_key] = total_val
        if pct_keys:
            for pk in pct_keys:
                total_row[pk] = round(sum(float(r.get(pk, 0) or 0) for r in rows), 2)
        out.append(total_row)
        return out

    # Build OT/Billable/NBOT tables with totals
    total_ot_from_comp = sum(float(r.get("ot_hours", 0) or 0) for r in ot_comp_rows) if ot_comp_rows else 0.0
    for r in (ot_comp_rows or []):
        r["ot_hours"] = float(r.get("ot_hours") or 0)
        r["pct_of_ot"] = round(float(r.get("pct_of_ot") or 0), 2)
    ot_comp_rows = _with_totals(ot_comp_rows, "ot_hours", ["pct_of_ot"], label_key="ot_category")

    for r in (billable_rows or []):
        r["billable_hours"] = float(r.get("billable_hours") or 0)
        r["pct_of_ot"] = round(float(r.get("pct_of_ot") or 0), 2)
    billable_rows = _with_totals(billable_rows, "billable_hours", ["pct_of_ot"], label_key="ot_category")

    # CRITICAL: NBOT = Total OT (hourly) – ALL Billable Hours (including Regular/Other)
    # Calculate total billable including Regular/Other premium
    total_billable_all_sources = sum(float(r.get("billable_hours") or 0) for r in (billable_rows[:-1] if billable_rows else []))

    # Build bill_map for OT categories only
    bill_map = {r.get("ot_category"): float(r.get("billable_hours") or 0) for r in (billable_rows[:-1] if billable_rows else [])}

    # Calculate billable from OT categories only (excludes Regular/Other)
    billable_from_ot_categories = sum(bill_map.get(r.get("ot_category"), 0.0) for r in (ot_comp_rows[:-1] if ot_comp_rows else []))

    # Unmatched billable (e.g., Regular/Other premium not in OT categories)
    unmatched_billable = total_billable_all_sources - billable_from_ot_categories

    # Calculate per-category NBOT
    nbot_rows = []
    for r in (ot_comp_rows[:-1] if ot_comp_rows else []):
        cat = r.get("ot_category")
        ot_h = float(r.get("ot_hours") or 0)
        bill_h = bill_map.get(cat, 0.0)
        nbot_h = max(ot_h - bill_h, 0.0)
        nbot_rows.append({
            "ot_category": cat,
            "nbot_hours": nbot_h,
            "pct_of_ot": round((nbot_h / total_ot_from_comp * 100) if total_ot_from_comp else 0.0, 2),
            "pct_of_twh": round((nbot_h / total_hours * 100) if total_hours else 0.0, 2),
        })

    # Handle unmatched billable hours (Regular/Other premium)
    # Subtract from the largest NBOT category to reconcile the total
    if unmatched_billable > 0 and nbot_rows:
        # Find category with largest NBOT
        max_idx = max(range(len(nbot_rows)), key=lambda i: nbot_rows[i]["nbot_hours"])
        nbot_rows[max_idx]["nbot_hours"] = max(nbot_rows[max_idx]["nbot_hours"] - unmatched_billable, 0.0)
        
        # Recalculate percentages after adjustment
        for r in nbot_rows:
            r["pct_of_ot"] = round((r["nbot_hours"] / total_ot_from_comp * 100) if total_ot_from_comp else 0.0, 2)
            r["pct_of_twh"] = round((r["nbot_hours"] / total_hours * 100) if total_hours else 0.0, 2)

    # Add totals row
    nbot_rows = _with_totals(nbot_rows, "nbot_hours", ["pct_of_ot","pct_of_twh"], label_key="ot_category")

    # Pay type unpack (Unknown kept for math, hidden in table)
    pt = pay_type_totals[0] if pay_type_totals else {}
    total_counter_hours_all     = float(pt.get("total_counter_hours") or 0.0)
    hourly_hours_total          = float(pt.get("hourly_hours") or 0.0)
    salaried_hours_total        = float(pt.get("salaried_hours") or 0.0)
    contractor_1099_hours_total = float(pt.get("contractor_1099_hours") or 0.0)
    unknown_hours_total         = float(pt.get("unknown_hours") or 0.0)

    hourly_pct          = round(float(pt.get("hourly_pct") or 0.0), 2)
    salaried_pct        = round(float(pt.get("salaried_pct") or 0.0), 2)
    contractor_1099_pct = round(float(pt.get("contractor_1099_pct") or 0.0), 2)
    unknown_pct         = round(float(pt.get("unknown_pct") or 0.0), 2)

    for r in (hourly_ct_rows or []):
        r["hours"] = float(r.get("hours") or 0)
        r["pct_of_hourly"] = round(float(r.get("pct_of_hourly") or 0), 2)
    hourly_ct_rows = _with_totals(hourly_ct_rows, "hours", ["pct_of_hourly"], label_key="category")

    header_suffix = f" – {region} Region" if region else ""

    context = {
        "customer_code": customer_code,
        "customer_name": t.get("customer_name") or "",
        "header_suffix": header_suffix,
        "start_date": start_date,
        "end_date": end_date,
        "report_ts": report_ts,
        "total_hours": f"{total_hours:,.2f}",
        "nbot_hours": f"{nbot_hours:,.2f}",
        "billable_ot_hours": f"{billable_ot_hours:,.2f}",
        "total_ot_hours": f"{total_ot_hours:,.2f}",
        "nbot_pct": nbot_pct,
        "billable_ot_pct": billable_ot_pct,
        "total_ot_pct": total_ot_pct,
        "regular_hours": f"{regular_hours:,.2f}",
        "regular_pct": f"{regular_pct:.1f}",
        "site_count": len(site_rows),
        "sites": site_rows,
        "ot_breakdown_rows": ot_breakdown_rows,
        "customer_health_status": customer_health_status,
        "nbot_status_color": nbot_status_color,
        "nbot_status_text": nbot_status_text,
        "sites_with_ot": sites_with_ot,
        "sites_with_ot_pct": sites_with_ot_pct,
        "ot_breakdown": ot_breakdown,
        "risk_flags": risk_flags,
        "recommendations": recommendations,
        # Unpaid & Sick for metrics
        "unpaid_time_off_hours_total": f"{unpaid_time_off_hours_total:,.2f}",
        "unpaid_pct_total": unpaid_pct_total,
        "sick_hours_total": f"{sick_hours_total:,.2f}",
        "sick_pct_total": sick_pct_total,
        # Pay type & hourly distributions
        "total_counter_hours_all": f"{total_counter_hours_all:,.2f}",
        "hourly_hours_total": f"{hourly_hours_total:,.2f}",
        "salaried_hours_total": f"{salaried_hours_total:,.2f}",
        "unknown_hours_total": f"{unknown_hours_total:,.2f}",
        "hourly_pct": hourly_pct,
        "salaried_pct": salaried_pct,
        "unknown_pct": unknown_pct,
        "hourly_ct_rows": hourly_ct_rows,
        # OT/Billable/NBOT compositions
        "ot_comp_rows": ot_comp_rows,
        "billable_rows": billable_rows,
        "nbot_rows": nbot_rows,
        # 1099 additions
        "contractor_1099_hours_total": f"{contractor_1099_hours_total:,.2f}",
        "contractor_1099_pct": contractor_1099_pct,
    }

    template = Template("""# 🌐 Excellence Performance Center 🌐
## NBOT Customer Analysis – {{ customer_name }} ({{ customer_code }}){{ header_suffix }}
**Period:** {{ start_date }} – {{ end_date }} | **Report Date:** {{ report_ts }}

---

## 📋 Executive Summary

**Customer Health:** {{ customer_health_status }}

### Key Findings
- **NBOT Performance:** {{ "%.2f"|format(nbot_pct) }}% ({{ nbot_status_color }}) — {{ nbot_status_text }}
- **Billable OT:** {{ "%.2f"|format(billable_ot_pct) }}% | **Total OT:** {{ "%.2f"|format(total_ot_pct) }}%
- **Sites with OT:** {{ sites_with_ot }} of {{ site_count }} sites ({{ "%.1f"|format(sites_with_ot_pct) }}%)
- **Total Hours Worked:** {{ total_hours }} hours across {{ site_count }} locations
- **NBOT Hours:** {{ nbot_hours }} hours | **Billable OT Hours:** {{ billable_ot_hours }} hours

**NBOT Thresholds:** 🟢 GREEN < 3% · 🟡 YELLOW 3–5% · 🔴 RED > 5%

{% if risk_flags and risk_flags|length > 0 -%}
### ⚠️ Risk Indicators
{% for flag in risk_flags -%}
- {{ flag }}
{% endfor -%}
{% endif %}

{% if recommendations and recommendations|length > 0 -%}
### 💡 Recommendations
{% for rec in recommendations -%}
- {{ rec }}
{% endfor -%}
{% endif %}

---

## 📊 Customer Key Metrics
| Metric | Value |
|:--|--:|
| Total Hours Worked | {{ total_hours }} |
| Total Sites | {{ site_count }} |
| NBOT Hours | {{ nbot_hours }} |
| NBOT % | {{ "%.2f"|format(nbot_pct) }}% |
| Billable OT Hours | {{ billable_ot_hours }} |
| Billable OT % | {{ "%.2f"|format(billable_ot_pct) }}% |
| **Unpaid Time Off Hours** | **{{ unpaid_time_off_hours_total }}** |
| **Unpaid Time Off %** | **{{ "%.2f"|format(unpaid_pct_total) }}%** |
| **Sick Hours** | **{{ sick_hours_total }}** |
| **Sick %** | **{{ "%.2f"|format(sick_pct_total) }}%** |
| Total OT Hours | {{ total_ot_hours }} |
| Total OT % | {{ "%.2f"|format(total_ot_pct) }}% |

---

## 🧮 Total Hours | Pay Type Breakdown
**Total Counter Hours (All counters):** {{ total_counter_hours_all }}

| Pay Type  | Hours | % of Total |
|:----------|------:|-----------:|
| Hourly    | {{ hourly_hours_total }} | {{ "%.2f"|format(hourly_pct) }}% |
| Salaried  | {{ salaried_hours_total }} | {{ "%.2f"|format(salaried_pct) }}% |
| 1099      | {{ contractor_1099_hours_total }} | {{ "%.2f"|format(contractor_1099_pct) }}% |
| **Total** | **{{ total_counter_hours_all }}** | **{{ "%.2f"|format(hourly_pct + salaried_pct + contractor_1099_pct) }}%** |

> **Note:** Only **Hourly** hours are used for OT/NBOT calculation and compliance exposure.

---

## 🧩 Hourly Worked Hours | by Counter Type
| Category | Hours | % of Hourly |
|:---------|------:|------------:|
{% for r in hourly_ct_rows -%}
| {{ r.category }} | {{ "%.2f"|format(r.hours or 0) }} | {{ "%.2f"|format(r.pct_of_hourly or 0) }}% |
{% endfor -%}

---

## 🔧 OT Composition (Hourly Only)
| OT Counter Type | OT Hours | % of OT |
|:----------------|---------:|--------:|
{% for r in ot_comp_rows -%}
| {{ r.ot_category }} | {{ "%.2f"|format(r.ot_hours or 0) }} | {{ "%.2f"|format(r.pct_of_ot or 0) }}% |
{% endfor -%}

---

## 💸 Billable OT (OT and Regular Hours Charged at Premium) — Hourly Only
| Counter Type | Billable Premium Hours | % of Premium |
|:-------------|-----------------------:|-------------:|
{% for r in billable_rows -%}
| {{ r.ot_category }} | {{ "%.2f"|format(r.billable_hours or 0) }} | {{ "%.2f"|format(r.pct_of_ot or 0) }}% |
{% endfor -%}

---

## 🚫 NBOT (Non-Billable Overtime) | by Counter Type
| OT Counter Type | NBOT Hours | % of OT | % of TWH |
|:----------------|-----------:|--------:|---------:|
{% for r in nbot_rows -%}
| {{ r.ot_category }} | {{ "%.2f"|format(r.nbot_hours or 0) }} | {{ "%.2f"|format(r.pct_of_ot or 0) }}% | {{ "%.2f"|format(r.pct_of_twh or 0) }}% |
{% endfor -%}

---

## 📅 HOURS BREAKDOWN BY CATEGORY

| Category | NBOT Hours | Billable OT | Total Hours | % of TWH | Visual Impact |
|:---------|----------:|------------:|------------:|---------:|:--------------|
| Regular (NON-OT) | — | — | — | {{ regular_pct }}% | ████████████████████ |
{% for row in ot_breakdown_rows -%}
| {{ row.ot_category }} | {{ "%.2f"|format(row.nbot_hours or 0) }} | {{ "%.2f"|format(row.billable_hours or 0) }} | {{ "%.2f"|format(row.total_ot_hours or 0) }} | {{ "%.2f"|format(row.total_ot_pct_of_twh or 0) }}% | {% if row.total_ot_pct_of_twh > 5 %}██████░░░░░░░░░░░░░░{% elif row.total_ot_pct_of_twh > 2 %}███░░░░░░░░░░░░░░░░░{% else %}█░░░░░░░░░░░░░░░░░░░{% endif %} |
{% endfor %}

{% if ot_breakdown and ot_breakdown|length > 0 -%}
**▶️ Key Insight:** {{ ot_breakdown[0].label }} represents {{ "%.1f"|format(ot_breakdown[0].pct_of_nbot) }}% of NBOT → Primary reduction target
{% endif %}

---

## 📈 Pareto – NBOT by Site
| Rank | Site | Region | State | Site Manager | Total Hours | NBOT Hours | NBOT % | Billable OT % | Cum NBOT % | Pareto 80% |
|---:|:--:|:--|:--:|:--|--:|--:|--:|--:|--:|:--:|
{% for s in sites -%}
| {{ s.nbot_rank }} | {{ s.location_number }} | {{ s.region }} | {{ s.state }} | {{ s.site_manager }} | {{ "%.2f"|format(s.total_hours or 0) }} | {{ "%.2f"|format(s.nbot_hours or 0) }} | {{ "%.2f"|format(s.nbot_pct or 0) }}% | {{ "%.2f"|format(s.billable_ot_pct or 0) }}% | {{ "%.2f"|format(s.nbot_cum_pct or 0) }}% | {% if s.pareto_80_flag == 'Yes' %}☑️{% endif %} |
{% endfor %}
""")
    return template.render(**context)


# ------------------------------------------------------------
# 4) NBOT Company by Region (Pareto)
# ------------------------------------------------------------

# ------------------------------------------------------------
# 4) NBOT Company by Region (Pareto)
# ------------------------------------------------------------

def _generate_nbot_company_by_region(
    start_date: str,
    end_date: str,
    project: str,
    dataset: str,
    compute_project: str
) -> str:
    if not all([start_date, end_date]):
        return "Missing required parameters: start_date, end_date"

    from jinja2 import Template
    from google.cloud import bigquery
    import datetime

    # Date-only report stamp
    report_ts = datetime.datetime.now().strftime("%Y-%m-%d")

    # ---------------------------
    # Regions Pareto
    # ---------------------------
    sql = f"""
WITH Base AS (
  SELECT
    COALESCE(NULLIF(TRIM(region), ''), 'Unassigned') AS region,
    LOWER(TRIM(counter_type)) AS counter_type,
    SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours,
    COALESCE(NULLIF(TRIM(is_billable_overtime), ''), 'UNKNOWN') AS is_billable_ot
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
),
Agg AS (
  SELECT
    region,
    SUM(counter_hours) AS total_hours,
    -- NBOT: Non-Billable OT only (confined to OT-like counters)
    SUM(
      CASE 
        WHEN (counter_type IN ('daily overtime','daily ot','weekly overtime','weekly ot','holiday worked')
              OR counter_type LIKE 'consecutive day ot%%'
              OR counter_type LIKE 'consecutive day dt%%'
              OR counter_type LIKE '%%double time%%'
              OR counter_type LIKE '%%overtime%%')
             AND is_billable_ot = 'NON-OT'
        THEN counter_hours ELSE 0 END
    ) AS nbot_hours,
    -- Billable OT (premium anywhere: OT AND regular)
    SUM(CASE WHEN is_billable_ot = 'OT' THEN counter_hours ELSE 0 END) AS billable_ot_hours
  FROM Base
  GROUP BY region
),
WithPct AS (
  SELECT
    region,
    total_hours, nbot_hours, billable_ot_hours,
    SAFE_DIVIDE(nbot_hours, total_hours) * 100 AS nbot_pct,
    SAFE_DIVIDE(billable_ot_hours, total_hours) * 100 AS billable_ot_pct,
    SAFE_DIVIDE(nbot_hours + billable_ot_hours, total_hours) * 100 AS total_ot_pct
  FROM Agg
),
WithPareto AS (
  SELECT
    *,
    RANK() OVER (ORDER BY nbot_hours DESC) AS nbot_rank,
    SUM(nbot_hours) OVER () AS nbot_total_all,
    SUM(nbot_hours) OVER (ORDER BY nbot_hours DESC
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS nbot_cum,
    SAFE_DIVIDE(
      SUM(nbot_hours) OVER (ORDER BY nbot_hours DESC
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW),
      SUM(nbot_hours) OVER ()
    ) * 100 AS nbot_cum_pct
  FROM WithPct
)
SELECT
  region, total_hours, nbot_hours, billable_ot_hours, nbot_pct, billable_ot_pct, total_ot_pct,
  nbot_rank, nbot_cum_pct,
  CASE WHEN nbot_cum_pct <= 80 THEN 'Yes' ELSE 'No' END AS pareto_80_flag
FROM WithPareto
ORDER BY nbot_hours DESC
"""

    # ---------------------------
    # Company Totals
    # ---------------------------
    totals_sql = f"""
WITH Base AS (
  SELECT
    LOWER(TRIM(counter_type)) AS counter_type,
    SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours,
    COALESCE(NULLIF(TRIM(is_billable_overtime), ''), 'UNKNOWN') AS is_billable_ot
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
)
SELECT
  SUM(counter_hours) AS total_hours,

  -- NBOT: Non-Billable OT only (confined to OT-like counters)
  SUM(
    CASE 
      WHEN (counter_type IN ('daily overtime','daily ot','weekly overtime','weekly ot','holiday worked')
            OR counter_type LIKE 'consecutive day ot%%'
            OR counter_type LIKE 'consecutive day dt%%'
            OR counter_type LIKE '%%double time%%'
            OR counter_type LIKE '%%overtime%%')
           AND is_billable_ot = 'NON-OT'
      THEN counter_hours ELSE 0 END
  ) AS nbot_hours,

  -- Billable OT (premium anywhere: OT AND regular)
  SUM(CASE WHEN is_billable_ot = 'OT' THEN counter_hours ELSE 0 END) AS billable_ot_hours,

  -- Unpaid Time Off + Sick totals
  SUM(CASE WHEN counter_type LIKE '%%unpaid time off%%' THEN counter_hours ELSE 0 END) AS unpaid_time_off_hours_total,
  SUM(CASE WHEN counter_type = 'sick' THEN counter_hours ELSE 0 END) AS sick_hours_total,

  -- Percentages (of total worked hours)
  SAFE_DIVIDE(
    SUM(
      CASE 
        WHEN (counter_type IN ('daily overtime','daily ot','weekly overtime','weekly ot','holiday worked')
              OR counter_type LIKE 'consecutive day ot%%'
              OR counter_type LIKE 'consecutive day dt%%'
              OR counter_type LIKE '%%double time%%'
              OR counter_type LIKE '%%overtime%%')
             AND is_billable_ot = 'NON-OT'
      THEN counter_hours ELSE 0 END),
    SUM(counter_hours)
  ) * 100 AS nbot_pct,

  SAFE_DIVIDE(
    SUM(CASE WHEN is_billable_ot = 'OT' THEN counter_hours ELSE 0 END),
    SUM(counter_hours)
  ) * 100 AS billable_ot_pct,

  SAFE_DIVIDE(
    SUM(CASE WHEN counter_type LIKE '%%unpaid time off%%' THEN counter_hours ELSE 0 END),
    SUM(counter_hours)
  ) * 100 AS unpaid_pct_total,

  SAFE_DIVIDE(
    SUM(CASE WHEN counter_type = 'sick' THEN counter_hours ELSE 0 END),
    SUM(counter_hours)
  ) * 100 AS sick_pct_total
FROM Base
"""

    # ---------------------------
    # OT breakdown
    # ---------------------------
    ot_breakdown_sql = f"""
WITH Base AS (
  SELECT
    LOWER(TRIM(counter_type)) AS counter_type,
    SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours,
    COALESCE(NULLIF(TRIM(is_billable_overtime), ''), 'UNKNOWN') AS is_billable_ot
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
)

-- Standard OT categories
SELECT
  CASE
    WHEN counter_type IN ('daily overtime','daily ot') THEN 'Daily Overtime'
    WHEN counter_type IN ('weekly overtime','weekly ot') THEN 'Weekly Overtime'
    WHEN counter_type LIKE '%%double time%%' THEN 'Daily Double Time'
    WHEN counter_type LIKE 'consecutive day ot%%' THEN 'Consecutive Day OT'
    WHEN counter_type LIKE 'consecutive day dt%%' THEN 'Consecutive Day DT'
    ELSE 'Other OT'
  END AS ot_category,
  SUM(CASE WHEN is_billable_ot = 'NON-OT' THEN counter_hours ELSE 0 END) AS nbot_hours,
  SUM(CASE WHEN is_billable_ot = 'OT' THEN counter_hours ELSE 0 END) AS billable_hours,
  SUM(counter_hours) AS total_ot_hours
FROM Base
WHERE (counter_type IN ('daily overtime','daily ot','weekly overtime','weekly ot')
       OR counter_type LIKE 'consecutive day ot%%'
       OR counter_type LIKE 'consecutive day dt%%'
       OR counter_type LIKE '%%double time%%'
       OR counter_type LIKE '%%overtime%%')
GROUP BY ot_category

UNION ALL
-- Unpaid Time Off Request (as its own row)
SELECT
  'Unpaid Time Off Request' AS ot_category,
  0 AS nbot_hours,
  0 AS billable_hours,
  SUM(CASE WHEN counter_type LIKE '%%unpaid time off%%' THEN counter_hours ELSE 0 END) AS total_ot_hours
FROM Base
WHERE counter_type LIKE '%%unpaid time off%%'

UNION ALL
-- Sick (as its own row)
SELECT
  'Sick' AS ot_category,
  0 AS nbot_hours,
  0 AS billable_hours,
  SUM(CASE WHEN counter_type = 'sick' THEN counter_hours ELSE 0 END) AS total_ot_hours
FROM Base
WHERE counter_type = 'sick'
ORDER BY total_ot_hours DESC
"""

    # ---------------------------
    # Pay type totals
    # ---------------------------
    pay_type_totals_sql = f"""
WITH Base AS (
  SELECT
    SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours,
    LOWER(TRIM(counter_type)) AS counter_type,
    LOWER(TRIM(COALESCE(CAST(pay_type AS STRING), ''))) AS pay_type_raw
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
),
Norm AS (
  SELECT
    counter_hours,
    counter_type,
    CASE
      WHEN pay_type_raw IN ('hourly','h','non-exempt','nonexempt') THEN 'Hourly'
      WHEN pay_type_raw IN ('salaried','salary','exempt')          THEN 'Salaried'
      WHEN pay_type_raw IN ('1099','contractor','independent','ic') THEN '1099'
      ELSE 'Unknown'
    END AS pay_type
  FROM Base
),
Agg AS (
  SELECT
    SUM(counter_hours) AS total_counter_hours,
    SUM(CASE WHEN pay_type = 'Hourly'   THEN counter_hours ELSE 0 END) AS hourly_hours,
    SUM(CASE WHEN pay_type = 'Salaried' THEN counter_hours ELSE 0 END) AS salaried_hours,
    SUM(CASE WHEN pay_type = '1099'     THEN counter_hours ELSE 0 END) AS contractor_1099_hours,
    SUM(CASE WHEN pay_type = 'Unknown'  THEN counter_hours ELSE 0 END) AS unknown_hours
  FROM Norm
)
SELECT
  total_counter_hours,
  hourly_hours,
  salaried_hours,
  contractor_1099_hours,
  unknown_hours,
  SAFE_DIVIDE(hourly_hours,   total_counter_hours) * 100 AS hourly_pct,
  SAFE_DIVIDE(salaried_hours, total_counter_hours) * 100 AS salaried_pct,
  SAFE_DIVIDE(contractor_1099_hours, total_counter_hours) * 100 AS contractor_1099_pct,
  SAFE_DIVIDE(unknown_hours,  total_counter_hours) * 100 AS unknown_pct
FROM Agg
"""

    # ---------------------------
    # Hourly-only breakdown by counter type
    # ---------------------------
    hourly_ct_breakdown_sql = f"""
WITH Base AS (
  SELECT
    SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours,
    LOWER(TRIM(counter_type)) AS counter_type,
    LOWER(TRIM(COALESCE(CAST(pay_type AS STRING), ''))) AS pay_type_raw
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
),
Hourly AS (
  SELECT counter_type, counter_hours
  FROM Base
  WHERE pay_type_raw IN ('hourly','h','non-exempt','nonexempt')
),
Agg AS (
  SELECT
    CASE
      WHEN counter_type IN ('daily overtime','daily ot')     THEN 'Daily Overtime'
      WHEN counter_type IN ('weekly overtime','weekly ot')   THEN 'Weekly Overtime'
      WHEN counter_type LIKE '%%double time%%'               THEN 'Daily Double Time'
      WHEN counter_type = 'holiday worked'                   THEN 'Holiday Worked'
      WHEN counter_type LIKE 'consecutive day ot%%'          THEN 'Consecutive Day OT'
      WHEN counter_type LIKE 'consecutive day dt%%'          THEN 'Consecutive Day DT'
      WHEN counter_type LIKE '%%unpaid time off%%'           THEN 'Unpaid Time Off'
      WHEN counter_type = 'sick'                             THEN 'Sick'
      ELSE 'Regular / Other'
    END AS category,
    SUM(counter_hours) AS hours
  FROM Hourly
  GROUP BY category
),
Total AS ( SELECT SUM(hours) AS total_hourly_worked FROM Agg )
SELECT
  category,
  hours,
  SAFE_DIVIDE(hours, (SELECT total_hourly_worked FROM Total)) * 100 AS pct_of_hourly
FROM Agg
ORDER BY hours DESC
"""

    # ---------------------------
    # OT Composition (Hourly only, OT-like counters)
    # ---------------------------
    ot_composition_sql = f"""
WITH Base AS (
  SELECT
    SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours,
    LOWER(TRIM(counter_type)) AS counter_type,
    LOWER(TRIM(COALESCE(CAST(pay_type AS STRING), ''))) AS pay_type_raw,
    COALESCE(NULLIF(TRIM(is_billable_overtime), ''), 'UNKNOWN') AS is_billable_ot
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
),
HourlyOT AS (
  SELECT counter_hours, counter_type, is_billable_ot
  FROM Base
  WHERE pay_type_raw IN ('hourly','h','non-exempt','nonexempt')
    AND (counter_type IN ('daily overtime','daily ot','weekly overtime','weekly ot')
         OR counter_type LIKE 'consecutive day ot%%'
         OR counter_type LIKE 'consecutive day dt%%'
         OR counter_type LIKE '%%double time%%'
         OR counter_type LIKE '%%overtime%%')
),
Agg AS (
  SELECT
    CASE
      WHEN counter_type IN ('daily overtime','daily ot') THEN 'Daily Overtime'
      WHEN counter_type IN ('weekly overtime','weekly ot') THEN 'Weekly Overtime'
      WHEN counter_type LIKE '%%double time%%' THEN 'Daily Double Time'
      WHEN counter_type LIKE 'consecutive day ot%%' THEN 'Consecutive Day OT'
      WHEN counter_type LIKE 'consecutive day dt%%' THEN 'Consecutive Day DT'
      ELSE 'Other OT'
    END AS ot_category,
    SUM(counter_hours) AS ot_hours
  FROM HourlyOT
  GROUP BY ot_category
),
Total AS ( SELECT SUM(ot_hours) AS total_ot FROM Agg )
SELECT
  ot_category,
  ot_hours,
  SAFE_DIVIDE(ot_hours, (SELECT total_ot FROM Total)) * 100 AS pct_of_ot
FROM Agg
ORDER BY ot_hours DESC
"""

    # ---------------------------
    # Billable OT by type (Hourly-only; premium anywhere, includes Regular/Other)
    # ---------------------------
    billable_ot_sql = f"""
WITH Base AS (
  SELECT
    SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours,
    LOWER(TRIM(counter_type)) AS counter_type,
    LOWER(TRIM(COALESCE(CAST(pay_type AS STRING), ''))) AS pay_type_raw,
    COALESCE(NULLIF(TRIM(is_billable_overtime), ''), 'UNKNOWN') AS is_billable_ot
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
),
Billable AS (
  SELECT
    CASE
      WHEN counter_type IN ('daily overtime','daily ot')   THEN 'Daily Overtime'
      WHEN counter_type IN ('weekly overtime','weekly ot') THEN 'Weekly Overtime'
      WHEN counter_type LIKE '%%double time%%'             THEN 'Daily Double Time'
      WHEN counter_type = 'holiday worked'                 THEN 'Holiday Worked'
      WHEN counter_type LIKE 'consecutive day ot%%'        THEN 'Consecutive Day OT'
      WHEN counter_type LIKE 'consecutive day dt%%'        THEN 'Consecutive Day DT'
      WHEN counter_type LIKE '%%unpaid time off%%'         THEN 'Unpaid Time Off'
      WHEN counter_type = 'sick'                           THEN 'Sick'
      ELSE 'Regular / Other'
    END AS ot_category,
    SUM(counter_hours) AS billable_hours
  FROM Base
  WHERE pay_type_raw IN ('hourly','h','non-exempt','nonexempt')
    AND is_billable_ot = 'OT'    -- premium anywhere (includes regular)
  GROUP BY ot_category
),
Total AS ( SELECT SUM(billable_hours) AS total_billable_ot FROM Billable )
SELECT
  ot_category,
  billable_hours,
  SAFE_DIVIDE(billable_hours, (SELECT total_billable_ot FROM Total)) * 100 AS pct_of_ot
FROM Billable
ORDER BY billable_hours DESC
"""

    # ---- Execute queries
    try:
        client = bigquery.Client(project=compute_project)
        rows = client.query(sql).to_dataframe().to_dict(orient="records")
        totals = client.query(totals_sql).to_dataframe().to_dict(orient="records")[0]
        ot_breakdown_rows = client.query(ot_breakdown_sql).to_dataframe().to_dict(orient="records")
        pay_type_totals = client.query(pay_type_totals_sql).to_dataframe().to_dict(orient="records")
        hourly_ct_rows  = client.query(hourly_ct_breakdown_sql).to_dataframe().to_dict(orient="records")
        ot_comp_rows    = client.query(ot_composition_sql).to_dataframe().to_dict(orient="records")
        billable_rows   = client.query(billable_ot_sql).to_dataframe().to_dict(orient="records")
    except Exception as e:
        return (
            f"Query failed: {str(e)}\n\n"
            f"SQL:\n{sql}\n\nTOTALS_SQL:\n{totals_sql}\n\n"
            f"OT_BREAKDOWN_SQL:\n{ot_breakdown_sql}\n\nPAY_TYPE_TOTALS_SQL:\n{pay_type_totals_sql}\n\n"
            f"HOURLY_CT_BREAKDOWN_SQL:\n{hourly_ct_breakdown_sql}\n\nOT_COMPOSITION_SQL:\n{ot_composition_sql}\n\n"
            f"BILLABLE_OT_SQL:\n{billable_ot_sql}"
        )

    total_hours = float(totals.get('total_hours') or 0)
    nbot_hours = float(totals.get('nbot_hours') or 0)
    billable_ot_hours = float(totals.get('billable_ot_hours') or 0)
    total_ot_hours = nbot_hours + billable_ot_hours

    # Unpaid & Sick totals
    unpaid_time_off_hours_total = float(totals.get('unpaid_time_off_hours_total') or 0)
    sick_hours_total = float(totals.get('sick_hours_total') or 0)
    unpaid_pct_total = round(float(totals.get('unpaid_pct_total') or 0), 2)
    sick_pct_total = round(float(totals.get('sick_pct_total') or 0), 2)

    nbot_pct = round(float(totals.get('nbot_pct') or 0), 2)
    billable_ot_pct = round(float(totals.get('billable_ot_pct') or 0), 2)
    total_ot_pct = round((total_ot_hours / total_hours * 100) if total_hours else 0, 2)

    # Regular hours
    regular_hours = total_hours - total_ot_hours
    regular_pct = round((regular_hours / total_hours * 100) if total_hours else 0, 1)

    # Add % of TWH to each OT breakdown row
    for r in ot_breakdown_rows:
        r["nbot_pct_of_twh"] = round((float(r.get("nbot_hours", 0)) / total_hours * 100) if total_hours else 0, 2)
        r["billable_pct_of_twh"] = round((float(r.get("billable_hours", 0)) / total_hours * 100) if total_hours else 0, 2)
        r["total_ot_pct_of_twh"] = round((float(r.get("total_ot_hours", 0)) / total_hours * 100) if total_hours else 0, 2)

    # Executive summary health
    if nbot_pct < 3:
        nbot_status_color = "🟢"; nbot_status_text = "Excellent — Under target"
    elif 3 <= nbot_pct <= 5:
        nbot_status_color = "🟡"; nbot_status_text = "Acceptable — Monitor closely"
    else:
        nbot_status_color = "🔴"; nbot_status_text = "Critical — Immediate action required"

    critical_regions = sum(1 for r in rows if r.get("nbot_pct", 0) > 5)
    if nbot_pct > 5 or (len(rows) > 0 and critical_regions > len(rows) * 0.4):
        company_health_status = "🔴 Needs Attention"
    elif nbot_pct > 3 or (len(rows) > 0 and critical_regions > len(rows) * 0.2):
        company_health_status = "🟡 Monitor"
    else:
        company_health_status = "🟢 Healthy"

    regions_with_ot = sum(1 for r in rows if (r.get("nbot_hours", 0) + r.get("billable_ot_hours", 0)) > 0)
    regions_with_ot_pct = round((regions_with_ot / len(rows) * 100) if rows else 0, 1)

    # Key Insight support list
    ot_breakdown = []
    if nbot_hours > 0:
        for r in ot_breakdown_rows:
            if r.get("nbot_hours", 0) > 0:
                pct_of_nbot = round((float(r["nbot_hours"]) / nbot_hours * 100), 1)
                ot_breakdown.append({"label": r["ot_category"], "pct_of_nbot": pct_of_nbot})

    pareto_regions = [r for r in rows if r.get('pareto_80_flag') == 'Yes']

    # Risk flags
    risk_flags = []
    if nbot_pct > 5:
        risk_flags.append(f"🔴 High Company-Wide NBOT ({nbot_pct:.1f}%) — Exceeds 5% threshold")
    if len(rows) > 0 and critical_regions > len(rows) * 0.3:
        risk_flags.append(f"🟠 Multiple Critical Regions — {critical_regions} of {len(rows)} regions exceed 5% NBOT")
    
    top_regions = sorted(rows, key=lambda x: float(x.get("nbot_pct", 0)), reverse=True)[:3]
    if top_regions and top_regions[0].get("nbot_pct", 0) > 10:
        risk_flags.append(f"⚠️ Severe Regional Issue — {top_regions[0]['region']} at {top_regions[0].get('nbot_pct', 0):.1f}% NBOT")
    
    if len(pareto_regions) > 0 and len(rows) > 0:
        concentration_pct = round((len(pareto_regions) / len(rows) * 100), 1)
        if concentration_pct < 40:
            risk_flags.append(f"📊 High Concentration — {len(pareto_regions)} regions ({concentration_pct}%) account for 80% of company NBOT")

    # Recommendations
    recommendations = []
    if nbot_pct > 5 and len(ot_breakdown_rows) > 0:
        top_ot = max(ot_breakdown_rows, key=lambda x: float(x.get("nbot_hours", 0)))
        if top_ot.get("nbot_hours", 0) > 0:
            recommendations.append(
                f"**Company-Wide Initiative: Reduce {top_ot['ot_category']}** (NBOT) — Accounts for "
                f"{top_ot.get('nbot_pct_of_twh', 0):.2f}% of total company hours"
            )

    if len(pareto_regions) > 0:
        pareto_nbot = sum(float(r.get('nbot_hours', 0)) for r in pareto_regions)
        top_3_pareto = [r['region'] for r in pareto_regions[:3]]
        recommendations.append(
            f"**Pareto Strategy** — {len(pareto_regions)} regions drive 80% of company NBOT ({pareto_nbot:,.0f} hours). "
            f"Focus efforts on: {', '.join(top_3_pareto)}"
        )

    if critical_regions > 0:
        top_3_regions = [r['region'] for r in top_regions[:3] if r.get('nbot_pct', 0) > 5]
        if top_3_regions:
            recommendations.append(
                f"**Regional Focus** — Deploy resources to high-NBOT regions: {', '.join(top_3_regions)}"
            )

    if len(rows) > 3 and critical_regions > 2:
        recommendations.append(
            "**Enterprise Policy Review** — Widespread regional NBOT issues suggest systemic "
            "operational challenges. Recommend company-wide scheduling and staffing policy review."
        )

    low_nbot_regions = [r for r in rows if r.get('nbot_pct', 0) < 3]
    if len(low_nbot_regions) > 0 and critical_regions > 0:
        best_region = min(rows, key=lambda x: float(x.get("nbot_pct", 0)))
        recommendations.append(
            f"**Best Practice Sharing** — {best_region['region']} maintains {best_region.get('nbot_pct', 0):.1f}% NBOT. "
            f"Document and share their operational practices with high-NBOT regions."
        )

    if not recommendations:
        recommendations.append("✅ Company is performing well across all regions — Continue current practices")

    # Helper: add totals rows
    def _with_totals(rows, hours_key, pct_keys=None, label_key=None, total_label="Total"):
        out = [dict(r) for r in rows] if rows else []
        total_row = {}
        total_val = round(sum(float(r.get(hours_key, 0) or 0) for r in rows), 2) if rows else 0.0
        if rows:
            for k in rows[0].keys():
                total_row[k] = ""
            lk = label_key or (rows and list(rows[0].keys())[0]) or "category"
            total_row[lk] = total_label
        total_row[hours_key] = total_val
        if pct_keys:
            for pk in pct_keys:
                total_row[pk] = round(sum(float(r.get(pk, 0) or 0) for r in rows), 2)
        out.append(total_row)
        return out

    # Build OT/Billable/NBOT tables with totals
    total_ot_from_comp = sum(float(r.get("ot_hours", 0) or 0) for r in ot_comp_rows) if ot_comp_rows else 0.0
    for r in (ot_comp_rows or []):
        r["ot_hours"] = float(r.get("ot_hours") or 0)
        r["pct_of_ot"] = round(float(r.get("pct_of_ot") or 0), 2)
    ot_comp_rows = _with_totals(ot_comp_rows, "ot_hours", ["pct_of_ot"], label_key="ot_category")

    for r in (billable_rows or []):
        r["billable_hours"] = float(r.get("billable_hours") or 0)
        r["pct_of_ot"] = round(float(r.get("pct_of_ot") or 0), 2)
    billable_rows = _with_totals(billable_rows, "billable_hours", ["pct_of_ot"], label_key="ot_category")

    # CRITICAL: NBOT = Total OT (hourly) – ALL Billable Hours (including Regular/Other)
    # Calculate total billable including Regular/Other premium
    total_billable_all_sources = sum(float(r.get("billable_hours") or 0) for r in (billable_rows[:-1] if billable_rows else []))

    # Build bill_map for OT categories only
    bill_map = {r.get("ot_category"): float(r.get("billable_hours") or 0) for r in (billable_rows[:-1] if billable_rows else [])}

    # Calculate billable from OT categories only (excludes Regular/Other)
    billable_from_ot_categories = sum(bill_map.get(r.get("ot_category"), 0.0) for r in (ot_comp_rows[:-1] if ot_comp_rows else []))

    # Unmatched billable (e.g., Regular/Other premium not in OT categories)
    unmatched_billable = total_billable_all_sources - billable_from_ot_categories

    # Calculate per-category NBOT
    nbot_rows = []
    for r in (ot_comp_rows[:-1] if ot_comp_rows else []):
        cat = r.get("ot_category")
        ot_h = float(r.get("ot_hours") or 0)
        bill_h = bill_map.get(cat, 0.0)
        nbot_h = max(ot_h - bill_h, 0.0)
        nbot_rows.append({
            "ot_category": cat,
            "nbot_hours": nbot_h,
            "pct_of_ot": round((nbot_h / total_ot_from_comp * 100) if total_ot_from_comp else 0.0, 2),
            "pct_of_twh": round((nbot_h / total_hours * 100) if total_hours else 0.0, 2),
        })

    # Handle unmatched billable hours (Regular/Other premium)
    # Subtract from the largest NBOT category to reconcile the total
    if unmatched_billable > 0 and nbot_rows:
        # Find category with largest NBOT
        max_idx = max(range(len(nbot_rows)), key=lambda i: nbot_rows[i]["nbot_hours"])
        nbot_rows[max_idx]["nbot_hours"] = max(nbot_rows[max_idx]["nbot_hours"] - unmatched_billable, 0.0)
        
        # Recalculate percentages after adjustment
        for r in nbot_rows:
            r["pct_of_ot"] = round((r["nbot_hours"] / total_ot_from_comp * 100) if total_ot_from_comp else 0.0, 2)
            r["pct_of_twh"] = round((r["nbot_hours"] / total_hours * 100) if total_hours else 0.0, 2)

    # Add totals row
    nbot_rows = _with_totals(nbot_rows, "nbot_hours", ["pct_of_ot","pct_of_twh"], label_key="ot_category")

    # Pay type unpack (Unknown kept for math, hidden in table)
    pt = pay_type_totals[0] if pay_type_totals else {}
    total_counter_hours_all     = float(pt.get("total_counter_hours") or 0.0)
    hourly_hours_total          = float(pt.get("hourly_hours") or 0.0)
    salaried_hours_total        = float(pt.get("salaried_hours") or 0.0)
    contractor_1099_hours_total = float(pt.get("contractor_1099_hours") or 0.0)
    unknown_hours_total         = float(pt.get("unknown_hours") or 0.0)

    hourly_pct          = round(float(pt.get("hourly_pct") or 0.0), 2)
    salaried_pct        = round(float(pt.get("salaried_pct") or 0.0), 2)
    contractor_1099_pct = round(float(pt.get("contractor_1099_pct") or 0.0), 2)
    unknown_pct         = round(float(pt.get("unknown_pct") or 0.0), 2)

    for r in (hourly_ct_rows or []):
        r["hours"] = float(r.get("hours") or 0)
        r["pct_of_hourly"] = round(float(r.get("pct_of_hourly") or 0), 2)
    hourly_ct_rows = _with_totals(hourly_ct_rows, "hours", ["pct_of_hourly"], label_key="category")

    context = {
        "start_date": start_date,
        "end_date": end_date,
        "report_ts": report_ts,
        "total_hours": f"{total_hours:,.2f}",
        "nbot_hours": f"{nbot_hours:,.2f}",
        "billable_ot_hours": f"{billable_ot_hours:,.2f}",
        "total_ot_hours": f"{total_ot_hours:,.2f}",
        "nbot_pct": nbot_pct,
        "billable_ot_pct": billable_ot_pct,
        "total_ot_pct": total_ot_pct,
        "regular_hours": f"{regular_hours:,.2f}",
        "regular_pct": f"{regular_pct:.1f}",
        "region_count": len(rows),
        "regions": rows,
        "ot_breakdown_rows": ot_breakdown_rows,
        "company_health_status": company_health_status,
        "nbot_status_color": nbot_status_color,
        "nbot_status_text": nbot_status_text,
        "regions_with_ot": regions_with_ot,
        "regions_with_ot_pct": regions_with_ot_pct,
        "ot_breakdown": ot_breakdown,
        "risk_flags": risk_flags,
        "recommendations": recommendations,
        # Unpaid & Sick for metrics
        "unpaid_time_off_hours_total": f"{unpaid_time_off_hours_total:,.2f}",
        "unpaid_pct_total": unpaid_pct_total,
        "sick_hours_total": f"{sick_hours_total:,.2f}",
        "sick_pct_total": sick_pct_total,
        # Pay type & hourly distributions
        "total_counter_hours_all": f"{total_counter_hours_all:,.2f}",
        "hourly_hours_total": f"{hourly_hours_total:,.2f}",
        "salaried_hours_total": f"{salaried_hours_total:,.2f}",
        "unknown_hours_total": f"{unknown_hours_total:,.2f}",
        "hourly_pct": hourly_pct,
        "salaried_pct": salaried_pct,
        "unknown_pct": unknown_pct,
        "hourly_ct_rows": hourly_ct_rows,
        # OT/Billable/NBOT compositions
        "ot_comp_rows": ot_comp_rows,
        "billable_rows": billable_rows,
        "nbot_rows": nbot_rows,
        # 1099 additions
        "contractor_1099_hours_total": f"{contractor_1099_hours_total:,.2f}",
        "contractor_1099_pct": contractor_1099_pct,
    }

    template = Template("""# 🌐 Excellence Performance Center 🌐
## NBOT Company Analysis – By Region
**Period:** {{ start_date }} – {{ end_date }} | **Report Date:** {{ report_ts }}

---

## 📋 Executive Summary

**Company Health:** {{ company_health_status }}

### Key Findings
- **NBOT Performance:** {{ "%.2f"|format(nbot_pct) }}% ({{ nbot_status_color }}) — {{ nbot_status_text }}
- **Billable OT:** {{ "%.2f"|format(billable_ot_pct) }}% | **Total OT:** {{ "%.2f"|format(total_ot_pct) }}%
- **Regions with OT:** {{ regions_with_ot }} of {{ region_count }} regions ({{ "%.1f"|format(regions_with_ot_pct) }}%)
- **Total Hours Worked:** {{ total_hours }} hours across {{ region_count }} regions
- **NBOT Hours:** {{ nbot_hours }} hours | **Billable OT Hours:** {{ billable_ot_hours }} hours

**NBOT Thresholds:** 🟢 GREEN < 3% · 🟡 YELLOW 3–5% · 🔴 RED > 5%

{% if risk_flags and risk_flags|length > 0 -%}
### ⚠️ Risk Indicators
{% for flag in risk_flags -%}
- {{ flag }}
{% endfor -%}
{% endif %}

{% if recommendations and recommendations|length > 0 -%}
### 💡 Recommendations
{% for rec in recommendations -%}
- {{ rec }}
{% endfor -%}
{% endif %}

---

## 📊 Company Key Metrics
| Metric | Value |
|:--|--:|
| Total Hours Worked | {{ total_hours }} |
| Total Regions | {{ region_count }} |
| NBOT Hours | {{ nbot_hours }} |
| NBOT % | {{ "%.2f"|format(nbot_pct) }}% |
| Billable OT Hours | {{ billable_ot_hours }} |
| Billable OT % | {{ "%.2f"|format(billable_ot_pct) }}% |
| **Unpaid Time Off Hours** | **{{ unpaid_time_off_hours_total }}** |
| **Unpaid Time Off %** | **{{ "%.2f"|format(unpaid_pct_total) }}%** |
| **Sick Hours** | **{{ sick_hours_total }}** |
| **Sick %** | **{{ "%.2f"|format(sick_pct_total) }}%** |
| Total OT Hours | {{ total_ot_hours }} |
| Total OT % | {{ "%.2f"|format(total_ot_pct) }}% |

---

## 🧮 Total Hours | Pay Type Breakdown
**Total Counter Hours (All counters):** {{ total_counter_hours_all }}

| Pay Type  | Hours | % of Total |
|:----------|------:|-----------:|
| Hourly    | {{ hourly_hours_total }} | {{ "%.2f"|format(hourly_pct) }}% |
| Salaried  | {{ salaried_hours_total }} | {{ "%.2f"|format(salaried_pct) }}% |
| 1099      | {{ contractor_1099_hours_total }} | {{ "%.2f"|format(contractor_1099_pct) }}% |
| **Total** | **{{ total_counter_hours_all }}** | **{{ "%.2f"|format(hourly_pct + salaried_pct + contractor_1099_pct) }}%** |

> **Note:** Only **Hourly** hours are used for OT/NBOT calculation and compliance exposure.

---

## 🧩 Hourly Worked Hours | by Counter Type
| Category | Hours | % of Hourly |
|:---------|------:|------------:|
{% for r in hourly_ct_rows -%}
| {{ r.category }} | {{ "%.2f"|format(r.hours or 0) }} | {{ "%.2f"|format(r.pct_of_hourly or 0) }}% |
{% endfor -%}

---

## 🔧 OT Composition (Hourly Only)
| OT Counter Type | OT Hours | % of OT |
|:----------------|---------:|--------:|
{% for r in ot_comp_rows -%}
| {{ r.ot_category }} | {{ "%.2f"|format(r.ot_hours or 0) }} | {{ "%.2f"|format(r.pct_of_ot or 0) }}% |
{% endfor -%}

---

## 💸 Billable OT (OT and Regular Hours Charged at Premium) — Hourly Only
| Counter Type | Billable Premium Hours | % of Premium |
|:-------------|-----------------------:|-------------:|
{% for r in billable_rows -%}
| {{ r.ot_category }} | {{ "%.2f"|format(r.billable_hours or 0) }} | {{ "%.2f"|format(r.pct_of_ot or 0) }}% |
{% endfor -%}

---

## 🚫 NBOT (Non-Billable Overtime) | by Counter Type
| OT Counter Type | NBOT Hours | % of OT | % of TWH |
|:----------------|-----------:|--------:|---------:|
{% for r in nbot_rows -%}
| {{ r.ot_category }} | {{ "%.2f"|format(r.nbot_hours or 0) }} | {{ "%.2f"|format(r.pct_of_ot or 0) }}% | {{ "%.2f"|format(r.pct_of_twh or 0) }}% |
{% endfor -%}

---

## 📅 HOURS BREAKDOWN BY CATEGORY

| Category | NBOT Hours | Billable OT | Total Hours | % of TWH | Visual Impact |
|:---------|----------:|------------:|------------:|---------:|:--------------|
| Regular (NON-OT) | — | — | — | {{ regular_pct }}% | ████████████████████ |
{% for row in ot_breakdown_rows -%}
| {{ row.ot_category }} | {{ "%.2f"|format(row.nbot_hours or 0) }} | {{ "%.2f"|format(row.billable_hours or 0) }} | {{ "%.2f"|format(row.total_ot_hours or 0) }} | {{ "%.2f"|format(row.total_ot_pct_of_twh or 0) }}% | {% if row.total_ot_pct_of_twh > 5 %}██████░░░░░░░░░░░░░░{% elif row.total_ot_pct_of_twh > 2 %}███░░░░░░░░░░░░░░░░░{% else %}█░░░░░░░░░░░░░░░░░░░{% endif %} |
{% endfor %}

{% if ot_breakdown and ot_breakdown|length > 0 -%}
**▶️ Key Insight:** {{ ot_breakdown[0].label }} represents {{ "%.1f"|format(ot_breakdown[0].pct_of_nbot) }}% of NBOT → Primary reduction target
{% endif %}

---

## 📍 Regional Breakdown (Pareto on NBOT)
| Rank | Region | Total Hours | NBOT Hours | NBOT % | Billable OT % | Cum NBOT % | Pareto 80% |
|---:|:--|--:|--:|--:|--:|--:|:--:|
{% for r in regions -%}
| {{ r.nbot_rank }} | {{ r.region }} | {{ "%.2f"|format(r.total_hours or 0) }} | {{ "%.2f"|format(r.nbot_hours or 0) }} | {{ "%.2f"|format(r.nbot_pct or 0) }}% | {{ "%.2f"|format(r.billable_ot_pct or 0) }}% | {{ "%.2f"|format(r.nbot_cum_pct or 0) }}% | {% if r.pareto_80_flag == 'Yes' %}☑️{% endif %} |
{% endfor %}
""")
    return template.render(**context)

# ------------------------------------------------------------
# 5) NBOT Company by Customer (Pareto)
# ------------------------------------------------------------


def _generate_nbot_company_by_customer(
    start_date: str,
    end_date: str,
    project: str,
    dataset: str,
    compute_project: str
) -> str:
    if not all([start_date, end_date]):
        return "Missing required parameters: start_date, end_date"

    sql = f"""
WITH Base AS (
  SELECT
    customer_code,
    COALESCE(NULLIF(TRIM(customer_name), ''), 'Unassigned') AS customer_name,
    counter_type,
    SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours,
    COALESCE(NULLIF(TRIM(is_billable_overtime), ''), 'UNKNOWN') AS is_billable_ot
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
),
Agg AS (
  SELECT
    customer_code, customer_name,
    SUM(counter_hours) AS total_hours,
    -- NBOT: Non-Billable OT only
    SUM(
      CASE 
        WHEN (LOWER(counter_type) IN ('daily overtime','daily ot','weekly overtime','weekly ot',
                                       'holiday worked','consecutive day ot','consecutive day dt')
              OR LOWER(counter_type) LIKE '%double time%'
              OR LOWER(counter_type) LIKE '%overtime%')
             AND is_billable_ot = 'NON-OT'
        THEN counter_hours 
        ELSE 0 
      END
    ) AS nbot_hours,
    -- Billable OT
    SUM(
      CASE 
        WHEN (LOWER(counter_type) IN ('daily overtime','daily ot','weekly overtime','weekly ot',
                                       'holiday worked','consecutive day ot','consecutive day dt')
              OR LOWER(counter_type) LIKE '%double time%'
              OR LOWER(counter_type) LIKE '%overtime%')
             AND is_billable_ot = 'OT'
        THEN counter_hours 
        ELSE 0 
      END
    ) AS billable_ot_hours
  FROM Base
  GROUP BY customer_code, customer_name
),
WithPct AS (
  SELECT
    customer_code, customer_name, total_hours, nbot_hours, billable_ot_hours,
    SAFE_DIVIDE(nbot_hours, total_hours) * 100 AS nbot_pct,
    SAFE_DIVIDE(billable_ot_hours, total_hours) * 100 AS billable_ot_pct,
    SAFE_DIVIDE(nbot_hours + billable_ot_hours, total_hours) * 100 AS total_ot_pct
  FROM Agg
),
WithPareto AS (
  SELECT
    *,
    RANK() OVER (ORDER BY nbot_hours DESC) AS nbot_rank,
    SUM(nbot_hours) OVER () AS nbot_total_all,
    SUM(nbot_hours) OVER (ORDER BY nbot_hours DESC
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS nbot_cum,
    SAFE_DIVIDE(
      SUM(nbot_hours) OVER (ORDER BY nbot_hours DESC
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW),
      SUM(nbot_hours) OVER ()
    ) * 100 AS nbot_cum_pct
  FROM WithPct
)
SELECT
  customer_code, customer_name, total_hours, nbot_hours, billable_ot_hours, nbot_pct, billable_ot_pct, total_ot_pct,
  nbot_rank, nbot_cum_pct,
  CASE WHEN nbot_cum_pct <= 80 THEN 'Yes' ELSE 'No' END AS pareto_80_flag
FROM WithPareto
ORDER BY nbot_hours DESC
"""

    totals_sql = f"""
WITH Base AS (
  SELECT
    counter_type,
    counter_hours,
    COALESCE(NULLIF(TRIM(is_billable_overtime), ''), 'UNKNOWN') AS is_billable_ot
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
)
SELECT
  SUM(counter_hours) AS total_hours,
  -- NBOT: Non-Billable OT only
  SUM(
    CASE 
      WHEN (LOWER(counter_type) IN ('daily overtime','daily ot','weekly overtime','weekly ot',
                                     'holiday worked','consecutive day ot','consecutive day dt')
            OR LOWER(counter_type) LIKE '%double time%'
            OR LOWER(counter_type) LIKE '%overtime%')
           AND is_billable_ot = 'NON-OT'
      THEN counter_hours 
      ELSE 0 
    END
  ) AS nbot_hours,
  -- Billable OT
  SUM(
    CASE 
      WHEN (LOWER(counter_type) IN ('daily overtime','daily ot','weekly overtime','weekly ot',
                                     'holiday worked','consecutive day ot','consecutive day dt')
            OR LOWER(counter_type) LIKE '%double time%'
            OR LOWER(counter_type) LIKE '%overtime%')
           AND is_billable_ot = 'OT'
      THEN counter_hours 
      ELSE 0 
    END
  ) AS billable_ot_hours,
  -- Percentages
  SAFE_DIVIDE(
    SUM(
      CASE 
        WHEN (LOWER(counter_type) IN ('daily overtime','daily ot','weekly overtime','weekly ot',
                                       'holiday worked','consecutive day ot','consecutive day dt')
              OR LOWER(counter_type) LIKE '%double time%'
              OR LOWER(counter_type) LIKE '%overtime%')
             AND is_billable_ot = 'NON-OT'
        THEN counter_hours 
        ELSE 0 
      END
    ),
    SUM(counter_hours)
  ) * 100 AS nbot_pct,
  SAFE_DIVIDE(
    SUM(
      CASE 
        WHEN (LOWER(counter_type) IN ('daily overtime','daily ot','weekly overtime','weekly ot',
                                       'holiday worked','consecutive day ot','consecutive day dt')
              OR LOWER(counter_type) LIKE '%double time%'
              OR LOWER(counter_type) LIKE '%overtime%')
             AND is_billable_ot = 'OT'
        THEN counter_hours 
        ELSE 0 
      END
    ),
    SUM(counter_hours)
  ) * 100 AS billable_ot_pct
FROM Base
"""

    ot_breakdown_sql = f"""
WITH Base AS (
  SELECT
    counter_type,
    counter_hours,
    COALESCE(NULLIF(TRIM(is_billable_overtime), ''), 'UNKNOWN') AS is_billable_ot
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
)
SELECT
  CASE
    WHEN LOWER(counter_type) IN ('daily overtime','daily ot') THEN 'Daily Overtime'
    WHEN LOWER(counter_type) IN ('weekly overtime','weekly ot') THEN 'Weekly Overtime'
    WHEN LOWER(counter_type) LIKE '%double time%' THEN 'Daily Double Time'
    WHEN LOWER(counter_type) = 'holiday worked' THEN 'Holiday Worked'
    WHEN LOWER(counter_type) LIKE 'consecutive day ot%' THEN 'Consecutive Day OT'
    WHEN LOWER(counter_type) LIKE 'consecutive day dt%' THEN 'Consecutive Day DT'
    ELSE 'Other OT'
  END AS ot_category,
  SUM(CASE WHEN is_billable_ot = 'NON-OT' THEN counter_hours ELSE 0 END) AS nbot_hours,
  SUM(CASE WHEN is_billable_ot = 'OT' THEN counter_hours ELSE 0 END) AS billable_hours,
  SUM(counter_hours) AS total_ot_hours
FROM Base
WHERE (LOWER(counter_type) IN ('daily overtime','daily ot','weekly overtime','weekly ot',
                                'holiday worked','consecutive day ot','consecutive day dt')
       OR LOWER(counter_type) LIKE '%double time%'
       OR LOWER(counter_type) LIKE '%overtime%')
GROUP BY ot_category
ORDER BY total_ot_hours DESC
"""

    try:
        client = bigquery.Client(project=compute_project)
        rows = client.query(sql).to_dataframe().to_dict(orient="records")
        totals = client.query(totals_sql).to_dataframe().to_dict(orient="records")[0]
        ot_breakdown_rows = client.query(ot_breakdown_sql).to_dataframe().to_dict(orient="records")
    except Exception as e:
        return f"Query failed: {str(e)}\n\nSQL:\n{sql}\n\nTOTALS_SQL:\n{totals_sql}"

    total_hours = float(totals.get('total_hours') or 0)
    nbot_hours = float(totals.get('nbot_hours') or 0)
    billable_ot_hours = float(totals.get('billable_ot_hours') or 0)
    total_ot_hours = nbot_hours + billable_ot_hours
    
    nbot_pct = round(float(totals.get('nbot_pct') or 0), 2)
    billable_ot_pct = round(float(totals.get('billable_ot_pct') or 0), 2)
    total_ot_pct = round((total_ot_hours / total_hours * 100) if total_hours else 0, 2)
    
    # Calculate regular hours
    regular_hours = total_hours - total_ot_hours
    regular_pct = round((regular_hours / total_hours * 100) if total_hours else 0, 1)
    
    # Process OT breakdown
    for r in ot_breakdown_rows:
        r["nbot_pct_of_twh"] = round((float(r["nbot_hours"]) / total_hours * 100) if total_hours else 0, 2)
        r["billable_pct_of_twh"] = round((float(r["billable_hours"]) / total_hours * 100) if total_hours else 0, 2)
        r["total_ot_pct_of_twh"] = round((float(r["total_ot_hours"]) / total_hours * 100) if total_hours else 0, 2)
    
    # === EXECUTIVE SUMMARY CALCULATIONS ===
    
    # NBOT Status
    if nbot_pct < 3:
        nbot_status_color = "🟢"
        nbot_status_text = "Excellent — Under target"
    elif 3 <= nbot_pct <= 5:
        nbot_status_color = "🟡"
        nbot_status_text = "Acceptable — Monitor closely"
    else:
        nbot_status_color = "🔴"
        nbot_status_text = "Critical — Immediate action required"
    
    # Company Health Status
    critical_customers = sum(1 for c in rows if c.get("nbot_pct", 0) > 5)
    
    if nbot_pct > 5 or (len(rows) > 0 and critical_customers > len(rows) * 0.4):
        company_health_status = "🔴 Needs Attention"
    elif nbot_pct > 3 or (len(rows) > 0 and critical_customers > len(rows) * 0.2):
        company_health_status = "🟡 Monitor"
    else:
        company_health_status = "🟢 Healthy"
    
    # Customers with OT
    customers_with_ot = sum(1 for c in rows if c.get("nbot_hours", 0) > 0)
    customers_with_ot_pct = round((customers_with_ot / len(rows) * 100) if rows else 0, 1)
    
    # OT Breakdown as % of NBOT
    ot_breakdown = []
    if nbot_hours > 0:
        for r in ot_breakdown_rows:
            if r.get("nbot_hours", 0) > 0:
                pct_of_nbot = round((float(r["nbot_hours"]) / nbot_hours * 100), 1)
                ot_breakdown.append({
                    "label": r["ot_category"],
                    "pct_of_nbot": pct_of_nbot
                })
    
    # Pareto Analysis
    pareto_customers = [c for c in rows if c.get('pareto_80_flag') == 'Yes']
    
    # Risk Flags
    risk_flags = []
    if nbot_pct > 5:
        risk_flags.append(f"🔴 High Company-Wide NBOT ({nbot_pct:.1f}%) — Exceeds 5% threshold")
    if len(rows) > 0 and critical_customers > len(rows) * 0.3:
        risk_flags.append(f"🟠 Multiple Critical Customers — {critical_customers} of {len(rows)} customers exceed 5% NBOT")
    
    # Find top offender customers
    top_customers = sorted(rows, key=lambda x: float(x.get("nbot_pct", 0)), reverse=True)[:3]
    if top_customers and top_customers[0].get("nbot_pct", 0) > 10:
        risk_flags.append(f"⚠️ Severe Customer Issue — {top_customers[0]['customer_name']} at {top_customers[0].get('nbot_pct', 0):.1f}% NBOT")
    
    # Pareto concentration analysis
    if len(pareto_customers) > 0 and len(rows) > 0:
        concentration_pct = round((len(pareto_customers) / len(rows) * 100), 1)
        if concentration_pct < 20:
            risk_flags.append(f"📊 High Concentration — {len(pareto_customers)} customers ({concentration_pct}%) account for 80% of NBOT")
    
    # Recommendations
    recommendations = []
    
    if nbot_pct > 5:
        if len(ot_breakdown_rows) > 0:
            top_ot = max(ot_breakdown_rows, key=lambda x: float(x.get("nbot_hours", 0)))
            if top_ot.get("nbot_hours", 0) > 0:
                recommendations.append(
                    f"**Company-Wide Initiative: Reduce {top_ot['ot_category']}** (NBOT) — Accounts for "
                    f"{top_ot.get('nbot_pct_of_twh', 0):.1f}% of total company hours"
                )
    
    # Pareto-based recommendations
    if len(pareto_customers) > 0:
        pareto_nbot = sum(float(c.get('nbot_hours', 0)) for c in pareto_customers)
        top_3_pareto = [c['customer_name'] for c in pareto_customers[:3]]
        recommendations.append(
            f"**Pareto Strategy** — {len(pareto_customers)} customers drive 80% of NBOT ({pareto_nbot:,.0f} hours). "
            f"Focus improvement efforts on these key accounts: {', '.join(top_3_pareto)}"
        )
    
    if critical_customers > 0:
        top_3_customers = [c['customer_name'] for c in top_customers[:3] if c.get('nbot_pct', 0) > 5]
        if top_3_customers:
            recommendations.append(
                f"**Customer Focus** — Deploy account management resources to high-NBOT customers: {', '.join(top_3_customers)}"
            )
    
    if len(rows) > 10 and critical_customers > 5:
        recommendations.append(
            "**Enterprise Policy Review** — Widespread customer NBOT issues suggest systemic "
            "operational challenges. Recommend company-wide contract terms, SLA, and staffing policy review."
        )
    
    # Identify best practices from low-NBOT customers
    low_nbot_customers = [c for c in rows if c.get('nbot_pct', 0) < 3]
    if len(low_nbot_customers) > 0 and critical_customers > 0:
        best_customer = min(rows, key=lambda x: float(x.get("nbot_pct", 0)))
        recommendations.append(
            f"**Best Practice Sharing** — {best_customer['customer_name']} maintains {best_customer.get('nbot_pct', 0):.1f}% NBOT. "
            f"Analyze their operational model and contract structure for replication."
        )
    
    if not recommendations:
        recommendations.append("✅ Company is performing well across all customers — Continue current practices")

    context = {
        "start_date": start_date,
        "end_date": end_date,
        "total_hours": f"{total_hours:,.2f}",
        "nbot_hours": f"{nbot_hours:,.2f}",
        "billable_ot_hours": f"{billable_ot_hours:,.2f}",
        "total_ot_hours": f"{total_ot_hours:,.2f}",
        "nbot_pct": nbot_pct,
        "billable_ot_pct": billable_ot_pct,
        "total_ot_pct": total_ot_pct,
        "regular_hours": f"{regular_hours:,.2f}",
        "regular_pct": f"{regular_pct:.1f}",
        "customer_count": len(rows),
        "customers": rows,
        "ot_breakdown_rows": ot_breakdown_rows,
        "company_health_status": company_health_status,
        "nbot_status_color": nbot_status_color,
        "nbot_status_text": nbot_status_text,
        "customers_with_ot": customers_with_ot,
        "customers_with_ot_pct": customers_with_ot_pct,
        "ot_breakdown": ot_breakdown,
        "risk_flags": risk_flags,
        "recommendations": recommendations,
    }

    template = Template("""# 🌐 Excellence Performance Center 🌐
## NBOT Company Analysis – By Customer
**Period:** {{ start_date }} – {{ end_date }}

---

## 📋 Executive Summary

**Company Health:** {{ company_health_status }}

### Key Findings
- **NBOT Performance:** {{ "%.2f"|format(nbot_pct) }}% ({{ nbot_status_color }}) — {{ nbot_status_text }}
- **Billable OT:** {{ "%.2f"|format(billable_ot_pct) }}% | **Total OT:** {{ "%.2f"|format(total_ot_pct) }}%
- **Customers with OT:** {{ customers_with_ot }} of {{ customer_count }} customers ({{ "%.1f"|format(customers_with_ot_pct) }}%)
- **Total Hours Worked:** {{ total_hours }} hours across {{ customer_count }} customers
- **NBOT Hours:** {{ nbot_hours }} hours | **Billable OT Hours:** {{ billable_ot_hours }} hours

**NBOT Thresholds:** 🟢 GREEN < 3% · 🟡 YELLOW 3–5% · 🔴 RED > 5%

{% if ot_breakdown and ot_breakdown|length > 0 -%}
### NBOT Composition
{% for row in ot_breakdown -%}
- **{{ row.label }}:** {{ "%.1f"|format(row.pct_of_nbot) }}%
{% endfor -%}
{% endif %}

{% if risk_flags and risk_flags|length > 0 -%}
### ⚠️ Risk Indicators
{% for flag in risk_flags -%}
- {{ flag }}
{% endfor -%}
{% endif %}

{% if recommendations and recommendations|length > 0 -%}
### 💡 Recommendations
{% for rec in recommendations -%}
- {{ rec }}
{% endfor -%}
{% endif %}

---

## 📊 Key Metrics (Company)
| Metric | Value |
|:--|--:|
| Total Hours Worked | {{ total_hours }} |
| Total Customers | {{ customer_count }} |
| NBOT Hours | {{ nbot_hours }} |
| NBOT % | {{ "%.2f"|format(nbot_pct) }}% |
| Billable OT Hours | {{ billable_ot_hours }} |
| Billable OT % | {{ "%.2f"|format(billable_ot_pct) }}% |
| Total OT Hours | {{ total_ot_hours }} |
| Total OT % | {{ "%.2f"|format(total_ot_pct) }}% |

---

## 📅 HOURS BREAKDOWN BY CATEGORY

| Category | NBOT Hours | Billable OT | Total OT | % of TWH | Visual Impact |
|:---------|----------:|------------:|---------:|---------:|:--------------|
| Regular (NON-OT) | — | — | — | {{ regular_pct }}% | ████████████████████ |
{% for row in ot_breakdown_rows -%}
| {{ row.ot_category }} | {{ "%.2f"|format(row.nbot_hours) }} | {{ "%.2f"|format(row.billable_hours) }} | {{ "%.2f"|format(row.total_ot_hours) }} | {{ "%.2f"|format(row.total_ot_pct_of_twh) }}% | {% if row.total_ot_pct_of_twh > 5 %}██████░░░░░░░░░░░░░░{% elif row.total_ot_pct_of_twh > 2 %}███░░░░░░░░░░░░░░░░░{% else %}█░░░░░░░░░░░░░░░░░░░{% endif %} |
{% endfor %}

{% if ot_breakdown and ot_breakdown|length > 0 -%}
**▶️ Key Insight:** {{ ot_breakdown[0].label }} represents {{ "%.1f"|format(ot_breakdown[0].pct_of_nbot) }}% of NBOT → Primary reduction target
{% endif %}

---

## 🧩 Customer Breakdown (Pareto on NBOT)
| Rank | Customer | Total Hours | NBOT Hours | Billable OT | NBOT % | Billable OT % | Total OT % | Cum NBOT % | Pareto 80% |
|:--:|:--|--:|--:|--:|--:|--:|--:|--:|:--:|
{% for c in customers -%}
| {{ c.nbot_rank }} | {{ c.customer_name }} | {{ "%.2f"|format(c.total_hours or 0) }} | {{ "%.2f"|format(c.nbot_hours or 0) }} | {{ "%.2f"|format(c.billable_ot_hours or 0) }} | {{ "%.2f"|format(c.nbot_pct or 0) }}% | {{ "%.2f"|format(c.billable_ot_pct or 0) }}% | {{ "%.2f"|format(c.total_ot_pct or 0) }}% | {{ "%.2f"|format(c.nbot_cum_pct or 0) }}% | {% if c.pareto_80_flag == 'Yes' %}☑️{% endif %} |
{% endfor %}
""")
    return template.render(**context)



# ------------------------------------------------------------
# 6) Region Analysis by Site (Pareto)
# ------------------------------------------------------------


def _generate_nbot_region_analysis_by_site(
    region: str,
    start_date: str,
    end_date: str,
    project: str,
    dataset: str,
    compute_project: str
) -> str:
    """
    NBOT Region Analysis with Pareto by Site (instead of by customer).
    Shows which sites within a region are driving NBOT.

    Returns:
        Markdown string (single value, no tuples).
    """

    # -----------------------------
    # Local helper: clean site mgrs
    # -----------------------------
    def clean_site_manager_in_rows(rows):
        """
        Normalize/clean site_manager values in-place for nicer reporting.
        """
        for r in rows:
            sm = (r.get("site_manager") or "").strip()
            if not sm or sm.upper() in {"UNASSIGNED", "N/A", "NA", "NONE", "NULL"}:
                sm = "Unassigned"
            # Title-case but preserve common particles
            sm_tc = " ".join(w.capitalize() if w.lower() not in {"of", "and", "de", "da"} else w.lower()
                             for w in sm.split())
            r["site_manager"] = sm_tc

    if not all([region, start_date, end_date]):
        return "Missing required parameters: region, start_date, end_date"

    # -----------------------------
    # SQLs
    # -----------------------------
    sites_sql = f"""
WITH Base AS (
  SELECT
    CAST(location_number AS STRING) AS location_number,
    COALESCE(NULLIF(TRIM(customer_name), ''), 'Unassigned') AS customer_name,
    COALESCE(NULLIF(TRIM(city), ''), 'N/A') AS city,
    COALESCE(NULLIF(TRIM(state), ''), 'NA') AS state,
    COALESCE(NULLIF(TRIM(site_manager), ''), 'Unassigned') AS site_manager,
    LOWER(TRIM(counter_type)) AS counter_type,
    SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours,
    COALESCE(NULLIF(TRIM(is_billable_overtime), ''), 'UNKNOWN') AS is_billable_ot
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
    AND TRIM(region) = '{region}'
),
Agg AS (
  SELECT
    location_number,
    ANY_VALUE(customer_name) AS customer_name,
    ANY_VALUE(city) AS city,
    ANY_VALUE(state) AS state,
    ANY_VALUE(site_manager) AS site_manager,
    SUM(counter_hours) AS total_hours,
    -- NBOT: Non-Billable OT only
    SUM(
      CASE 
        WHEN (counter_type IN ('daily overtime','daily ot','weekly overtime','weekly ot','holiday worked')
              OR counter_type LIKE 'consecutive day ot%%'
              OR counter_type LIKE 'consecutive day dt%%'
              OR counter_type LIKE '%%double time%%'
              OR counter_type LIKE '%%overtime%%')
             AND is_billable_ot = 'NON-OT'
        THEN counter_hours 
        ELSE 0 
      END
    ) AS nbot_hours,
    -- Billable OT
    SUM(
      CASE 
        WHEN (counter_type IN ('daily overtime','daily ot','weekly overtime','weekly ot','holiday worked')
              OR counter_type LIKE 'consecutive day ot%%'
              OR counter_type LIKE 'consecutive day dt%%'
              OR counter_type LIKE '%%double time%%'
              OR counter_type LIKE '%%overtime%%')
             AND is_billable_ot = 'OT'
        THEN counter_hours 
        ELSE 0 
      END
    ) AS billable_ot_hours,
    -- Unpaid Time Off + Sick
    SUM(CASE WHEN counter_type LIKE '%%unpaid time off%%' THEN counter_hours ELSE 0 END) AS unpaid_time_off_hours,
    SUM(CASE WHEN counter_type = 'sick' THEN counter_hours ELSE 0 END) AS sick_hours
  FROM Base
  GROUP BY location_number
),
WithPct AS (
  SELECT
    location_number, customer_name, city, state, site_manager,
    total_hours, nbot_hours, billable_ot_hours, unpaid_time_off_hours, sick_hours,
    SAFE_DIVIDE(nbot_hours, total_hours) * 100 AS nbot_pct,
    SAFE_DIVIDE(billable_ot_hours, total_hours) * 100 AS billable_ot_pct,
    SAFE_DIVIDE(unpaid_time_off_hours, total_hours) * 100 AS unpaid_pct,
    SAFE_DIVIDE(sick_hours, total_hours) * 100 AS sick_pct,
    SAFE_DIVIDE(nbot_hours + billable_ot_hours, total_hours) * 100 AS total_ot_pct
  FROM Agg
),
Pareto AS (
  SELECT
    *,
    RANK() OVER (ORDER BY nbot_hours DESC) AS nbot_rank,
    SUM(nbot_hours) OVER () AS nbot_total_all,
    SUM(nbot_hours) OVER (ORDER BY nbot_hours DESC
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS nbot_cum,
    SAFE_DIVIDE(
      SUM(nbot_hours) OVER (ORDER BY nbot_hours DESC
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW),
      SUM(nbot_hours) OVER ()
    ) * 100 AS nbot_cum_pct
  FROM WithPct
)
SELECT
  location_number, customer_name, city, state, site_manager,
  total_hours, nbot_hours, billable_ot_hours, unpaid_time_off_hours, sick_hours,
  nbot_pct, billable_ot_pct, unpaid_pct, sick_pct, total_ot_pct,
  nbot_rank, nbot_cum_pct,
  CASE WHEN nbot_cum_pct <= 80 THEN 'Yes' ELSE 'No' END AS pareto_80_flag
FROM Pareto
ORDER BY nbot_hours DESC
"""

    region_totals_sql = f"""
WITH Base AS (
  SELECT
    LOWER(TRIM(counter_type)) AS counter_type,
    SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours,
    COALESCE(NULLIF(TRIM(is_billable_overtime), ''), 'UNKNOWN') AS is_billable_ot
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
    AND TRIM(region) = '{region}'
)
SELECT
  SUM(counter_hours) AS total_hours,
  SUM(
    CASE 
      WHEN (counter_type IN ('daily overtime','daily ot','weekly overtime','weekly ot','holiday worked')
            OR counter_type LIKE 'consecutive day ot%%'
            OR counter_type LIKE 'consecutive day dt%%'
            OR counter_type LIKE '%%double time%%'
            OR counter_type LIKE '%%overtime%%')
           AND is_billable_ot = 'NON-OT'
      THEN counter_hours 
      ELSE 0 
    END
  ) AS nbot_hours,
  SUM(
    CASE 
      WHEN (counter_type IN ('daily overtime','daily ot','weekly overtime','weekly ot','holiday worked')
            OR counter_type LIKE 'consecutive day ot%%'
            OR counter_type LIKE 'consecutive day dt%%'
            OR counter_type LIKE '%%double time%%'
            OR counter_type LIKE '%%overtime%%')
           AND is_billable_ot = 'OT'
      THEN counter_hours 
      ELSE 0 
    END
  ) AS billable_ot_hours,
  SUM(CASE WHEN counter_type LIKE '%%unpaid time off%%' THEN counter_hours ELSE 0 END) AS unpaid_time_off_hours_total,
  SUM(CASE WHEN counter_type = 'sick' THEN counter_hours ELSE 0 END) AS sick_hours_total,
  SAFE_DIVIDE(
    SUM(
      CASE 
        WHEN (counter_type IN ('daily overtime','daily ot','weekly overtime','weekly ot','holiday worked')
              OR counter_type LIKE 'consecutive day ot%%'
              OR counter_type LIKE 'consecutive day dt%%'
              OR counter_type LIKE '%%double time%%'
              OR counter_type LIKE '%%overtime%%')
             AND is_billable_ot = 'NON-OT'
      THEN counter_hours ELSE 0 END),
    SUM(counter_hours)
  ) * 100 AS nbot_pct,
  SAFE_DIVIDE(
    SUM(
      CASE 
        WHEN (counter_type IN ('daily overtime','daily ot','weekly overtime','weekly ot','holiday worked')
              OR counter_type LIKE 'consecutive day ot%%'
              OR counter_type LIKE 'consecutive day dt%%'
              OR counter_type LIKE '%%double time%%'
              OR counter_type LIKE '%%overtime%%')
             AND is_billable_ot = 'OT'
      THEN counter_hours ELSE 0 END),
    SUM(counter_hours)
  ) * 100 AS billable_ot_pct,
  SAFE_DIVIDE(
    SUM(CASE WHEN counter_type LIKE '%%unpaid time off%%' THEN counter_hours ELSE 0 END),
    SUM(counter_hours)
  ) * 100 AS unpaid_pct_total,
  SAFE_DIVIDE(
    SUM(CASE WHEN counter_type = 'sick' THEN counter_hours ELSE 0 END),
    SUM(counter_hours)
  ) * 100 AS sick_pct_total
FROM Base
"""

    # Wrap UNION ALL in a subquery to allow ORDER BY across the full unioned set
    ot_breakdown_sql = f"""
WITH Base AS (
  SELECT
    LOWER(TRIM(counter_type)) AS counter_type,
    SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours,
    COALESCE(NULLIF(TRIM(is_billable_overtime), ''), 'UNKNOWN') AS is_billable_ot
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
    AND TRIM(region) = '{region}'
),
Unioned AS (
  SELECT
    CASE
      WHEN counter_type IN ('daily overtime','daily ot') THEN 'Daily Overtime'
      WHEN counter_type IN ('weekly overtime','weekly ot') THEN 'Weekly Overtime'
      WHEN counter_type LIKE '%%double time%%' THEN 'Daily Double Time'
      WHEN counter_type LIKE 'consecutive day ot%%' THEN 'Consecutive Day OT'
      WHEN counter_type LIKE 'consecutive day dt%%' THEN 'Consecutive Day DT'
      ELSE 'Other OT'
    END AS ot_category,
    SUM(CASE WHEN is_billable_ot = 'NON-OT' THEN counter_hours ELSE 0 END) AS nbot_hours,
    SUM(CASE WHEN is_billable_ot = 'OT' THEN counter_hours ELSE 0 END) AS billable_hours,
    SUM(counter_hours) AS total_ot_hours
  FROM Base
  WHERE (counter_type IN ('daily overtime','daily ot','weekly overtime','weekly ot')
         OR counter_type LIKE 'consecutive day ot%%'
         OR counter_type LIKE 'consecutive day dt%%'
         OR counter_type LIKE '%%double time%%'
         OR counter_type LIKE '%%overtime%%')
  GROUP BY ot_category

  UNION ALL

  SELECT
    'Unpaid Time Off Request' AS ot_category,
    0 AS nbot_hours,
    0 AS billable_hours,
    SUM(CASE WHEN counter_type LIKE '%%unpaid time off%%' THEN counter_hours ELSE 0 END) AS total_ot_hours
  FROM Base
  WHERE counter_type LIKE '%%unpaid time off%%'

  UNION ALL

  SELECT
    'Sick' AS ot_category,
    0 AS nbot_hours,
    0 AS billable_hours,
    SUM(CASE WHEN counter_type = 'sick' THEN counter_hours ELSE 0 END) AS total_ot_hours
  FROM Base
  WHERE counter_type = 'sick'
)
SELECT * FROM Unioned
ORDER BY total_ot_hours DESC
"""

    # -----------------------------
    # Execute queries
    # -----------------------------
    try:
        from google.cloud import bigquery
        from jinja2 import Template

        client = bigquery.Client(project=compute_project)

        site_rows = client.query(sites_sql).to_dataframe().to_dict(orient="records")
        totals = client.query(region_totals_sql).to_dataframe().to_dict(orient="records")
        ot_breakdown_rows = client.query(ot_breakdown_sql).to_dataframe().to_dict(orient="records")
    except Exception as e:
        # Return the failure and the SQL for quick debugging in the notebook/logs
        return (
            f"Query failed: {str(e)}\n\n"
            f"SITES_SQL:\n{sites_sql}\n\n"
            f"REGION_TOTALS_SQL:\n{region_totals_sql}\n\n"
            f"OT_BREAKDOWN_SQL:\n{ot_breakdown_sql}"
        )

    # -----------------------------
    # Post-processing
    # -----------------------------
    clean_site_manager_in_rows(site_rows)

    if not totals:
        return f"No data found for region={region}, dates={start_date} to {end_date}"

    t = totals[0]
    total_hours = float(t.get('total_hours') or 0.0)
    nbot_hours = float(t.get('nbot_hours') or 0.0)
    billable_ot_hours = float(t.get('billable_ot_hours') or 0.0)
    total_ot_hours = nbot_hours + billable_ot_hours

    unpaid_time_off_hours_total = float(t.get('unpaid_time_off_hours_total') or 0.0)
    sick_hours_total = float(t.get('sick_hours_total') or 0.0)
    unpaid_pct_total = round(float(t.get('unpaid_pct_total') or 0.0), 2)
    sick_pct_total = round(float(t.get('sick_pct_total') or 0.0), 2)

    nbot_pct = round(float(t.get('nbot_pct') or 0.0), 2)
    billable_ot_pct = round(float(t.get('billable_ot_pct') or 0.0), 2)
    total_ot_pct = round((total_ot_hours / total_hours * 100.0) if total_hours else 0.0, 2)

    regular_hours = max(total_hours - total_ot_hours, 0.0)
    regular_pct = round((regular_hours / total_hours * 100.0) if total_hours else 0.0, 1)

    # Add TWH-based %s to breakdown rows
    for r in ot_breakdown_rows:
        r["nbot_pct_of_twh"] = round((float(r.get("nbot_hours", 0.0)) / total_hours * 100.0) if total_hours else 0.0, 2)
        r["billable_pct_of_twh"] = round((float(r.get("billable_hours", 0.0)) / total_hours * 100.0) if total_hours else 0.0, 2)
        r["total_ot_pct_of_twh"] = round((float(r.get("total_ot_hours", 0.0)) / total_hours * 100.0) if total_hours else 0.0, 2)

    # Executive status
    if nbot_pct < 3:
        nbot_status_color = "🟢"
        nbot_status_text = "Excellent — Under target"
    elif 3 <= nbot_pct <= 5:
        nbot_status_color = "🟡"
        nbot_status_text = "Acceptable — Monitor closely"
    else:
        nbot_status_color = "🔴"
        nbot_status_text = "Critical — Immediate action required"

    critical_sites = sum(1 for s in site_rows if (s.get("nbot_pct") or 0) > 5)
    if nbot_pct > 5 or (len(site_rows) > 0 and critical_sites > len(site_rows) * 0.4):
        region_health_status = "🔴 Needs Attention"
    elif nbot_pct > 3 or (len(site_rows) > 0 and critical_sites > len(site_rows) * 0.2):
        region_health_status = "🟡 Monitor"
    else:
        region_health_status = "🟢 Healthy"

    sites_with_ot = sum(1 for s in site_rows if (float(s.get("nbot_hours") or 0) + float(s.get("billable_ot_hours") or 0)) > 0)
    sites_with_ot_pct = round((sites_with_ot / len(site_rows) * 100.0) if site_rows else 0.0, 1)

    # Composition of NBOT
    ot_breakdown = []
    if nbot_hours > 0:
        for r in ot_breakdown_rows:
            if float(r.get("nbot_hours", 0.0)) > 0:
                pct_of_nbot = round((float(r["nbot_hours"]) / nbot_hours * 100.0), 1)
                ot_breakdown.append({"label": r["ot_category"], "pct_of_nbot": pct_of_nbot})

    # Pareto set
    pareto_sites = [s for s in site_rows if s.get('pareto_80_flag') == 'Yes']

    # Risk flags
    risk_flags = []
    if nbot_pct > 5:
        risk_flags.append(f"🔴 High Regional NBOT ({nbot_pct:.1f}%) — Exceeds 5% threshold")
    if len(site_rows) > 0 and critical_sites > len(site_rows) * 0.3:
        risk_flags.append(f"🟠 Multiple Critical Sites — {critical_sites} of {len(site_rows)} sites exceed 5% NBOT")

    top_sites = sorted(site_rows, key=lambda x: float(x.get("nbot_pct", 0.0)), reverse=True)[:3]
    if top_sites and float(top_sites[0].get("nbot_pct", 0.0)) > 10.0:
        risk_flags.append(f"⚠️ Severe Site Issue — Location {top_sites[0]['location_number']} at {float(top_sites[0].get('nbot_pct', 0.0)):.1f}% NBOT")

    if len(pareto_sites) > 0 and len(site_rows) > 0:
        concentration_pct = round((len(pareto_sites) / len(site_rows) * 100.0), 1)
        if concentration_pct < 30:
            risk_flags.append(f"📊 High Concentration — {len(pareto_sites)} sites ({concentration_pct}%) account for 80% of regional NBOT")

    # Recommendations
    recommendations = []
    if nbot_pct > 5 and len(ot_breakdown_rows) > 0:
        top_nbot_category = max(ot_breakdown_rows, key=lambda x: float(x.get("nbot_hours", 0.0)))
        if float(top_nbot_category.get("nbot_hours", 0.0)) > 0:
            recommendations.append(
                f"**Reduce {top_nbot_category['ot_category']}** (NBOT) across region — Accounts for "
                f"{top_nbot_category.get('nbot_pct_of_twh', 0.0):.2f}% of total regional hours"
            )

    if len(pareto_sites) > 0:
        pareto_nbot = sum(float(s.get('nbot_hours', 0.0)) for s in pareto_sites)
        top_3_pareto = [f"Location {s['location_number']}" for s in pareto_sites[:3]]
        recommendations.append(
            f"**Pareto Strategy** — {len(pareto_sites)} sites drive 80% of regional NBOT ({pareto_nbot:,.0f} hours). "
            f"Focus efforts on: {', '.join(top_3_pareto)}"
        )

    if critical_sites > 0:
        top_3_sites = [f"Location {s['location_number']}" for s in top_sites[:3] if float(s.get('nbot_pct', 0.0)) > 5.0]
        if top_3_sites:
            recommendations.append(
                f"**Focus on High-NBOT Sites** — Prioritize intervention at: {', '.join(top_3_sites)}"
            )

    if len(site_rows) > 5 and critical_sites > 3:
        recommendations.append(
            "**Regional Review** — High number of sites with NBOT issues suggests regional "
            "operational challenges. Consider region-wide policy and scheduling review."
        )

    if not recommendations:
        recommendations.append("✅ Region is performing well across all sites — Continue current practices")

    # -----------------------------
    # Render markdown
    # -----------------------------
    from jinja2 import Template
    context = {
        "region": region,
        "start_date": start_date,
        "end_date": end_date,
        "total_hours": f"{total_hours:,.2f}",
        "nbot_hours": f"{nbot_hours:,.2f}",
        "billable_ot_hours": f"{billable_ot_hours:,.2f}",
        "total_ot_hours": f"{total_ot_hours:,.2f}",
        "nbot_pct": nbot_pct,
        "billable_ot_pct": billable_ot_pct,
        "total_ot_pct": total_ot_pct,
        "regular_hours": f"{regular_hours:,.2f}",
        "regular_pct": f"{regular_pct:.1f}",
        "site_count": len(site_rows),
        "sites": site_rows,
        "ot_breakdown_rows": ot_breakdown_rows,
        "region_health_status": region_health_status,
        "nbot_status_color": nbot_status_color,
        "nbot_status_text": nbot_status_text,
        "sites_with_ot": sites_with_ot,
        "sites_with_ot_pct": sites_with_ot_pct,
        "ot_breakdown": ot_breakdown,
        "risk_flags": risk_flags,
        "recommendations": recommendations,
        "unpaid_time_off_hours_total": f"{unpaid_time_off_hours_total:,.2f}",
        "unpaid_pct_total": unpaid_pct_total,
        "sick_hours_total": f"{sick_hours_total:,.2f}",
        "sick_pct_total": sick_pct_total,
    }

    template = Template("""# 🌐 Excellence Performance Center 🌐
## NBOT Region Analysis — {{ region }} (Pareto by Site)
**Period:** {{ start_date }} — {{ end_date }}

---

## 📋 Executive Summary

**Regional Health:** {{ region_health_status }}

### Key Findings
- **NBOT Performance:** {{ "%.2f"|format(nbot_pct) }}% ({{ nbot_status_color }}) — {{ nbot_status_text }}
- **Billable OT:** {{ "%.2f"|format(billable_ot_pct) }}% | **Total OT:** {{ "%.2f"|format(total_ot_pct) }}%
- **Sites with OT:** {{ sites_with_ot }} of {{ site_count }} sites ({{ "%.1f"|format(sites_with_ot_pct) }}%)
- **Total Hours Worked:** {{ total_hours }} hours across {{ site_count }} sites
- **NBOT Hours:** {{ nbot_hours }} hours | **Billable OT Hours:** {{ billable_ot_hours }} hours

**NBOT Thresholds:** 🟢 < 3% · 🟡 3–5% · 🔴 > 5%

{% if ot_breakdown and ot_breakdown|length > 0 -%}
### NBOT Composition
{% for row in ot_breakdown -%}
- **{{ row.label }}:** {{ "%.1f"|format(row.pct_of_nbot) }}%
{% endfor -%}
{% endif %}

{% if risk_flags and risk_flags|length > 0 -%}
### ⚠️ Risk Indicators
{% for flag in risk_flags -%}
- {{ flag }}
{% endfor -%}
{% endif %}

{% if recommendations and recommendations|length > 0 -%}
### 💡 Recommendations
{% for rec in recommendations -%}
- {{ rec }}
{% endfor -%}
{% endif %}

---

## 📊 Regional Key Metrics
| Metric | Value |
|:--|--:|
| Total Hours Worked | {{ total_hours }} |
| Total Sites | {{ site_count }} |
| NBOT Hours | {{ nbot_hours }} |
| NBOT % | {{ "%.2f"|format(nbot_pct) }}% |
| Billable OT Hours | {{ billable_ot_hours }} |
| Billable OT % | {{ "%.2f"|format(billable_ot_pct) }}% |
| **Unpaid Time Off Hours** | **{{ unpaid_time_off_hours_total }}** |
| **Unpaid Time Off %** | **{{ "%.2f"|format(unpaid_pct_total) }}%** |
| **Sick Hours** | **{{ sick_hours_total }}** |
| **Sick %** | **{{ "%.2f"|format(sick_pct_total) }}%** |
| Total OT Hours | {{ total_ot_hours }} |
| Total OT % | {{ "%.2f"|format(total_ot_pct) }}% |

---

## 📅 HOURS BREAKDOWN BY CATEGORY

| Category | NBOT Hours | Billable OT | Total Hours | % of TWH | Visual Impact |
|:---------|----------:|------------:|------------:|---------:|:--------------|
| Regular (NON-OT) | — | — | — | {{ regular_pct }}% | ████████████████████ |
{% for row in ot_breakdown_rows -%}
| {{ row.ot_category }} | {{ "%.2f"|format(row.nbot_hours or 0) }} | {{ "%.2f"|format(row.billable_hours or 0) }} | {{ "%.2f"|format(row.total_ot_hours or 0) }} | {{ "%.2f"|format(row.total_ot_pct_of_twh or 0) }}% | {% if row.total_ot_pct_of_twh > 5 %}██████▒▒▒▒▒▒▒▒▒▒▒▒▒▒{% elif row.total_ot_pct_of_twh > 2 %}███▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒{% else %}█▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒{% endif %} |
{% endfor %}

{% if ot_breakdown and ot_breakdown|length > 0 -%}
**▶️ Key Insight:** {{ ot_breakdown[0].label }} represents {{ "%.1f"|format(ot_breakdown[0].pct_of_nbot) }}% of NBOT → Primary reduction target
{% endif %}

---

## 📈 Pareto — NBOT by Site (Region: {{ region }})
| Index | Rank | Site | Customer | City | State | Total Hours | NBOT Hours | NBOT % | Unpaid % | Sick % | Cum NBOT % | Pareto 80% |
|---:|---:|:--:|:--|:--|:--:|--:|--:|--:|--:|--:|--:|:--:|
{% for s in sites -%}
| {{ loop.index }} | {{ s.nbot_rank }} | {{ s.location_number }} | {{ s.customer_name }} | {{ s.city }} | {{ s.state }} | {{ "%.2f"|format(s.total_hours or 0) }} | {{ "%.2f"|format(s.nbot_hours or 0) }} | {{ "%.2f"|format(s.nbot_pct or 0) }}% | {{ "%.2f"|format(s.unpaid_pct or 0) }}% | {{ "%.2f"|format(s.sick_pct or 0) }}% | {{ "%.2f"|format(s.nbot_cum_pct or 0) }}% | {% if s.pareto_80_flag == 'Yes' %}☑️{% endif %} |
{% endfor %}
""")

    return template.render(**context)








# ============================================================
# MERGED NBOT 4-Week Snapshot Report - ULTIMATE VERSION
# With Beveled Metal 3D Styling, Chart.js, Sortable Tables, and Workforce Analysis
# ============================================================

from jinja2 import Template
from typing import Optional, List, Dict, Any
from google.cloud import bigquery
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# ============================================================
# clean_site_manager_name
# ============================================================

def clean_site_manager_name(manager_name: str) -> str:
    """
    Clean site manager name by removing everything after the first '('.
    
    Example:
        Input: "Diego Altamirano (M-1 West Coast (AZ,CA,ID,NM,NV,OR,WA)) (209290)"
        Output: "Diego Altamirano"
    
    Args:
        manager_name: Full site manager string from database
    
    Returns:
        Cleaned manager name (first name + last name only)
    """
    if not manager_name:
        return "Unassigned"
    
    manager_name = str(manager_name).strip()
    
    # Extract only the name before the first "("
    if '(' in manager_name:
        return manager_name.split('(')[0].strip()
    
    return manager_name

def _generate_report_filename_option2(
    scope_type: str,
    scope_name: str,
    start_date: str,
    end_date: str
) -> str:
    """
    Generate standardized filename for NBOT reports - Option 2 (Report-First).
    
    Format: 4Week_NBOT_Snapshot_ScopeType_ScopeName_MmmDD-MmmDD_YYYY.html
    
    Args:
        scope_type: "Company_Wide", "Region", "Customer", or "Site"
        scope_name: Sanitized name (e.g., "Waymo_LLC", "Central_South")
        start_date: Report start date in YYYY-MM-DD format
        end_date: Report end date in YYYY-MM-DD format
    
    Returns:
        Filename string
    
    Examples:
        4Week_NBOT_Snapshot_Customer_Waymo_LLC_Oct12-Nov08_2025.html
        4Week_NBOT_Snapshot_Region_Central_South_Oct12-Nov08_2025.html
        4Week_NBOT_Snapshot_Company_Wide_Oct12-Nov08_2025.html
    """
    from datetime import datetime
    
    # Sanitize scope name for filename (replace spaces with underscores, remove special chars)
    safe_scope_name = scope_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
    safe_scope_name = "".join(c for c in safe_scope_name if c.isalnum() or c in ('_', '-'))
    
    # Parse dates
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    
    # Format dates as MmmDD (e.g., Oct12, Nov08)
    start_formatted = start_dt.strftime('%b%d')  # Oct12
    end_formatted = end_dt.strftime('%b%d')      # Nov08
    year = end_dt.strftime('%Y')                  # 2025
    
    # Build filename
    filename = (
        f"4Week_NBOT_Snapshot_"
        f"{scope_type}_"
        f"{safe_scope_name}_"
        f"{start_formatted}-{end_formatted}_{year}"
        f".html"
    )
    
    return filename

def _generate_nbot_company_4week_snapshot(
    end_date: str,
    project: str,
    dataset: str,
    compute_project: str,
    region: Optional[str] = None,
    customer_code: Optional[int] = None,
    location_number: Optional[str] = None
) -> str:
    """
    Generate 4-week NBOT snapshot report with week-by-week comparison.
    
    MERGED ULTIMATE VERSION with:
    - Beveled metal 3D styling throughout
    - Wider layout (1800px container, 5 metric cards per row)
    - Centered navigation buttons
    - Meta cards section (5 cards: Scope, Customer, Period, Timestamp, Status)
    - Chart.js interactive charts (trend line + NBOT breakdown bar chart)
    - Sortable and filterable site performance table
    - Manager performance table
    - Workforce Analysis with metrics and benchmarks
    - CSV export functionality
    - Detailed weekly comparison cards with full breakdown
    - All existing sections preserved (Pay Type, Detailed Breakdown, Recommendations)
    
    NBOT Calculation: Total OT Hours - Billable OT Hours
    - Total OT = All overtime-type counters (Daily OT, Weekly OT, Double Time, etc.)
    - Billable OT = All hours where is_billable_overtime = 'OT' (premium anywhere)
    - NBOT = Total OT - Billable OT
    
    Scope options:
    - Company-wide (default): No parameters
    - Regional: region parameter
    - Customer: customer_code parameter
    - Site: customer_code + location_number parameters
    
    end_date should be the last day of the most recent week (Saturday).
    """
    
    # Determine scope and build WHERE clause
    scope_type = "Company-Wide"
    scope_name = "All Operations"
    where_clause = ""
    
    if location_number and customer_code:
        scope_type = "Site"
        scope_name = f"Customer {customer_code} - Location {location_number}"
        where_clause = f"AND customer_code = '{customer_code}' AND CAST(location_number AS STRING) = '{location_number}'"
    elif customer_code:
        scope_type = "Customer"
        where_clause = f"AND customer_code = '{customer_code}'"
    elif region:
        scope_type = "Region"
        scope_name = region
        where_clause = f"AND TRIM(region) = '{region}'"
    
    # Calculate 4 weeks of date ranges (Sunday to Saturday)
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    
    # Ensure end_date is a Saturday
    days_since_saturday = (end_dt.weekday() + 2) % 7
    if days_since_saturday != 0:
        end_dt = end_dt - timedelta(days=days_since_saturday)
    
    weeks = []
    for i in range(4):
        week_end = end_dt - timedelta(weeks=i)
        week_start = week_end - timedelta(days=6)
        week_num = week_end.isocalendar()[1]
        weeks.append({
            'week_num': week_num,
            'start_date': week_start.strftime('%Y-%m-%d'),
            'end_date': week_end.strftime('%Y-%m-%d'),
            'start_display': week_start.strftime('%b %d'),
            'end_display': week_end.strftime('%b %d'),
            'index': 3 - i
        })
    
    weeks.reverse()  # Oldest to newest
    
    # Query for each week's metrics with scope filter
    weekly_metrics_sql = f"""
    WITH WeeklyData AS (
      SELECT
        DATE_TRUNC(counter_date, WEEK(SUNDAY)) as week_start,
        ANY_VALUE(customer_name) as customer_name,
        ANY_VALUE(region) as region,
        -- Total counter hours
        SUM(counter_hours) AS total_hours,
        -- Unpaid Time Off hours
        SUM(
          CASE 
            WHEN LOWER(TRIM(counter_type)) LIKE '%unpaid time off%'
            THEN counter_hours ELSE 0 END
        ) AS unpaid_timeoff_hours,
        -- Total hourly hours (pay_type filtering)
        SUM(
          CASE 
            WHEN LOWER(TRIM(COALESCE(CAST(pay_type AS STRING), ''))) IN ('hourly','h','non-exempt','nonexempt')
            THEN counter_hours ELSE 0 END
        ) AS total_hourly_hours,
        -- Total salaried hours (pay_type filtering)
        SUM(
          CASE 
            WHEN LOWER(TRIM(COALESCE(CAST(pay_type AS STRING), ''))) IN ('salaried','salary','exempt')
            THEN counter_hours ELSE 0 END
        ) AS total_salaried_hours,
        -- Total 1099 hours (pay_type filtering)
        SUM(
          CASE 
            WHEN LOWER(TRIM(COALESCE(CAST(pay_type AS STRING), ''))) IN ('1099','contractor','independent','ic')
            THEN counter_hours ELSE 0 END
        ) AS total_1099_hours,
        -- Total OT hours (all OT-type counters)
        SUM(
          CASE 
            WHEN (LOWER(counter_type) IN ('daily overtime','daily ot','weekly overtime','weekly ot')
                  OR LOWER(counter_type) LIKE 'consecutive day ot%%'
                  OR LOWER(counter_type) LIKE 'consecutive day dt%%'
                  OR LOWER(counter_type) LIKE '%%double time%%'
                  OR LOWER(counter_type) LIKE '%%overtime%%')
            THEN counter_hours ELSE 0 END
        ) AS total_ot_hours,
        -- Billable OT (premium anywhere: is_billable_overtime = 'OT')
        SUM(
          CASE 
            WHEN COALESCE(NULLIF(TRIM(is_billable_overtime), ''), 'UNKNOWN') = 'OT'
            THEN counter_hours ELSE 0 END
        ) AS billable_ot_hours,
        -- Billable OT from Actual OT counter types
        SUM(
          CASE 
            WHEN COALESCE(NULLIF(TRIM(is_billable_overtime), ''), 'UNKNOWN') = 'OT'
                 AND (LOWER(counter_type) IN ('daily overtime','daily ot','weekly overtime','weekly ot','holiday worked')
                      OR LOWER(counter_type) LIKE 'consecutive day ot%%'
                      OR LOWER(counter_type) LIKE 'consecutive day dt%%'
                      OR LOWER(counter_type) LIKE '%%double time%%'
                      OR LOWER(counter_type) LIKE '%%overtime%%')
            THEN counter_hours ELSE 0 END
        ) AS billable_ot_actual_ot,
        -- Billable OT from Regular/Non-OT counter types
        SUM(
          CASE 
            WHEN COALESCE(NULLIF(TRIM(is_billable_overtime), ''), 'UNKNOWN') = 'OT'
                 AND NOT (LOWER(counter_type) IN ('daily overtime','daily ot','weekly overtime','weekly ot','holiday worked')
                          OR LOWER(counter_type) LIKE 'consecutive day ot%%'
                          OR LOWER(counter_type) LIKE 'consecutive day dt%%'
                          OR LOWER(counter_type) LIKE '%%double time%%'
                          OR LOWER(counter_type) LIKE '%%overtime%%')
            THEN counter_hours ELSE 0 END
        ) AS billable_ot_regular_hours
      FROM `{project}.{dataset}.APEX_Counters`
      WHERE counter_date BETWEEN '{weeks[0]['start_date']}' AND '{weeks[-1]['end_date']}'
      {where_clause}
      GROUP BY week_start
    )
    SELECT 
      week_start,
      customer_name,
      region,
      total_hours,
      unpaid_timeoff_hours,
      total_hourly_hours,
      total_salaried_hours,
      total_1099_hours,
      total_ot_hours,
      billable_ot_hours,
      billable_ot_actual_ot,
      billable_ot_regular_hours,
      -- NBOT = Total OT - Billable OT
      (total_ot_hours - billable_ot_hours) AS nbot_hours,
      -- Percentages
      ROUND(SAFE_DIVIDE(total_hourly_hours, total_hours) * 100, 2) as hourly_pct,
      ROUND(SAFE_DIVIDE(total_salaried_hours, total_hours) * 100, 2) as salaried_pct,
      ROUND(SAFE_DIVIDE(total_1099_hours, total_hours) * 100, 2) as contractor_1099_pct,
      ROUND(SAFE_DIVIDE(total_ot_hours, (total_hours - unpaid_timeoff_hours)) * 100, 2) as total_ot_pct,
      ROUND(SAFE_DIVIDE(billable_ot_hours, (total_hours - unpaid_timeoff_hours)) * 100, 2) as billable_ot_pct,
      ROUND(SAFE_DIVIDE(billable_ot_actual_ot, (total_hours - unpaid_timeoff_hours)) * 100, 2) as billable_ot_actual_ot_pct,
      ROUND(SAFE_DIVIDE(billable_ot_regular_hours, (total_hours - unpaid_timeoff_hours)) * 100, 2) as billable_ot_regular_pct,
      -- NBOT % based on TWH (Total Worked Hours = Total Hours - Unpaid Time Off)
      ROUND(SAFE_DIVIDE((total_ot_hours - billable_ot_hours), (total_hours - unpaid_timeoff_hours)) * 100, 2) as nbot_pct
    FROM WeeklyData
    ORDER BY week_start
    """
    
    # OT Breakdown for most recent week
    ot_breakdown_sql = f"""
    WITH Base AS (
      SELECT
        LOWER(TRIM(counter_type)) AS counter_type,
        SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours,
        COALESCE(NULLIF(TRIM(is_billable_overtime), ''), 'UNKNOWN') AS is_billable_ot
      FROM `{project}.{dataset}.APEX_Counters`
      WHERE counter_date BETWEEN '{weeks[-1]['start_date']}' AND '{weeks[-1]['end_date']}'
      {where_clause}
    ),
    OTByCategory AS (
      SELECT
        CASE
          WHEN counter_type IN ('daily overtime','daily ot') THEN 'Daily Overtime'
          WHEN counter_type IN ('weekly overtime','weekly ot') THEN 'Weekly Overtime'
          WHEN counter_type LIKE '%%double time%%' THEN 'Daily Double Time'
          
          WHEN counter_type LIKE 'consecutive day ot%%' THEN 'Consecutive Day OT'
          WHEN counter_type LIKE 'consecutive day dt%%' THEN 'Consecutive Day DT'
          ELSE 'Other OT'
        END AS ot_category,
        SUM(counter_hours) AS total_ot_hours,
        SUM(CASE WHEN is_billable_ot = 'OT' THEN counter_hours ELSE 0 END) AS billable_hours
      FROM Base
      WHERE (counter_type IN ('daily overtime','daily ot','weekly overtime','weekly ot')
             OR counter_type LIKE 'consecutive day ot%%'
             OR counter_type LIKE 'consecutive day dt%%'
             OR counter_type LIKE '%%double time%%'
             OR counter_type LIKE '%%overtime%%')
      GROUP BY ot_category
    )
    SELECT
      ot_category,
      total_ot_hours,
      billable_hours,
      (total_ot_hours - billable_hours) AS nbot_hours
    FROM OTByCategory
    ORDER BY nbot_hours DESC
    """
    
    # Pay type totals for most recent week
    pay_type_sql = f"""
    WITH Base AS (
      SELECT
        SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours,
        LOWER(TRIM(COALESCE(CAST(pay_type AS STRING), ''))) AS pay_type_raw
      FROM `{project}.{dataset}.APEX_Counters`
      WHERE counter_date BETWEEN '{weeks[-1]['start_date']}' AND '{weeks[-1]['end_date']}'
      {where_clause}
    ),
    Norm AS (
      SELECT
        counter_hours,
        CASE
          WHEN pay_type_raw IN ('hourly','h','non-exempt','nonexempt') THEN 'Hourly'
          WHEN pay_type_raw IN ('salaried','salary','exempt')          THEN 'Salaried'
          WHEN pay_type_raw IN ('1099','contractor','independent','ic') THEN '1099'
          ELSE 'Unknown'
        END AS pay_type
      FROM Base
    )
    SELECT
      SUM(counter_hours) AS total_counter_hours,
      SUM(CASE WHEN pay_type = 'Hourly'   THEN counter_hours ELSE 0 END) AS hourly_hours,
      SUM(CASE WHEN pay_type = 'Salaried' THEN counter_hours ELSE 0 END) AS salaried_hours,
      SUM(CASE WHEN pay_type = '1099'     THEN counter_hours ELSE 0 END) AS contractor_1099_hours,
      SAFE_DIVIDE(SUM(CASE WHEN pay_type = 'Hourly' THEN counter_hours ELSE 0 END), SUM(counter_hours)) * 100 AS hourly_pct,
      SAFE_DIVIDE(SUM(CASE WHEN pay_type = 'Salaried' THEN counter_hours ELSE 0 END), SUM(counter_hours)) * 100 AS salaried_pct,
      SAFE_DIVIDE(SUM(CASE WHEN pay_type = '1099' THEN counter_hours ELSE 0 END), SUM(counter_hours)) * 100 AS contractor_1099_pct
    FROM Norm
    """
    
    # Hourly-only OT composition
    hourly_ot_comp_sql = f"""
    WITH Base AS (
      SELECT
        SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours,
        LOWER(TRIM(counter_type)) AS counter_type,
        LOWER(TRIM(COALESCE(CAST(pay_type AS STRING), ''))) AS pay_type_raw
      FROM `{project}.{dataset}.APEX_Counters`
      WHERE counter_date BETWEEN '{weeks[-1]['start_date']}' AND '{weeks[-1]['end_date']}'
      {where_clause}
    ),
    HourlyOT AS (
      SELECT counter_hours, counter_type
      FROM Base
      WHERE pay_type_raw IN ('hourly','h','non-exempt','nonexempt')
        AND (counter_type IN ('daily overtime','daily ot','weekly overtime','weekly ot')
             OR counter_type LIKE 'consecutive day ot%%'
             OR counter_type LIKE 'consecutive day dt%%'
             OR counter_type LIKE '%%double time%%'
             OR counter_type LIKE '%%overtime%%')
    )
    SELECT
      CASE
        WHEN counter_type IN ('daily overtime','daily ot') THEN 'Daily Overtime'
        WHEN counter_type IN ('weekly overtime','weekly ot') THEN 'Weekly Overtime'
        WHEN counter_type LIKE '%%double time%%' THEN 'Daily Double Time'
        
        WHEN counter_type LIKE 'consecutive day ot%%' THEN 'Consecutive Day OT'
        WHEN counter_type LIKE 'consecutive day dt%%' THEN 'Consecutive Day DT'
        ELSE 'Other OT'
      END AS ot_category,
      SUM(counter_hours) AS ot_hours,
      SAFE_DIVIDE(SUM(counter_hours), (SELECT SUM(counter_hours) FROM HourlyOT)) * 100 AS pct_of_ot
    FROM HourlyOT
    GROUP BY ot_category
    ORDER BY ot_hours DESC
    """
    
    # Billable OT by type
    billable_ot_sql = f"""
    WITH Base AS (
      SELECT
        SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours,
        LOWER(TRIM(counter_type)) AS counter_type,
        LOWER(TRIM(COALESCE(CAST(pay_type AS STRING), ''))) AS pay_type_raw,
        COALESCE(NULLIF(TRIM(is_billable_overtime), ''), 'UNKNOWN') AS is_billable_ot
      FROM `{project}.{dataset}.APEX_Counters`
      WHERE counter_date BETWEEN '{weeks[-1]['start_date']}' AND '{weeks[-1]['end_date']}'
      {where_clause}
    ),
    Billable AS (
      SELECT
        CASE
          WHEN counter_type IN ('daily overtime','daily ot')   THEN 'Daily Overtime'
          WHEN counter_type IN ('weekly overtime','weekly ot') THEN 'Weekly Overtime'
          WHEN counter_type LIKE '%%double time%%'             THEN 'Daily Double Time'
          WHEN counter_type LIKE 'consecutive day ot%%'        THEN 'Consecutive Day OT'
          WHEN counter_type LIKE 'consecutive day dt%%'        THEN 'Consecutive Day DT'
          ELSE 'Regular / Other'
        END AS ot_category,
        SUM(counter_hours) AS billable_hours
      FROM Base
      WHERE pay_type_raw IN ('hourly','h','non-exempt','nonexempt')
        AND is_billable_ot = 'OT'
      GROUP BY ot_category
    )
    SELECT
      ot_category,
      billable_hours,
      SAFE_DIVIDE(billable_hours, (SELECT SUM(billable_hours) FROM Billable)) * 100 AS pct_of_ot
    FROM Billable
    ORDER BY billable_hours DESC
    """
    
    # Site Performance Data (for table)
    site_performance_sql = f"""
    WITH SiteData AS (
      SELECT
        CAST(location_number AS STRING) as location_number,
        ANY_VALUE(city) as city,
        ANY_VALUE(state) as state,
        ANY_VALUE(site_manager) as manager,
        COUNT(DISTINCT employee_id) as employee_count,
        SUM(counter_hours) AS total_hours,
        SUM(
          CASE 
            WHEN (LOWER(counter_type) IN ('daily overtime','daily ot','weekly overtime','weekly ot')
                  OR LOWER(counter_type) LIKE 'consecutive day ot%%'
                  OR LOWER(counter_type) LIKE 'consecutive day dt%%'
                  OR LOWER(counter_type) LIKE '%%double time%%'
                  OR LOWER(counter_type) LIKE '%%overtime%%')
            THEN counter_hours ELSE 0 END
        ) AS total_ot_hours,
        SUM(
          CASE 
            WHEN COALESCE(NULLIF(TRIM(is_billable_overtime), ''), 'UNKNOWN') = 'OT'
            THEN counter_hours ELSE 0 END
        ) AS billable_ot_hours,
        COUNTIF(LOWER(TRIM(counter_type)) = 'sick') as sick_events,
        COUNTIF(LOWER(TRIM(counter_type)) LIKE '%%unpaid time off%%') as unpaid_events
      FROM `{project}.{dataset}.APEX_Counters`
      WHERE counter_date BETWEEN '{weeks[-1]['start_date']}' AND '{weeks[-1]['end_date']}'
      {where_clause}
      GROUP BY location_number
      HAVING total_hours > 0
    )
    SELECT
      location_number,
      city,
      state,
      manager,
      employee_count,
      total_hours,
      total_ot_hours,
      billable_ot_hours,
      (total_ot_hours - billable_ot_hours) as nbot_hours,
      ROUND(SAFE_DIVIDE((total_ot_hours - billable_ot_hours), total_hours) * 100, 2) as nbot_pct,
      ROUND(SAFE_DIVIDE(billable_ot_hours, total_ot_hours) * 100, 1) as billable_capture_rate,
      sick_events,
      unpaid_events,
      (sick_events + unpaid_events) as total_calloffs
    FROM SiteData
    WHERE total_hours >= 100  -- Filter out very small sites
    ORDER BY nbot_hours DESC  -- Order by NBOT hours for Pareto analysis
    LIMIT 50
    """
    
    # Manager Performance Data
    manager_performance_sql = f"""
    WITH ManagerData AS (
      SELECT
        site_manager as manager,
        COUNT(DISTINCT CAST(location_number AS STRING)) as site_count,
        SUM(counter_hours) AS total_hours,
        SUM(
          CASE 
            WHEN (LOWER(counter_type) IN ('daily overtime','daily ot','weekly overtime','weekly ot')
                  OR LOWER(counter_type) LIKE 'consecutive day ot%%'
                  OR LOWER(counter_type) LIKE 'consecutive day dt%%'
                  OR LOWER(counter_type) LIKE '%%double time%%'
                  OR LOWER(counter_type) LIKE '%%overtime%%')
            THEN counter_hours ELSE 0 END
        ) AS total_ot_hours,
        SUM(
          CASE 
            WHEN COALESCE(NULLIF(TRIM(is_billable_overtime), ''), 'UNKNOWN') = 'OT'
            THEN counter_hours ELSE 0 END
        ) AS billable_ot_hours
      FROM `{project}.{dataset}.APEX_Counters`
      WHERE counter_date BETWEEN '{weeks[-1]['start_date']}' AND '{weeks[-1]['end_date']}'
      {where_clause}
      GROUP BY manager
      HAVING total_hours > 0
    )
    SELECT
      manager,
      site_count,
      total_hours,
      total_ot_hours,
      billable_ot_hours,
      (total_ot_hours - billable_ot_hours) as nbot_hours,
      ROUND(SAFE_DIVIDE((total_ot_hours - billable_ot_hours), total_hours) * 100, 2) as nbot_pct,
      ROUND(SAFE_DIVIDE(billable_ot_hours, total_ot_hours) * 100, 1) as billable_capture_rate
    FROM ManagerData
    WHERE total_hours >= 100
    ORDER BY nbot_pct DESC
    LIMIT 30
    """
    
    # Workforce Analysis - Current Week
    workforce_current_sql = f"""
    WITH EmployeeData AS (
      SELECT
        employee_id,
        ANY_VALUE(employee_status) as employee_status,
        ANY_VALUE(employee_date_started) as hire_date,
        SUM(counter_hours) as total_hours,
        COUNTIF(LOWER(TRIM(counter_type)) = 'sick') as sick_events,
        COUNTIF(LOWER(TRIM(counter_type)) LIKE '%%unpaid time off%%') as unpaid_events,
        SUM(CASE WHEN LOWER(TRIM(counter_type)) = 'sick' THEN counter_hours ELSE 0 END) as sick_hours,
        SUM(CASE WHEN LOWER(TRIM(counter_type)) LIKE '%%unpaid time off%%' THEN counter_hours ELSE 0 END) as unpaid_hours
      FROM `{project}.{dataset}.APEX_Counters`
      WHERE counter_date BETWEEN '{weeks[-1]['start_date']}' AND '{weeks[-1]['end_date']}'
      {where_clause}
      GROUP BY employee_id
    ),
    Metrics AS (
    SELECT
        COUNT(DISTINCT employee_id) as total_employees,
        COUNTIF(TRIM(employee_status) LIKE 'Active%' AND TRIM(employee_status) NOT LIKE '%Bench%') as active_employees,
        COUNTIF(TRIM(employee_status) LIKE '%Bench%') as active_bench,
        AVG(total_hours) as avg_utilization,
        AVG(CASE WHEN TRIM(employee_status) LIKE 'Active%' AND TRIM(employee_status) NOT LIKE '%Bench%' THEN total_hours ELSE NULL END) as avg_utilization_active,
        AVG(CASE WHEN TRIM(employee_status) LIKE '%Bench%' THEN total_hours ELSE NULL END) as avg_utilization_bench,
        AVG(DATE_DIFF(CURRENT_DATE(), SAFE_CAST(hire_date AS DATE), DAY)) as avg_tenure_days,
        AVG(CASE WHEN TRIM(employee_status) LIKE 'Active%' AND TRIM(employee_status) NOT LIKE '%Bench%' THEN DATE_DIFF(CURRENT_DATE(), SAFE_CAST(hire_date AS DATE), DAY) ELSE NULL END) as avg_tenure_days_active,
        AVG(CASE WHEN TRIM(employee_status) LIKE '%Bench%' THEN DATE_DIFF(CURRENT_DATE(), SAFE_CAST(hire_date AS DATE), DAY) ELSE NULL END) as avg_tenure_days_bench,
        SUM(sick_events) as total_sick_events,
        SUM(unpaid_events) as total_unpaid_events,
        SUM(sick_hours) as total_sick_hours,
        SUM(unpaid_hours) as total_unpaid_hours,
        SUM(total_hours) as total_hours
      FROM EmployeeData
    )
    SELECT
        total_employees,
        active_employees,
        active_bench,
        ROUND(avg_utilization, 1) as avg_utilization,
        ROUND(avg_utilization_active, 1) as avg_utilization_active,
        ROUND(avg_utilization_bench, 1) as avg_utilization_bench,
        ROUND(avg_tenure_days, 0) as avg_tenure_days,
        ROUND(avg_tenure_days_active, 0) as avg_tenure_days_active,
        ROUND(avg_tenure_days_bench, 0) as avg_tenure_days_bench,
        total_sick_events,
        total_unpaid_events,
        ROUND(total_sick_hours, 2) as total_sick_hours,
        ROUND(total_unpaid_hours, 2) as total_unpaid_hours,
        ROUND(total_hours, 2) as total_hours
    FROM Metrics
    """
    
        # Workforce Analysis - Previous Week (for WoW comparison)
    workforce_previous_sql = f"""
    WITH EmployeeData AS (
    SELECT
        employee_id,
        ANY_VALUE(employee_status) as employee_status,
        ANY_VALUE(employee_date_started) as hire_date,
        SUM(counter_hours) as total_hours,
        COUNTIF(LOWER(TRIM(counter_type)) = 'sick') as sick_events,
        COUNTIF(LOWER(TRIM(counter_type)) LIKE '%%unpaid time off%%') as unpaid_events
    FROM `{project}.{dataset}.APEX_Counters`
    WHERE counter_date BETWEEN '{weeks[-2]['start_date']}' AND '{weeks[-2]['end_date']}'
    {where_clause}
    GROUP BY employee_id
    ),
    Metrics AS (
    SELECT
        COUNT(DISTINCT employee_id) as total_employees,
        COUNTIF(employee_status LIKE 'Active%' AND employee_status != 'Active - Bench') as active_employees,
        COUNTIF(employee_status = 'Active - Bench') as active_bench,
        AVG(total_hours) as avg_utilization,
        AVG(CASE WHEN employee_status LIKE 'Active%' AND employee_status != 'Active - Bench' THEN total_hours END) as avg_utilization_active,
        AVG(CASE WHEN employee_status = 'Active - Bench' THEN total_hours END) as avg_utilization_bench,
        AVG(DATE_DIFF(CURRENT_DATE(), SAFE_CAST(hire_date AS DATE), DAY)) as avg_tenure_days,
        AVG(CASE WHEN employee_status LIKE 'Active%' AND employee_status != 'Active - Bench' THEN DATE_DIFF(CURRENT_DATE(), SAFE_CAST(hire_date AS DATE), DAY) END) as avg_tenure_days_active,
        AVG(CASE WHEN employee_status = 'Active - Bench' THEN DATE_DIFF(CURRENT_DATE(), SAFE_CAST(hire_date AS DATE), DAY) END) as avg_tenure_days_bench,
        SUM(sick_events) as total_sick_events,
        SUM(unpaid_events) as total_unpaid_events
    FROM EmployeeData
    )
    SELECT * FROM Metrics
    """

    # Workforce Analysis - All 4 Weeks (for absenteeism chart)
    workforce_all_weeks_sql = f"""
    WITH EmployeeData AS (
      SELECT
        DATE_TRUNC(counter_date, WEEK(SUNDAY)) as week_start,
        employee_id,
        COUNTIF(LOWER(TRIM(counter_type)) = 'sick') as sick_events,
        COUNTIF(LOWER(TRIM(counter_type)) LIKE '%%unpaid time off%%') as unpaid_events
      FROM `{project}.{dataset}.APEX_Counters`
      WHERE counter_date BETWEEN '{weeks[0]['start_date']}' AND '{weeks[-1]['end_date']}'
      {where_clause}
      GROUP BY week_start, employee_id
    ),
    WeeklyMetrics AS (
      SELECT
        week_start,
        SUM(sick_events) as total_sick_events,
        SUM(unpaid_events) as total_unpaid_events
      FROM EmployeeData
      GROUP BY week_start
    )
    SELECT 
      week_start,
      total_sick_events,
      total_unpaid_events
    FROM WeeklyMetrics
    ORDER BY week_start
    """
    
        # Employee Call-Out Details (last 4 weeks)
    employee_callout_sql = f"""
    WITH EmployeeCallouts AS (
    SELECT
        employee_id,
        ANY_VALUE(employee_name) as employee_name,
        ANY_VALUE(employee_status) as employee_status,
        ANY_VALUE(CAST(location_number AS STRING)) as location_number,
        ANY_VALUE(city) as city,
        ANY_VALUE(state) as state,
        -- Last week hours (most recent week)
        SUM(CASE 
        WHEN counter_date BETWEEN '{weeks[-1]['start_date']}' AND '{weeks[-1]['end_date']}'
        THEN counter_hours ELSE 0 END
        ) as last_week_hours,
        -- Total hours last 4 weeks
        SUM(counter_hours) as total_hours_4weeks,
        -- Sick call-outs
        COUNTIF(LOWER(TRIM(counter_type)) = 'sick') as sick_callouts,
        -- Unpaid time off call-outs
        COUNTIF(LOWER(TRIM(counter_type)) LIKE '%unpaid time off%') as unpaid_callouts,
        -- Sick hours
        SUM(CASE WHEN LOWER(TRIM(counter_type)) = 'sick' THEN counter_hours ELSE 0 END) as sick_hours,
        -- Unpaid hours
        SUM(CASE WHEN LOWER(TRIM(counter_type)) LIKE '%unpaid time off%' THEN counter_hours ELSE 0 END) as unpaid_hours
    FROM `{project}.{dataset}.APEX_Counters`
    WHERE counter_date BETWEEN '{weeks[0]['start_date']}' AND '{weeks[-1]['end_date']}'
    {where_clause}
    GROUP BY employee_id
    )
    SELECT
    employee_id,
    employee_name,
    employee_status,
    location_number,
    city,
    state,
    ROUND(total_hours_4weeks / 4, 1) as avg_hours_per_week,
    ROUND(last_week_hours, 1) as last_week_hours,
    sick_callouts,
    unpaid_callouts,
    (sick_callouts + unpaid_callouts) as total_callouts,
    ROUND(sick_hours, 1) as sick_hours,
    ROUND(unpaid_hours, 1) as unpaid_hours,
    ROUND(sick_hours + unpaid_hours, 1) as total_callout_hours
    FROM EmployeeCallouts
    WHERE (sick_callouts + unpaid_callouts) > 0
    ORDER BY total_callouts DESC, total_callout_hours DESC
    LIMIT 150
    """


                # Employee Call-Out Details - TOP 2 DAYS WORKING VERSION (last 4 weeks)
    employee_callout_sql = f"""
    WITH EmployeeCallouts AS (
    SELECT
        employee_id,
        ANY_VALUE(employee_name) as employee_name,
        ANY_VALUE(employee_status) as employee_status,
        ANY_VALUE(CAST(location_number AS STRING)) as location_number,
        ANY_VALUE(city) as city,
        ANY_VALUE(state) as state,
        SUM(CASE 
        WHEN counter_date BETWEEN '{weeks[-1]['start_date']}' AND '{weeks[-1]['end_date']}'
        THEN counter_hours ELSE 0 END
        ) as last_week_hours,
        SUM(counter_hours) as total_hours_4weeks,
        COUNTIF(LOWER(TRIM(counter_type)) = 'sick') as sick_callouts,
        COUNTIF(LOWER(TRIM(counter_type)) LIKE '%unpaid time off%') as unpaid_callouts,
        SUM(CASE WHEN LOWER(TRIM(counter_type)) = 'sick' THEN counter_hours ELSE 0 END) as sick_hours,
        SUM(CASE WHEN LOWER(TRIM(counter_type)) LIKE '%unpaid time off%' THEN counter_hours ELSE 0 END) as unpaid_hours,
        
        -- Day counts
        COUNTIF((LOWER(TRIM(counter_type)) = 'sick' OR LOWER(TRIM(counter_type)) LIKE '%unpaid time off%') 
                AND EXTRACT(DAYOFWEEK FROM counter_date) = 2) as monday_callouts,
        COUNTIF((LOWER(TRIM(counter_type)) = 'sick' OR LOWER(TRIM(counter_type)) LIKE '%unpaid time off%') 
                AND EXTRACT(DAYOFWEEK FROM counter_date) = 3) as tuesday_callouts,
        COUNTIF((LOWER(TRIM(counter_type)) = 'sick' OR LOWER(TRIM(counter_type)) LIKE '%unpaid time off%') 
                AND EXTRACT(DAYOFWEEK FROM counter_date) = 4) as wednesday_callouts,
        COUNTIF((LOWER(TRIM(counter_type)) = 'sick' OR LOWER(TRIM(counter_type)) LIKE '%unpaid time off%') 
                AND EXTRACT(DAYOFWEEK FROM counter_date) = 5) as thursday_callouts,
        COUNTIF((LOWER(TRIM(counter_type)) = 'sick' OR LOWER(TRIM(counter_type)) LIKE '%unpaid time off%') 
                AND EXTRACT(DAYOFWEEK FROM counter_date) = 6) as friday_callouts,
        COUNTIF((LOWER(TRIM(counter_type)) = 'sick' OR LOWER(TRIM(counter_type)) LIKE '%unpaid time off%') 
                AND EXTRACT(DAYOFWEEK FROM counter_date) IN (1, 7)) as weekend_callouts
                
    FROM `{project}.{dataset}.APEX_Counters`
    WHERE counter_date BETWEEN '{weeks[0]['start_date']}' AND '{weeks[-1]['end_date']}'
    {where_clause}
    GROUP BY employee_id
    ),
    RankedDays AS (
    SELECT
        *,
        (sick_callouts + unpaid_callouts) as total_callouts,
        ROUND(sick_hours + unpaid_hours, 1) as total_callout_hours,
        
        -- Find Day #1 (highest count)
        GREATEST(monday_callouts, tuesday_callouts, wednesday_callouts, thursday_callouts, friday_callouts, weekend_callouts) as day1_count,
        
        CASE 
        WHEN GREATEST(monday_callouts, tuesday_callouts, wednesday_callouts, thursday_callouts, friday_callouts, weekend_callouts) = monday_callouts THEN 'Monday'
        WHEN GREATEST(monday_callouts, tuesday_callouts, wednesday_callouts, thursday_callouts, friday_callouts, weekend_callouts) = tuesday_callouts THEN 'Tuesday'
        WHEN GREATEST(monday_callouts, tuesday_callouts, wednesday_callouts, thursday_callouts, friday_callouts, weekend_callouts) = wednesday_callouts THEN 'Wednesday'
        WHEN GREATEST(monday_callouts, tuesday_callouts, wednesday_callouts, thursday_callouts, friday_callouts, weekend_callouts) = thursday_callouts THEN 'Thursday'
        WHEN GREATEST(monday_callouts, tuesday_callouts, wednesday_callouts, thursday_callouts, friday_callouts, weekend_callouts) = friday_callouts THEN 'Friday'
        WHEN GREATEST(monday_callouts, tuesday_callouts, wednesday_callouts, thursday_callouts, friday_callouts, weekend_callouts) = weekend_callouts THEN 'Weekend'
        ELSE 'None'
        END as day1_name
        
    FROM EmployeeCallouts
    ),
    WithSecondDay AS (
    SELECT
        *,
        -- Find Day #2 (second highest, excluding Day #1)
        CASE day1_name
        WHEN 'Monday' THEN GREATEST(tuesday_callouts, wednesday_callouts, thursday_callouts, friday_callouts, weekend_callouts)
        WHEN 'Tuesday' THEN GREATEST(monday_callouts, wednesday_callouts, thursday_callouts, friday_callouts, weekend_callouts)
        WHEN 'Wednesday' THEN GREATEST(monday_callouts, tuesday_callouts, thursday_callouts, friday_callouts, weekend_callouts)
        WHEN 'Thursday' THEN GREATEST(monday_callouts, tuesday_callouts, wednesday_callouts, friday_callouts, weekend_callouts)
        WHEN 'Friday' THEN GREATEST(monday_callouts, tuesday_callouts, wednesday_callouts, thursday_callouts, weekend_callouts)
        WHEN 'Weekend' THEN GREATEST(monday_callouts, tuesday_callouts, wednesday_callouts, thursday_callouts, friday_callouts)
        ELSE 0
        END as day2_count,
        
        CASE 
        WHEN day1_name != 'Monday' AND 
            CASE day1_name
                WHEN 'Tuesday' THEN GREATEST(monday_callouts, wednesday_callouts, thursday_callouts, friday_callouts, weekend_callouts)
                WHEN 'Wednesday' THEN GREATEST(monday_callouts, tuesday_callouts, thursday_callouts, friday_callouts, weekend_callouts)
                WHEN 'Thursday' THEN GREATEST(monday_callouts, tuesday_callouts, wednesday_callouts, friday_callouts, weekend_callouts)
                WHEN 'Friday' THEN GREATEST(monday_callouts, tuesday_callouts, wednesday_callouts, thursday_callouts, weekend_callouts)
                WHEN 'Weekend' THEN GREATEST(monday_callouts, tuesday_callouts, wednesday_callouts, thursday_callouts, friday_callouts)
                ELSE 0
            END = monday_callouts 
        THEN 'Monday'
        
        WHEN day1_name != 'Tuesday' AND 
            CASE day1_name
                WHEN 'Monday' THEN GREATEST(tuesday_callouts, wednesday_callouts, thursday_callouts, friday_callouts, weekend_callouts)
                WHEN 'Wednesday' THEN GREATEST(monday_callouts, tuesday_callouts, thursday_callouts, friday_callouts, weekend_callouts)
                WHEN 'Thursday' THEN GREATEST(monday_callouts, tuesday_callouts, wednesday_callouts, friday_callouts, weekend_callouts)
                WHEN 'Friday' THEN GREATEST(monday_callouts, tuesday_callouts, wednesday_callouts, thursday_callouts, weekend_callouts)
                WHEN 'Weekend' THEN GREATEST(monday_callouts, tuesday_callouts, wednesday_callouts, thursday_callouts, friday_callouts)
                ELSE 0
            END = tuesday_callouts 
        THEN 'Tuesday'
        
        WHEN day1_name != 'Wednesday' AND 
            CASE day1_name
                WHEN 'Monday' THEN GREATEST(tuesday_callouts, wednesday_callouts, thursday_callouts, friday_callouts, weekend_callouts)
                WHEN 'Tuesday' THEN GREATEST(monday_callouts, wednesday_callouts, thursday_callouts, friday_callouts, weekend_callouts)
                WHEN 'Thursday' THEN GREATEST(monday_callouts, tuesday_callouts, wednesday_callouts, friday_callouts, weekend_callouts)
                WHEN 'Friday' THEN GREATEST(monday_callouts, tuesday_callouts, wednesday_callouts, thursday_callouts, weekend_callouts)
                WHEN 'Weekend' THEN GREATEST(monday_callouts, tuesday_callouts, wednesday_callouts, thursday_callouts, friday_callouts)
                ELSE 0
            END = wednesday_callouts 
        THEN 'Wednesday'
        
        WHEN day1_name != 'Thursday' AND 
            CASE day1_name
                WHEN 'Monday' THEN GREATEST(tuesday_callouts, wednesday_callouts, thursday_callouts, friday_callouts, weekend_callouts)
                WHEN 'Tuesday' THEN GREATEST(monday_callouts, wednesday_callouts, thursday_callouts, friday_callouts, weekend_callouts)
                WHEN 'Wednesday' THEN GREATEST(monday_callouts, tuesday_callouts, thursday_callouts, friday_callouts, weekend_callouts)
                WHEN 'Friday' THEN GREATEST(monday_callouts, tuesday_callouts, wednesday_callouts, thursday_callouts, weekend_callouts)
                WHEN 'Weekend' THEN GREATEST(monday_callouts, tuesday_callouts, wednesday_callouts, thursday_callouts, friday_callouts)
                ELSE 0
            END = thursday_callouts 
        THEN 'Thursday'
        
        WHEN day1_name != 'Friday' AND 
            CASE day1_name
                WHEN 'Monday' THEN GREATEST(tuesday_callouts, wednesday_callouts, thursday_callouts, friday_callouts, weekend_callouts)
                WHEN 'Tuesday' THEN GREATEST(monday_callouts, wednesday_callouts, thursday_callouts, friday_callouts, weekend_callouts)
                WHEN 'Wednesday' THEN GREATEST(monday_callouts, tuesday_callouts, thursday_callouts, friday_callouts, weekend_callouts)
                WHEN 'Thursday' THEN GREATEST(monday_callouts, tuesday_callouts, wednesday_callouts, friday_callouts, weekend_callouts)
                WHEN 'Weekend' THEN GREATEST(monday_callouts, tuesday_callouts, wednesday_callouts, thursday_callouts, friday_callouts)
                ELSE 0
            END = friday_callouts 
        THEN 'Friday'
        
        WHEN day1_name != 'Weekend' AND 
            CASE day1_name
                WHEN 'Monday' THEN GREATEST(tuesday_callouts, wednesday_callouts, thursday_callouts, friday_callouts, weekend_callouts)
                WHEN 'Tuesday' THEN GREATEST(monday_callouts, wednesday_callouts, thursday_callouts, friday_callouts, weekend_callouts)
                WHEN 'Wednesday' THEN GREATEST(monday_callouts, tuesday_callouts, thursday_callouts, friday_callouts, weekend_callouts)
                WHEN 'Thursday' THEN GREATEST(monday_callouts, tuesday_callouts, wednesday_callouts, friday_callouts, weekend_callouts)
                WHEN 'Friday' THEN GREATEST(monday_callouts, tuesday_callouts, wednesday_callouts, thursday_callouts, weekend_callouts)
                ELSE 0
            END = weekend_callouts 
        THEN 'Weekend'
        
        ELSE 'None'
        END as day2_name
        
    FROM RankedDays
    )
    SELECT
    employee_id,
    employee_name,
    employee_status,
    location_number,
    city,
    state,
    ROUND(total_hours_4weeks / 4, 1) as avg_hours_per_week,
    ROUND(last_week_hours, 1) as last_week_hours,
    sick_callouts,
    unpaid_callouts,
    total_callouts,
    ROUND(sick_hours, 1) as sick_hours,
    ROUND(unpaid_hours, 1) as unpaid_hours,
    total_callout_hours,
    
    -- Top 2 Days Display
    CASE 
        WHEN day2_count > 0 AND day2_count < day1_count 
        THEN CONCAT(day1_name, ' (', day1_count, '), ', day2_name, ' (', day2_count, ')')
        WHEN day2_count > 0 AND day2_count = day1_count
        THEN CONCAT(day1_name, ' & ', day2_name, ' (', day1_count, ' each)')
        WHEN day1_count > 0
        THEN CONCAT(day1_name, ' (', day1_count, ')')
        ELSE 'No Pattern'
    END as top_2_days,
    
    -- Pattern type
    CASE
        WHEN total_callouts >= 3 AND weekend_callouts >= (total_callouts * 0.5) THEN '🔴 Weekend Pattern'
        WHEN total_callouts >= 2 AND (monday_callouts + weekend_callouts) >= (total_callouts * 0.7) THEN '🔴 Long Weekend (Mon)'
        WHEN total_callouts >= 2 AND (friday_callouts + weekend_callouts) >= (total_callouts * 0.7) THEN '🔴 Long Weekend (Fri)'
        WHEN total_callouts >= 3 AND monday_callouts >= (total_callouts * 0.5) THEN '🔴 Monday Pattern'
        WHEN total_callouts >= 3 AND friday_callouts >= (total_callouts * 0.5) THEN '🔴 Friday Pattern'
        WHEN total_callouts >= 2 AND (monday_callouts + friday_callouts) >= (total_callouts * 0.7) THEN '🟡 Mon/Fri Pattern'
        WHEN total_callouts >= 3 AND (tuesday_callouts + wednesday_callouts + thursday_callouts) >= (total_callouts * 0.7) THEN '🟢 Mid-week'
        WHEN total_callouts = 1 THEN '⚪ Single Event'
        ELSE '🔵 Mixed Pattern'
    END as pattern_type,
    
    CONCAT('M:', monday_callouts, ' Tu:', tuesday_callouts, ' W:', wednesday_callouts, 
            ' Th:', thursday_callouts, ' F:', friday_callouts, ' Weekend:', weekend_callouts) as day_breakdown
            
    FROM WithSecondDay
    WHERE total_callouts > 0
    ORDER BY total_callouts DESC, total_callout_hours DESC
    LIMIT 100
"""


    try:
        client = bigquery.Client(project=compute_project)
        weekly_data = client.query(weekly_metrics_sql).to_dataframe().to_dict(orient="records")
        ot_breakdown = client.query(ot_breakdown_sql).to_dataframe().to_dict(orient="records")
        pay_type_data = client.query(pay_type_sql).to_dataframe().to_dict(orient="records")
        hourly_ot_comp = client.query(hourly_ot_comp_sql).to_dataframe().to_dict(orient="records")
        billable_ot_data = client.query(billable_ot_sql).to_dataframe().to_dict(orient="records")
        site_performance = client.query(site_performance_sql).to_dataframe().to_dict(orient="records")
        manager_performance = client.query(manager_performance_sql).to_dataframe().to_dict(orient="records")
        workforce_current = client.query(workforce_current_sql).to_dataframe().to_dict(orient="records")
        workforce_previous = client.query(workforce_previous_sql).to_dataframe().to_dict(orient="records")
        workforce_all_weeks = client.query(workforce_all_weeks_sql).to_dataframe().to_dict(orient="records")
        employee_callouts = client.query(employee_callout_sql).to_dataframe().to_dict(orient="records")


        
        # Clean manager names in site performance data
        for row in site_performance:
            if 'manager' in row:
                row['manager'] = clean_site_manager_name(row['manager'])
        
        # Calculate Pareto metrics for site performance
        if site_performance:
            total_nbot_all_sites = sum(float(site.get('nbot_hours', 0)) for site in site_performance)
            cumulative_nbot = 0
            pareto_80_reached = False
            pareto_80_count = 0
            
            for idx, site in enumerate(site_performance):
                nbot_hours = float(site.get('nbot_hours', 0))
                site['nbot_contribution_pct'] = round((nbot_hours / total_nbot_all_sites * 100) if total_nbot_all_sites > 0 else 0, 2)
                cumulative_nbot += nbot_hours
                site['cumulative_nbot_pct'] = round((cumulative_nbot / total_nbot_all_sites * 100) if total_nbot_all_sites > 0 else 0, 2)
                
                # Mark sites in top 80% (Pareto principle)
                if not pareto_80_reached and site['cumulative_nbot_pct'] <= 80:
                    site['is_pareto_80'] = True
                    pareto_80_count = idx + 1
                elif not pareto_80_reached and site['cumulative_nbot_pct'] > 80:
                    site['is_pareto_80'] = True
                    pareto_80_count = idx + 1
                    pareto_80_reached = True
                else:
                    site['is_pareto_80'] = False
            
            # Calculate Pareto stats
            pareto_stats = {
                'total_sites': len(site_performance),
                'pareto_80_count': pareto_80_count,
                'pareto_80_pct': round((pareto_80_count / len(site_performance) * 100) if len(site_performance) > 0 else 0, 1),
                'top_3_nbot': sum(float(site.get('nbot_hours', 0)) for site in site_performance[:3]),
                'top_3_pct': round((sum(float(site.get('nbot_hours', 0)) for site in site_performance[:3]) / total_nbot_all_sites * 100) if total_nbot_all_sites > 0 else 0, 1)
            }
        else:
            pareto_stats = None
        
        # Clean manager names in manager performance data
        for row in manager_performance:
            if 'manager' in row:
                row['manager'] = clean_site_manager_name(row['manager'])
                
    except Exception as e:
        return f"Query failed: {str(e)}"
    
    if not weekly_data:
        return f"No data found for date range with specified scope"
    
    # Update scope_name if we got customer_name or region from data
    if customer_code and weekly_data:
        scope_name = weekly_data[0].get('customer_name', f'Customer {customer_code}')
        if location_number:
            scope_name = f"{scope_name} - Location {location_number}"
    elif region and weekly_data:
        scope_name = weekly_data[0].get('region', region)
    
    # Match weeks with data and populate all fields
    for week in weeks:
        matching_data = next((d for d in weekly_data if d['week_start'].strftime('%Y-%m-%d') == week['start_date']), None)
        if matching_data:
            week['total_hours'] = float(matching_data['total_hours'] or 0)
            week['unpaid_timeoff_hours'] = float(matching_data['unpaid_timeoff_hours'] or 0)
            week['twh'] = week['total_hours'] - week['unpaid_timeoff_hours']
            week['total_hourly_hours'] = float(matching_data['total_hourly_hours'] or 0)
            week['total_salaried_hours'] = float(matching_data['total_salaried_hours'] or 0)
            week['total_1099_hours'] = float(matching_data['total_1099_hours'] or 0)
            week['total_ot_hours'] = float(matching_data['total_ot_hours'] or 0)
            week['billable_ot_hours'] = float(matching_data['billable_ot_hours'] or 0)
            week['billable_ot_actual_ot'] = float(matching_data['billable_ot_actual_ot'] or 0)
            week['billable_ot_regular_hours'] = float(matching_data['billable_ot_regular_hours'] or 0)
            week['nbot_hours'] = float(matching_data['nbot_hours'] or 0)
            week['hourly_pct'] = float(matching_data['hourly_pct'] or 0)
            week['salaried_pct'] = float(matching_data['salaried_pct'] or 0)
            week['contractor_1099_pct'] = float(matching_data['contractor_1099_pct'] or 0)
            week['total_ot_pct'] = float(matching_data['total_ot_pct'] or 0)
            week['billable_ot_pct'] = float(matching_data['billable_ot_pct'] or 0)
            week['billable_ot_actual_ot_pct'] = float(matching_data['billable_ot_actual_ot_pct'] or 0)
            week['billable_ot_regular_pct'] = float(matching_data['billable_ot_regular_pct'] or 0)
            week['nbot_pct'] = float(matching_data['nbot_pct'] or 0)
        else:
            week['total_hours'] = 0
            week['unpaid_timeoff_hours'] = 0
            week['twh'] = 0
            week['total_hourly_hours'] = 0
            week['total_salaried_hours'] = 0
            week['total_1099_hours'] = 0
            week['total_ot_hours'] = 0
            week['billable_ot_hours'] = 0
            week['billable_ot_actual_ot'] = 0
            week['billable_ot_regular_hours'] = 0
            week['nbot_hours'] = 0
            week['hourly_pct'] = 0
            week['salaried_pct'] = 0
            week['contractor_1099_pct'] = 0
            week['total_ot_pct'] = 0
            week['billable_ot_pct'] = 0
            week['billable_ot_actual_ot_pct'] = 0
            week['billable_ot_regular_pct'] = 0
            week['nbot_pct'] = 0
    
    # Match workforce data to weeks for absenteeism chart
    for week in weeks:
        matching_workforce = next((d for d in workforce_all_weeks if d['week_start'].strftime('%Y-%m-%d') == week['start_date']), None)
        if matching_workforce:
            week['sick_events'] = int(matching_workforce.get('total_sick_events', 0))
            week['unpaid_events'] = int(matching_workforce.get('total_unpaid_events', 0))
            week['total_callouts'] = week['sick_events'] + week['unpaid_events']
        else:
            week['sick_events'] = 0
            week['unpaid_events'] = 0
            week['total_callouts'] = 0
    
    # Calculate changes
    latest_week = weeks[-1]
    first_week = weeks[0]
    prev_week = weeks[-2] if len(weeks) > 1 else weeks[-1]
    
    # Calculate WoW (Week-over-Week) deltas for all metrics
    wow_deltas = {
        'total_hours': latest_week['total_hours'] - prev_week['total_hours'],
        'twh': latest_week['twh'] - prev_week['twh'],
        'hourly_hours': latest_week['total_hourly_hours'] - prev_week['total_hourly_hours'],
        'hourly_pct': latest_week['hourly_pct'] - prev_week['hourly_pct'],
        'salaried_hours': latest_week['total_salaried_hours'] - prev_week['total_salaried_hours'],
        'salaried_pct': latest_week['salaried_pct'] - prev_week['salaried_pct'],
        '1099_hours': latest_week['total_1099_hours'] - prev_week['total_1099_hours'],
        '1099_pct': latest_week['contractor_1099_pct'] - prev_week['contractor_1099_pct'],
        'ot_hours': latest_week['total_ot_hours'] - prev_week['total_ot_hours'],
        'ot_pct': latest_week['total_ot_pct'] - prev_week['total_ot_pct'],
        'billable_hours': latest_week['billable_ot_hours'] - prev_week['billable_ot_hours'],
        'billable_pct': latest_week['billable_ot_pct'] - prev_week['billable_ot_pct'],
        'billable_actual_ot_hours': latest_week['billable_ot_actual_ot'] - prev_week['billable_ot_actual_ot'],
        'billable_actual_ot_pct': latest_week['billable_ot_actual_ot_pct'] - prev_week['billable_ot_actual_ot_pct'],
        'billable_regular_hours': latest_week['billable_ot_regular_hours'] - prev_week['billable_ot_regular_hours'],
        'billable_regular_pct': latest_week['billable_ot_regular_pct'] - prev_week['billable_ot_regular_pct'],
        'nbot_hours': latest_week['nbot_hours'] - prev_week['nbot_hours'],
        'nbot_pct': latest_week['nbot_pct'] - prev_week['nbot_pct']
    }
    
     # Calculate NBOT 4-week changes
    nbot_pct_change = latest_week['nbot_pct'] - first_week['nbot_pct']
    nbot_hours_change = latest_week['nbot_hours'] - first_week['nbot_hours']

    # Calculate Total OT and Billable OT 4-week changes
    total_ot_hours_change = latest_week['total_ot_hours'] - first_week['total_ot_hours']
    total_ot_pct_change = latest_week['total_ot_pct'] - first_week['total_ot_pct']
    billable_ot_hours_change = latest_week['billable_ot_hours'] - first_week['billable_ot_hours']
    billable_ot_pct_change = latest_week['billable_ot_pct'] - first_week['billable_ot_pct']
        
    # Calculate OT breakdown percentages
    total_nbot_latest = latest_week['nbot_hours']
    total_nbot_from_breakdown = sum(float(item.get('nbot_hours', 0)) for item in ot_breakdown) if ot_breakdown else 0
    
    # Use the larger of the two to avoid >100% individual percentages
    denominator = max(total_nbot_latest, total_nbot_from_breakdown) if total_nbot_from_breakdown > 0 else total_nbot_latest
    
    for item in ot_breakdown:
        item['percentage'] = round((float(item['nbot_hours']) / denominator * 100), 1) if denominator > 0 else 0
    
    # Use the larger of the two to avoid >100% individual percentages
    denominator = max(total_nbot_latest, total_nbot_from_breakdown) if total_nbot_from_breakdown > 0 else total_nbot_latest
    
    for item in ot_breakdown:
        item['percentage'] = round((float(item['nbot_hours']) / denominator * 100), 1) if denominator > 0 else 0
    
    # Process pay type data
    pay_type = pay_type_data[0] if pay_type_data else {}
    
    # Calculate NBOT breakdown by counter type
    total_ot_from_comp = sum(float(r.get("ot_hours", 0) or 0) for r in hourly_ot_comp) if hourly_ot_comp else 0.0
    
    # Build bill_map
    bill_map = {r.get("ot_category"): float(r.get("billable_hours") or 0) for r in billable_ot_data}
    
    # Calculate total billable
    total_billable_all = sum(float(r.get("billable_hours") or 0) for r in billable_ot_data)
    
    # Calculate billable from OT categories only
    billable_from_ot_cats = sum(bill_map.get(r.get("ot_category"), 0.0) for r in hourly_ot_comp)
    
    # Unmatched billable
    unmatched_billable = total_billable_all - billable_from_ot_cats
    
    # Build NBOT rows
    nbot_breakdown = []
    for r in hourly_ot_comp:
        cat = r.get("ot_category")
        ot_h = float(r.get("ot_hours") or 0)
        bill_h = bill_map.get(cat, 0.0)
        nbot_h = max(ot_h - bill_h, 0.0)
        nbot_breakdown.append({
            "ot_category": cat,
            "nbot_hours": nbot_h,
            "pct_of_ot": round((nbot_h / total_ot_from_comp * 100) if total_ot_from_comp else 0.0, 1)
        })
    
    # Adjust for unmatched billable
    if unmatched_billable > 0 and nbot_breakdown:
        max_idx = max(range(len(nbot_breakdown)), key=lambda i: nbot_breakdown[i]["nbot_hours"])
        nbot_breakdown[max_idx]["nbot_hours"] = max(nbot_breakdown[max_idx]["nbot_hours"] - unmatched_billable, 0.0)
        
        # Recalculate percentages
        for r in nbot_breakdown:
            r["pct_of_ot"] = round((r["nbot_hours"] / total_ot_from_comp * 100) if total_ot_from_comp else 0.0, 1)
    
    # Determine status
    if latest_week['nbot_pct'] < 3:
        status = "🟢 Acceptable"
        status_class = "success"
    elif latest_week['nbot_pct'] < 4:
        status = "🟡 Needs Improvement"
        status_class = "warning"
    else:
        status = "🔴 Critical"
        status_class = "critical"
    
    # Add dynamic status message
    nbot_change = wow_deltas['nbot_pct']
    
    if abs(nbot_change) < 0.1:
        status_change = "Remained steady"
        status_trend = "➡️"
    elif nbot_change < 0:
        status_change = f"Decreased by {abs(nbot_change):.2f}%"
        status_trend = "⬇️"
    else:
        status_change = f"Increased by {abs(nbot_change):.2f}%"
        status_trend = "⬆️"
    
    status_with_trend = f"{status}<br><span style='font-size: 0.75em; font-weight: 600;'>{status_trend} {status_change} since Week {prev_week['week_num']}</span>"
    
    # ============================================================
    # WORKFORCE METRICS PROCESSING
    # ============================================================
    wf_curr = workforce_current[0] if workforce_current else {}
    wf_prev = workforce_previous[0] if workforce_previous else {}
    
    total_employees = int(wf_curr.get('total_employees', 0))
    active_employees = int(wf_curr.get('active_employees', 0))
    active_bench = int(wf_curr.get('active_bench', 0))
    avg_utilization = float(wf_curr.get('avg_utilization', 0))

    avg_tenure_days = int(wf_curr.get('avg_tenure_days', 0))
    avg_tenure_days_active = int(wf_curr.get('avg_tenure_days_active', 0) or 0)
    avg_tenure_days_bench = int(wf_curr.get('avg_tenure_days_bench', 0) or 0) 
    
    total_sick_events = int(wf_curr.get('total_sick_events', 0))
    total_unpaid_events = int(wf_curr.get('total_unpaid_events', 0))
    total_sick_hours = float(wf_curr.get('total_sick_hours', 0))
    total_unpaid_hours = float(wf_curr.get('total_unpaid_hours', 0))
    total_hours_wf = float(wf_curr.get('total_hours', 0))
    
    # Calculate percentages and additional metrics
    active_employees_pct = round((active_employees / total_employees * 100) if total_employees > 0 else 0, 1)
    active_bench_pct = round((active_bench / total_employees * 100) if total_employees > 0 else 0, 1)
    sick_hours_pct = round((total_sick_hours / total_hours_wf * 100) if total_hours_wf > 0 else 0, 2)
    unpaid_hours_pct = round((total_unpaid_hours / total_hours_wf * 100) if total_hours_wf > 0 else 0, 2)
    
    total_callouts = total_sick_events + total_unpaid_events
    total_callout_hours = total_sick_hours + total_unpaid_hours
    total_callout_hours_pct = round((total_callout_hours / total_hours_wf * 100) if total_hours_wf > 0 else 0, 2)
    
    avg_tenure_years = round(avg_tenure_days / 365.25, 1)
    avg_tenure_years_active = round(avg_tenure_days_active / 365.25, 1) if avg_tenure_days_active > 0 else 0
    avg_tenure_years_bench = round(avg_tenure_days_bench / 365.25, 1) if avg_tenure_days_bench > 0 else 0
    
       # Tenure status (All employees)
    if avg_tenure_days < 90:
        tenure_status = "🔴 Critical Risk"
    elif avg_tenure_days < 180:
        tenure_status = "🟠 High Risk"
    elif avg_tenure_days < 365:
        tenure_status = "🟡 Medium Risk"
    else:
        tenure_status = "🟢 Stable"

    # Tenure status for Active
    if avg_tenure_days_active < 90:
        tenure_status_active = "🔴 Critical Risk"
    elif avg_tenure_days_active < 180:
        tenure_status_active = "🟠 High Risk"
    elif avg_tenure_days_active < 365:
        tenure_status_active = "🟡 Medium Risk"
    else:
        tenure_status_active = "🟢 Stable"

    # Tenure status for Bench
    if avg_tenure_days_bench < 90:
        tenure_status_bench = "🔴 Critical Risk"
    elif avg_tenure_days_bench < 180:
        tenure_status_bench = "🟠 High Risk"
    elif avg_tenure_days_bench < 365:
        tenure_status_bench = "🟡 Medium Risk"
    else:
        tenure_status_bench = "🟢 Stable"
    
    # WoW comparisons
    wow_total_employees = total_employees - int(wf_prev.get('total_employees', 0))
    wow_active_employees = active_employees - int(wf_prev.get('active_employees', 0))
    wow_active_bench = active_bench - int(wf_prev.get('active_bench', 0))
    wow_avg_utilization = round(avg_utilization - float(wf_prev.get('avg_utilization', 0)), 1)
    avg_utilization_active = float(wf_curr.get('avg_utilization_active', 0))
    avg_utilization_bench = float(wf_curr.get('avg_utilization_bench', 0))
    wow_avg_utilization_active = round(avg_utilization_active - float(wf_prev.get('avg_utilization_active', 0)), 1)
    wow_avg_utilization_bench = round(avg_utilization_bench - float(wf_prev.get('avg_utilization_bench', 0)), 1)
    wow_sick_events = total_sick_events - int(wf_prev.get('total_sick_events', 0))
    wow_unpaid_events = total_unpaid_events - int(wf_prev.get('total_unpaid_events', 0))
    wow_total_callouts = wow_sick_events + wow_unpaid_events
    
    workforce_metrics = {
        'total_employees': total_employees,
        'active_employees': active_employees,
        'active_bench': active_bench,
        'avg_utilization': avg_utilization,
        'avg_utilization_active': avg_utilization_active,
        'avg_utilization_bench': avg_utilization_bench,
        'avg_tenure_days': avg_tenure_days,
        'avg_tenure_days_active': avg_tenure_days_active,
        'avg_tenure_days_bench': avg_tenure_days_bench,
        'avg_tenure_years': avg_tenure_years,
        'avg_tenure_years_active': avg_tenure_years_active,
        'avg_tenure_years_bench': avg_tenure_years_bench,
        'tenure_status': tenure_status,
        'tenure_status_active': tenure_status_active,
        'tenure_status_bench': tenure_status_bench,
        'total_sick_events': total_sick_events,
        'total_unpaid_events': total_unpaid_events,
        'total_sick_hours': total_sick_hours,
        'total_unpaid_hours': total_unpaid_hours,
        'active_employees_pct': active_employees_pct,
        'active_bench_pct': active_bench_pct,
        'sick_hours_pct': sick_hours_pct,
        'unpaid_hours_pct': unpaid_hours_pct,
        'total_callouts': total_callouts,
        'total_callout_hours': total_callout_hours,
        'total_callout_hours_pct': total_callout_hours_pct,
        'wow_total_employees': wow_total_employees,
        'wow_active_employees': wow_active_employees,
        'wow_active_bench': wow_active_bench,
        'wow_avg_utilization': wow_avg_utilization,
        'wow_sick_events': wow_sick_events,
        'wow_unpaid_events': wow_unpaid_events,
        'wow_total_callouts': wow_total_callouts
    }
    
    # Generate filename
    scope_type_for_filename = scope_type.replace(" ", "_").replace("-", "_")
    report_filename = _generate_report_filename_option2(
        scope_type=scope_type_for_filename,
        scope_name=scope_name,
        start_date=weeks[0]['start_date'],
        end_date=weeks[-1]['end_date']
    )
    
    # Generate HTML
    html_content = _generate_4week_snapshot_html(
        weeks=weeks,
        latest_week=latest_week,
        first_week=first_week,
        prev_week=prev_week,
        ot_breakdown=ot_breakdown,
        nbot_pct_change=nbot_pct_change,
        nbot_hours_change=nbot_hours_change,
        total_ot_hours_change=total_ot_hours_change,
        total_ot_pct_change=total_ot_pct_change,
        billable_ot_hours_change=billable_ot_hours_change,
        billable_ot_pct_change=billable_ot_pct_change,
        wow_deltas=wow_deltas,
        status=status,
        status_class=status_class,
        status_with_trend=status_with_trend,
        scope_type=scope_type,
        scope_name=scope_name,
        pay_type=pay_type,
        hourly_ot_comp=hourly_ot_comp,
        billable_ot_data=billable_ot_data,
        nbot_breakdown=nbot_breakdown,
        site_performance=site_performance,
        manager_performance=manager_performance,
        workforce_metrics=workforce_metrics,
        workforce_previous=workforce_previous,
        pareto_stats=pareto_stats,
        employee_callouts=employee_callouts
    )
    
    return html_content, report_filename


def _generate_4week_snapshot_html(
    weeks,
    latest_week,
    first_week,
    prev_week,
    ot_breakdown,
    nbot_pct_change,
    nbot_hours_change,
    total_ot_hours_change,
    total_ot_pct_change,
    billable_ot_hours_change,
    billable_ot_pct_change,
    wow_deltas,
    status,
    status_class,
    status_with_trend: str,
    scope_type: str = "Company-Wide",
    scope_name: str = "All Operations",
    pay_type: dict = None,
    hourly_ot_comp: list = None,
    billable_ot_data: list = None,
    nbot_breakdown: list = None,
    site_performance: list = None,
    manager_performance: list = None,
    workforce_metrics: dict = None,
    workforce_previous: list = None,
    pareto_stats: dict = None,
    employee_callouts: list = None
) -> str:
    """Generate the MERGED ULTIMATE HTML report with beveled metal 3D styling and Chart.js."""
    
    cst = ZoneInfo('America/Chicago')
    now_cst = datetime.now(cst)
    timestamp = now_cst.strftime("%b %d, %Y %H:%M CST")
    
    # Default empty values if not provided
    pay_type = pay_type or {}
    hourly_ot_comp = hourly_ot_comp or []
    billable_ot_data = billable_ot_data or []
    nbot_breakdown = nbot_breakdown or []
    site_performance = site_performance or []
    manager_performance = manager_performance or []
    workforce_metrics = workforce_metrics or {}
    workforce_previous = workforce_previous or []
    pareto_stats = pareto_stats or {}
    employee_callouts = employee_callouts or []
    
    # Calculate chart bar heights
    max_nbot = max(w['nbot_hours'] for w in weeks)
    for week in weeks:
        week['bar_height'] = int((week['nbot_hours'] / max_nbot * 350)) if max_nbot > 0 else 0
        if week['nbot_pct'] < 3.5:
            week['status_class'] = 'improving'
        elif week['nbot_pct'] < 4.2:
            week['status_class'] = 'stable'
        else:
            week['status_class'] = 'declining'
    
    # Prepare Chart.js data
    week_labels = [f"Week {w['week_num']}" for w in weeks]
    nbot_pct_data = [w['nbot_pct'] for w in weeks]
    billable_ot_pct_data = [w['billable_ot_pct'] for w in weeks]
    total_ot_pct_data = [w['total_ot_pct'] for w in weeks]
    
    # Hours data for tooltips
    nbot_hours_data = [w['nbot_hours'] for w in weeks]
    billable_ot_hours_data = [w['billable_ot_hours'] for w in weeks]
    total_ot_hours_data = [w['total_ot_hours'] for w in weeks]
    
    # OT Breakdown Chart Data
    ot_categories = [item['ot_category'] for item in ot_breakdown]
    ot_nbot_data = [float(item['nbot_hours']) for item in ot_breakdown]
    ot_billable_data = [float(item['billable_hours']) for item in ot_breakdown]
    
    # Pareto Chart Data (top 20 sites)
    if site_performance:
        pareto_site_labels = [f"Site {site.get('location_number', 'N/A')}" for site in site_performance[:20]]
        pareto_nbot_hours = [float(site.get('nbot_hours', 0)) for site in site_performance[:20]]
        pareto_cumulative = [float(site.get('cumulative_nbot_pct', 0)) for site in site_performance[:20]]
    else:
        pareto_site_labels = []
        pareto_nbot_hours = []
        pareto_cumulative = []
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🌐 EPC NBOT 4-Week Snapshot - {scope_name} 🌐</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        {_get_snapshot_css()}
    </style>
</head>
<body>
    <div class="container">
        <div id="top"></div>
        
        <!-- Navigation Buttons -->
        <div class="nav-container">
            <a href="#section-metrics" class="nav-button">👆 Key Metrics</a>
            <a href="#section-charts" class="nav-button">👆 OT Trend Charts</a>
            <a href="#section-comparison" class="nav-button">👆 4-Week NBOT Comparison</a>
            <a href="#section-workforce" class="nav-button">👆 Workforce Analysis</a>
            <a href="#section-contributors" class="nav-button">👆 Absenteeism Trends</a>
            <a href="#section-employee-callouts" class="nav-button">👆 Employee Call-Outs</a>
            <a href="#section-sites" class="nav-button">👆 Site Performance</a>
            <a href="#section-managers" class="nav-button">👆 Manager Performance</a>
            <a href="#section-recommendations" class="nav-button">💡 Recommendations</a>
        </div>

        <!-- Chrome Industrial Header -->
        <div class="header">
            <h1>🌐 Excellence Performance Center 🌐</h1>
            <div class="subtitle">NBOT 4-Week Snapshot</div>
            <div class="subtitle">Report Prepared by Carlos Guzman</div>
        </div>

        <!-- Meta Cards -->
        <div class="report-meta">
            <div class="meta-item">
                <div class="meta-label">Report Scope</div>
                <div class="meta-value">{scope_type}</div>
            </div>
            <div class="meta-item">
                <div class="meta-label">{scope_type} Name</div>
                <div class="meta-value">{scope_name}</div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Analysis Period</div>
                <div class="meta-value">{weeks[0]['start_display']} - {weeks[-1]['end_display']}, {datetime.now().year}</div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Generated</div>
                <div class="meta-value">{timestamp}</div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Status</div>
                <div class="meta-value" style="line-height: 1.4;">{status_with_trend}</div>
            </div>
        </div>

        <!-- Key Performance Metrics Section -->
        <div class="section">
            <div class="section-header" onclick="toggleSection('metrics')">
                <span> Key Performance Metrics</span>
                <div class="section-header-right">
                    <a href="#top" class="back-to-top" onclick="event.stopPropagation();">⬆ Back to Top</a>
                    <span class="toggle-icon">▼</span>
                </div>
            </div>
            <div class="section-content expanded" id="section-metrics">
                <h3 style="font-size: 1.5em; color: #505050; margin-bottom: 25px; font-weight: 1000; text-align: center;">Week {weeks[-1]['week_num']} Performance Snapshot (v. Previous Week)</h3>
                
                <div class="metrics-grid">
                    <!-- 1. Total Worked Hours (TWH) -->
                    <div class="metric-card">
                        <div class="metric-label">Total Worked Hours (TWH)</div>
                        <div class="metric-value">{latest_week['twh']:,.0f}</div>
                        <div class="metric-sublabel" style="font-size: 0.85em; color: #6b7280; margin: 8px 0; line-height: 1.4;">Total Counter Hours - Unpaid Time Off</div>
                        <div class="metric-change {'positive' if wow_deltas['twh'] < 0 else 'negative' if wow_deltas['twh'] > 0 else 'neutral'}">
                            {'⬇️' if wow_deltas['twh'] < 0 else '⬆️' if wow_deltas['twh'] > 0 else '➡️'} {abs(wow_deltas['twh']):,.0f} hours vs Week {prev_week['week_num']}
                        </div>
                    </div>

                    <!-- 2. Total Hours | Hourly -->
                    <div class="metric-card">
                        <div class="metric-label">Total Hours | Hourly</div>
                        <div class="metric-value">{latest_week['total_hourly_hours']:,.0f}</div>
                        <div class="metric-sublabel" style="font-size: 1.1em; color: #808080; margin: 8px 0;">{latest_week['hourly_pct']:.2f}% of total</div>
                        <div class="metric-change {'positive' if wow_deltas['hourly_hours'] < 0 else 'negative' if wow_deltas['hourly_hours'] > 0 else 'neutral'}">
                            {'⬇️' if wow_deltas['hourly_hours'] < 0 else '⬆️' if wow_deltas['hourly_hours'] > 0 else '➡️'} {abs(wow_deltas['hourly_hours']):,.0f} hours ({wow_deltas['hourly_pct']:+.2f}pp)
                        </div>
                    </div>

                    <!-- 3. Total Hours | Salaried -->
                    <div class="metric-card">
                        <div class="metric-label">Total Hours | Salaried</div>
                        <div class="metric-value">{latest_week['total_salaried_hours']:,.0f}</div>
                        <div class="metric-sublabel" style="font-size: 1.1em; color: #808080; margin: 8px 0;">{latest_week['salaried_pct']:.2f}% of total</div>
                        <div class="metric-change {'positive' if wow_deltas['salaried_hours'] < 0 else 'negative' if wow_deltas['salaried_hours'] > 0 else 'neutral'}">
                            {'⬇️' if wow_deltas['salaried_hours'] < 0 else '⬆️' if wow_deltas['salaried_hours'] > 0 else '➡️'} {abs(wow_deltas['salaried_hours']):,.0f} hours ({wow_deltas['salaried_pct']:+.2f}pp)
                        </div>
                    </div>
                    
                    <!-- 4. Total Hours | 1099 -->
                    <div class="metric-card">
                        <div class="metric-label">Total Hours | 1099</div>
                        <div class="metric-value">{latest_week['total_1099_hours']:,.0f}</div>
                        <div class="metric-sublabel" style="font-size: 1.1em; color: #808080; margin: 8px 0;">{latest_week['contractor_1099_pct']:.2f}% of total</div>
                        <div class="metric-change {'positive' if wow_deltas['1099_hours'] < 0 else 'negative' if wow_deltas['1099_hours'] > 0 else 'neutral'}">
                            {'⬇️' if wow_deltas['1099_hours'] < 0 else '⬆️' if wow_deltas['1099_hours'] > 0 else '➡️'} {abs(wow_deltas['1099_hours']):,.0f} hours ({wow_deltas['1099_pct']:+.2f}pp)
                        </div>
                    </div>
                    
                    <!-- 5. Total OT Hours -->
                    <div class="metric-card">
                        <div class="metric-label">Total OT Hours</div>
                        <div class="metric-value">{latest_week['total_ot_hours']:,.0f}</div>
                        <div class="metric-sublabel" style="font-size: 1.1em; color: #f59e0b; margin: 8px 0;">{latest_week['total_ot_pct']:.2f}% of TWH</div>
                        <div class="metric-change {'positive' if wow_deltas['ot_hours'] < 0 else 'negative' if wow_deltas['ot_hours'] > 0 else 'neutral'}">
                            {'⬇️' if wow_deltas['ot_hours'] < 0 else '⬆️' if wow_deltas['ot_hours'] > 0 else '➡️'} {abs(wow_deltas['ot_hours']):,.0f} hours ({wow_deltas['ot_pct']:+.2f}pp)
                        </div>
                    </div>
                    
                    <!-- 6. Billable OT Hours -->
                    <div class="metric-card">
                        <div class="metric-label">Billable OT Hours</div>
                        <div class="metric-value">{latest_week['billable_ot_hours']:,.0f}</div>
                        <div class="metric-sublabel" style="font-size: 1.1em; color: #10b981; margin: 8px 0;">{latest_week['billable_ot_pct']:.2f}% of TWH</div>
                        <div class="metric-change {'positive' if wow_deltas['billable_hours'] > 0 else 'negative' if wow_deltas['billable_hours'] < 0 else 'neutral'}">
                            {'⬆️' if wow_deltas['billable_hours'] > 0 else '⬇️' if wow_deltas['billable_hours'] < 0 else '➡️'} {abs(wow_deltas['billable_hours']):,.0f} hours ({wow_deltas['billable_pct']:+.2f}pp)
                        </div>
                    </div>
                    
                    <!-- 7. Billable OT (Actual OT Hrs) -->
                    <div class="metric-card">
                        <div class="metric-label">Billable OT (Actual OT Hrs)</div>
                        <div class="metric-value">{latest_week['billable_ot_actual_ot']:,.0f}</div>
                        <div class="metric-sublabel" style="font-size: 1.1em; color: #10b981; margin: 8px 0;">{latest_week['billable_ot_actual_ot_pct']:.2f}% of total</div>
                        <div class="metric-change {'positive' if wow_deltas['billable_actual_ot_hours'] > 0 else 'negative' if wow_deltas['billable_actual_ot_hours'] < 0 else 'neutral'}">
                            {'⬆️' if wow_deltas['billable_actual_ot_hours'] > 0 else '⬇️' if wow_deltas['billable_actual_ot_hours'] < 0 else '➡️'} {abs(wow_deltas['billable_actual_ot_hours']):,.0f} hours ({wow_deltas['billable_actual_ot_pct']:+.2f}pp)
                        </div>
                    </div>
                    
                    <!-- 8. Billable OT (Regular Hours) -->
                    <div class="metric-card">
                        <div class="metric-label">Billable OT (Regular Hours)</div>
                        <div class="metric-value">{latest_week['billable_ot_regular_hours']:,.0f}</div>
                        <div class="metric-sublabel" style="font-size: 1.1em; color: #10b981; margin: 8px 0;">{latest_week['billable_ot_regular_pct']:.2f}% of total</div>
                        <div class="metric-change {'positive' if wow_deltas['billable_regular_hours'] > 0 else 'negative' if wow_deltas['billable_regular_hours'] < 0 else 'neutral'}">
                            {'⬆️' if wow_deltas['billable_regular_hours'] > 0 else '⬇️' if wow_deltas['billable_regular_hours'] < 0 else '➡️'} {abs(wow_deltas['billable_regular_hours']):,.0f} hours ({wow_deltas['billable_regular_pct']:+.2f}pp)
                        </div>
                    </div>
                    
                    <!-- 9. NBOT Hours -->
                    <div class="metric-card">
                        <div class="metric-label">NBOT Hours</div>
                        <div class="metric-value">{latest_week['nbot_hours']:,.0f}</div>
                        <div class="metric-sublabel" style="font-size: 0.9em; color: #6b7280; margin: 8px 0;">Total OT - Billable OT</div>
                        <div class="metric-change {'positive' if wow_deltas['nbot_hours'] < 0 else 'negative' if wow_deltas['nbot_hours'] > 0 else 'neutral'}">
                            {'⬇️' if wow_deltas['nbot_hours'] < 0 else '⬆️' if wow_deltas['nbot_hours'] > 0 else '➡️'} {abs(wow_deltas['nbot_hours']):,.0f} hours vs Week {prev_week['week_num']}
                        </div>
                    </div>
                    
                    <!-- 10. NBOT % -->
                    <div class="metric-card">
                        <div class="metric-label">NBOT % <span style="color: #1d4ed8; font-weight: 800;">(NBOT Hours / TWH)</span></div>
                        <div class="metric-value">{latest_week['nbot_pct']:.2f}%</div>
                        <div class="metric-sublabel" style="font-size: 0.9em; color: #6b7280; margin: 8px 0;">Target: &lt; 3.0%</div>
                        <div class="metric-change {'positive' if wow_deltas['nbot_pct'] < 0 else 'negative' if wow_deltas['nbot_pct'] > 0 else 'neutral'}">
                            {'⬇️' if wow_deltas['nbot_pct'] < 0 else '⬆️' if wow_deltas['nbot_pct'] > 0 else '➡️'} {abs(wow_deltas['nbot_pct']):.2f}pp vs Week {prev_week['week_num']}
                        </div>
                    </div>
                </div>
                
                <div class="highlight-box" style="margin-top: 25px;">
                <strong>📈 4-Week Trends (Week {first_week['week_num']} → Week {latest_week['week_num']}):</strong><br>
                <div style="font-size: 0.9em; color: #6b7280; margin-top: 5px; font-style: italic;">Note: All percentages calculated as % of TWH (Total Worked Hours = Total Counter Hours - Unpaid Time Off)</div>
    
                <div style="margin-top: 10px; line-height: 1.8;">
                    <strong>NBOT:</strong> {'⬇️ Decreased' if nbot_hours_change < 0 else '⬆️ Increased' if nbot_hours_change > 0 else '➡️ Remained stable'} by <strong>{abs(nbot_hours_change):,.0f} hours</strong> ({nbot_pct_change:+.2f}pp) 
                    <span style="color: {'#16a34a' if nbot_hours_change < 0 else '#dc2626' if nbot_hours_change > 0 else '#6b7280'};">{'✓ Good' if nbot_hours_change < 0 else '⚠ Concern' if nbot_hours_change > 0 else 'Neutral'}</span><br>
                    
                    <strong>Total OT:</strong> {'⬇️ Decreased' if total_ot_hours_change < 0 else '⬆️ Increased' if total_ot_hours_change > 0 else '➡️ Remained stable'} by <strong>{abs(total_ot_hours_change):,.0f} hours</strong> ({total_ot_pct_change:+.2f}pp)<br>
                    
                    <strong>Billable OT:</strong> {'⬆️ Increased' if billable_ot_hours_change > 0 else '⬇️ Decreased' if billable_ot_hours_change < 0 else '➡️ Remained stable'} by <strong>{abs(billable_ot_hours_change):,.0f} hours</strong> ({billable_ot_pct_change:+.2f}pp) 
                    <span style="color: {'#16a34a' if billable_ot_hours_change > 0 else '#dc2626' if billable_ot_hours_change < 0 else '#6b7280'};">{'✓ Good' if billable_ot_hours_change > 0 else '⚠ Concern' if billable_ot_hours_change < 0 else 'Neutral'}</span>
                </div>
            </div>
            </div>
        </div>

        

        
        


        <!-- 4-Week Comparison Section -->
        <div class="section">
            <div class="section-header" onclick="toggleSection('comparison')">
                <span> Last 4 Weeks Performance Comparison | 📌 <span style="color: #00BFFF;">Reminder</span> 📌 NBOT % = NBOT Hrs / TWH (Total Counter Hrs — Unpaid Time Off)</span>
                <div class="section-header-right">
                    <a href="#top" class="back-to-top" onclick="event.stopPropagation();">⬆ Back to Top</a>
                    <span class="toggle-icon">▼</span>
                </div>
            </div>
            <div class="section-content expanded" id="section-comparison">
                <div class="four-week-grid">
"""
    
    # Add week cards
    for week in weeks:
        html += f"""
                    <div class="week-card {week['status_class']}">
                        <div class="week-title">Week {week['week_num']}</div>
                        <div class="week-title" style="font-size: 0.8em; color: #6b7280;">{week['start_display']} - {week['end_display']}</div>
                        <div class="week-nbot">{week['nbot_pct']:.2f}%</div>
                        <div class="week-details">
                            <div>Total Counter Hours: <strong>{week['total_hours']:,.0f}</strong></div>
                            <div style="padding-left: 15px;">📌 TWH (Total Worked Hours): <strong>{week['twh']:,.0f}</strong></div>
                            <div>Hourly Hours: <strong>{week['total_hourly_hours']:,.0f}</strong> <span style="color: #6b7280;">({week['hourly_pct']:.2f}%)</span></div>
                            <div>Salaried Hours: <strong>{week['total_salaried_hours']:,.0f}</strong> <span style="color: #6b7280;">({week['salaried_pct']:.2f}%)</span></div>
                            <div>1099 Hours: <strong>{week['total_1099_hours']:,.0f}</strong> <span style="color: #6b7280;">({week['contractor_1099_pct']:.2f}%)</span></div>
                            <div>Total OT Hours: <strong>{week['total_ot_hours']:,.0f}</strong> <span style="color: #6b7280;">({week['total_ot_pct']:.2f}%)</span></div>
                            <div>Billable OT: <strong>{week['billable_ot_hours']:,.0f}</strong> <span style="color: #6b7280;">({week['billable_ot_pct']:.2f}%)</span></div>
                            <div style="padding-left: 15px;">Billable OT (Actual OT Hrs): <strong>{week['billable_ot_actual_ot']:,.0f}</strong> <span style="color: #6b7280;">({week['billable_ot_actual_ot_pct']:.2f}%)</span></div>
                            <div style="padding-left: 15px;">Billable OT (Regular Hours): <strong>{week['billable_ot_regular_hours']:,.0f}</strong> <span style="color: #6b7280;">({week['billable_ot_regular_pct']:.2f}%)</span></div>
                            <div style="border-top: 2px solid #808080; padding-top: 8px; margin-top: 8px;">📌 NBOT Hours: <strong>{week['nbot_hours']:,.0f}</strong></div>
                        </div>
                    </div>
"""
    
    html += """
                </div>
                
                <!-- Grouped Bar Chart -->
                <div style="margin-top: 50px;">
                    <h3 style="font-size: 1.5em; color: #505050; margin-bottom: 140px; font-weight: 1000; text-align: center;">NBOT & Total OT Hours | Trend Comparison</h3>
                    <div style="position: relative;">
                        <div class="chart-bars-grouped">
"""
    
    # Add grouped chart bars
    for week in weeks:
        ot_bar_height = int((week['total_ot_hours'] / max_nbot * 350)) if max_nbot > 0 else 0
        html += f"""
                            <div class="chart-bar-group">
                                <div class="bar-group-label">Week {week['week_num']}</div>
                                <div class="bars-container">
                                    <div class="chart-bar-container-grouped">
                                        <div class="bar-value">{week['nbot_hours']:,.0f}h</div>
                                        <div class="chart-bar-nbot" style="height: {week['bar_height']}px;"></div>
                                        <div class="bar-sublabel">NBOT</div>
                                    </div>
                                    <div class="chart-bar-container-grouped">
                                        <div class="bar-value">{week['total_ot_hours']:,.0f}h</div>
                                        <div class="chart-bar-ot" style="height: {ot_bar_height}px;"></div>
                                        <div class="bar-sublabel">Total OT</div>
                                    </div>
                                </div>
                                <div class="bar-percent-grouped">{week['nbot_pct']:.2f}%</div>
                            </div>
"""
    
# Calculate absenteeism trend values for proper interpolation (MUST BE BEFORE html += f""")
    wow_total_change = workforce_metrics.get('wow_sick_events', 0) + workforce_metrics.get('wow_unpaid_events', 0)
    if wow_total_change > 0:
        trend_message = "Call-outs increased"
    elif wow_total_change < 0:
        trend_message = "Call-outs decreased"
    else:
        trend_message = "Call-outs remained stable"

    impact_warning = "⚠️ Monitor closely for operational impact." if workforce_metrics.get('total_callout_hours_pct', 0) > 3 else "✅ Within acceptable range."

    prev_sick = int(workforce_previous[0].get('total_sick_events', 0)) if workforce_previous else 0
    prev_unpaid = int(workforce_previous[0].get('total_unpaid_events', 0)) if workforce_previous else 0

    # Get current week values
    curr_week_num = weeks[-1]['week_num']
    prev_week_num = weeks[-2]['week_num']
    curr_sick = workforce_metrics.get('total_sick_events', 0)
    curr_unpaid = workforce_metrics.get('total_unpaid_events', 0)
    curr_callouts = workforce_metrics.get('total_callouts', 0)
    curr_callout_pct = workforce_metrics.get('total_callout_hours_pct', 0)

    html += f"""
                        </div>
                    </div>
                </div>
            </div>
        </div>


<!-- Chart.js Trend Charts Section -->
        <div class="section">
            <div class="section-header" onclick="toggleSection('charts')">
                <span> Trend Charts</span>
                <div class="section-header-right">
                    <a href="#top" class="back-to-top" onclick="event.stopPropagation();">⬆ Back to Top</a>
                    <span class="toggle-icon">▼</span>
                </div>
            </div>
            <div class="section-content expanded" id="section-charts">
                <div style="margin-bottom: 40px;">
                    <h3 style="font-size: 1.4em; color: #505050; margin-bottom: 20px; font-weight: 800;">NBOT, Billable OT & Total OT Trends (Last 4 Weeks)</h3>
                    <div class="chart-container">
                        <canvas id="trendChart"></canvas>
                    </div>
                </div>



                
            <div>
                    <h3 style="font-size: 1.3em; color: #505050; margin-bottom: 20px; font-weight: 800;">OT Contributors by Category (Week {weeks[-1]['week_num']})</h3>
                    <div class="chart-container">
                        <canvas id="nbotChart"></canvas>
                    </div>
                </div>
                
                <!-- OT Contributors Insight Box -->
                <div class="highlight-box" style="margin-top: 25px;">
                    <strong>🎯 OT Breakdown Analysis:</strong>
"""

    # Add top contributor analysis
    if ot_breakdown:
        top_contributor = ot_breakdown[0]
        total_ot_week = latest_week['total_ot_hours']
        total_nbot_week = latest_week['nbot_hours']
        
        html += f"""
                    <div style="margin-top: 10px;">
                        <strong>{top_contributor['ot_category']}</strong> is the leading NBOT contributor with <strong>{top_contributor['nbot_hours']:,.0f} hours ({top_contributor['percentage']:.1f}%)</strong> of all NBOT.
                    </div>
                    <div style="margin-top: 10px;">
                        📊 <strong>Total OT Hours:</strong> {total_ot_week:,.0f} hours | 
                        <strong>NBOT Hours:</strong> {total_nbot_week:,.0f} hours | 
                        <strong>Billable OT:</strong> {latest_week['billable_ot_hours']:,.0f} hours
                    </div>
                    <div style="margin-top: 10px;">
                        💡 <strong>Recommendation:</strong> Focus improvement efforts on {top_contributor['ot_category']} to achieve maximum impact. 
                        Consider reviewing scheduling practices, staffing levels, and operational procedures specific to this category.
                    </div>
"""
    
    html += f"""
                        </div>
                    </div>
                </div>
            </div>
        </div>



<!-- Workforce Analysis Section -->
        <div class="section">
            <div class="section-header" onclick="toggleSection('workforce')">
                <span> Workforce Analysis | Last Week | (Week {weeks[-1]['week_num']})</span>
                <div class="section-header-right">
                    <a href="#top" class="back-to-top" onclick="event.stopPropagation();">⬆ Back to Top</a>
                    <span class="toggle-icon">▼</span>
                </div>
            </div>
            <div class="section-content expanded" id="section-workforce">
                <h3 style="font-size: 1.5em; color: #505050; margin-bottom: 25px; font-weight: 1000; text-align: center;">Core Workforce Metrics</h3>
                
                <!-- Row 1: Core Workforce + Tenure (7 cards) -->
                <div class="metrics-grid" style="grid-template-columns: repeat(6, 1fr);">
                    

                    <!-- 2. Total Employees -->
                    <div class="metric-card">
                        <div class="metric-label">Total Employees</div>
                        <div class="metric-value">{workforce_metrics.get('total_employees', 0)}</div>
                        <div class="metric-change {'positive' if workforce_metrics.get('wow_total_employees', 0) > 0 else 'negative' if workforce_metrics.get('wow_total_employees', 0) < 0 else 'neutral'}">
                            {'⬆️' if workforce_metrics.get('wow_total_employees', 0) > 0 else '⬇️' if workforce_metrics.get('wow_total_employees', 0) < 0 else '➡️'} {abs(workforce_metrics.get('wow_total_employees', 0))} vs Week {prev_week['week_num']}
                        </div>
                    </div>

                    <!-- 3. Active Employees -->
                    <div class="metric-card">
                        <div class="metric-label">Active Employees</div>
                        <div class="metric-value">{workforce_metrics.get('active_employees', 0)}</div>
                        <div class="metric-sublabel" style="font-size: 1.1em; color: #10b981; margin: 8px 0;">{workforce_metrics.get('active_employees_pct', 0):.1f}% of workforce</div>
                        <div class="metric-change {'positive' if workforce_metrics.get('wow_active_employees', 0) > 0 else 'negative' if workforce_metrics.get('wow_active_employees', 0) < 0 else 'neutral'}">
                            {'⬆️' if workforce_metrics.get('wow_active_employees', 0) > 0 else '⬇️' if workforce_metrics.get('wow_active_employees', 0) < 0 else '➡️'} {abs(workforce_metrics.get('wow_active_employees', 0))} vs Week {prev_week['week_num']}
                        </div>
                    </div>

                    <!-- 4. Active Bench -->
                    <div class="metric-card">
                        <div class="metric-label">Active Bench</div>
                        <div class="metric-value">{workforce_metrics.get('active_bench', 0)}</div>
                        <div class="metric-sublabel" style="font-size: 1.1em; color: #f59e0b; margin: 8px 0;">{workforce_metrics.get('active_bench_pct', 0):.1f}% of workforce</div>
                        <div class="metric-change {'negative' if workforce_metrics.get('wow_active_bench', 0) > 0 else 'positive' if workforce_metrics.get('wow_active_bench', 0) < 0 else 'neutral'}">
                            {'⬆️' if workforce_metrics.get('wow_active_bench', 0) > 0 else '⬇️' if workforce_metrics.get('wow_active_bench', 0) < 0 else '➡️'} {abs(workforce_metrics.get('wow_active_bench', 0))} vs Week {prev_week['week_num']}
                        </div>
                    </div>

                    <!-- 5. Average Tenure (All) -->
                    <div class="metric-card">
                        <div class="metric-label">Avg Tenure (All)</div>
                        <div class="metric-value">{workforce_metrics.get('avg_tenure_days', 0)} days</div>
                        <div class="metric-sublabel" style="font-size: 1.1em; color: #808080; margin: 8px 0;">{workforce_metrics.get('avg_tenure_years', 0):.1f} years</div>
                        <div class="metric-change neutral" style="font-size: 0.85em; padding: 6px 10px;">
                            {workforce_metrics.get('tenure_status', 'Unknown')}
                        </div>
                    </div>

                    <!-- 6. Average Tenure (Active) -->
                    <div class="metric-card">
                        <div class="metric-label">Avg Tenure (Active)</div>
                        <div class="metric-value">{workforce_metrics.get('avg_tenure_days_active', 0)} days</div>
                        <div class="metric-sublabel" style="font-size: 1.1em; color: #10b981; margin: 8px 0;">{workforce_metrics.get('avg_tenure_years_active', 0):.1f} years</div>
                        <div class="metric-change neutral" style="font-size: 0.85em; padding: 6px 10px;">
                            {workforce_metrics.get('tenure_status_active', 'Unknown')}
                        </div>
                    </div>

                    <!-- 7. Average Tenure (Bench) -->
                    <div class="metric-card">
                        <div class="metric-label">Avg Tenure (Bench)</div>
                        <div class="metric-value">{workforce_metrics.get('avg_tenure_days_bench', 0)} days</div>
                        <div class="metric-sublabel" style="font-size: 1.1em; color: #f59e0b; margin: 8px 0;">{workforce_metrics.get('avg_tenure_years_bench', 0):.1f} years</div>
                        <div class="metric-change neutral" style="font-size: 0.85em; padding: 6px 10px;">
                            {workforce_metrics.get('tenure_status_bench', 'Unknown')}
                        </div>
                    </div>
                </div>

                <!-- Row 2: Utilization & Absenteeism (6 cards) -->
                <div class="metrics-grid" style="grid-template-columns: repeat(6, 1fr); margin-top: 20px;">
                    <!-- 8. Average Utilization (All) -->
                    <div class="metric-card">
                        <div class="metric-label">Avg Utilization (All)</div>
                        <div class="metric-value">{workforce_metrics.get('avg_utilization', 0):.1f}</div>
                        <div class="metric-sublabel" style="font-size: 0.9em; color: #6b7280; margin: 8px 0;">hours per week</div>
                        <div class="metric-change {'positive' if workforce_metrics.get('wow_avg_utilization', 0) > 0 else 'negative' if workforce_metrics.get('wow_avg_utilization', 0) < 0 else 'neutral'}">
                            {'⬆️' if workforce_metrics.get('wow_avg_utilization', 0) > 0 else '⬇️' if workforce_metrics.get('wow_avg_utilization', 0) < 0 else '➡️'} {abs(workforce_metrics.get('wow_avg_utilization', 0)):.1f} hrs vs Week {prev_week['week_num']}
                        </div>
                    </div>

                    <!-- 9. Average Utilization (Active) -->
                    <div class="metric-card">
                        <div class="metric-label">Avg Utilization (Active)</div>
                        <div class="metric-value">{workforce_metrics.get('avg_utilization_active', 0):.1f}</div>
                        <div class="metric-sublabel" style="font-size: 0.9em; color: #10b981; margin: 8px 0;">active employees</div>
                        <div class="metric-change {'positive' if workforce_metrics.get('wow_avg_utilization_active', 0) > 0 else 'negative' if workforce_metrics.get('wow_avg_utilization_active', 0) < 0 else 'neutral'}">
                            {'⬆️' if workforce_metrics.get('wow_avg_utilization_active', 0) > 0 else '⬇️' if workforce_metrics.get('wow_avg_utilization_active', 0) < 0 else '➡️'} {abs(workforce_metrics.get('wow_avg_utilization_active', 0)):.1f} hrs vs Week {prev_week['week_num']}
                        </div>
                    </div>

                    <!-- 10. Average Utilization (Bench) -->
                    <div class="metric-card">
                        <div class="metric-label">Avg Utilization (Bench)</div>
                        <div class="metric-value">{workforce_metrics.get('avg_utilization_bench', 0):.1f}</div>
                        <div class="metric-sublabel" style="font-size: 0.9em; color: #f59e0b; margin: 8px 0;">bench employees</div>
                        <div class="metric-change {'positive' if workforce_metrics.get('wow_avg_utilization_bench', 0) > 0 else 'negative' if workforce_metrics.get('wow_avg_utilization_bench', 0) < 0 else 'neutral'}">
                            {'⬆️' if workforce_metrics.get('wow_avg_utilization_bench', 0) > 0 else '⬇️' if workforce_metrics.get('wow_avg_utilization_bench', 0) < 0 else '➡️'} {abs(workforce_metrics.get('wow_avg_utilization_bench', 0)):.1f} hrs vs Week {prev_week['week_num']}
                        </div>
                    </div>

                    <!-- 11. Sick Call-Outs -->
                    <div class="metric-card">
                        <div class="metric-label">Sick Call-Outs</div>
                        <div class="metric-value">{workforce_metrics.get('total_sick_events', 0)}</div>
                        <div class="metric-sublabel" style="font-size: 1.1em; color: #dc2626; margin: 8px 0;">{workforce_metrics.get('total_sick_hours', 0):.1f} hours ({workforce_metrics.get('sick_hours_pct', 0):.2f}%)</div>
                        <div class="metric-change {'positive' if workforce_metrics.get('wow_sick_events', 0) < 0 else 'negative' if workforce_metrics.get('wow_sick_events', 0) > 0 else 'neutral'}">
                            {'⬇️' if workforce_metrics.get('wow_sick_events', 0) < 0 else '⬆️' if workforce_metrics.get('wow_sick_events', 0) > 0 else '➡️'} {abs(workforce_metrics.get('wow_sick_events', 0))} events vs Week {prev_week['week_num']}
                        </div>
                    </div>

                    <!-- 12. Unpaid Time Off -->
                    <div class="metric-card">
                        <div class="metric-label">Unpaid Time Off Events</div>
                        <div class="metric-value">{workforce_metrics.get('total_unpaid_events', 0)}</div>
                        <div class="metric-sublabel" style="font-size: 1.1em; color: #dc2626; margin: 8px 0;">{workforce_metrics.get('total_unpaid_hours', 0):.1f} hours ({workforce_metrics.get('unpaid_hours_pct', 0):.2f}%)</div>
                        <div class="metric-change {'positive' if workforce_metrics.get('wow_unpaid_events', 0) < 0 else 'negative' if workforce_metrics.get('wow_unpaid_events', 0) > 0 else 'neutral'}">
                            {'⬇️' if workforce_metrics.get('wow_unpaid_events', 0) < 0 else '⬆️' if workforce_metrics.get('wow_unpaid_events', 0) > 0 else '➡️'} {abs(workforce_metrics.get('wow_unpaid_events', 0))} events vs Week {prev_week['week_num']}
                        </div>
                    </div>

                    <!-- 13. Total Call-Outs -->
                    <div class="metric-card">
                        <div class="metric-label">Total Call-Outs</div>
                        <div class="metric-value">{workforce_metrics.get('total_callouts', 0)}</div>
                        <div class="metric-sublabel" style="font-size: 1.1em; color: #dc2626; margin: 8px 0;">{workforce_metrics.get('total_callout_hours', 0):.1f} hours ({workforce_metrics.get('total_callout_hours_pct', 0):.2f}%)</div>
                        <div class="metric-change {'positive' if workforce_metrics.get('wow_total_callouts', 0) < 0 else 'negative' if workforce_metrics.get('wow_total_callouts', 0) > 0 else 'neutral'}">
                            {'⬇️' if workforce_metrics.get('wow_total_callouts', 0) < 0 else '⬆️' if workforce_metrics.get('wow_total_callouts', 0) > 0 else '➡️'} {abs(workforce_metrics.get('wow_total_callouts', 0))} events vs Week {prev_week['week_num']}
                        </div>
                    </div>
                </div>

                <div class="highlight-box" style="margin-top: 25px;">
                    <strong> Workforce Insight:</strong> With {workforce_metrics.get('total_employees', 0)} employees averaging {workforce_metrics.get('avg_utilization', 0):.1f} hours per week, the workforce is {'underutilized' if workforce_metrics.get('avg_utilization', 0) < 32 else 'optimally utilized' if workforce_metrics.get('avg_utilization', 0) <= 40 else 'overutilized'}. Average tenure of {workforce_metrics.get('avg_tenure_days', 0)} days indicates {workforce_metrics.get('tenure_status', 'Unknown').split()[1] if len(workforce_metrics.get('tenure_status', '').split()) > 1 else 'unknown'} retention risk. Total call-outs represent {workforce_metrics.get('total_callout_hours_pct', 0):.2f}% of worked hours.
                </div>
            </div>
        </div>


        <!-- NBOT Contributors Section -->
        <div class="section">
            <div class="section-header" onclick="toggleSection('contributors')">
                <span>🏥 Absenteeism Trends</span>
                <div class="section-header-right">
                    <a href="#top" class="back-to-top" onclick="event.stopPropagation();">⬆ Back to Top</a>
                    <span class="toggle-icon">▼</span>
                </div>
            </div>



            <div class="section-content expanded" id="section-contributors">
                <h3 style="font-size: 1.4em; color: #505050; margin-bottom: 20px; font-weight: 800;">Last 4-Weeks Absenteeism Trends</h3>
                <div class="chart-container">
                    <canvas id="absenteeismChart"></canvas>
                </div>
                
                <div class="highlight-box" style="margin-top: 25px;">
                    <strong> Absenteeism Analysis:</strong>
                    <div style="margin-top: 10px;">
                        Current Week (Week {curr_week_num}): 
                        <strong>{curr_sick} sick events</strong>, 
                        <strong>{curr_unpaid} unpaid events</strong>, 
                        <strong>{curr_callouts} total call-outs</strong> 
                        ({curr_callout_pct:.2f}% of worked hours)
                    </div>
                    <div style="margin-top: 10px;">
                        Previous Week (Week {prev_week_num}): 
                        <strong>{prev_sick} sick events</strong>, 
                        <strong>{prev_unpaid} unpaid events</strong>
                    </div>
                    <div style="margin-top: 10px;">
                        💡 <strong>Trend:</strong> 
                        {trend_message} 
                        by <strong>{abs(wow_total_change)}</strong> events week-over-week.
                        {impact_warning}
                    </div>
                </div>
            </div>
        </div>
"""
    
# Employee Call-Out Table Section
    if employee_callouts:
        html += f"""
        <!-- Employee Call-Out Details Section -->
        <div class="section">
            <div class="section-header" onclick="toggleSection('employee-callouts')">
                <span> Employee Call-Out Details (Last 4 Weeks)</span>
                <div class="section-header-right">
                    <a href="#top" class="back-to-top" onclick="event.stopPropagation();">⬆ Back to Top</a>
                    <span class="toggle-icon">▼</span>
                </div>
            </div>
            <div class="section-content expanded" id="section-employee-callouts">
    
    
    <h3 style="font-size: 1.4em; color: #505050; margin-bottom: 20px; font-weight: 800;">Employees with Call-Outs (Sorted by Total Events)</h3>
                
                <div class="highlight-box" style="margin-bottom: 25px;">
                    <strong>📊 Call-Out Summary (Last 4 Weeks):</strong><br>
                    <div style="margin-top: 10px; line-height: 1.8;">
                        <strong>{len(employee_callouts)}</strong> employees had call-outs (<strong>{(len(employee_callouts) / workforce_metrics.get('total_employees', 1) * 100):.1f}%</strong> of workforce)<br>
                        
                        <strong>By Severity:</strong><br>
                        🔴 <strong>{len([e for e in employee_callouts if int(e.get('total_callouts', 0)) >= 3])}</strong> employees with 3+ call-outs (High Risk - {(len([e for e in employee_callouts if int(e.get('total_callouts', 0)) >= 3]) / workforce_metrics.get('total_employees', 1) * 100):.1f}% of workforce)<br>
                        🟡 <strong>{len([e for e in employee_callouts if int(e.get('total_callouts', 0)) == 2])}</strong> employees with 2 call-outs (Moderate Risk - {(len([e for e in employee_callouts if int(e.get('total_callouts', 0)) == 2]) / workforce_metrics.get('total_employees', 1) * 100):.1f}% of workforce)<br>
                        🟢 <strong>{len([e for e in employee_callouts if int(e.get('total_callouts', 0)) == 1])}</strong> employees with 1 call-out (Low Risk - {(len([e for e in employee_callouts if int(e.get('total_callouts', 0)) == 1]) / workforce_metrics.get('total_employees', 1) * 100):.1f}% of workforce)<br>
                        
                        <strong>Event Totals:</strong><br>
                        Sick events: <strong>{sum(int(e.get('sick_callouts', 0)) for e in employee_callouts)}</strong> | 
                        Unpaid events: <strong>{sum(int(e.get('unpaid_callouts', 0)) for e in employee_callouts)}</strong> | 
                        Combined: <strong>{sum(int(e.get('total_callouts', 0)) for e in employee_callouts)}</strong> events<br>
                        
                        <strong>Hours Impact:</strong> <strong>{sum(float(e.get('total_callout_hours', 0)) for e in employee_callouts):.1f}</strong> total hours lost ({workforce_metrics.get('total_callout_hours_pct', 0):.2f}% of worked hours)
                    </div>
                </div>
                
                <input type="text" class="search-box" id="employeeCalloutSearch" onkeyup="filterTable('employeeCalloutTable', 'employeeCalloutSearch')" placeholder="🔍 Search employees...">
                
                <table id="employeeCalloutTable" class="performance-table">
                    <thead>
                        <tr>
                            <th class="sortable" onclick="sortTable('employeeCalloutTable', 0)">#</th>
                            <th class="sortable" onclick="sortTable('employeeCalloutTable', 1)">Employee ID</th>
                            <th class="sortable" onclick="sortTable('employeeCalloutTable', 2)">Name</th>
                            <th class="sortable" onclick="sortTable('employeeCalloutTable', 3)">Status</th>
                            <th class="sortable" onclick="sortTable('employeeCalloutTable', 4)">Location</th>
                            <th class="sortable" onclick="sortTable('employeeCalloutTable', 5)">City</th>
                            <th class="sortable" onclick="sortTable('employeeCalloutTable', 6)">State</th>
                            <th class="sortable" onclick="sortTable('employeeCalloutTable', 7)">Avg Hours/Week</th>
                            <th class="sortable" onclick="sortTable('employeeCalloutTable', 8)">Last Week Hours</th>
                            <th class="sortable" onclick="sortTable('employeeCalloutTable', 9)">Sick Call-Outs</th>
                            <th class="sortable" onclick="sortTable('employeeCalloutTable', 10)">Sick Hours</th>
                            <th class="sortable" onclick="sortTable('employeeCalloutTable', 11)">Unpaid Call-Outs</th>
                            <th class="sortable" onclick="sortTable('employeeCalloutTable', 12)">Unpaid Hours</th>
                            <th class="sortable" onclick="sortTable('employeeCalloutTable', 13)">Total Call-Outs</th>
                            <th class="sortable" onclick="sortTable('employeeCalloutTable', 14)">Total Call-Out Hours</th>
                            <th class="sortable" onclick="sortTable('employeeCalloutTable', 15)">Most Frequent Day</th>
                            <th class="sortable" onclick="sortTable('employeeCalloutTable', 16)">Pattern Type</th>
                        </tr>
                    </thead>
                    <tbody>
"""
        
        for idx, emp in enumerate(employee_callouts, 1):
            total_callouts = int(emp.get('total_callouts', 0))
            if total_callouts >= 3:
                status_class = "status-red"
            elif total_callouts >= 2:
                status_class = "status-yellow"
            else:
                status_class = "status-green"
            
            # Get pattern info
            top_2_days = emp.get('top_2_days', 'N/A')
            pattern_type = emp.get('pattern_type', 'N/A')
            day_breakdown = emp.get('day_breakdown', '')
            
            html += f"""
                        <tr title="{day_breakdown}">
                            <td>{idx}</td>
                            <td><strong>{emp.get('employee_id', 'N/A')}</strong></td>
                            <td>{emp.get('employee_name', 'Unknown')}</td>
                            <td><span style="font-size: 0.9em; padding: 4px 8px; background: {'#dcfce7' if 'Active' in str(emp.get('employee_status', '')) and 'Bench' not in str(emp.get('employee_status', '')) else '#fef3c7' if 'Bench' in str(emp.get('employee_status', '')) else '#fee2e2'}; border-radius: 4px; font-weight: 600;">{emp.get('employee_status', 'N/A')}</span></td>
                            <td><strong>{emp.get('location_number', 'N/A')}</strong></td>
                            <td>{emp.get('city', 'N/A')}</td>
                            <td>{emp.get('state', 'N/A')}</td>
                            <td>{emp.get('avg_hours_per_week', 0):.1f}</td>
                            <td>{emp.get('last_week_hours', 0):.1f}</td>
                            <td>{emp.get('sick_callouts', 0)}</td>
                            <td>{emp.get('sick_hours', 0):.1f}</td>
                            <td>{emp.get('unpaid_callouts', 0)}</td>
                            <td>{emp.get('unpaid_hours', 0):.1f}</td>
                            <td class="{status_class}"><strong>{total_callouts}</strong></td>
                            <td>{emp.get('total_callout_hours', 0):.1f}</td>
                            <td><strong>{top_2_days}</strong></td>
                            <td>{pattern_type}</td>
                        </tr>
"""
        
        html += """
                    </tbody>
                </table>
                <button class="export-btn" onclick="exportTableToCSV('employeeCalloutTable', 'employee_callouts.csv')">📥 Export to CSV</button>
                
                <div class="highlight-box" style="margin-top: 25px;">
                    <strong>💡 Pattern Interpretation:</strong><br>
                    <strong>Attendance Risk:</strong> 
                    <span style="color: #dc2626;">●</span> Red = 3+ call-outs (High Risk) | 
                    <span style="color: #ca8a04;">●</span> Yellow = 2 call-outs (Moderate Risk) | 
                    <span style="color: #16a34a;">●</span> Green = 1 call-out (Low Risk)<br>
                    <strong>Patterns (Most Suspicious First):</strong><br>
                    🔴 <strong>Weekend Pattern</strong> = 50%+ call-outs on Sat/Sun (extended weekends) |
                    🔴 <strong>Long Weekend (Mon)</strong> = 70%+ on Mon + Weekend combined (extending weekend) |
                    🔴 <strong>Long Weekend (Fri)</strong> = 70%+ on Fri + Weekend combined (extending weekend) |
                    🔴 <strong>Monday Pattern</strong> = 50%+ on Monday only |
                    🔴 <strong>Friday Pattern</strong> = 50%+ on Friday only |
                    🟡 <strong>Mon/Fri Pattern</strong> = 70%+ on Mon/Fri combined (no weekend) |
                    🟢 <strong>Mid-week</strong> = Most call-outs Tue-Thu (more legitimate) |
                    🔵 <strong>Mixed</strong> = No clear pattern |
                    ⚪ <strong>Single Event</strong> = Only 1 call-out<br>
                    <em>Hover over rows to see detailed day-by-day breakdown including Sat/Sun split.</em>
                </div>
            </div>
        </div>
"""

    # Site Performance Table Section
    if site_performance:
        html += f"""
        <!-- Site Performance Table Section -->
        <div class="section">
            <div class="section-header" onclick="toggleSection('sites')">
                <span> Site Performance Analysis | Last Week | (Week {weeks[-1]['week_num']})</span>
                <div class="section-header-right">
                    <a href="#top" class="back-to-top" onclick="event.stopPropagation();">⬆ Back to Top</a>
                    <span class="toggle-icon">▼</span>
                </div>
            </div>
            <div class="section-content expanded" id="section-sites">
                
                <!-- Pareto Chart -->
                <div style="margin-bottom: 30px;">
                    <h3 style="font-size: 1.4em; color: #505050; margin-bottom: 20px; font-weight: 800;">Pareto Chart | Site NBOT Contributors</h3>
                    <div class="chart-container">
                        <canvas id="paretoChart"></canvas>
                    </div>
                </div>
                
                <input type="text" class="search-box" id="siteSearch" onkeyup="filterTable('siteTable', 'siteSearch')" placeholder="🔍 Search sites...">
                
                <table id="siteTable" class="performance-table">
                    <thead>
                        <tr>
                            <th class="sortable" onclick="sortTable('siteTable', 0)">#</th>
                            <th class="sortable" onclick="sortTable('siteTable', 1)">Location</th>
                            <th class="sortable" onclick="sortTable('siteTable', 2)">City</th>
                            <th class="sortable" onclick="sortTable('siteTable', 3)">State</th>
                            <th class="sortable" onclick="sortTable('siteTable', 4)">Manager</th>
                            <th class="sortable" onclick="sortTable('siteTable', 5)">Employees</th>
                            <th class="sortable" onclick="sortTable('siteTable', 6)">Total Hours</th>
                            <th class="sortable" onclick="sortTable('siteTable', 7)">Total OT</th>
                            <th class="sortable" onclick="sortTable('siteTable', 8)">NBOT Hours</th>
                            <th class="sortable" onclick="sortTable('siteTable', 9)">NBOT %</th>
                            <th class="sortable" onclick="sortTable('siteTable', 10)">Cumulative NBOT %</th>
                            <th class="sortable" onclick="sortTable('siteTable', 11)">Billable Capture</th>
                            <th class="sortable" onclick="sortTable('siteTable', 12)">Sick Events</th>
                            <th class="sortable" onclick="sortTable('siteTable', 13)">Unpaid Events</th>
                            <th class="sortable" onclick="sortTable('siteTable', 14)">Total Call-Offs</th>
                        </tr>
                    </thead>
                    <tbody>
"""
        
        for idx, site in enumerate(site_performance, 1):
            nbot_pct = float(site.get('nbot_pct', 0))
            if nbot_pct < 3:
                status_class = "status-green"
            elif nbot_pct < 4:
                status_class = "status-yellow"
            else:
                status_class = "status-red"
            
            # Add Pareto highlighting class
            pareto_class = " pareto-80" if site.get('is_pareto_80', False) else ""
            
            html += f"""
                        <tr class="{pareto_class}">
                            <td>{idx}</td>
                            <td><strong>{site.get('location_number', 'N/A')}</strong></td>
                            <td>{site.get('city', 'N/A')}</td>
                            <td>{site.get('state', 'N/A')}</td>
                            <td>{site.get('manager', 'Unassigned')}</td>
                            <td>{site.get('employee_count', 0)}</td>
                            <td>{site.get('total_hours', 0):,.2f}</td>
                            <td>{site.get('total_ot_hours', 0):,.2f}</td>
                            <td>{site.get('nbot_hours', 0):,.2f}</td>
                            <td class="{status_class}">{nbot_pct:.2f}%</td>
                            <td><strong>{site.get('cumulative_nbot_pct', 0):.1f}%</strong></td>
                            <td>{site.get('billable_capture_rate', 0):.1f}%</td>
                            <td>{site.get('sick_events', 0)}</td>
                            <td>{site.get('unpaid_events', 0)}</td>
                            <td><strong>{site.get('total_calloffs', 0)}</strong></td>
                        </tr>
"""
        
        html += """
                    </tbody>
                </table>
"""
        
        # Add Pareto insight box if stats available
        if pareto_stats and pareto_stats.get('total_sites', 0) > 0:
            html += f"""
                <div class="highlight-box" style="margin-top: 25px;">
                    <strong>📊 Pareto Analysis (80/20 Rule):</strong> The top <strong>{pareto_stats.get('pareto_80_count', 0)} sites</strong> ({pareto_stats.get('pareto_80_pct', 0):.1f}% of locations) contribute <strong>80% of total NBOT hours</strong>. Focus improvement efforts here for maximum impact. The top 3 sites alone account for <strong>{pareto_stats.get('top_3_pct', 0):.1f}%</strong> ({pareto_stats.get('top_3_nbot', 0):,.0f} hours) of all NBOT. <span style="background: rgba(255,193,7,0.2); padding: 2px 6px; border-radius: 4px; font-weight: 600;">🟨 Highlighted rows</span> indicate sites in the critical 80%.
                </div>
"""
        
        html += """
                <button class="export-btn" onclick="exportTableToCSV('siteTable', 'site_performance.csv')">📥 Export to CSV</button>
            </div>
        </div>
"""

    # Manager Performance Table Section
    if manager_performance:
        html += f"""
        <!-- Manager Performance Table Section -->
        <div class="section">
            <div class="section-header" onclick="toggleSection('managers')">
                <span>👨‍💼 Manager Performance Analysis (Week {weeks[-1]['week_num']})</span>
                <div class="section-header-right">
                    <a href="#top" class="back-to-top" onclick="event.stopPropagation();">⬆ Back to Top</a>
                    <span class="toggle-icon">▼</span>
                </div>
            </div>
            <div class="section-content expanded" id="section-managers">
                <input type="text" class="search-box" id="managerSearch" onkeyup="filterTable('managerTable', 'managerSearch')" placeholder="🔍 Search managers...">
                
                <table id="managerTable" class="performance-table">
                    <thead>
                        <tr>
                            <th class="sortable" onclick="sortTable('managerTable', 0)">#</th>
                            <th class="sortable" onclick="sortTable('managerTable', 1)">Manager</th>
                            <th class="sortable" onclick="sortTable('managerTable', 2)">Sites</th>
                            <th class="sortable" onclick="sortTable('managerTable', 3)">Total Hours</th>
                            <th class="sortable" onclick="sortTable('managerTable', 4)">Total OT</th>
                            <th class="sortable" onclick="sortTable('managerTable', 5)">NBOT Hours</th>
                            <th class="sortable" onclick="sortTable('managerTable', 6)">NBOT %</th>
                            <th class="sortable" onclick="sortTable('managerTable', 7)">Billable Capture</th>
                        </tr>
                    </thead>
                    <tbody>
"""
        
        for idx, mgr in enumerate(manager_performance, 1):
            nbot_pct = float(mgr.get('nbot_pct', 0))
            if nbot_pct < 3:
                status_class = "status-green"
            elif nbot_pct < 4:
                status_class = "status-yellow"
            else:
                status_class = "status-red"
            
            html += f"""
                        <tr>
                            <td>{idx}</td>
                            <td><strong>{mgr.get('manager', 'Unassigned')}</strong></td>
                            <td>{mgr.get('site_count', 0)}</td>
                            <td>{mgr.get('total_hours', 0):,.2f}</td>
                            <td>{mgr.get('total_ot_hours', 0):,.2f}</td>
                            <td>{mgr.get('nbot_hours', 0):,.2f}</td>
                            <td class="{status_class}">{nbot_pct:.2f}%</td>
                            <td>{mgr.get('billable_capture_rate', 0):.1f}%</td>
                        </tr>
"""
        
        html += """
                    </tbody>
                </table>
                <button class="export-btn" onclick="exportTableToCSV('managerTable', 'manager_performance.csv')">📥 Export to CSV</button>
            </div>
        </div>
"""

    # Pay Type Distribution Section
    if pay_type:
        total_hours = pay_type.get('total_counter_hours', 0)
        hourly_hours = pay_type.get('hourly_hours', 0)
        salaried_hours = pay_type.get('salaried_hours', 0)
        contractor_hours = pay_type.get('contractor_1099_hours', 0)
        
        html += f"""
        <!-- Pay Type Distribution Section -->
        <div class="section">
            <div class="section-header" onclick="toggleSection('paytype')">
                <span>👥 Total Hours Distribution by Pay Type (Week {weeks[-1]['week_num']})</span>
                <div class="section-header-right">
                    <a href="#top" class="back-to-top" onclick="event.stopPropagation();">⬆ Back to Top</a>
                    <span class="toggle-icon">▼</span>
                </div>
            </div>
            <div class="section-content expanded" id="section-paytype">
                <h3 style="font-size: 1.2em; color: #505050; margin-bottom: 16px; font-weight: 800;">Total Hours by Pay Type</h3>
                
                <div class="pareto-bar">
                    <div class="pareto-item">
                        <div class="pareto-label">
                            <span>Hourly</span>
                            <span style="color: #808080;">{(hourly_hours/total_hours*100) if total_hours > 0 else 0:.1f}%</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {min((hourly_hours/total_hours*100) if total_hours > 0 else 0, 100):.1f}%;">{hourly_hours:,.0f}h</div>
                        </div>
                    </div>
                    
                    <div class="pareto-item">
                        <div class="pareto-label">
                            <span>Salaried</span>
                            <span style="color: #808080;">{(salaried_hours/total_hours*100) if total_hours > 0 else 0:.1f}%</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {min((salaried_hours/total_hours*100) if total_hours > 0 else 0, 100):.1f}%;">{salaried_hours:,.0f}h</div>
                        </div>
                    </div>
                    
                    <div class="pareto-item">
                        <div class="pareto-label">
                            <span>1099 / Contractor</span>
                            <span style="color: #808080;">{(contractor_hours/total_hours*100) if total_hours > 0 else 0:.1f}%</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {min((contractor_hours/total_hours*100) if total_hours > 0 else 0, 100):.1f}%;">{contractor_hours:,.0f}h</div>
                        </div>
                    </div>
                </div>
                
                <div class="highlight-box">
                    <strong>💡 Pay Type Insight:</strong> Hourly employees represent {(hourly_hours/total_hours*100) if total_hours > 0 else 0:.1f}% of total counter hours.
                    <br><span style="font-size: 0.9em; font-style: italic; color: #6b7280;">Note: Pay type percentages use Total Counter Hours (includes all paid time). OT percentages use TWH (excludes unpaid time off).</span> NBOT analysis focuses primarily on hourly employees as they are most impacted by overtime regulations.
                </div>
            </div>
        </div>
"""

    # Detailed Breakdown Section
    if hourly_ot_comp or billable_ot_data or nbot_breakdown:
        html += f"""
        <!-- Detailed Breakdown Section -->
        <div class="section">
            <div class="section-header" onclick="toggleSection('breakdown')">
                <span>📋 Detailed OT Breakdown (Week {weeks[-1]['week_num']} - Hourly Only)</span>
                <div class="section-header-right">
                    <a href="#top" class="back-to-top" onclick="event.stopPropagation();">⬆ Back to Top</a>
                    <span class="toggle-icon">▼</span>
                </div>
            </div>
            <div class="section-content expanded" id="section-breakdown">
"""
        
        # Hourly OT Composition
        if hourly_ot_comp:
            html += """
                <h3 style="font-size: 1.2em; color: #505050; margin-bottom: 16px; font-weight: 800;">Total Hourly OT Composition</h3>
                <div class="pareto-bar">
"""
            for item in hourly_ot_comp:
                html += f"""
                    <div class="pareto-item">
                        <div class="pareto-label">
                            <span>{item.get('ot_category', 'Unknown')}</span>
                            <span style="color: #808080;">{item.get('pct_of_ot', 0):.1f}%</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {min(item.get('pct_of_ot', 0), 100):.1f}%;">{item.get('ot_hours', 0):,.0f}h</div>
                        </div>
                    </div>
"""
            html += """
                </div>
"""
        
        # Billable OT Breakdown
        if billable_ot_data:
            html += """
                <h3 style="font-size: 1.2em; color: #505050; margin-bottom: 16px; margin-top: 30px; font-weight: 800;">Billable OT Breakdown (Premium Anywhere)</h3>
                <div class="pareto-bar">
"""
            for item in billable_ot_data:
                html += f"""
                    <div class="pareto-item">
                        <div class="pareto-label">
                            <span>{item.get('ot_category', 'Unknown')}</span>
                            <span style="color: #10b981;">{item.get('pct_of_ot', 0):.1f}%</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {min(item.get('pct_of_ot', 0), 100):.1f}%; background: linear-gradient(145deg, #10b981 0%, #047857 100%); border-color: #6ee7b7 #065f46 #065f46;">{item.get('billable_hours', 0):,.0f}h</div>
                        </div>
                    </div>
"""
            html += """
                </div>
"""
        
        # NBOT Breakdown
        if nbot_breakdown:
            html += """
                <h3 style="font-size: 1.2em; color: #505050; margin-bottom: 16px; margin-top: 30px; font-weight: 800;">Non-Billable OT (NBOT) Breakdown</h3>
                <div class="pareto-bar">
"""
            for item in nbot_breakdown:
                if item.get('nbot_hours', 0) > 0:
                    html += f"""
                    <div class="pareto-item">
                        <div class="pareto-label">
                            <span>{item.get('ot_category', 'Unknown')}</span>
                            <span style="color: #dc2626;">{item.get('pct_of_ot', 0):.1f}%</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {min(item.get('pct_of_ot', 0), 100):.1f}%; background: linear-gradient(145deg, #dc2626 0%, #991b1b 100%); border-color: #fca5a5 #7f1d1d #7f1d1d;">{item.get('nbot_hours', 0):,.0f}h</div>
                        </div>
                    </div>
"""
            html += """
                </div>
                
                <div class="highlight-box">
                    <strong>🔍 Analysis Note:</strong> NBOT hours are calculated as Total OT minus Billable OT for each category. This shows which overtime types contribute most to non-billable costs after accounting for premium billing.
                </div>
"""
        
        html += """
            </div>
        </div>
"""

    # Add this section after employee callouts

        # Calculate metrics for recommendations
    if ot_breakdown and employee_callouts:
        top_ot_cat = ot_breakdown[0] if ot_breakdown else {}
        top_cat_name = top_ot_cat.get('ot_category', 'Top Category')
        top_cat_hours = float(top_ot_cat.get('nbot_hours', 0))
        top_cat_pct = float(top_ot_cat.get('percentage', 0))
        
        # Absenteeism metrics
        weekend_pattern_count = len([e for e in employee_callouts if '🔴 Weekend' in e.get('pattern_type', '') or '🔴 Long Weekend' in e.get('pattern_type', '')])
        high_risk_count = len([e for e in employee_callouts if int(e.get('total_callouts', 0)) >= 3])
        total_callout_hours = sum(float(e.get('total_callout_hours', 0)) for e in employee_callouts)
        
        # Calculate gap
        nbot_gap_hours = latest_week['nbot_hours'] - (latest_week['twh'] * 0.03)
        nbot_gap_pct = latest_week['nbot_pct'] - 3.0
        
        # Trend analysis
        nbot_trend = latest_week['nbot_pct'] - first_week['nbot_pct']
        wow_change = latest_week['nbot_pct'] - prev_week['nbot_pct']
        
        # Billable OT opportunity
        billable_conversion_rate = (latest_week['billable_ot_hours'] / latest_week['total_ot_hours'] * 100) if latest_week['total_ot_hours'] > 0 else 0
        
        # Site variance (if available)
        site_variance_high = False
        if site_performance and len(site_performance) >= 3:
            top_site_nbot = float(site_performance[0].get('nbot_pct', 0))
            avg_site_nbot = sum(float(s.get('nbot_pct', 0)) for s in site_performance[:5]) / min(5, len(site_performance))
            site_variance_high = (top_site_nbot - avg_site_nbot) > 2.0  # More than 2% variance
        
        # Manager variance (if available)
        manager_variance_high = False
        if manager_performance and len(manager_performance) >= 3:
            top_mgr_nbot = float(manager_performance[0].get('nbot_pct', 0))
            avg_mgr_nbot = sum(float(m.get('nbot_pct', 0)) for m in manager_performance[:5]) / min(5, len(manager_performance))
            manager_variance_high = (top_mgr_nbot - avg_mgr_nbot) > 2.0

    html += f"""
            <!-- Strategic Recommendations Section -->
            <div class="section">
                <div class="section-header" onclick="toggleSection('recommendations')">
                    <span>💡 Strategic Recommendations & Action Plan</span>
                    <div class="section-header-right">
                        <a href="#top" class="back-to-top" onclick="event.stopPropagation();">⬆ Back to Top</a>
                        <span class="toggle-icon">▼</span>
                    </div>
                </div>
                <div class="section-content expanded" id="section-recommendations">
                    
                    <!-- Executive Summary -->
                    <div style="background: linear-gradient(145deg, {'#dcfce7' if nbot_gap_pct <= 0 else '#fee2e2'} 0%, {'#bbf7d0' if nbot_gap_pct <= 0 else '#fecaca'} 100%); border: 3px solid {'#16a34a' if nbot_gap_pct <= 0 else '#dc2626'}; border-radius: 12px; padding: 25px; margin-bottom: 30px; box-shadow: 0 4px 12px rgba({'22, 163, 74' if nbot_gap_pct <= 0 else '220, 38, 38'}, 0.3);">
                        <h2 style="color: {'#065f46' if nbot_gap_pct <= 0 else '#991b1b'}; margin: 0 0 15px 0; font-size: 1.8em;">
                            {'✅ NBOT Below Target!' if nbot_gap_pct <= 0 else f'🚨 Close {abs(nbot_gap_hours):,.0f} Hour Gap to Target'}
                        </h2>
                        <div style="color: {'#064e3b' if nbot_gap_pct <= 0 else '#7f1d1d'}; font-size: 1.15em; line-height: 1.8;">
                            Current NBOT is <strong>{latest_week['nbot_pct']:.2f}%</strong>, which is <strong>{abs(nbot_gap_pct):.2f}%</strong> {'below' if nbot_gap_pct <= 0 else 'above'} the 3% target. 
                            {'Great work maintaining performance!' if nbot_gap_pct <= 0 else f"This represents approximately <strong>{abs(nbot_gap_hours):,.0f} hours</strong> that need reduction."}<br><br>
                            
                            <strong>🎯 Focus Areas:</strong><br>
                            • <strong>{top_cat_name}:</strong> {top_cat_hours:,.0f} hours ({top_cat_pct:.1f}% of NBOT) - largest contributor<br>
                            • <strong>Absenteeism Patterns:</strong> {total_callout_hours:,.0f} hours lost, {weekend_pattern_count} employees with suspicious patterns<br>
                            • <strong>High-Risk Employees:</strong> {high_risk_count} employees with 3+ call-outs in 4 weeks
                        </div>
                    </div>

                    <!-- Dynamic Recommendations -->
                    <div style="background: white; border-radius: 12px; padding: 30px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
    """

    # Generate dynamic recommendations based on data
    recommendations_added = 0

    # RECOMMENDATION 1: Trend-based (Always show)
    if wow_change > 0.5:
        html += f"""
                        <div style="background: #fef2f2; border-left: 4px solid #dc2626; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                            <h4 style="color: #991b1b; margin: 0 0 10px 0;">🚨 URGENT: NBOT Worsening</h4>
                            <div style="color: #7f1d1d; line-height: 1.7;">
                                <strong>Data Alert:</strong> NBOT increased by <strong>{wow_change:.2f}%</strong> week-over-week. 
                                Immediate intervention required to prevent further deterioration.<br><br>
                                <strong>Immediate Actions:</strong>
                                <ul style="margin: 10px 0; padding-left: 25px;">
                                    <li>Emergency leadership review today to identify spike drivers</li>
                                    <li>Freeze non-critical OT approvals until root cause identified</li>
                                    <li>Daily NBOT check-ins with site managers</li>
                                </ul>
                                <strong>Owner:</strong> Operations Director | <strong>Timeline:</strong> Immediate
                            </div>
                        </div>
    """
        recommendations_added += 1
    elif nbot_trend < -0.5 and nbot_gap_pct <= 0:
        html += f"""
                        <div style="background: #f0fdf4; border-left: 4px solid #16a34a; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                            <h4 style="color: #065f46; margin: 0 0 10px 0;">🎯 Sustain Success</h4>
                            <div style="color: #064e3b; line-height: 1.7;">
                                <strong>Success Story:</strong> NBOT improved by <strong>{abs(nbot_trend):.2f}%</strong> over 4 weeks and is now below target. 
                                Document what's working to maintain performance.<br><br>
                                <strong>Key Actions:</strong>
                                <ul style="margin: 10px 0; padding-left: 25px;">
                                    <li>Document successful practices from last 4 weeks</li>
                                    <li>Share best practices across all sites/managers</li>
                                    <li>Continue weekly NBOT monitoring to prevent regression</li>
                                </ul>
                                <strong>Owner:</strong> Operations Leadership | <strong>Timeline:</strong> This Week
                            </div>
                        </div>
    """
        recommendations_added += 1

    # RECOMMENDATION 2: Top OT Category (if dominant)
    if top_cat_pct > 60:
        html += f"""
                        <div style="background: #fffbeb; border-left: 4px solid #f59e0b; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                            <h4 style="color: #92400e; margin: 0 0 10px 0;">⚙️ {top_cat_name} Dominates NBOT</h4>
                            <div style="color: #78350f; line-height: 1.7;">
                                <strong>Data Analysis:</strong> {top_cat_name} accounts for <strong>{top_cat_pct:.1f}%</strong> of NBOT ({top_cat_hours:,.0f} hours). 
                                This single category is the primary driver - fixing it will have outsized impact.<br><br>
                                <strong>Root Cause Investigation:</strong>
                                <ul style="margin: 10px 0; padding-left: 25px;">
                                    <li>Review scheduling patterns: Are we short-staffed during peak {top_cat_name} times?</li>
                                    <li>Manager approval audit: Which managers approve most {top_cat_name} OT?</li>
                                    <li>Process efficiency: Can we complete work faster to avoid OT need?</li>
                                    <li>Cross-training: Can other employees cover {top_cat_name} work during regular hours?</li>
                                </ul>
                                <strong>Owner:</strong> Operations + Workforce Planning | <strong>Timeline:</strong> 1-2 Weeks
                            </div>
                        </div>
    """
        recommendations_added += 1

    # RECOMMENDATION 3: Weekend Pattern Absenteeism (if exists)
    if weekend_pattern_count > 0:
        html += f"""
                        <div style="background: #fef2f2; border-left: 4px solid #dc2626; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                            <h4 style="color: #991b1b; margin: 0 0 10px 0;">👥 Address {weekend_pattern_count} Weekend Pattern Abusers</h4>
                            <div style="color: #7f1d1d; line-height: 1.7;">
                                <strong>Pattern Detection:</strong> {weekend_pattern_count} employees show suspicious attendance patterns 
                                (🔴 Weekend Pattern, 🔴 Long Weekend), suggesting intentional weekend extensions.<br><br>
                                <strong>Immediate Actions:</strong>
                                <ul style="margin: 10px 0; padding-left: 25px;">
                                    <li>Site managers review patterns with each employee this week</li>
                                    <li>Present data: "Your call-outs follow a pattern - let's discuss"</li>
                                    <li>Issue documented warning for pattern continuation</li>
                                    <li>HR tracks for progressive discipline if patterns persist</li>
                                </ul>
                                <strong>Target:</strong> 50% reduction in weekend call-outs within 2 weeks | <strong>Owner:</strong> Site Managers + HR
                            </div>
                        </div>
    """
        recommendations_added += 1

    # RECOMMENDATION 4: High-Risk Employees (if count >= 3)
    if high_risk_count >= 3:
        html += f"""
                        <div style="background: #fffbeb; border-left: 4px solid #f59e0b; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                            <h4 style="color: #92400e; margin: 0 0 10px 0;">📋 {high_risk_count} High-Risk Employees Need Intervention</h4>
                            <div style="color: #78350f; line-height: 1.7;">
                                <strong>Attendance Alert:</strong> {high_risk_count} employees have 3+ call-outs in 4 weeks, representing 
                                <strong>{total_callout_hours:,.0f} hours</strong> of lost productivity.<br><br>
                                <strong>Progressive Discipline Process:</strong>
                                <ul style="margin: 10px 0; padding-left: 25px;">
                                    <li>HR reviews full attendance history for each employee</li>
                                    <li>Issue formal written warnings for excessive absenteeism</li>
                                    <li>Weekly attendance tracking for flagged employees</li>
                                    <li>Performance improvement plans for repeat offenders</li>
                                </ul>
                                <strong>Target:</strong> Zero employees with 3+ call-outs within 4 weeks | <strong>Owner:</strong> HR + Site Managers
                            </div>
                        </div>
    """
        recommendations_added += 1

    # RECOMMENDATION 5: Billable OT Conversion Opportunity (if low)
    if billable_conversion_rate < 60 and latest_week['total_ot_hours'] > 100:
        html += f"""
                        <div style="background: #eff6ff; border-left: 4px solid #3b82f6; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                            <h4 style="color: #1e40af; margin: 0 0 10px 0;">💰 Low Billable OT Conversion ({billable_conversion_rate:.1f}%)</h4>
                            <div style="color: #1e3a8a; line-height: 1.7;">
                                <strong>Opportunity:</strong> Only <strong>{billable_conversion_rate:.1f}%</strong> of Total OT is billable. 
                                Opportunity to convert more OT to billable by reviewing project codes and customer agreements.<br><br>
                                <strong>Actions:</strong>
                                <ul style="margin: 10px 0; padding-left: 25px;">
                                    <li>Audit project coding: Is OT being charged to correct billable projects?</li>
                                    <li>Review customer contracts: Are there billable opportunities we're missing?</li>
                                    <li>Manager training on billable vs non-billable classification</li>
                                </ul>
                                <strong>Target:</strong> 70% billable conversion rate | <strong>Owner:</strong> Finance + Operations
                            </div>
                        </div>
    """
        recommendations_added += 1

    # RECOMMENDATION 6: Site Variance (if high)
    if site_variance_high and site_performance:
        top_site = site_performance[0]
        html += f"""
                        <div style="background: #fef2f2; border-left: 4px solid #dc2626; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                            <h4 style="color: #991b1b; margin: 0 0 10px 0;">🏢 High Site Variance Detected</h4>
                            <div style="color: #7f1d1d; line-height: 1.7;">
                                <strong>Outlier Alert:</strong> Site {top_site.get('location_number', 'N/A')} has NBOT of <strong>{top_site.get('nbot_pct', 0):.2f}%</strong>, 
                                significantly higher than average. This site needs targeted intervention.<br><br>
                                <strong>Site-Specific Actions:</strong>
                                <ul style="margin: 10px 0; padding-left: 25px;">
                                    <li>Meet with Site Manager {top_site.get('manager', 'N/A')} to review drivers</li>
                                    <li>Compare staffing levels, volume, and processes vs. better-performing sites</li>
                                    <li>Implement best practices from top-performing sites</li>
                                </ul>
                                <strong>Owner:</strong> Regional Manager + Site Manager | <strong>Timeline:</strong> This Week
                            </div>
                        </div>
    """
        recommendations_added += 1

    # RECOMMENDATION 7: Manager Variance (if high)
    if manager_variance_high and manager_performance:
        top_mgr = manager_performance[0]
        html += f"""
                        <div style="background: #fffbeb; border-left: 4px solid #f59e0b; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                            <h4 style="color: #92400e; margin: 0 0 10px 0;">👔 Manager Performance Variance</h4>
                            <div style="color: #78350f; line-height: 1.7;">
                                <strong>Coaching Opportunity:</strong> Manager {top_mgr.get('manager', 'N/A')} has NBOT of <strong>{top_mgr.get('nbot_pct', 0):.2f}%</strong>, 
                                significantly higher than peer average. One-on-one coaching needed.<br><br>
                                <strong>Manager Development:</strong>
                                <ul style="margin: 10px 0; padding-left: 25px;">
                                    <li>Review OT approval patterns and decision-making</li>
                                    <li>Shadow high-performing managers to learn best practices</li>
                                    <li>Weekly NBOT review meetings with direct supervisor</li>
                                </ul>
                                <strong>Owner:</strong> Regional Manager | <strong>Timeline:</strong> 1 Week
                            </div>
                        </div>
    """
        recommendations_added += 1

    # RECOMMENDATION 8: OneTouch Dashboard (if no other urgent issues)
    if recommendations_added < 3:
        html += f"""
                        <div style="background: #eff6ff; border-left: 4px solid #3b82f6; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                            <h4 style="color: #1e40af; margin: 0 0 10px 0;">📊 Real-Time Tracking with OneTouch NBOT Workbench</h4>
                            <div style="color: #1e3a8a; line-height: 1.7;">
                                Implement daily NBOT tracking showing current week progress toward target. 
                                Early visibility prevents end-of-week surprises and enables mid-week corrections.<br><br>
                                <strong>Implementation:</strong> Contact Fusion Center to activate dashboard access for all managers.
                            </div>
                        </div>
    """

    # If no recommendations at all (perfect performance)
    if recommendations_added == 0:
        html += f"""
                        <div style="background: #f0fdf4; border-left: 4px solid #16a34a; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                            <h4 style="color: #065f46; margin: 0 0 10px 0;">✅ Excellent Performance - Maintain Current Practices</h4>
                            <div style="color: #064e3b; line-height: 1.7;">
                                No critical issues identified. Continue current practices and monitor weekly to maintain performance.
                                Consider documenting successful strategies to share across organization.
                            </div>
                        </div>
"""
    
    html += """
                </div>
            </div>
        </div>

        <footer>
            <p><strong>Excellence Performance Center</strong></p>
            <p>NBOT Snapshot Report | Generated: """ + timestamp + """</p>
            <p style="margin-top: 10px; color: #fbbf24;">⚠️ Confidential - For Internal Use Only</p>
        </footer>
    </div>

    <script>
        // Chart.js - Trend Chart
        const trendCtx = document.getElementById('trendChart').getContext('2d');
        const trendChart = new Chart(trendCtx, {
            type: 'line',
            data: {
                labels: """ + str(week_labels) + """,
                datasets: [{
                    label: 'NBOT %',
                    data: """ + str(nbot_pct_data) + """,
                    borderColor: '#dc2626',
                    backgroundColor: 'rgba(220, 38, 38, 0.1)',
                    tension: 0.4,
                    fill: true,
                    borderWidth: 3,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    hours: """ + str(nbot_hours_data) + """
                }, {
                    label: 'Billable OT %',
                    data: """ + str(billable_ot_pct_data) + """,
                    borderColor: '#16a34a',
                    backgroundColor: 'rgba(22, 163, 74, 0.1)',
                    tension: 0.4,
                    fill: true,
                    borderWidth: 3,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    hours: """ + str(billable_ot_hours_data) + """
                }, {
                    label: 'Total OT %',
                    data: """ + str(total_ot_pct_data) + """,
                    borderColor: '#f59e0b',
                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                    tension: 0.4,
                    fill: true,
                    borderWidth: 3,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    hours: """ + str(total_ot_hours_data) + """
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'NBOT, Billable OT & Total OT Trends (4 Weeks)',
                        font: { size: 18, weight: 'bold' },
                        color: '#505050'
                    },
                    legend: {
                        position: 'top',
                        labels: {
                            font: { size: 14 },
                            padding: 15
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.dataset.label || '';
                                const percentage = context.parsed.y.toFixed(2) + '%';
                                const hours = context.dataset.hours[context.dataIndex].toFixed(0);
                                return label + ': ' + percentage + ' (' + hours + ' hours)';
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Percentage (%)',
                            font: { size: 14, weight: 'bold' }
                        },
                        ticks: {
                            font: { size: 12 }
                        }
                    },
                    x: {
                        ticks: {
                            font: { size: 12 }
                        }
                    }
                }
            }
        });


        // Chart.js - NBOT Breakdown with Percentage Labels
        const nbotCtx = document.getElementById('nbotChart').getContext('2d');
        const nbotData = """ + str(ot_nbot_data) + """;
        const totalNbotHours = nbotData.reduce((a, b) => a + b, 0);
        
        const nbotChart = new Chart(nbotCtx, {
            type: 'bar',
            data: {
                labels: """ + str(ot_categories) + """,
                datasets: [{
                    label: 'NBOT Hours',
                    data: nbotData,
                    backgroundColor: 'rgba(220, 38, 38, 0.7)',
                    borderColor: '#dc2626',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'OT Contributors by Category',
                        font: { size: 18, weight: 'bold' },
                        color: '#505050'
                    },
                    legend: {
                        position: 'top',
                        labels: {
                            font: { size: 14 },
                            padding: 15
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const hours = context.parsed.y;
                                const pct = ((hours / totalNbotHours) * 100).toFixed(1);
                                return 'NBOT Hours: ' + hours.toFixed(0) + ' (' + pct + '%)';
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'NBOT Hours',
                            font: { size: 14, weight: 'bold' }
                        },
                        ticks: {
                            font: { size: 12 }
                        }
                    },
                    x: {
                        ticks: {
                            font: { size: 11 }
                        }
                    }
                }
            },
            plugins: [{
                afterDatasetsDraw: function(chart) {
                    const ctx = chart.ctx;
                    chart.data.datasets.forEach(function(dataset, i) {
                        const meta = chart.getDatasetMeta(i);
                        if (!meta.hidden) {
                            meta.data.forEach(function(element, index) {
                                ctx.fillStyle = '#505050';
                                const fontSize = 12;
                                const fontStyle = 'bold';
                                const fontFamily = 'Roboto';
                                ctx.font = fontStyle + ' ' + fontSize + 'px ' + fontFamily;
                                
                                const hours = dataset.data[index];
                                const pct = ((hours / totalNbotHours) * 100).toFixed(1);
                                const dataString = hours.toFixed(0) + 'h (' + pct + '%)';
                                ctx.textAlign = 'center';
                                ctx.textBaseline = 'bottom';
                                
                                const padding = 5;
                                const position = element.tooltipPosition();
                                ctx.fillText(dataString, position.x, position.y - padding);
                            });
                        }
                    });
                }
            }]
        });

        


        // Chart.js - Absenteeism Trends (4 weeks)
        const absenteeismCtx = document.getElementById('absenteeismChart').getContext('2d');
        
        const sickData = [
            """ + str(weeks[0]['sick_events']) + """,  // Week 1
            """ + str(weeks[1]['sick_events']) + """,  // Week 2
            """ + str(weeks[2]['sick_events']) + """,  // Week 3
            """ + str(weeks[3]['sick_events']) + """   // Week 4 (current)
        ];
        
        const unpaidData = [
            """ + str(weeks[0]['unpaid_events']) + """,  // Week 1
            """ + str(weeks[1]['unpaid_events']) + """,  // Week 2
            """ + str(weeks[2]['unpaid_events']) + """,  // Week 3
            """ + str(weeks[3]['unpaid_events']) + """   // Week 4 (current)
        ];
        
        const totalCallouts = sickData.map((val, idx) => val + unpaidData[idx]);
        
        const absenteeismChart = new Chart(absenteeismCtx, {
            type: 'bar',
            data: {
                labels: """ + str(week_labels) + """,
                datasets: [{
                    label: 'Sick Call-Offs',
                    data: sickData,
                    backgroundColor: 'rgba(220, 38, 38, 0.7)',
                    borderColor: '#dc2626',
                    borderWidth: 2,
                    yAxisID: 'y'
                }, {
                    label: 'Unpaid Time Off',
                    data: unpaidData,
                    backgroundColor: 'rgba(245, 158, 11, 0.7)',
                    borderColor: '#f59e0b',
                    borderWidth: 2,
                    yAxisID: 'y'
                }, {
                    label: 'Total Call-Outs',
                    data: totalCallouts,
                    type: 'line',
                    borderColor: '#6b7280',
                    backgroundColor: 'rgba(107, 114, 128, 0.1)',
                    borderWidth: 3,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    yAxisID: 'y',
                    order: 1,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Absenteeism Trends - 4 Week Overview',
                        font: { size: 18, weight: 'bold' },
                        color: '#505050'
                    },
                    legend: {
                        position: 'top',
                        labels: {
                            font: { size: 14 },
                            padding: 15
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.dataset.label + ': ' + context.parsed.y + ' events';
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Number of Events',
                            font: { size: 14, weight: 'bold' }
                        },
                        ticks: {
                            font: { size: 12 },
                            stepSize: 1
                        }
                    },
                    x: {
                        ticks: {
                            font: { size: 12 }
                        }
                    }
                }
            }
        });


        
        // Chart.js - Pareto Chart
        const paretoCtx = document.getElementById('paretoChart').getContext('2d');
        const paretoChart = new Chart(paretoCtx, {
            type: 'bar',
            data: {
                labels: """ + str(pareto_site_labels) + """,
                datasets: [{
                    label: 'NBOT Hours',
                    data: """ + str(pareto_nbot_hours) + """,
                    backgroundColor: 'rgba(220, 38, 38, 0.7)',
                    borderColor: '#dc2626',
                    borderWidth: 2,
                    yAxisID: 'y',
                    order: 2
                }, {
                    label: 'Cumulative %',
                    data: """ + str(pareto_cumulative) + """,
                    type: 'line',
                    borderColor: '#f59e0b',
                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                    borderWidth: 3,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    yAxisID: 'y1',
                    order: 1,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Pareto Analysis - Top 20 Sites by NBOT Hours',
                        font: { size: 18, weight: 'bold' },
                        color: '#505050'
                    },
                    legend: {
                        position: 'top',
                        labels: {
                            font: { size: 14 },
                            padding: 15
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                if (context.dataset.label === 'Cumulative %') {
                                    return 'Cumulative: ' + context.parsed.y.toFixed(1) + '%';
                                } else {
                                    return 'NBOT Hours: ' + context.parsed.y.toFixed(0);
                                }
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'NBOT Hours',
                            font: { size: 14, weight: 'bold' },
                            color: '#dc2626'
                        },
                        ticks: {
                            font: { size: 12 }
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Cumulative %',
                            font: { size: 14, weight: 'bold' },
                            color: '#f59e0b'
                        },
                        ticks: {
                            font: { size: 12 },
                            callback: function(value) {
                                return value + '%';
                            }
                        },
                        grid: {
                            drawOnChartArea: false
                        }
                    },
                    x: {
                        ticks: {
                            font: { size: 10 },
                            maxRotation: 45,
                            minRotation: 45
                        }
                    }
                }
            }
        });
        
        // Table sorting function with bidirectional support
        function sortTable(tableId, colIndex) {
            const table = document.getElementById(tableId);
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            const header = table.querySelectorAll('th')[colIndex];
            
            // Get current sort direction from header (default to descending)
            const currentDirection = header.getAttribute('data-sort-direction') || 'desc';
            const newDirection = currentDirection === 'asc' ? 'desc' : 'asc';
            
            // Clear all sort indicators
            table.querySelectorAll('th').forEach(th => {
                th.removeAttribute('data-sort-direction');
                th.classList.remove('sort-asc', 'sort-desc');
            });
            
            // Set new sort direction
            header.setAttribute('data-sort-direction', newDirection);
            header.classList.add(newDirection === 'asc' ? 'sort-asc' : 'sort-desc');
            
            const isNumeric = !isNaN(parseFloat(rows[0].cells[colIndex].textContent.replace(/[^0-9.-]/g, '')));
            
            rows.sort((a, b) => {
                let aVal = a.cells[colIndex].textContent.trim();
                let bVal = b.cells[colIndex].textContent.trim();
                
                if (isNumeric) {
                    aVal = parseFloat(aVal.replace(/[^0-9.-]/g, '')) || 0;
                    bVal = parseFloat(bVal.replace(/[^0-9.-]/g, '')) || 0;
                    return newDirection === 'asc' ? (aVal - bVal) : (bVal - aVal);
                } else {
                    return newDirection === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
                }
            });
            
            rows.forEach(row => tbody.appendChild(row));
        }
        
        // Table filtering function
        function filterTable(tableId, searchId) {
            const input = document.getElementById(searchId);
            const filter = input.value.toLowerCase();
            const table = document.getElementById(tableId);
            const rows = table.querySelectorAll('tbody tr');
            
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(filter) ? '' : 'none';
            });
        }
        
        // Export table to CSV
        function exportTableToCSV(tableId, filename) {
            const table = document.getElementById(tableId);
            const rows = table.querySelectorAll('tr');
            const csv = [];
            
            rows.forEach(row => {
                const cols = row.querySelectorAll('td, th');
                const csvRow = [];
                cols.forEach(col => csvRow.push(col.textContent));
                csv.push(csvRow.join(','));
            });
            
            const csvContent = csv.join('\\n');
            const blob = new Blob([csvContent], { type: 'text/csv' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = filename;
            link.click();
        }

        function toggleSection(sectionId) {
            const content = document.getElementById('section-' + sectionId);
            const header = content.previousElementSibling;
            const icon = header.querySelector('.toggle-icon');
            
            if (content.classList.contains('expanded')) {
                content.classList.remove('expanded');
                icon.classList.remove('expanded');
            } else {
                content.classList.add('expanded');
                icon.classList.add('expanded');
            }
        }

        document.addEventListener('DOMContentLoaded', function() {
            document.documentElement.style.scrollBehavior = 'smooth';
            
            const navButtons = document.querySelectorAll('.nav-button');
            
            navButtons.forEach(button => {
                button.addEventListener('click', function(e) {
                    e.preventDefault();
                    
                    const targetId = this.getAttribute('href').substring(1);
                    const targetSection = document.getElementById(targetId);
                    
                    if (targetSection) {
                        const content = targetSection;
                        const header = content.previousElementSibling;
                        const icon = header ? header.querySelector('.toggle-icon') : null;
                        
                        if (!content.classList.contains('expanded')) {
                            content.classList.add('expanded');
                            if (icon) icon.classList.add('expanded');
                        }
                        
                        const sectionHeader = content.previousElementSibling;
                        const offset = 100;
                        const elementPosition = sectionHeader.getBoundingClientRect().top;
                        const offsetPosition = elementPosition + window.pageYOffset - offset;
                        
                        window.scrollTo({
                            top: offsetPosition,
                            behavior: 'smooth'
                        });
                    }
                });
            });

            const backToTopLinks = document.querySelectorAll('.back-to-top');
            
            backToTopLinks.forEach(link => {
                link.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    
                    window.scrollTo({
                        top: 0,
                        behavior: 'smooth'
                    });
                });
            });
        });
    </script>

</body>
</html>"""
    
    return html


def _get_snapshot_css() -> str:
    """Return the complete beveled metal 3D CSS styling."""
    return """
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;600;700;900&display=swap');
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Roboto', sans-serif;
            background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
            padding: 40px 20px;
            min-height: 100vh;
        }

        .container {
            max-width: 1800px;
            margin: 0 auto;
        }

        /* NAVIGATION BUTTONS - Centered at Top */
        .nav-container {
            display: flex;
            justify-content: center;
            gap: 12px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }

        .nav-button {
            background: linear-gradient(145deg, #808080 0%, #606060 100%);
            color: white;
            border: 2px solid;
            border-color: #60a5fa #505050 #505050 #60a5fa;
            border-radius: 12px;
            padding: 10px 18px;
            font-weight: 700;
            font-size: 0.75em;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 
                inset 0 1px 0 rgba(255,255,255,0.3),
                inset 0 -1px 0 rgba(0,0,0,0.2),
                0 3px 0 #505050,
                0 5px 10px rgba(59,130,246,0.5);
            text-shadow: 0 1px 2px rgba(0,0,0,0.4);
            text-decoration: none;
            display: inline-block;
            text-align: center;
        }

        .nav-button:hover {
            transform: translateY(-2px);
            box-shadow: 
                inset 0 1px 0 rgba(255,255,255,0.4),
                inset 0 -1px 0 rgba(0,0,0,0.25),
                0 4px 0 #505050,
                0 7px 15px rgba(59,130,246,0.6);
        }

        .nav-button:active {
            transform: translateY(1px);
            box-shadow: 
                inset 0 1px 0 rgba(255,255,255,0.3),
                inset 0 -1px 0 rgba(0,0,0,0.2),
                0 1px 0 #505050,
                0 3px 6px rgba(59,130,246,0.4);
        }

        /* Chrome Industrial Header with Beveled Metal */
        .header {
            background: 
                linear-gradient(135deg, 
                    rgba(255,255,255,0.1) 0%, 
                    transparent 20%, 
                    transparent 80%, 
                    rgba(0,0,0,0.2) 100%),
                linear-gradient(135deg, 
                    #000814 0%, 
                    #505050 25%, 
                    #808080 50%, 
                    #505050 75%, 
                    #000814 100%);
            padding: 30px 40px;
            text-align: center;
            border-radius: 16px;
            margin-bottom: 30px;
            position: relative;
            overflow: hidden;
            border: 3px solid;
            border-color: #60a5fa #505050 #505050 #60a5fa;
            box-shadow: 
                inset 0 2px 0 rgba(255,255,255,0.2),
                inset 0 -2px 0 rgba(0,0,0,0.4),
                0 8px 0 #505050,
                0 10px 0 #505050,
                0 12px 0 #1e293b,
                0 16px 30px rgba(0,0,0,0.6);
        }

        .header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 60%;
            background: linear-gradient(180deg, 
                rgba(255,255,255,0.25) 0%,
                rgba(255,255,255,0.1) 30%, 
                transparent 100%);
        }

        h1 {
            font-size: 2.2em;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: 2px;
            color: white;
            text-shadow: 
                0 1px 0 rgba(255,255,255,0.3),
                0 2px 4px rgba(0,0,0,0.8),
                0 4px 8px rgba(0,0,0,0.6);
            margin-bottom: 10px;
            position: relative;
            z-index: 1;
        }

        .subtitle {
            font-size: 1.1em;
            color: #bfdbfe;
            font-weight: 600;
            position: relative;
            z-index: 1;
            text-shadow: 0 1px 3px rgba(0,0,0,0.6);
        }

        /* Meta Cards - Beveled Metal Style */
        .report-meta {
            background: linear-gradient(145deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 16px;
            padding: 25px;
            margin-bottom: 30px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            border: 3px solid;
            border-color: #ffffff #c0c0c0 #a0a0a0 #ffffff;
            box-shadow: 
                inset 0 2px 0 rgba(255,255,255,0.9),
                inset 0 -2px 0 rgba(0,0,0,0.2),
                0 6px 0 #c0c0c0,
                0 8px 0 #a0a0a0,
                0 10px 20px rgba(0,0,0,0.4);
        }

        .meta-item {
            text-align: center;
            padding: 15px;
            background: linear-gradient(145deg, #ffffff 0%, #f0f0f0 100%);
            border-radius: 8px;
            border: 1px solid;
            border-color: rgba(255,255,255,0.8) rgba(0,0,0,0.1) rgba(0,0,0,0.1) rgba(255,255,255,0.8);
            box-shadow: 
                inset 0 1px 0 rgba(255,255,255,0.8),
                0 2px 4px rgba(0,0,0,0.1);
        }

        .meta-label {
            font-size: 0.85em;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
            font-weight: 700;
            text-shadow: 0 1px 0 rgba(255,255,255,0.8);
        }

        .meta-value {
            font-size: 1.4em;
            font-weight: 800;
            color: #505050;
            text-shadow: 
                0 1px 0 rgba(255,255,255,0.8),
                0 2px 3px rgba(0,0,0,0.2);
        }

        /* Section Container - Beveled Metal */
        .section {
            background: linear-gradient(145deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 16px;
            margin-bottom: 25px;
            border: 3px solid;
            border-color: #ffffff #c0c0c0 #a0a0a0 #ffffff;
            box-shadow: 
                inset 0 2px 0 rgba(255,255,255,0.9),
                inset 0 -2px 0 rgba(0,0,0,0.2),
                0 6px 0 #c0c0c0,
                0 8px 0 #a0a0a0,
                0 10px 20px rgba(0,0,0,0.4);
            overflow: hidden;
            transition: all 0.3s ease;
        }

        /* Section Header - Clickable with Metal Finish */
        .section-header {
            background: 
                linear-gradient(145deg, 
                    rgba(255,255,255,0.08) 0%, 
                    transparent 50%, 
                    rgba(0,0,0,0.15) 100%),
                linear-gradient(90deg, 
                    #606060 0%, 
                    #808080 50%, 
                    #606060 100%);
            color: white;
            padding: 18px 25px;
            font-size: 1.3em;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            cursor: pointer;
            user-select: none;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid;
            border-color: #60a5fa #505050 #505050;
            box-shadow: 
                inset 0 1px 0 rgba(255,255,255,0.2),
                inset 0 -1px 0 rgba(0,0,0,0.3),
                0 2px 4px rgba(0,0,0,0.2);
            transition: all 0.3s ease;
            text-shadow: 0 1px 2px rgba(0,0,0,0.4);
        }

        .section-header-right {
            display: flex;
            align-items: center;
            gap: 15px;
        }

        .back-to-top {
            background: linear-gradient(145deg, rgba(255,255,255,0.15) 0%, rgba(255,255,255,0.05) 100%);
            color: white;
            border: 2px solid rgba(255,255,255,0.3);
            border-radius: 8px;
            padding: 6px 12px;
            font-size: 0.65em;
            font-weight: 700;
            text-decoration: none;
            transition: all 0.3s ease;
            box-shadow: 
                inset 0 1px 0 rgba(255,255,255,0.2),
                0 2px 4px rgba(0,0,0,0.2);
            text-shadow: 0 1px 2px rgba(0,0,0,0.4);
            white-space: nowrap;
        }

        .back-to-top:hover {
            background: linear-gradient(145deg, rgba(255,255,255,0.25) 0%, rgba(255,255,255,0.15) 100%);
            border-color: rgba(255,255,255,0.5);
            transform: translateY(-2px);
            box-shadow: 
                inset 0 1px 0 rgba(255,255,255,0.3),
                0 3px 6px rgba(0,0,0,0.3);
        }

        .section-header:hover {
            background: 
                linear-gradient(145deg, 
                    rgba(255,255,255,0.12) 0%, 
                    transparent 50%, 
                    rgba(0,0,0,0.2) 100%),
                linear-gradient(90deg, 
                    #808080 0%, 
                    #60a5fa 50%, 
                    #808080 100%);
        }

        .toggle-icon {
            font-size: 0.8em;
            transition: transform 0.3s ease;
            display: inline-block;
        }

        .toggle-icon.expanded {
            transform: rotate(180deg);
        }

        /* Section Content - Collapsible */
        .section-content {
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.5s ease-out, padding 0.3s ease;
            padding: 0 25px;
        }

        .section-content.expanded {
            max-height: 10000px;
            padding: 25px;
            transition: max-height 0.8s ease-in, padding 0.3s ease;
        }

        h2 {
            font-size: 1.8em;
            color: #505050;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #808080;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 1px;
            text-shadow: 
                0 1px 0 rgba(255,255,255,0.8),
                0 2px 3px rgba(0,0,0,0.2);
        }

        h3 {
            font-size: 1.3em;
            color: #505050;
            margin: 25px 0 15px 0;
            font-weight: 700;
            text-shadow: 0 1px 0 rgba(255,255,255,0.6);
        }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 20px;
            margin: 25px 0;
        }

        /* Metric Card - Beveled Metal */
        .metric-card {
            background: linear-gradient(145deg, #ffffff 0%, #f0f0f0 100%);
            border-radius: 12px;
            padding: 25px;
            text-align: center;
            position: relative;
            transition: all 0.3s ease;
            border: 2px solid;
            border-color: #ffffff #d0d0d0 #b0b0b0 #ffffff;
            box-shadow: 
                inset 0 1px 0 rgba(255,255,255,0.8),
                inset 0 -1px 0 rgba(0,0,0,0.2),
                0 6px 0 #d0d0d0,
                0 8px 0 #b0b0b0,
                0 10px 0 #a0a0a0,
                0 14px 20px rgba(0,0,0,0.4);
        }

        .metric-card::before {
            content: '';
            position: absolute;
            top: 2px;
            left: 2px;
            right: 2px;
            bottom: 2px;
            border-radius: 10px;
            background: linear-gradient(145deg, 
                rgba(255,255,255,0.6) 0%, 
                rgba(255,255,255,0) 30%,
                rgba(0,0,0,0) 70%,
                rgba(0,0,0,0.2) 100%);
            pointer-events: none;
        }

        .metric-card:hover {
            transform: translateY(-4px);
            box-shadow: 
                inset 0 1px 0 rgba(255,255,255,0.9),
                inset 0 -1px 0 rgba(0,0,0,0.25),
                0 8px 0 #d0d0d0,
                0 10px 0 #b0b0b0,
                0 12px 0 #a0a0a0,
                0 18px 30px rgba(0,0,0,0.5);
        }

        .metric-label {
            font-size: 0.9em;
            color: #6b7280;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 700;
            text-shadow: 0 1px 0 rgba(255,255,255,0.8);
            position: relative;
        }

        .metric-value {
            font-size: 2.5em;
            font-weight: 900;
            color: #505050;
            margin: 15px 0;
            line-height: 1;
            text-shadow: 
                0 1px 0 rgba(255,255,255,0.8),
                0 2px 4px rgba(0,0,0,0.3);
            position: relative;
        }

        .metric-sublabel {
            font-size: 1.1em;
            color: #808080;
            margin: 8px 0;
            font-weight: 600;
            position: relative;
        }

        .metric-change {
            font-size: 0.95em;
            padding: 8px 12px;
            border-radius: 8px;
            font-weight: 600;
            display: inline-block;
            margin-top: 8px;
            border: 1px solid;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            position: relative;
        }

        .metric-change.positive {
            background: linear-gradient(145deg, #d1fae5 0%, #a7f3d0 100%);
            color: #065f46;
            border-color: rgba(16,185,129,0.3);
        }

        .metric-change.negative {
            background: linear-gradient(145deg, #fee2e2 0%, #fecaca 100%);
            color: #991b1b;
            border-color: rgba(239,68,68,0.3);
        }

        .metric-change.neutral {
            background: linear-gradient(145deg, #f3f4f6 0%, #e5e7eb 100%);
            color: #4b5563;
            border-color: rgba(107,114,128,0.3);
        }

        /* Chart Container */
        .chart-container {
            position: relative;
            height: 400px;
            margin: 30px 0;
            padding: 20px;
            background: linear-gradient(145deg, #ffffff 0%, #f8f9fa 100%);
            border-radius: 12px;
            border: 2px solid;
            border-color: #ffffff #d0d0d0 #b0b0b0 #ffffff;
            box-shadow: 
                inset 0 1px 0 rgba(255,255,255,0.8),
                0 4px 8px rgba(0,0,0,0.1);
        }

        /* Week Card - Beveled Metal Style */
        .four-week-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 25px 0;
        }

        .week-card {
            background: linear-gradient(145deg, #ffffff 0%, #f0f0f0 100%);
            border-radius: 12px;
            padding: 25px;
            position: relative;
            transition: all 0.3s ease;
            border: 2px solid;
            border-color: #ffffff #d0d0d0 #b0b0b0 #ffffff;
            box-shadow: 
                inset 0 1px 0 rgba(255,255,255,0.8),
                inset 0 -1px 0 rgba(0,0,0,0.2),
                0 6px 0 #d0d0d0,
                0 8px 0 #b0b0b0,
                0 10px 0 #a0a0a0,
                0 14px 20px rgba(0,0,0,0.4);
        }

        .week-card::before {
            content: '';
            position: absolute;
            top: 2px;
            left: 2px;
            right: 2px;
            bottom: 2px;
            border-radius: 10px;
            background: linear-gradient(145deg, 
                rgba(255,255,255,0.6) 0%, 
                rgba(255,255,255,0) 30%,
                rgba(0,0,0,0) 70%,
                rgba(0,0,0,0.2) 100%);
            pointer-events: none;
        }

        .week-card:hover {
            transform: translateY(-6px);
            box-shadow: 
                inset 0 1px 0 rgba(255,255,255,0.9),
                inset 0 -1px 0 rgba(0,0,0,0.25),
                0 8px 0 #d0d0d0,
                0 10px 0 #b0b0b0,
                0 12px 0 #a0a0a0,
                0 18px 30px rgba(0,0,0,0.5);
        }

        .week-title {
            font-size: 1.2em;
            font-weight: 800;
            color: #808080;
            text-transform: uppercase;
            margin-bottom: 8px;
            text-shadow: 
                0 1px 0 rgba(255,255,255,0.8),
                0 2px 3px rgba(0,0,0,0.2);
            position: relative;
        }

        .week-nbot {
            font-size: 3em;
            font-weight: 900;
            color: #dc2626;
            margin: 20px 0;
            line-height: 1;
            text-shadow: 
                0 1px 0 rgba(255,255,255,0.8),
                0 3px 6px rgba(220,38,38,0.4);
            position: relative;
        }

        .week-details {
            margin-top: 15px;
            font-size: 0.9em;
            line-height: 1.8;
            color: #374151;
            position: relative;
        }

        .week-details div {
            padding: 8px 0;
            border-bottom: 1px solid rgba(209,213,219,0.5);
        }

        .week-details div:last-child {
            border-bottom: none;
        }

        /* Grouped Bar Chart Styles */
        .chart-bars-grouped {
            display: flex;
            align-items: flex-end;
            justify-content: space-around;
            height: 450px;
            gap: 30px;
            padding: 20px;
        }

        .chart-bar-group {
            display: flex;
            flex-direction: column;
            align-items: center;
            flex: 1;
        }

        .bar-group-label {
            font-size: 1em;
            font-weight: 700;
            color: #505050;
            margin-bottom: 95px;
            text-shadow: 0 1px 0 rgba(255,255,255,0.8);
        }

        .bars-container {
            display: flex;
            gap: 10px;
            align-items: flex-end;
            height: 370px;
        }

        .chart-bar-container-grouped {
            display: flex;
            flex-direction: column;
            align-items: center;
            position: relative;
        }

        .chart-bar-nbot {
            width: 60px;
            background: linear-gradient(180deg, #ef4444 0%, #991b1b 100%);
            border-radius: 8px 8px 0 0;
            position: relative;
            transition: all 0.3s ease;
            border: 2px solid;
            border-color: #fca5a5 #7f1d1d #7f1d1d;
            box-shadow: 
                inset 0 1px 0 rgba(255,255,255,0.2),
                0 4px 8px rgba(239, 68, 68, 0.4);
        }

        .chart-bar-ot {
            width: 60px;
            background: linear-gradient(180deg, #808080 0%, #505050 100%);
            border-radius: 8px 8px 0 0;
            position: relative;
            transition: all 0.3s ease;
            border: 2px solid;
            border-color: #60a5fa #505050 #505050;
            box-shadow: 
                inset 0 1px 0 rgba(255,255,255,0.2),
                0 4px 8px rgba(59, 130, 246, 0.4);
        }

        .chart-bar-nbot:hover, .chart-bar-ot:hover {
            box-shadow: 
                inset 0 1px 0 rgba(255,255,255,0.3),
                0 6px 16px rgba(59, 130, 246, 0.5);
            transform: scale(1.05);
        }

        .bar-sublabel {
            font-size: 0.75em;
            color: #6b7280;
            margin-top: 8px;
            font-weight: 600;
            text-shadow: 0 1px 0 rgba(255,255,255,0.6);
        }

        .bar-percent-grouped {
            font-weight: 700;
            font-size: 1.1em;
            color: #505050;
            margin-top: 12px;
            text-shadow: 0 1px 0 rgba(255,255,255,0.8);
        }

        .bar-value {
            position: absolute;
            top: -30px;
            left: 0;
            right: 0;
            text-align: center;
            font-weight: 700;
            font-size: 0.95em;
            color: #111827;
            text-shadow: 0 1px 0 rgba(255,255,255,0.8);
        }

        /* Pareto and Progress Bars - Beveled */
        .pareto-bar {
            background: linear-gradient(145deg, #ffffff 0%, #f0f0f0 100%);
            border: 2px solid;
            border-color: #ffffff #d0d0d0 #b0b0b0 #ffffff;
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
            box-shadow: 
                inset 0 1px 0 rgba(255,255,255,0.8),
                0 2px 4px rgba(0,0,0,0.1);
        }

        .pareto-item {
            margin-bottom: 20px;
            position: relative;
        }

        .pareto-label {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            font-weight: 700;
            color: #374151;
            text-shadow: 0 1px 0 rgba(255,255,255,0.6);
        }

        .progress-bar {
            background: linear-gradient(145deg, #e5e7eb 0%, #d1d5db 100%);
            border-radius: 10px;
            height: 30px;
            overflow: hidden;
            position: relative;
            border: 1px solid;
            border-color: #9ca3af #f3f4f6 #f3f4f6 #9ca3af;
            box-shadow: 
                inset 0 2px 4px rgba(0,0,0,0.2),
                0 1px 0 rgba(255,255,255,0.5);
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(145deg, #808080 0%, #505050 100%);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            padding-right: 10px;
            font-weight: 700;
            font-size: 0.85em;
            color: white;
            transition: width 0.8s ease;
            border: 1px solid;
            border-color: #60a5fa #505050 #505050;
            box-shadow: 
                inset 0 1px 0 rgba(255,255,255,0.3),
                0 2px 4px rgba(59, 130, 246, 0.4);
            text-shadow: 0 1px 2px rgba(0,0,0,0.4);
        }

        /* Tables */
        .search-box {
            margin: 20px 0;
            padding: 12px;
            width: 100%;
            max-width: 400px;
            border: 2px solid #cbd5e0;
            border-radius: 8px;
            font-size: 1em;
            background: white;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
        }

        .performance-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }

        .performance-table th {
            background: linear-gradient(135deg, #505050 0%, #808080 100%);
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
            cursor: pointer;
            user-select: none;
            border: 2px solid;
            border-color: #60a5fa #505050 #505050;
            text-shadow: 0 1px 2px rgba(0,0,0,0.4);
        }

        .performance-table th:hover {
            background: linear-gradient(135deg, #505050 0%, #606060 100%);
        }

        .performance-table th.sortable::after {
            content: ' ⬍';
            opacity: 0.5;
        }
        
        .performance-table th.sort-asc::after {
            content: ' ▲';
            opacity: 1;
            color: #60a5fa;
        }
        
        .performance-table th.sort-desc::after {
            content: ' ▼';
            opacity: 1;
            color: #60a5fa;
        }

        .performance-table td {
            padding: 12px 15px;
            border-bottom: 1px solid #e9ecef;
        }

        .performance-table tr:hover {
            background: #f8f9fa;
        }
        
        /* Pareto 80% highlighting */
        .performance-table tr.pareto-80 {
            background: rgba(255, 193, 7, 0.15);
        }
        
        .performance-table tr.pareto-80:hover {
            background: rgba(255, 193, 7, 0.25);
        }

        .status-green { color: #16a34a; font-weight: bold; }
        .status-yellow { color: #ca8a04; font-weight: bold; }
        .status-red { color: #dc2626; font-weight: bold; }

        .export-btn {
            background: linear-gradient(145deg, #10b981 0%, #059669 100%);
            color: white;
            border: 2px solid;
            border-color: #6ee7b7 #065f46 #065f46;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 700;
            margin-top: 20px;
            transition: all 0.3s;
            box-shadow: 
                inset 0 1px 0 rgba(255,255,255,0.3),
                0 3px 0 #059669,
                0 5px 10px rgba(16,185,129,0.4);
            text-shadow: 0 1px 2px rgba(0,0,0,0.4);
        }

        .export-btn:hover {
            transform: translateY(-2px);
            box-shadow: 
                inset 0 1px 0 rgba(255,255,255,0.4),
                0 4px 0 #059669,
                0 7px 15px rgba(16,185,129,0.5);
        }

        .export-btn:active {
            transform: translateY(1px);
            box-shadow: 
                inset 0 1px 0 rgba(255,255,255,0.3),
                0 1px 0 #059669,
                0 3px 6px rgba(16,185,129,0.3);
        }

        /* Highlight Box - Beveled */
        .highlight-box {
            background: linear-gradient(145deg, rgba(59, 130, 246, 0.15) 0%, rgba(59, 130, 246, 0.08) 100%);
            border-left: 4px solid #808080;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
            border: 2px solid;
            border-color: rgba(96,165,250,0.3) rgba(30,64,175,0.2) rgba(30,64,175,0.2) rgba(96,165,250,0.3);
            box-shadow: 
                inset 0 1px 0 rgba(255,255,255,0.5),
                0 2px 4px rgba(59,130,246,0.2);
            color: #505050;
            text-shadow: 0 1px 0 rgba(255,255,255,0.6);
        }

        /* Recommendations - Beveled */
        .recommendations {
            counter-reset: rec-counter;
        }

        .recommendation-item {
            background: linear-gradient(145deg, #ffffff 0%, #f0f0f0 100%);
            border: 2px solid;
            border-color: #ffffff #d0d0d0 #b0b0b0 #ffffff;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            position: relative;
            padding-left: 70px;
            box-shadow: 
                inset 0 1px 0 rgba(255,255,255,0.8),
                inset 0 -1px 0 rgba(0,0,0,0.1),
                0 4px 0 #d0d0d0,
                0 6px 12px rgba(0,0,0,0.2);
            transition: all 0.3s ease;
        }

        .recommendation-item:hover {
            transform: translateY(-3px);
            box-shadow: 
                inset 0 1px 0 rgba(255,255,255,0.9),
                inset 0 -1px 0 rgba(0,0,0,0.15),
                0 6px 0 #d0d0d0,
                0 8px 16px rgba(59, 130, 246, 0.3);
        }

        .recommendation-item::before {
            counter-increment: rec-counter;
            content: counter(rec-counter);
            position: absolute;
            left: 15px;
            top: 20px;
            background: linear-gradient(145deg, #808080 0%, #505050 100%);
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 900;
            font-size: 1.3em;
            color: white;
            border: 2px solid;
            border-color: #60a5fa #505050 #505050 #60a5fa;
            box-shadow: 
                inset 0 1px 0 rgba(255,255,255,0.3),
                0 3px 0 #505050,
                0 5px 10px rgba(59, 130, 246, 0.5);
            text-shadow: 0 1px 2px rgba(0,0,0,0.4);
        }

        .rec-title {
            font-weight: 700;
            font-size: 1.1em;
            color: #505050;
            margin-bottom: 8px;
            text-shadow: 0 1px 0 rgba(255,255,255,0.6);
        }

        .recommendation-item p {
            color: #374151;
            line-height: 1.6;
            text-shadow: 0 1px 0 rgba(255,255,255,0.5);
        }

        .rec-timeline {
            display: inline-block;
            background: linear-gradient(145deg, #808080 0%, #606060 100%);
            border: 2px solid;
            border-color: #60a5fa #505050 #505050 #60a5fa;
            padding: 6px 14px;
            border-radius: 12px;
            font-size: 0.85em;
            margin-top: 10px;
            color: white;
            font-weight: 700;
            box-shadow: 
                inset 0 1px 0 rgba(255,255,255,0.2),
                0 2px 0 #505050,
                0 4px 8px rgba(59,130,246,0.4);
            text-shadow: 0 1px 2px rgba(0,0,0,0.4);
        }

        /* Footer - Beveled */
        footer {
            text-align: center;
            padding: 30px;
            color: #e5e7eb;
            border-top: 3px solid #4b5563;
            margin-top: 40px;
            background: 
                linear-gradient(145deg, 
                    rgba(255,255,255,0.05) 0%, 
                    transparent 50%, 
                    rgba(0,0,0,0.1) 100%),
                linear-gradient(90deg, 
                    #1f2937 0%, 
                    #374151 50%, 
                    #1f2937 100%);
            border-radius: 12px;
            border: 2px solid;
            border-color: #4b5563 #1f2937 #111827 #4b5563;
            box-shadow: 
                inset 0 1px 0 rgba(255,255,255,0.1),
                0 4px 8px rgba(0,0,0,0.3);
            text-shadow: 0 1px 2px rgba(0,0,0,0.5);
        }

        footer p {
            margin: 5px 0;
        }

        @media (max-width: 1600px) {
            .metrics-grid {
                grid-template-columns: repeat(4, 1fr);
            }
        }

        @media (max-width: 1200px) {
            .metrics-grid {
                grid-template-columns: repeat(3, 1fr);
            }
        }

        @media (max-width: 768px) {
            .container {
                max-width: 100%;
            }
            
            .four-week-grid {
                grid-template-columns: 1fr;
            }
            .metrics-grid {
                grid-template-columns: 1fr;
            }
            .chart-bars-grouped {
                flex-direction: column;
                height: auto;
                gap: 30px;
            }
            .bars-container {
                height: auto;
            }
            .chart-bar-nbot, .chart-bar-ot {
                width: 50px;
            }
            .nav-container {
                flex-direction: column;
            }
            .nav-button {
                width: 100%;
            }
        }
    """


# ============================================================
# Example Usage
# ============================================================

if __name__ == "__main__":
    # Test with company-wide scope
    print("Generating 4-Week NBOT Snapshot Report...")
    
    html_content, filename = _generate_nbot_company_4week_snapshot(
        end_date="2025-11-08",
        project="your-project",
        dataset="your-dataset",
        compute_project="your-compute-project"
    )
    
    output_path = f"/mnt/user-data/outputs/{filename}"
    with open(output_path, "w") as f:
        f.write(html_content)
    
    print(f"✅ Report generated: {filename}")
    print(f"✅ Saved to: {output_path}")
    print("✅ Features:")
    print("   • Beveled metal 3D styling throughout")
    print("   • 1800px container width")
    print("   • 5 metric cards per row")
    print("   • Centered navigation buttons (10 sections)")
    print("   • Meta cards section (5 cards)")
    print("   • Chart.js interactive charts (trend line + bar chart)")
    print("   • Workforce Analysis with SQL queries and data processing")
    print("   • Sortable site performance table with search & CSV export")
    print("   • Sortable manager performance table with search & CSV export")
    print("   • Detailed week comparison cards")
    print("   • Grouped bar chart (NBOT + Total OT)")
    print("   • All existing sections preserved")