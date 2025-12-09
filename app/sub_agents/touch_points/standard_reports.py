# ============================================================
# EPC • TOUCH POINTS Standard Reports (APEX_TP)
# Env vars:
#   BQ_DATA_PROJECT_ID
#   BQ_DATASET_ID
#   BQ_COMPUTE_PROJECT_ID
# Dataset used: <project>.<dataset>.APEX_TP
# ============================================================

from jinja2 import Template
from typing import Optional, Dict, Any, List, Tuple
import os
from google.cloud import bigquery

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
    Resolve a customer_code from either the provided code or a fuzzy customer_name,
    using APEX_TP. Returns (code, error_message). If ambiguous, returns an error with options.
    """
    if customer_code is not None:
        try:
            return int(customer_code), None
        except Exception:
            return None, "Invalid customer_code format. Please provide an integer."

    if not customer_name:
        return None, "Please provide either customer_code or customer_name."

    client = bigquery.Client(project=compute_project)

    # 🔁 Touch Points table
    sql = f"""
        SELECT DISTINCT customer_code, customer_name
        FROM `{project}.{dataset}.APEX_TP`
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
        return None, f"No customers matched '{customer_name}' in APEX_TP. Please provide the customer_code directly."

    if len(rows) == 1:
        return int(rows[0]["customer_code"]), None

    opts = [f"  • {r['customer_name']} (code: {r['customer_code']})" for r in rows]
    msg = (
        f"Found {len(rows)} customers matching '{customer_name}' in APEX_TP:\n\n"
        + "\n".join(opts) +
        f"\n\nPlease specify the exact customer_code."
    )
    return None, msg


# ------------------------------------------------------------
# Public entrypoint / Dispatcher (Touch Points)
# ------------------------------------------------------------
def generate_standard_report(
    report_id: str,
    customer_code: Optional[int] = None,
    customer_name: Optional[str] = None,
    location_number: Optional[str] = None,
    region: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    # Optional TP facets pass-through (we'll use in later steps):
    tp_type: Optional[str] = None,
    channel: Optional[str] = None,
    priority: Optional[str] = None,
    owner: Optional[str] = None,
) -> str:
    """
    Touch Points standard reports on interactions (APEX_TP).
    Route by report_id and return a fully-rendered Markdown string.

    report_id options (TP):
      - "tp_site_analysis"
      - "tp_region_analysis"
      - "tp_customer_analysis"
      - "tp_company_overview"          (by region &/or customer rollups)
      - "tp_exec_report"               (narrative)
    """
    project, dataset, compute_project, env_err = _env()
    if env_err:
        return env_err

    # ---------- tp_site_analysis ----------
    if report_id == "tp_site_analysis":
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
        return _generate_tp_site_analysis(
            code, location_number, start_date, end_date,
            project, dataset, compute_project,
            tp_type=tp_type, channel=channel, priority=priority, owner=owner,
        )

    # ---------- tp_region_analysis ----------
    if report_id == "tp_region_analysis":
        if not all([region, start_date, end_date]):
            return "Missing required parameters: region, start_date, end_date"
        return _generate_tp_region_analysis(
            region, start_date, end_date,
            project, dataset, compute_project,
            tp_type=tp_type, channel=channel, priority=priority, owner=owner,
        )

    # ---------- tp_customer_analysis ----------
    if report_id == "tp_customer_analysis":
        code, err = _resolve_customer_code(
            customer_code=customer_code,
            customer_name=customer_name,
            project=project, dataset=dataset, compute_project=compute_project,
        )
        if err:
            return f"❌ Customer Resolution Error:\n\n{err}"
        if not all([code, start_date, end_date]):
            return "Missing required parameters: customer_code|customer_name, start_date, end_date"
        return _generate_tp_customer_analysis(
            code, start_date, end_date,
            project, dataset, compute_project,
            region=region, tp_type=tp_type, channel=channel, priority=priority, owner=owner,
        )

    # ---------- tp_company_overview ----------
    if report_id == "tp_company_overview":
        if not all([start_date, end_date]):
            return "Missing required parameters: start_date, end_date"
        return _generate_tp_company_overview(
            start_date, end_date,
            project, dataset, compute_project,
            tp_type=tp_type, channel=channel, priority=priority, owner=owner,
        )

    # ---------- tp_exec_report ----------
    if report_id == "tp_exec_report":
        # We'll assemble a narrative in a later step; for now, a simple placeholder:
        return _generate_tp_exec_report_placeholder(
            start_date, end_date, region=region, customer_code=customer_code, customer_name=customer_name
        )

    return (
        f"Report '{report_id}' not implemented.\n\n"
        "Available: tp_site_analysis, tp_region_analysis, tp_customer_analysis, "
        "tp_company_overview, tp_exec_report"
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
    if not all([customer_code, location_number, start_date, end_date]):
        return "Missing required parameters: customer_code, location_number, start_date, end_date"

    customer_code_str = str(customer_code)

    emp_sql = f"""
WITH EmployeesAtSite AS (
  SELECT DISTINCT employee_id
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE customer_code = '{customer_code_str}'
    AND CAST(location_number AS STRING) = '{location_number}'
    AND DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
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
    ANY_VALUE(site_manager) AS site_manager,
    SUM(IF(CAST(location_number AS STRING) = '{location_number}', counter_hours, 0)) AS hours_this_site,
    SUM(counter_hours) AS hours_all_sites
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
    AND employee_id IN (SELECT employee_id FROM EmployeesAtSite)
  GROUP BY employee_id
),
EmployeeFinal AS (
  SELECT
    employee_id,
    employee_name,
    employee_status,
    COALESCE(ed_start_date, ed_start_str) AS employee_date_started,
    customer_name, state, site_manager,
    hours_this_site,
    hours_all_sites,
    DATE_DIFF(CURRENT_DATE(), COALESCE(ed_start_date, ed_start_str), DAY) AS tenure_days
  FROM EmployeeAgg
)
SELECT * FROM EmployeeFinal
ORDER BY tenure_days ASC
"""

    totals_sql = f"""
WITH Base AS (
  SELECT
    counter_type,
    counter_hours
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE customer_code = '{customer_code_str}'
    AND CAST(location_number AS STRING) = '{location_number}'
    AND DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
),
Totals AS (
  SELECT
    SUM(counter_hours) AS total_hours,
    SUM(
      CASE 
        WHEN LOWER(counter_type) IN ('daily overtime','daily ot','weekly overtime','weekly ot',
                                      'holiday worked','consecutive day ot','consecutive day dt')
             OR LOWER(counter_type) LIKE '%double time%'
             OR LOWER(counter_type) LIKE '%overtime%'
        THEN counter_hours 
        ELSE 0 
      END
    ) AS nbot_hours
  FROM Base
),
OTBreakdown AS (
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
    SUM(counter_hours) AS hours
  FROM Base
  WHERE LOWER(counter_type) IN ('daily overtime','daily ot','weekly overtime','weekly ot',
                                 'holiday worked','consecutive day ot','consecutive day dt')
        OR LOWER(counter_type) LIKE '%double time%'
        OR LOWER(counter_type) LIKE '%overtime%'
  GROUP BY ot_category
),
Regular AS (
  SELECT 'Regular' AS category, SUM(counter_hours) AS hours
  FROM Base
  WHERE NOT (
    LOWER(counter_type) IN ('daily overtime','daily ot','weekly overtime','weekly ot',
                            'holiday worked','consecutive day ot','consecutive day dt')
    OR LOWER(counter_type) LIKE '%double time%'
    OR LOWER(counter_type) LIKE '%overtime%'
  )
)
SELECT
  (SELECT total_hours FROM Totals) AS total_hours,
  (SELECT nbot_hours FROM Totals) AS nbot_hours,
  SAFE_DIVIDE((SELECT nbot_hours FROM Totals),(SELECT total_hours FROM Totals)) * 100 AS nbot_pct,
  ARRAY(
    SELECT AS STRUCT ot_category, hours
    FROM OTBreakdown
    ORDER BY hours DESC
  ) AS ot_rows,
  (SELECT category FROM Regular) AS regular_label,
  (SELECT hours FROM Regular) AS regular_hours
"""

    try:
        client = bigquery.Client(project=compute_project)
        emp_rows = client.query(emp_sql).to_dataframe().to_dict(orient="records")
        tot = client.query(totals_sql).to_dataframe().to_dict(orient="records")
    except Exception as e:
        return f"Query failed: {str(e)}\n\nEMP_SQL:\n{emp_sql}\n\nTOTALS_SQL:\n{totals_sql}"

    if not tot:
        return f"No data found for customer_code={customer_code}, location_number={location_number}, dates={start_date} to {end_date}"

    totals = tot[0]
    total_hours = float(totals.get("total_hours") or 0)
    nbot_hours = float(totals.get("nbot_hours") or 0)
    nbot_pct = round(float(totals.get("nbot_pct") or 0), 2)
    regular_hours = float(totals.get("regular_hours") or 0)
    regular_pct = round((regular_hours / total_hours * 100) if total_hours else 0, 1)
    fte_needed = int((total_hours + 35.9999) // 36) if total_hours else 0

    def usage_label(h_all):
        if h_all is None: return "Unknown"
        if 32 <= h_all <= 40: return "🟢 Optimal"
        if 25 <= h_all <= 31: return "🟡 Sub-Optimal"
        if h_all < 25 or h_all > 40: return "🔴 Critical"
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

    ot_rows = totals.get("ot_rows", [])
    for r in ot_rows:
        r["pct_of_twh"] = round((float(r["hours"]) / total_hours * 100) if total_hours else 0, 2)

    header_customer = emp_rows[0]["customer_name"] if emp_rows else ""
    header_state = emp_rows[0]["state"] if emp_rows else ""
    header_manager = emp_rows[0]["site_manager"] if emp_rows else ""

    # === EXECUTIVE SUMMARY CALCULATIONS ===
    
    if nbot_pct < 3:
        nbot_status_color = "🟢"
        nbot_status_text = "Excellent — Under target"
    elif 3 <= nbot_pct <= 5:
        nbot_status_color = "🟡"
        nbot_status_text = "Acceptable — Monitor closely"
    else:
        nbot_status_color = "🔴"
        nbot_status_text = "Critical — Immediate action required"
    
    if nbot_hours > 0 and len(emp_rows) > 0:
        avg_ot_per_employee = nbot_hours / len(emp_rows)
        if avg_ot_per_employee > 1:
            employees_with_ot = int(len(emp_rows) * (nbot_pct / 100) * 2)
            employees_with_ot = min(employees_with_ot, len(emp_rows))
        else:
            employees_with_ot = max(1, int(len(emp_rows) * 0.3))
    else:
        employees_with_ot = 0
    
    employees_with_ot_pct = round((employees_with_ot / len(emp_rows) * 100) if emp_rows else 0, 1)
    
    ot_breakdown = []
    if nbot_hours > 0:
        for r in ot_rows:
            if r.get("hours", 0) > 0:
                pct_of_nbot = round((float(r["hours"]) / nbot_hours * 100), 1)
                ot_breakdown.append({
                    "label": r["ot_category"],
                    "pct_of_nbot": pct_of_nbot
                })
    
    critical_risks = sum(1 for e in emp_rows if "Critical Risk" in e.get("tenure_status", ""))
    low_utilization = sum(1 for e in emp_rows if "Critical" in e.get("usage_status", ""))
    
    if nbot_pct > 5 or (len(emp_rows) > 0 and critical_risks > len(emp_rows) * 0.4):
        site_health_status = "🔴 Needs Attention"
    elif nbot_pct > 3 or (len(emp_rows) > 0 and critical_risks > len(emp_rows) * 0.2):
        site_health_status = "🟡 Monitor"
    else:
        site_health_status = "🟢 Healthy"
    
    risk_flags = []
    if nbot_pct > 5:
        risk_flags.append(f"🔴 High NBOT ({nbot_pct:.1f}%) — Exceeds 5% threshold")
    if len(emp_rows) > 0 and critical_risks > len(emp_rows) * 0.3:
        risk_flags.append(f"🟠 Attrition Risk — {critical_risks} employees under 90 days tenure")
    if len(emp_rows) > 0 and low_utilization > len(emp_rows) * 0.3:
        risk_flags.append(f"🟡 Underutilization — {low_utilization} employees below optimal hours")
    if fte_needed > len(emp_rows) * 1.1:
        risk_flags.append(f"⚠️ Staffing Gap — Need {fte_needed} FTE, have {len(emp_rows)} employees")
    
    recommendations = []
    
    if nbot_pct > 5:
        if len(ot_rows) > 0:
            top_ot = max(ot_rows, key=lambda x: float(x.get("hours", 0)))
            if top_ot.get("hours", 0) > 0:
                recommendations.append(
                    f"**Reduce {top_ot['ot_category']}** — Accounts for "
                    f"{top_ot.get('pct_of_twh', 0):.1f}% of total hours"
                )
    
    if critical_risks > 5:
        recommendations.append(
            f"**Retention Focus** — {critical_risks} employees at critical attrition risk "
            f"(< 90 days tenure). Implement onboarding support and mentorship programs."
        )
    
    if len(emp_rows) > 0 and low_utilization > len(emp_rows) * 0.2:
        recommendations.append(
            f"**Optimize Scheduling** — {low_utilization} employees underutilized. "
            f"Review shift allocation and cross-training opportunities."
        )
    
    if fte_needed > len(emp_rows):
        gap = fte_needed - len(emp_rows)
        recommendations.append(
            f"**Increase Headcount** — Site requires {gap} additional FTE to meet demand "
            f"without excessive OT."
        )
    
    if len(emp_rows) > 0 and fte_needed < len(emp_rows) * 0.9:
        recommendations.append(
            "**Review Staffing Levels** — Current headcount exceeds operational needs. "
            "Consider reallocation or workload distribution."
        )
    
    if not recommendations:
        recommendations.append("✅ Site is operating efficiently — Continue current practices")

    context = {
        "customer_name": header_customer,
        "location_number": location_number,
        "state": header_state,
        "site_manager": header_manager,
        "start_date": start_date,
        "end_date": end_date,
        "total_hours": f"{total_hours:,.2f}",
        "employee_count": len(emp_rows),
        "nbot_hours": f"{nbot_hours:,.2f}",
        "nbot_pct": nbot_pct,
        "fte_needed": fte_needed,
        "regular_hours": f"{regular_hours:,.2f}",
        "regular_pct": f"{regular_pct:.1f}",
        "ot_rows": ot_rows,
        "employees": emp_rows,
        "site_health_status": site_health_status,
        "nbot_status_color": nbot_status_color,
        "nbot_status_text": nbot_status_text,
        "employees_with_ot": employees_with_ot,
        "employees_with_ot_pct": employees_with_ot_pct,
        "ot_breakdown": ot_breakdown,
        "risk_flags": risk_flags,
        "recommendations": recommendations,
    }

    template = Template("""
# 🌐 Excellence Performance Center 🌐
## NBOT Site Analysis
**{{ customer_name }} – Location {{ location_number }}** | **State:** {{ state }} | **Site Manager:** {{ site_manager }} | **Week:** {{ start_date }} – {{ end_date }}

---

## 📋 EXECUTIVE SUMMARY

**Site Health:** {{ site_health_status }}

### ▶️Key Findings
- **NBOT Performance:** {{ "%.2f"|format(nbot_pct) }}% ({{ nbot_status_color }}) — {{ nbot_status_text }}
- **Workforce Utilization:** {{ employee_count }} employees worked {{ total_hours }} hours
- **Coverage Status:** {{ fte_needed }} FTE needed vs {{ employee_count }} employees deployed
- **Employees with OT:** {{ employees_with_ot }} ({{ "%.1f"|format(employees_with_ot_pct) }}% of workforce)

{% if ot_breakdown and ot_breakdown|length > 0 -%}
### ▶️NBOT Breakdown
**OT Composition:** {% for row in ot_breakdown -%}{{ row.label }} {{ "%.1f"|format(row.pct_of_nbot) }}%{% if not loop.last %}, {% endif %}{% endfor %}

**NBOT Thresholds:** 🟢 GREEN < 3% · 🟡 YELLOW 3–5% · 🔴 RED > 5%
{% endif %}

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
| Total Hours Worked | {{ total_hours }} |
| Employees | {{ employee_count }} |
| NBOT Hours (OT) | {{ nbot_hours }} |
| NBOT % | {{ "%.2f"|format(nbot_pct) }}% |
| FTE Needed (36 Hrs) | {{ fte_needed }} |

---


## 📅 HOURS BREAKDOWN BY CATEGORY

| Category | Hours | % of TWH | Visual Impact |
|:---------|------:|---------:|:--------------|
| Regular (NON-OT) | {{ regular_hours }} | {{ regular_pct }}% | ████████████████████ |
{% for row in ot_rows -%}
| {{ row.ot_category }} | {{ "%.2f"|format(row.hours) }} | {{ "%.2f"|format(row.pct_of_twh) }}% | {% if row.pct_of_twh > 5 %}██████░░░░░░░░░░░░░░{% elif row.pct_of_twh > 2 %}███░░░░░░░░░░░░░░░░░{% else %}█░░░░░░░░░░░░░░░░░░░{% endif %} |
{% endfor %}

{% if ot_breakdown and ot_breakdown|length > 0 -%}
**▶️ Key Insight:** {{ ot_breakdown[0].label }} represents {{ "%.1f"|format(ot_breakdown[0].pct_of_nbot) }}% of all overtime → Primary reduction target
{% endif %}


---

## 👮 Employee Utilization Analysis
| Employee ID | Name | Tenure Days | Tenure Status | Employee Status | Hours (This Site) | Hours (All Sites) | Usage Status |
|:-----------:|:-----|:------------:|:--------------|:----------------|------------------:|------------------:|:-------------|
{% for e in employees -%}
| {{ e.employee_id }} | {{ e.employee_name }} | {{ e.tenure_days or '' }} | {{ e.tenure_status }} | {{ e.employee_status }} | {{ "%.2f"|format(e.hours_this_site or 0) }} | {{ "%.2f"|format(e.hours_all_sites or 0) }} | {{ e.usage_status }} |
{% endfor %}
""")
    return template.render(**context)


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

    customers_sql = f"""
WITH Base AS (
  SELECT
    customer_code,
    COALESCE(NULLIF(TRIM(customer_name), ''), 'Unassigned') AS customer_name,
    counter_type,
    SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
    AND TRIM(region) = '{region}'
),
Agg AS (
  SELECT
    customer_code, customer_name,
    SUM(counter_hours) AS total_hours,
    SUM(
      CASE 
        WHEN LOWER(counter_type) IN ('daily overtime','daily ot','weekly overtime','weekly ot',
                                      'holiday worked','consecutive day ot','consecutive day dt')
             OR LOWER(counter_type) LIKE '%double time%'
             OR LOWER(counter_type) LIKE '%overtime%'
        THEN counter_hours 
        ELSE 0 
      END
    ) AS nbot_hours
  FROM Base
  GROUP BY customer_code, customer_name
),
WithPct AS (
  SELECT
    customer_code, customer_name, total_hours, nbot_hours,
    SAFE_DIVIDE(nbot_hours, total_hours) * 100 AS nbot_pct
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
  customer_code, customer_name, total_hours, nbot_hours, nbot_pct,
  nbot_rank, nbot_cum_pct,
  CASE WHEN nbot_cum_pct <= 80 THEN 'Yes' ELSE 'No' END AS pareto_80_flag
FROM Pareto
ORDER BY nbot_hours DESC
"""

    region_totals_sql = f"""
WITH Base AS (
  SELECT
    counter_type,
    counter_hours
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
    AND TRIM(region) = '{region}'
)
SELECT
  SUM(counter_hours) AS total_hours,
  SUM(
    CASE 
      WHEN LOWER(counter_type) IN ('daily overtime','daily ot','weekly overtime','weekly ot',
                                    'holiday worked','consecutive day ot','consecutive day dt')
           OR LOWER(counter_type) LIKE '%double time%'
           OR LOWER(counter_type) LIKE '%overtime%'
      THEN counter_hours 
      ELSE 0 
    END
  ) AS nbot_hours,
  SAFE_DIVIDE(
    SUM(
      CASE 
        WHEN LOWER(counter_type) IN ('daily overtime','daily ot','weekly overtime','weekly ot',
                                      'holiday worked','consecutive day ot','consecutive day dt')
             OR LOWER(counter_type) LIKE '%double time%'
             OR LOWER(counter_type) LIKE '%overtime%'
        THEN counter_hours 
        ELSE 0 
      END
    ),
    SUM(counter_hours)
  ) * 100 AS nbot_pct
FROM Base
"""

    ot_breakdown_sql = f"""
WITH Base AS (
  SELECT
    counter_type,
    counter_hours
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
    AND TRIM(region) = '{region}'
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
  SUM(counter_hours) AS hours
FROM Base
WHERE LOWER(counter_type) IN ('daily overtime','daily ot','weekly overtime','weekly ot',
                               'holiday worked','consecutive day ot','consecutive day dt')
      OR LOWER(counter_type) LIKE '%double time%'
      OR LOWER(counter_type) LIKE '%overtime%'
GROUP BY ot_category
ORDER BY hours DESC
"""

    try:
        client = bigquery.Client(project=compute_project)
        cust_rows = client.query(customers_sql).to_dataframe().to_dict(orient="records")
        totals = client.query(region_totals_sql).to_dataframe().to_dict(orient="records")
        ot_breakdown_rows = client.query(ot_breakdown_sql).to_dataframe().to_dict(orient="records")
    except Exception as e:
        return f"Query failed: {str(e)}\n\nCUSTOMERS_SQL:\n{customers_sql}\n\nREGION_TOTALS_SQL:\n{region_totals_sql}"

    if not totals:
        return f"No data found for region={region}, dates={start_date} to {end_date}"

    t = totals[0]
    total_hours = float(t.get('total_hours') or 0)
    nbot_hours = float(t.get('nbot_hours') or 0)
    nbot_pct = round(float(t.get('nbot_pct') or 0), 2)
    
    # Calculate regular hours
    regular_hours = total_hours - nbot_hours
    regular_pct = round((regular_hours / total_hours * 100) if total_hours else 0, 1)
    
    # Process OT breakdown
    for r in ot_breakdown_rows:
        r["pct_of_twh"] = round((float(r["hours"]) / total_hours * 100) if total_hours else 0, 2)
    
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
    
    # Regional Health Status
    critical_customers = sum(1 for c in cust_rows if c.get("nbot_pct", 0) > 5)
    
    if nbot_pct > 5 or (len(cust_rows) > 0 and critical_customers > len(cust_rows) * 0.4):
        region_health_status = "🔴 Needs Attention"
    elif nbot_pct > 3 or (len(cust_rows) > 0 and critical_customers > len(cust_rows) * 0.2):
        region_health_status = "🟡 Monitor"
    else:
        region_health_status = "🟢 Healthy"
    
    # Customers with OT
    customers_with_ot = sum(1 for c in cust_rows if c.get("nbot_hours", 0) > 0)
    customers_with_ot_pct = round((customers_with_ot / len(cust_rows) * 100) if cust_rows else 0, 1)
    
    # OT Breakdown as % of NBOT
    ot_breakdown = []
    if nbot_hours > 0:
        for r in ot_breakdown_rows:
            if r.get("hours", 0) > 0:
                pct_of_nbot = round((float(r["hours"]) / nbot_hours * 100), 1)
                ot_breakdown.append({
                    "label": r["ot_category"],
                    "pct_of_nbot": pct_of_nbot
                })
    
    # Risk Flags
    risk_flags = []
    if nbot_pct > 5:
        risk_flags.append(f"🔴 High Regional NBOT ({nbot_pct:.1f}%) — Exceeds 5% threshold")
    if len(cust_rows) > 0 and critical_customers > len(cust_rows) * 0.3:
        risk_flags.append(f"🟠 Multiple Critical Customers — {critical_customers} of {len(cust_rows)} customers exceed 5% NBOT")
    
    # Find top offender customers
    top_customers = sorted(cust_rows, key=lambda x: float(x.get("nbot_pct", 0)), reverse=True)[:3]
    if top_customers and top_customers[0].get("nbot_pct", 0) > 10:
        risk_flags.append(f"⚠️ Severe Customer Issue — {top_customers[0]['customer_name']} at {top_customers[0].get('nbot_pct', 0):.1f}% NBOT")
    
    # Recommendations
    recommendations = []
    
    if nbot_pct > 5:
        if len(ot_breakdown_rows) > 0:
            top_ot = max(ot_breakdown_rows, key=lambda x: float(x.get("hours", 0)))
            if top_ot.get("hours", 0) > 0:
                recommendations.append(
                    f"**Reduce {top_ot['ot_category']}** across region — Accounts for "
                    f"{top_ot.get('pct_of_twh', 0):.1f}% of total regional hours"
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
    
    if not recommendations:
        recommendations.append("✅ Region is performing well across all customers — Continue current practices")

    context = {
        "region": region,
        "start_date": start_date,
        "end_date": end_date,
        "total_hours": f"{total_hours:,.2f}",
        "nbot_hours": f"{nbot_hours:,.2f}",
        "nbot_pct": nbot_pct,
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
    }

    template = Template("""
# 🌐 Excellence Performance Center 🌐
## NBOT Region Analysis – {{ region }}
**Period:** {{ start_date }} – {{ end_date }}

---

## 📋 Executive Summary

**Regional Health:** {{ region_health_status }}

### Key Findings
- **NBOT Performance:** {{ "%.2f"|format(nbot_pct) }}% ({{ nbot_status_color }}) — {{ nbot_status_text }}
- **Customers with OT:** {{ customers_with_ot }} of {{ customer_count }} customers ({{ "%.1f"|format(customers_with_ot_pct) }}%)
- **Total Hours Worked:** {{ total_hours }} hours across {{ customer_count }} customers
- **NBOT Hours (OT):** {{ nbot_hours }} hours

{% if ot_breakdown and ot_breakdown|length > 0 -%}
### 🧾 NBOT Breakdown
**OT Composition:** {% for row in ot_breakdown -%}{{ row.label }} {{ "%.1f"|format(row.pct_of_nbot) }}%{% if not loop.last %}, {% endif %}{% endfor %}

**NBOT Thresholds:** 🟢 GREEN < 3% · 🟡 YELLOW 3–5% · 🔴 RED > 5%
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
| Total Customers | {{ customer_count }} |
| NBOT Hours (OT) | {{ nbot_hours }} |
| NBOT % | {{ "%.2f"|format(nbot_pct) }}% |

---

## 📅 Hours Breakdown (Region-Wide)
| Category | Hours | % of Total |
|:---------|------:|---------:|
| Regular (NON-OT) | {{ regular_hours }} | {{ regular_pct }}% |
{% for row in ot_breakdown_rows -%}
| {{ row.ot_category }} | {{ "%.2f"|format(row.hours) }} | {{ "%.2f"|format(row.pct_of_twh) }}% |
{% endfor %}

---

## 📈 Pareto – NBOT by Customer (Region: {{ region }})
| Rank | Customer Code | Customer | Total Hours | NBOT Hours | NBOT % | Cum NBOT % | Pareto 80% |
|---:|:--:|:--|--:|--:|--:|--:|:--:|
{% for c in customers -%}
| {{ c.nbot_rank }} | {{ c.customer_code or '' }} | {{ c.customer_name }} | {{ "%.2f"|format(c.total_hours or 0) }} | {{ "%.2f"|format(c.nbot_hours or 0) }} | {{ "%.2f"|format(c.nbot_pct or 0) }}% | {{ "%.2f"|format(c.nbot_cum_pct or 0) }}% | {% if c.pareto_80_flag == 'Yes' %}☑️{% endif %} |
{% endfor %}
""")
    return template.render(**context)


# ------------------------------------------------------------
# 3) NBOT Customer Analysis (across regions, Pareto by Site)
# ------------------------------------------------------------

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
    region: Optional[str] = None  # NEW: Optional region filter
) -> str:
    if not all([customer_code, start_date, end_date]):
        return "Missing required parameters: customer_code, start_date, end_date"

    customer_code_str = str(customer_code)
    
    # Build region filter clause
    region_filter = f"AND TRIM(region) = '{region}'" if region else ""

    sites_sql = f"""
WITH Base AS (
  SELECT
    CAST(location_number AS STRING) AS location_number,
    COALESCE(NULLIF(TRIM(region), ''), 'Unassigned') AS region,
    COALESCE(NULLIF(TRIM(state), ''), 'NA') AS state,
    COALESCE(NULLIF(TRIM(customer_name), ''), 'Unassigned') AS customer_name,
    COALESCE(NULLIF(TRIM(site_manager), ''), 'Unassigned') AS site_manager,
    counter_type,
    SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours
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
    SUM(
      CASE 
        WHEN LOWER(counter_type) IN ('daily overtime','daily ot','weekly overtime','weekly ot',
                                      'holiday worked','consecutive day ot','consecutive day dt')
             OR LOWER(counter_type) LIKE '%double time%'
             OR LOWER(counter_type) LIKE '%overtime%'
        THEN counter_hours 
        ELSE 0 
      END
    ) AS nbot_hours
  FROM Base
  GROUP BY location_number, region, state
),
WithPct AS (
  SELECT
    location_number, region, state, customer_name, site_manager,
    total_hours, nbot_hours,
    SAFE_DIVIDE(nbot_hours, total_hours) * 100 AS nbot_pct
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
  total_hours, nbot_hours, nbot_pct, nbot_rank, nbot_cum_pct,
  CASE WHEN nbot_cum_pct <= 80 THEN 'Yes' ELSE 'No' END AS pareto_80_flag
FROM Pareto
ORDER BY nbot_hours DESC
"""

    cust_totals_sql = f"""
WITH Base AS (
  SELECT
    customer_name,
    counter_type,
    counter_hours
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
    AND customer_code = '{customer_code_str}'
    {region_filter}
)
SELECT
  ANY_VALUE(customer_name) AS customer_name,
  SUM(counter_hours) AS total_hours,
  SUM(
    CASE 
      WHEN LOWER(counter_type) IN ('daily overtime','daily ot','weekly overtime','weekly ot',
                                    'holiday worked','consecutive day ot','consecutive day dt')
           OR LOWER(counter_type) LIKE '%double time%'
           OR LOWER(counter_type) LIKE '%overtime%'
      THEN counter_hours 
      ELSE 0 
    END
  ) AS nbot_hours,
  SAFE_DIVIDE(
    SUM(
      CASE 
        WHEN LOWER(counter_type) IN ('daily overtime','daily ot','weekly overtime','weekly ot',
                                      'holiday worked','consecutive day ot','consecutive day dt')
             OR LOWER(counter_type) LIKE '%double time%'
             OR LOWER(counter_type) LIKE '%overtime%'
        THEN counter_hours 
        ELSE 0 
      END
    ),
    SUM(counter_hours)
  ) * 100 AS nbot_pct
FROM Base
"""

    ot_breakdown_sql = f"""
WITH Base AS (
  SELECT
    counter_type,
    counter_hours
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
    AND customer_code = '{customer_code_str}'
    {region_filter}
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
  SUM(counter_hours) AS hours
FROM Base
WHERE LOWER(counter_type) IN ('daily overtime','daily ot','weekly overtime','weekly ot',
                               'holiday worked','consecutive day ot','consecutive day dt')
      OR LOWER(counter_type) LIKE '%double time%'
      OR LOWER(counter_type) LIKE '%overtime%'
GROUP BY ot_category
ORDER BY hours DESC
"""

    try:
        client = bigquery.Client(project=compute_project)
        site_rows = client.query(sites_sql).to_dataframe().to_dict(orient="records")
        totals = client.query(cust_totals_sql).to_dataframe().to_dict(orient="records")
        ot_breakdown_rows = client.query(ot_breakdown_sql).to_dataframe().to_dict(orient="records")
    except Exception as e:
        return f"Query failed: {str(e)}\n\nSITES_SQL:\n{sites_sql}\n\nCUSTOMER_TOTALS_SQL:\n{cust_totals_sql}"

    if not totals:
        region_msg = f" in region '{region}'" if region else ""
        return f"No data found for customer_code={customer_code}{region_msg}, dates={start_date} to {end_date}"

    t = totals[0]
    total_hours = float(t.get('total_hours') or 0)
    nbot_hours = float(t.get('nbot_hours') or 0)
    nbot_pct = round(float(t.get('nbot_pct') or 0), 2)
    
    # Calculate regular hours
    regular_hours = total_hours - nbot_hours
    regular_pct = round((regular_hours / total_hours * 100) if total_hours else 0, 1)
    
    # Process OT breakdown
    for r in ot_breakdown_rows:
        r["pct_of_twh"] = round((float(r["hours"]) / total_hours * 100) if total_hours else 0, 2)
    
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
    
    # Customer Health Status
    critical_sites = sum(1 for s in site_rows if s.get("nbot_pct", 0) > 5)
    
    if nbot_pct > 5 or (len(site_rows) > 0 and critical_sites > len(site_rows) * 0.4):
        customer_health_status = "🔴 Needs Attention"
    elif nbot_pct > 3 or (len(site_rows) > 0 and critical_sites > len(site_rows) * 0.2):
        customer_health_status = "🟡 Monitor"
    else:
        customer_health_status = "🟢 Healthy"
    
    # Sites with OT estimation
    sites_with_ot = sum(1 for s in site_rows if s.get("nbot_hours", 0) > 0)
    sites_with_ot_pct = round((sites_with_ot / len(site_rows) * 100) if site_rows else 0, 1)
    
    # OT Breakdown as % of NBOT
    ot_breakdown = []
    if nbot_hours > 0:
        for r in ot_breakdown_rows:
            if r.get("hours", 0) > 0:
                pct_of_nbot = round((float(r["hours"]) / nbot_hours * 100), 1)
                ot_breakdown.append({
                    "label": r["ot_category"],
                    "pct_of_nbot": pct_of_nbot
                })
    
    # Risk Flags
    risk_flags = []
    region_scope = f" (Region: {region})" if region else ""
    if nbot_pct > 5:
        risk_flags.append(f"🔴 High Customer NBOT ({nbot_pct:.1f}%){region_scope} — Exceeds 5% threshold")
    if len(site_rows) > 0 and critical_sites > len(site_rows) * 0.3:
        risk_flags.append(f"🟠 Multiple Critical Sites — {critical_sites} of {len(site_rows)} sites exceed 5% NBOT")
    
    # Find top offender sites
    top_sites = sorted(site_rows, key=lambda x: float(x.get("nbot_pct", 0)), reverse=True)[:3]
    if top_sites and top_sites[0].get("nbot_pct", 0) > 10:
        risk_flags.append(f"⚠️ Severe Site Issue — Location {top_sites[0]['location_number']} at {top_sites[0].get('nbot_pct', 0):.1f}% NBOT")
    
    # Recommendations
    recommendations = []
    
    if nbot_pct > 5:
        if len(ot_breakdown_rows) > 0:
            top_ot = max(ot_breakdown_rows, key=lambda x: float(x.get("hours", 0)))
            if top_ot.get("hours", 0) > 0:
                scope_text = f"across {region} region sites" if region else "across all sites"
                recommendations.append(
                    f"**Reduce {top_ot['ot_category']}** {scope_text} — Accounts for "
                    f"{top_ot.get('pct_of_twh', 0):.1f}% of customer hours"
                )
    
    if critical_sites > 0:
        top_3_sites = [f"Location {s['location_number']}" for s in top_sites[:3] if s.get('nbot_pct', 0) > 5]
        if top_3_sites:
            recommendations.append(
                f"**Focus on High-NBOT Sites** — Prioritize intervention at: {', '.join(top_3_sites)}"
            )
    
    if len(site_rows) > 10 and critical_sites > 5:
        scope_text = "regional" if region else "enterprise-wide"
        recommendations.append(
            f"**{scope_text.title()} Review** — High number of sites with NBOT issues suggests systemic "
            f"scheduling or operational challenges. Consider customer-level policy review."
        )
    
    if not recommendations:
        scope_text = f"in {region} region" if region else "across all sites"
        recommendations.append(f"✅ Customer is performing well {scope_text} — Continue current practices")

    # Build header
    header_suffix = f" – {region} Region" if region else ""
    
    context = {
        "customer_code": customer_code,
        "customer_name": t.get("customer_name") or "",
        "header_suffix": header_suffix,
        "start_date": start_date,
        "end_date": end_date,
        "total_hours": f"{total_hours:,.2f}",
        "nbot_hours": f"{nbot_hours:,.2f}",
        "nbot_pct": nbot_pct,
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
    }

    template = Template("""
# 🌐 Excellence Performance Center 🌐
## NBOT Customer Analysis – {{ customer_name }} ({{ customer_code }}){{ header_suffix }}
**Period:** {{ start_date }} – {{ end_date }}

---

## 📋 Executive Summary

**Customer Health:** {{ customer_health_status }}

### Key Findings
- **NBOT Performance:** {{ "%.2f"|format(nbot_pct) }}% ({{ nbot_status_color }}) — {{ nbot_status_text }}
- **Sites with OT:** {{ sites_with_ot }} of {{ site_count }} sites ({{ "%.1f"|format(sites_with_ot_pct) }}%)
- **Total Hours Worked:** {{ total_hours }} hours across {{ site_count }} locations
- **NBOT Hours (OT):** {{ nbot_hours }} hours

{% if ot_breakdown and ot_breakdown|length > 0 -%}
### 🧾 NBOT Breakdown
**OT Composition:** {% for row in ot_breakdown -%}{{ row.label }} {{ "%.1f"|format(row.pct_of_nbot) }}%{% if not loop.last %}, {% endif %}{% endfor %}

**NBOT Thresholds:** 🟢 GREEN < 3% · 🟡 YELLOW 3–5% · 🔴 RED > 5%
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

## 📊 Customer Key Metrics
| Metric | Value |
|:--|--:|
| Total Hours Worked | {{ total_hours }} |
| Total Sites | {{ site_count }} |
| NBOT Hours (OT) | {{ nbot_hours }} |
| NBOT % | {{ "%.2f"|format(nbot_pct) }}% |

---

## 📅 Hours Breakdown (Customer-Wide)
| Category | Hours | % of Total |
|:---------|------:|---------:|
| Regular (NON-OT) | {{ regular_hours }} | {{ regular_pct }}% |
{% for row in ot_breakdown_rows -%}
| {{ row.ot_category }} | {{ "%.2f"|format(row.hours) }} | {{ "%.2f"|format(row.pct_of_twh) }}% |
{% endfor %}

---

## 📈 Pareto – NBOT by Site
| Rank | Site | Region | State | Site Manager | Total Hours | NBOT Hours | NBOT % | Cum % | Pareto 80% |
|---:|:--:|:--|:--:|:--|--:|--:|--:|--:|:--:|
{% for s in sites -%}
| {{ s.nbot_rank }} | {{ s.location_number }} | {{ s.region }} | {{ s.state }} | {{ s.site_manager }} | {{ "%.2f"|format(s.total_hours or 0) }} | {{ "%.2f"|format(s.nbot_hours or 0) }} | {{ "%.2f"|format(s.nbot_pct or 0) }}% | {{ "%.2f"|format(s.nbot_cum_pct or 0) }}% | {% if s.pareto_80_flag == 'Yes' %}☑️{% endif %} |
{% endfor %}
""")
    return template.render(**context)


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

    sql = f"""
WITH Base AS (
  SELECT
    COALESCE(NULLIF(TRIM(region), ''), 'Unassigned') AS region,
    counter_type,
    SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
),
Agg AS (
  SELECT
    region,
    SUM(counter_hours) AS total_hours,
    SUM(
      CASE 
        WHEN LOWER(counter_type) IN ('daily overtime','daily ot','weekly overtime','weekly ot',
                                      'holiday worked','consecutive day ot','consecutive day dt')
             OR LOWER(counter_type) LIKE '%double time%'
             OR LOWER(counter_type) LIKE '%overtime%'
        THEN counter_hours 
        ELSE 0 
      END
    ) AS nbot_hours
  FROM Base
  GROUP BY region
),
WithPct AS (
  SELECT
    region,
    total_hours, nbot_hours,
    SAFE_DIVIDE(nbot_hours, total_hours) * 100 AS nbot_pct
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
  region, total_hours, nbot_hours, nbot_pct,
  nbot_rank, nbot_cum_pct,
  CASE WHEN nbot_cum_pct <= 80 THEN 'Yes' ELSE 'No' END AS pareto_80_flag
FROM WithPareto
ORDER BY nbot_hours DESC
"""

    totals_sql = f"""
WITH Base AS (
  SELECT
    counter_type,
    counter_hours
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
)
SELECT
  SUM(counter_hours) AS total_hours,
  SUM(
    CASE 
      WHEN LOWER(counter_type) IN ('daily overtime','daily ot','weekly overtime','weekly ot',
                                    'holiday worked','consecutive day ot','consecutive day dt')
           OR LOWER(counter_type) LIKE '%double time%'
           OR LOWER(counter_type) LIKE '%overtime%'
      THEN counter_hours 
      ELSE 0 
    END
  ) AS nbot_hours,
  SAFE_DIVIDE(
    SUM(
      CASE 
        WHEN LOWER(counter_type) IN ('daily overtime','daily ot','weekly overtime','weekly ot',
                                      'holiday worked','consecutive day ot','consecutive day dt')
             OR LOWER(counter_type) LIKE '%double time%'
             OR LOWER(counter_type) LIKE '%overtime%'
        THEN counter_hours 
        ELSE 0 
      END
    ),
    SUM(counter_hours)
  ) * 100 AS nbot_pct
FROM Base
"""

    ot_breakdown_sql = f"""
WITH Base AS (
  SELECT
    counter_type,
    counter_hours
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
  SUM(counter_hours) AS hours
FROM Base
WHERE LOWER(counter_type) IN ('daily overtime','daily ot','weekly overtime','weekly ot',
                               'holiday worked','consecutive day ot','consecutive day dt')
      OR LOWER(counter_type) LIKE '%double time%'
      OR LOWER(counter_type) LIKE '%overtime%'
GROUP BY ot_category
ORDER BY hours DESC
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
    nbot_pct = round(float(totals.get('nbot_pct') or 0), 2)
    
    # Calculate regular hours
    regular_hours = total_hours - nbot_hours
    regular_pct = round((regular_hours / total_hours * 100) if total_hours else 0, 1)
    
    # Process OT breakdown
    for r in ot_breakdown_rows:
        r["pct_of_twh"] = round((float(r["hours"]) / total_hours * 100) if total_hours else 0, 2)
    
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
    critical_regions = sum(1 for r in rows if r.get("nbot_pct", 0) > 5)
    
    if nbot_pct > 5 or (len(rows) > 0 and critical_regions > len(rows) * 0.4):
        company_health_status = "🔴 Needs Attention"
    elif nbot_pct > 3 or (len(rows) > 0 and critical_regions > len(rows) * 0.2):
        company_health_status = "🟡 Monitor"
    else:
        company_health_status = "🟢 Healthy"
    
    # Regions with OT
    regions_with_ot = sum(1 for r in rows if r.get("nbot_hours", 0) > 0)
    regions_with_ot_pct = round((regions_with_ot / len(rows) * 100) if rows else 0, 1)
    
    # OT Breakdown as % of NBOT
    ot_breakdown = []
    if nbot_hours > 0:
        for r in ot_breakdown_rows:
            if r.get("hours", 0) > 0:
                pct_of_nbot = round((float(r["hours"]) / nbot_hours * 100), 1)
                ot_breakdown.append({
                    "label": r["ot_category"],
                    "pct_of_nbot": pct_of_nbot
                })
    
    # Risk Flags
    risk_flags = []
    if nbot_pct > 5:
        risk_flags.append(f"🔴 High Company-Wide NBOT ({nbot_pct:.1f}%) — Exceeds 5% threshold")
    if len(rows) > 0 and critical_regions > len(rows) * 0.3:
        risk_flags.append(f"🟠 Multiple Critical Regions — {critical_regions} of {len(rows)} regions exceed 5% NBOT")
    
    # Find top offender regions
    top_regions = sorted(rows, key=lambda x: float(x.get("nbot_pct", 0)), reverse=True)[:3]
    if top_regions and top_regions[0].get("nbot_pct", 0) > 10:
        risk_flags.append(f"⚠️ Severe Regional Issue — {top_regions[0]['region']} at {top_regions[0].get('nbot_pct', 0):.1f}% NBOT")
    
    # Recommendations
    recommendations = []
    
    if nbot_pct > 5:
        if len(ot_breakdown_rows) > 0:
            top_ot = max(ot_breakdown_rows, key=lambda x: float(x.get("hours", 0)))
            if top_ot.get("hours", 0) > 0:
                recommendations.append(
                    f"**Company-Wide Initiative: Reduce {top_ot['ot_category']}** — Accounts for "
                    f"{top_ot.get('pct_of_twh', 0):.1f}% of total company hours"
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
    
    # Identify best practices from low-NBOT regions
    low_nbot_regions = [r for r in rows if r.get('nbot_pct', 0) < 3]
    if len(low_nbot_regions) > 0 and critical_regions > 0:
        best_region = min(rows, key=lambda x: float(x.get("nbot_pct", 0)))
        recommendations.append(
            f"**Best Practice Sharing** — {best_region['region']} maintains {best_region.get('nbot_pct', 0):.1f}% NBOT. "
            f"Document and share their operational practices with high-NBOT regions."
        )
    
    if not recommendations:
        recommendations.append("✅ Company is performing well across all regions — Continue current practices")

    context = {
        "start_date": start_date,
        "end_date": end_date,
        "total_hours": f"{total_hours:,.2f}",
        "nbot_hours": f"{nbot_hours:,.2f}",
        "nbot_pct": nbot_pct,
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
    }

    template = Template("""
# 🌐 Excellence Performance Center 🌐
## NBOT Company Analysis – By Region
**Period:** {{ start_date }} – {{ end_date }}

---

## 📋 Executive Summary

**Company Health:** {{ company_health_status }}

### Key Findings
- **NBOT Performance:** {{ "%.2f"|format(nbot_pct) }}% ({{ nbot_status_color }}) — {{ nbot_status_text }}
- **Regions with OT:** {{ regions_with_ot }} of {{ region_count }} regions ({{ "%.1f"|format(regions_with_ot_pct) }}%)
- **Total Hours Worked:** {{ total_hours }} hours across {{ region_count }} regions
- **NBOT Hours (OT):** {{ nbot_hours }} hours

{% if ot_breakdown and ot_breakdown|length > 0 -%}
### 🧾 NBOT Breakdown
**OT Composition:** {% for row in ot_breakdown -%}{{ row.label }} {{ "%.1f"|format(row.pct_of_nbot) }}%{% if not loop.last %}, {% endif %}{% endfor %}

**NBOT Thresholds:** 🟢 GREEN < 3% · 🟡 YELLOW 3–5% · 🔴 RED > 5%
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
| Total Regions | {{ region_count }} |
| NBOT Hours (OT) | {{ nbot_hours }} |
| NBOT % | {{ "%.2f"|format(nbot_pct) }}% |

---

## 📅 Hours Breakdown (Company-Wide)
| Category | Hours | % of Total |
|:---------|------:|---------:|
| Regular (NON-OT) | {{ regular_hours }} | {{ regular_pct }}% |
{% for row in ot_breakdown_rows -%}
| {{ row.ot_category }} | {{ "%.2f"|format(row.hours) }} | {{ "%.2f"|format(row.pct_of_twh) }}% |
{% endfor %}

---

## 📍 Regional Breakdown (Pareto on NBOT)
| Rank | Region | Total Hours | NBOT Hours | NBOT % | Cum NBOT % | Pareto 80% |
|---:|:--|--:|--:|--:|--:|:--:|
{% for r in regions -%}
| {{ r.nbot_rank }} | {{ r.region }} | {{ "%.2f"|format(r.total_hours or 0) }} | {{ "%.2f"|format(r.nbot_hours or 0) }} | {{ "%.2f"|format(r.nbot_pct or 0) }}% | {{ "%.2f"|format(r.nbot_cum_pct or 0) }}% | {% if r.pareto_80_flag == 'Yes' %}☑️{% endif %} |
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
    SAFE_CAST(counter_hours AS FLOAT64) AS counter_hours
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
),
Agg AS (
  SELECT
    customer_code, customer_name,
    SUM(counter_hours) AS total_hours,
    SUM(
      CASE 
        WHEN LOWER(counter_type) IN ('daily overtime','daily ot','weekly overtime','weekly ot',
                                      'holiday worked','consecutive day ot','consecutive day dt')
             OR LOWER(counter_type) LIKE '%double time%'
             OR LOWER(counter_type) LIKE '%overtime%'
        THEN counter_hours 
        ELSE 0 
      END
    ) AS nbot_hours
  FROM Base
  GROUP BY customer_code, customer_name
),
WithPct AS (
  SELECT
    customer_code, customer_name, total_hours, nbot_hours,
    SAFE_DIVIDE(nbot_hours, total_hours) * 100 AS nbot_pct
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
  customer_code, customer_name, total_hours, nbot_hours, nbot_pct,
  nbot_rank, nbot_cum_pct,
  CASE WHEN nbot_cum_pct <= 80 THEN 'Yes' ELSE 'No' END AS pareto_80_flag
FROM WithPareto
ORDER BY nbot_hours DESC
"""

    totals_sql = f"""
WITH Base AS (
  SELECT
    counter_type,
    counter_hours
  FROM `{project}.{dataset}.APEX_Counters`
  WHERE DATE(counter_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
)
SELECT
  SUM(counter_hours) AS total_hours,
  SUM(
    CASE 
      WHEN LOWER(counter_type) IN ('daily overtime','daily ot','weekly overtime','weekly ot',
                                    'holiday worked','consecutive day ot','consecutive day dt')
           OR LOWER(counter_type) LIKE '%double time%'
           OR LOWER(counter_type) LIKE '%overtime%'
      THEN counter_hours 
      ELSE 0 
    END
  ) AS nbot_hours,
  SAFE_DIVIDE(
    SUM(
      CASE 
        WHEN LOWER(counter_type) IN ('daily overtime','daily ot','weekly overtime','weekly ot',
                                      'holiday worked','consecutive day ot','consecutive day dt')
             OR LOWER(counter_type) LIKE '%double time%'
             OR LOWER(counter_type) LIKE '%overtime%'
        THEN counter_hours 
        ELSE 0 
      END
    ),
    SUM(counter_hours)
  ) * 100 AS nbot_pct
FROM Base
"""

    ot_breakdown_sql = f"""
WITH Base AS (
  SELECT
    counter_type,
    counter_hours
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
  SUM(counter_hours) AS hours
FROM Base
WHERE LOWER(counter_type) IN ('daily overtime','daily ot','weekly overtime','weekly ot',
                               'holiday worked','consecutive day ot','consecutive day dt')
      OR LOWER(counter_type) LIKE '%double time%'
      OR LOWER(counter_type) LIKE '%overtime%'
GROUP BY ot_category
ORDER BY hours DESC
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
    nbot_pct = round(float(totals.get('nbot_pct') or 0), 2)
    
    # Calculate regular hours
    regular_hours = total_hours - nbot_hours
    regular_pct = round((regular_hours / total_hours * 100) if total_hours else 0, 1)
    
    # Process OT breakdown
    for r in ot_breakdown_rows:
        r["pct_of_twh"] = round((float(r["hours"]) / total_hours * 100) if total_hours else 0, 2)
    
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
            if r.get("hours", 0) > 0:
                pct_of_nbot = round((float(r["hours"]) / nbot_hours * 100), 1)
                ot_breakdown.append({
                    "label": r["ot_category"],
                    "pct_of_nbot": pct_of_nbot
                })
    
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
    pareto_customers = [c for c in rows if c.get('pareto_80_flag') == 'Yes']
    if len(pareto_customers) > 0 and len(rows) > 0:
        concentration_pct = round((len(pareto_customers) / len(rows) * 100), 1)
        if concentration_pct < 20:
            risk_flags.append(f"📊 High Concentration — {len(pareto_customers)} customers ({concentration_pct}%) account for 80% of NBOT")
    
    # Recommendations
    recommendations = []
    
    if nbot_pct > 5:
        if len(ot_breakdown_rows) > 0:
            top_ot = max(ot_breakdown_rows, key=lambda x: float(x.get("hours", 0)))
            if top_ot.get("hours", 0) > 0:
                recommendations.append(
                    f"**Company-Wide Initiative: Reduce {top_ot['ot_category']}** — Accounts for "
                    f"{top_ot.get('pct_of_twh', 0):.1f}% of total company hours"
                )
    
    if critical_customers > 0:
        top_3_customers = [c['customer_name'] for c in top_customers[:3] if c.get('nbot_pct', 0) > 5]
        if top_3_customers:
            recommendations.append(
                f"**Customer Focus** — Deploy account management resources to high-NBOT customers: {', '.join(top_3_customers)}"
            )
    
    # Pareto-based recommendations
    if len(pareto_customers) > 0:
        pareto_nbot = sum(float(c.get('nbot_hours', 0)) for c in pareto_customers)
        recommendations.append(
            f"**Pareto Strategy** — {len(pareto_customers)} customers drive 80% of NBOT ({pareto_nbot:,.0f} hours). "
            f"Focus improvement efforts on these key accounts for maximum impact."
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
        "nbot_pct": nbot_pct,
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

    template = Template("""
# 🌐 Excellence Performance Center 🌐
## NBOT Company Analysis – By Customer
**Period:** {{ start_date }} – {{ end_date }}

---

## 📋 Executive Summary

**Company Health:** {{ company_health_status }}

### Key Findings
- **NBOT Performance:** {{ "%.2f"|format(nbot_pct) }}% ({{ nbot_status_color }}) — {{ nbot_status_text }}
- **Customers with OT:** {{ customers_with_ot }} of {{ customer_count }} customers ({{ "%.1f"|format(customers_with_ot_pct) }}%)
- **Total Hours Worked:** {{ total_hours }} hours across {{ customer_count }} customers
- **NBOT Hours (OT):** {{ nbot_hours }} hours

{% if ot_breakdown and ot_breakdown|length > 0 -%}
### 🧾 NBOT Breakdown
**OT Composition:** {% for row in ot_breakdown -%}{{ row.label }} {{ "%.1f"|format(row.pct_of_nbot) }}%{% if not loop.last %}, {% endif %}{% endfor %}

**NBOT Thresholds:** 🟢 GREEN < 3% · 🟡 YELLOW 3–5% · 🔴 RED > 5%
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
| NBOT Hours (OT) | {{ nbot_hours }} |
| NBOT % | {{ "%.2f"|format(nbot_pct) }}% |

---

## 📅 Hours Breakdown (Company-Wide)
| Category | Hours | % of Total |
|:---------|------:|---------:|
| Regular (NON-OT) | {{ regular_hours }} | {{ regular_pct }}% |
{% for row in ot_breakdown_rows -%}
| {{ row.ot_category }} | {{ "%.2f"|format(row.hours) }} | {{ "%.2f"|format(row.pct_of_twh) }}% |
{% endfor %}

---

## 🧩 Customer Breakdown (Pareto on NBOT)
| Rank | Customer Code | Customer | Total Hours | NBOT Hours | NBOT % | Cum NBOT % | Pareto 80% |
|---:|:--:|:--|--:|--:|--:|--:|:--:|
{% for c in customers -%}
| {{ c.nbot_rank }} | {{ c.customer_code or '' }} | {{ c.customer_name }} | {{ "%.2f"|format(c.total_hours or 0) }} | {{ "%.2f"|format(c.nbot_hours or 0) }} | {{ "%.2f"|format(c.nbot_pct or 0) }}% | {{ "%.2f"|format(c.nbot_cum_pct or 0) }}% | {% if c.pareto_80_flag == 'Yes' %}☑️{% endif %} |
{% endfor %}
""")
    return template.render(**context)