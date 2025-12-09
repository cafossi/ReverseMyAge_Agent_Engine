"""Optimization Card Report - Detailed site optimization card with state-specific OT rules."""

from jinja2 import Template
from collections import defaultdict, OrderedDict
from datetime import datetime, date
from typing import Dict, List, Union
from ..common import (
    BQ_DATA_PROJECT_ID,
    BQ_DATASET_ID,
    execute_query,
    add_status_icons,
    get_nbot_status,
    get_fte_hours,
    has_daily_ot_rules,
    has_double_time_rules,
    categorize_alerts,
)


def generate_optimization_card(
    customer_code: int,
    location_id: Union[int, str],
    state: str,
    start_date: str,
    end_date: str
) -> str:
    """
    Schedule Health & Optimization Card (Markdown) with state-specific OT logic.

    State-specific rules:
      • CA, AK, NV, CO: Daily OT rules apply (>8 hrs/day)
      • CA only: Double Time rules apply (>12 hrs/day or >8 on 7th day)
      • All states: Weekly OT applies (>40 hrs/week)
      
    For California, implements full compliance:
      • Daily OT (9–12 hrs/day @ 1.5×)
      • Double Time (>12 hrs/day @ 2.0×)
      • 7th consecutive day: first 8 hrs @ 1.5×; >8 hrs @ 2.0×
      • Weekly OT (>40 hrs/week @ 1.5×) applied to ALL hours over 40,
        but NOT double-counted with daily OT or DT
    
    Args:
        customer_code: Customer code (integer)
        location_id: Location ID (can be integer or string)
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    
    Returns:
        Markdown formatted report string
    """
    
    # ✅ FIX: Convert location_id to string and extract numeric value if present
    location_id_str = str(location_id).strip()
    
    # Extract numeric value (e.g., "Site 2501" -> "2501", "2501" -> "2501")
    numeric_candidate = "".join(ch for ch in location_id_str if ch.isdigit())
    
    # Use numeric value if available, otherwise use original string
    filter_value = numeric_candidate if numeric_candidate else location_id_str
    
    # CONCAT forces string type - works whether location_id column is INT64 or STRING
    loc_id_filter = f"CONCAT('', location_id) = '{filter_value}'"
    
    # ✅ FIX: Apply same CONCAT fix to customer_code
    customer_code_filter = f"CONCAT('', customer_code) = '{customer_code}'"
    
    # Weekly snapshot (base) - using composite key (location_id + state)
    sql = f"""
WITH EmployeesAtSite AS (
  SELECT DISTINCT employee_id
  FROM `{BQ_DATA_PROJECT_ID}.{BQ_DATASET_ID}.APEX_NWS`
  WHERE {customer_code_filter}
    AND {loc_id_filter}
    AND state = '{state}'
    AND scheduled_date BETWEEN '{start_date}' AND '{end_date}'
),
EmployeeWeeklyData AS (
  SELECT
    employee_id,
    ANY_VALUE(employee_name) AS employee_name,
    -- ✅ FIX: Use conditional aggregation to get location_name from the specific location
    MAX(IF({loc_id_filter}, location_name, NULL)) AS location_name,
    ANY_VALUE(employee_status) AS employee_status,
    ANY_VALUE(employee_date_started) AS employee_date_started,
    -- ✅ FIX: Use conditional aggregation for site_manager from the specific location
    MAX(IF({loc_id_filter}, site_manager, NULL)) AS site_manager,
    ANY_VALUE(customer_name) AS customer_name,
    -- ✅ FIX: Use conditional aggregation for state from the specific location
    MAX(IF({loc_id_filter}, state, NULL)) AS state,
    -- ✅ FIX: Use conditional aggregation for region from the specific location
    MAX(IF({loc_id_filter}, region, NULL)) AS region,
    SUM(IF({loc_id_filter}, scheduled_hours, 0)) AS hours_this_site,
    SUM(scheduled_hours) AS hours_all_sites,
    DATE_DIFF(CURRENT_DATE(), ANY_VALUE(employee_date_started), DAY) AS tenure_days,
    CASE 
      WHEN DATE_DIFF(CURRENT_DATE(), ANY_VALUE(employee_date_started), DAY) <= 90 THEN 'Critical Risk'
      WHEN DATE_DIFF(CURRENT_DATE(), ANY_VALUE(employee_date_started), DAY) BETWEEN 91 AND 179 THEN 'High Risk'
      WHEN DATE_DIFF(CURRENT_DATE(), ANY_VALUE(employee_date_started), DAY) BETWEEN 180 AND 365 THEN 'Medium Risk'
      ELSE 'Low Risk'
    END AS tenure_status,
    CASE 
      WHEN SUM(scheduled_hours) >= 36 AND SUM(scheduled_hours) <= 40 THEN 'Optimal'
      WHEN SUM(scheduled_hours) BETWEEN 25 AND 35 THEN 'Sub-Optimal'
      ELSE 'Critical'
    END AS usage_status,
    CASE 
      WHEN MAX(IF(course_name = 'ONB101-ALL: Metro One LPSG - General Onboarding (All Employees)',
                  course_completion_date, NULL)) IS NOT NULL THEN 'Completed'
      ELSE 'Not Completed'
    END AS training_status
  FROM `{BQ_DATA_PROJECT_ID}.{BQ_DATASET_ID}.APEX_NWS`
  WHERE scheduled_date BETWEEN '{start_date}' AND '{end_date}'
    AND employee_id IN (SELECT employee_id FROM EmployeesAtSite)
    AND {loc_id_filter}
    AND state = '{state}'
  GROUP BY employee_id
)
SELECT * FROM EmployeeWeeklyData
ORDER BY tenure_days ASC
"""
    
    try:
        results = execute_query(sql)
    except Exception as e:
        return f"Query failed: {str(e)}\n\nSQL:\n{sql}"

    if not results:
        return (
            f"No data found for customer_code={customer_code}, "
            f"location_id={location_id}, dates={start_date} to {end_date}"
        )

    # STATE-SPECIFIC OT RULES
    state = results[0]['state']
    region = results[0]['region']
    location_name = results[0].get('location_name', 'N/A')
    
    has_daily_ot = has_daily_ot_rules(state)
    has_double_time = has_double_time_rules(state)
    is_california = state == "CA"

    # Daily hours at the site - WITH MIDNIGHT SPLITTING (for CA Daily OT)
    daily_sql = f"""
WITH ShiftSegments AS (
  SELECT
    employee_id,
    employee_name,
    scheduled_date,
    start,
    `end`,
    scheduled_hours,
    
    -- Convert "06:00a" / "02:00p" format to TIME (with safe parsing)
    SAFE.PARSE_TIME('%I:%M%p', REPLACE(REPLACE(UPPER(start), 'A', 'AM'), 'P', 'PM')) AS start_time,
    SAFE.PARSE_TIME('%I:%M%p', REPLACE(REPLACE(UPPER(`end`), 'A', 'AM'), 'P', 'PM')) AS end_time,
    
    -- Check if shift crosses midnight (only if both times parsed successfully)
    CASE 
      WHEN SAFE.PARSE_TIME('%I:%M%p', REPLACE(REPLACE(UPPER(start), 'A', 'AM'), 'P', 'PM')) IS NOT NULL
        AND SAFE.PARSE_TIME('%I:%M%p', REPLACE(REPLACE(UPPER(`end`), 'A', 'AM'), 'P', 'PM')) IS NOT NULL
        AND SAFE.PARSE_TIME('%I:%M%p', REPLACE(REPLACE(UPPER(start), 'A', 'AM'), 'P', 'PM')) >= 
            SAFE.PARSE_TIME('%I:%M%p', REPLACE(REPLACE(UPPER(`end`), 'A', 'AM'), 'P', 'PM'))
      THEN TRUE 
      ELSE FALSE 
    END AS crosses_midnight,
    
    -- Calculate hours on next date
    CASE
      WHEN SAFE.PARSE_TIME('%I:%M%p', REPLACE(REPLACE(UPPER(start), 'A', 'AM'), 'P', 'PM')) IS NOT NULL
        AND SAFE.PARSE_TIME('%I:%M%p', REPLACE(REPLACE(UPPER(`end`), 'A', 'AM'), 'P', 'PM')) IS NOT NULL
        AND SAFE.PARSE_TIME('%I:%M%p', REPLACE(REPLACE(UPPER(start), 'A', 'AM'), 'P', 'PM')) >= 
            SAFE.PARSE_TIME('%I:%M%p', REPLACE(REPLACE(UPPER(`end`), 'A', 'AM'), 'P', 'PM')) THEN
        EXTRACT(HOUR FROM SAFE.PARSE_TIME('%I:%M%p', REPLACE(REPLACE(UPPER(`end`), 'A', 'AM'), 'P', 'PM'))) +
        EXTRACT(MINUTE FROM SAFE.PARSE_TIME('%I:%M%p', REPLACE(REPLACE(UPPER(`end`), 'A', 'AM'), 'P', 'PM'))) / 60.0
      ELSE 
        0.0
    END AS hours_on_next_date,
    
    -- Calculate hours on scheduled_date
    CASE
      WHEN SAFE.PARSE_TIME('%I:%M%p', REPLACE(REPLACE(UPPER(start), 'A', 'AM'), 'P', 'PM')) IS NOT NULL
        AND SAFE.PARSE_TIME('%I:%M%p', REPLACE(REPLACE(UPPER(`end`), 'A', 'AM'), 'P', 'PM')) IS NOT NULL
        AND SAFE.PARSE_TIME('%I:%M%p', REPLACE(REPLACE(UPPER(start), 'A', 'AM'), 'P', 'PM')) >= 
            SAFE.PARSE_TIME('%I:%M%p', REPLACE(REPLACE(UPPER(`end`), 'A', 'AM'), 'P', 'PM')) THEN
        scheduled_hours - (
          EXTRACT(HOUR FROM SAFE.PARSE_TIME('%I:%M%p', REPLACE(REPLACE(UPPER(`end`), 'A', 'AM'), 'P', 'PM'))) +
          EXTRACT(MINUTE FROM SAFE.PARSE_TIME('%I:%M%p', REPLACE(REPLACE(UPPER(`end`), 'A', 'AM'), 'P', 'PM'))) / 60.0
        )
      ELSE 
        scheduled_hours
    END AS hours_on_scheduled_date
    
  FROM `{BQ_DATA_PROJECT_ID}.{BQ_DATASET_ID}.APEX_NWS`
  WHERE {customer_code_filter}
    AND {loc_id_filter}
    AND state = '{state}'
    AND scheduled_date BETWEEN '{start_date}' AND '{end_date}'
),
ExpandedShifts AS (
  SELECT
    employee_id,
    employee_name,
    scheduled_date AS workday_date,
    hours_on_scheduled_date AS daily_hours
  FROM ShiftSegments
  WHERE hours_on_scheduled_date > 0
  
  UNION ALL
  
  SELECT
    employee_id,
    employee_name,
    DATE_ADD(scheduled_date, INTERVAL 1 DAY) AS workday_date,
    hours_on_next_date AS daily_hours
  FROM ShiftSegments
  WHERE crosses_midnight AND hours_on_next_date > 0
)
SELECT
  employee_id,
  MAX(employee_name) AS employee_name,
  workday_date AS scheduled_date,
  SUM(daily_hours) AS daily_hours
FROM ExpandedShifts
GROUP BY employee_id, workday_date
ORDER BY employee_id, workday_date
"""
    
    try:
        daily_rows = execute_query(daily_sql)
        daily_error = ""
        
        # FALLBACK: If midnight-splitting returns no data, use simple aggregation
        if not daily_rows:
            daily_error = "\n\n> Note: Midnight-splitting returned no data, using simple aggregation\n"
            fallback_sql = f"""
SELECT
  employee_id,
  ANY_VALUE(employee_name) AS employee_name,
  scheduled_date,
  SUM(scheduled_hours) AS daily_hours
FROM `{BQ_DATA_PROJECT_ID}.{BQ_DATASET_ID}.APEX_NWS`
WHERE {customer_code_filter}
  AND {loc_id_filter}
  AND state = '{state}'
  AND scheduled_date BETWEEN '{start_date}' AND '{end_date}'
GROUP BY employee_id, scheduled_date
ORDER BY employee_id, scheduled_date
"""
            daily_rows = execute_query(fallback_sql)
            
    except Exception as e:
        daily_rows = []
        daily_error = f"\n\n> Daily detail query failed: {e}\n\nSQL:\n{daily_sql}"

    # Icons & basic fields
    for emp in results:
        add_status_icons(emp)
        emp['hours_this_site'] = float(emp.get('hours_this_site') or 0.0)
        emp['hours_all_sites'] = float(emp.get('hours_all_sites') or 0.0)

    # State-specific OT allocation
    by_emp = defaultdict(lambda: OrderedDict())
    names = {}
    for r in daily_rows:
        eid = r['employee_id']
        names[eid] = r.get('employee_name') or str(eid)
        by_emp[eid][str(r['scheduled_date'])] = float(r.get('daily_hours') or 0.0)

    def _d(s: str) -> date:
        return datetime.strptime(s, "%Y-%m-%d").date()

    site_daily_ot = 0.0
    site_doubletime = 0.0
    site_weekly_ot = 0.0
    employees_with_ot_details = []

    for emp in results:
        eid = emp['employee_id']
        if eid not in by_emp:
            emp['daily_ot'] = emp['double_time'] = emp['weekly_ot'] = emp['total_ot_exposure'] = 0.0
            emp['total_daily_ot'] = emp['total_double_time'] = 0.0
            continue

        days = sorted(by_emp[eid].keys(), key=_d)

        # Step 1: allocate D/DT per day (only for states with daily OT rules)
        per_day = []
        for idx, dstr in enumerate(days):
            hours = by_emp[eid][dstr]
            
            daily_ot = 0.0
            double_t = 0.0
            regular = hours
            
            if has_daily_ot:
                seventh = (len(days) >= 7 and idx == 6 and all(by_emp[eid][days[k]] > 0.0 for k in range(0, 6)))

                if seventh and has_double_time:
                    # CA 7th day rule
                    daily_ot = min(hours, 8.0)
                    double_t = max(0.0, hours - 8.0)
                    regular = max(0.0, hours - daily_ot - double_t)
                else:
                    # Standard daily OT rules
                    if has_double_time:
                        double_t = max(0.0, hours - 12.0)
                    if hours > 8.0:
                        daily_ot = min(hours - 8.0, 4.0) if has_double_time else (hours - 8.0)
                    regular = max(0.0, hours - daily_ot - double_t)

            per_day.append({
                "date": dstr,
                "total": round(hours, 2),
                "regular": round(regular, 2),
                "daily_ot": round(daily_ot, 2),
                "double_time": round(double_t, 2),
                "weekly_ot": 0.0,
            })

        total_week_hours = round(sum(r["total"] for r in per_day), 2)
        hours_over_40 = max(0.0, total_week_hours - 40.0)

        # Step 2: allocate WEEKLY OT by converting REGULAR hours from last day backward
        remaining = hours_over_40
        for r in reversed(per_day):
            if remaining <= 0.0:
                break
            take = min(remaining, r["regular"])
            r["regular"] = round(r["regular"] - take, 2)
            r["weekly_ot"] = round(r["weekly_ot"] + take, 2)
            remaining -= take

        # Totals per employee (non-overlapping)
        emp_daily_ot = round(sum(r["daily_ot"] for r in per_day), 2)
        emp_doubletime = round(sum(r["double_time"] for r in per_day), 2)
        emp_weekly_ot = round(sum(r["weekly_ot"] for r in per_day), 2)

        site_daily_ot += emp_daily_ot
        site_doubletime += emp_doubletime
        site_weekly_ot += emp_weekly_ot

        # Store with both field name conventions
        emp['daily_ot'] = emp_daily_ot
        emp['double_time'] = emp_doubletime
        emp['weekly_ot'] = emp_weekly_ot
        emp['total_ot_exposure'] = round(emp_daily_ot + emp_doubletime + emp_weekly_ot, 2)
        
        # ✅ FIX: Also store with field names that categorize_alerts() expects
        emp['total_daily_ot'] = emp_daily_ot
        emp['total_double_time'] = emp_doubletime

        # Include in detailed schedules if any OT exists
        if any((r["daily_ot"] > 0 or r["double_time"] > 0 or r["weekly_ot"] > 0) for r in per_day):
            employees_with_ot_details.append({
                "employee_id": eid,
                "employee_name": names.get(eid, emp.get("employee_name") or str(eid)),
                "weekly_hours": total_week_hours,
                "daily_breakdown": per_day,
                "totals": {
                    "regular": round(sum(r["regular"] for r in per_day), 2),
                    "daily_ot": emp_daily_ot,
                    "double_time": emp_doubletime,
                    "weekly_ot": emp_weekly_ot,
                    "total_hours": total_week_hours,
                },
            })

    # Site-level metrics
    total_hours = sum(emp['hours_this_site'] for emp in results)
    avg_hours_this_site = round(total_hours / len(results), 1) if results else 0.0
    total_hours_all_sites = sum(emp['hours_all_sites'] for emp in results)
    avg_hours_all_sites = round(total_hours_all_sites / len(results), 1) if results else 0.0

    fte_hours = get_fte_hours(state)
    fte_needed = int((total_hours + (fte_hours - 1e-4)) // fte_hours) if total_hours else 0
    capacity_gap = fte_needed - len(results)
    capacity_status = "Balanced" if abs(capacity_gap) <= 0.5 else ("Understaffed" if capacity_gap > 0 else "Overstaffed")

    weekly_ot_hours = round(site_weekly_ot, 2)
    daily_ot_hours = round(site_daily_ot, 2) if has_daily_ot else 0.0
    double_time_hours = round(site_doubletime, 2) if has_double_time else 0.0
    total_ot_nonoverlap = round(weekly_ot_hours + daily_ot_hours + double_time_hours, 2)
    total_ot_pct = round((total_ot_nonoverlap / total_hours * 100), 1) if total_hours > 0 else 0.0

    alerts = categorize_alerts(results, has_daily_ot, has_double_time)

    over_40_pct = round((len(alerts['over_40']) / len(results) * 100), 1) if results else 0.0
    under_32_pct = round((len(alerts['under_32']) / len(results) * 100), 1) if results else 0.0
    training_complete_pct = round(((len(results) - len(alerts['training_incomplete'])) / len(results) * 100), 0) if results else 100.0
    daily_ot_emp_pct = round((len(alerts['daily_ot']) / len(results) * 100), 1) if results and has_daily_ot else 0.0
    double_time_emp_pct = round((len(alerts['double_time']) / len(results) * 100), 1) if results and has_double_time else 0.0

    nbot_status, nbot_text = get_nbot_status(total_ot_pct)

    # Recommendations
    recs = []
    if alerts['training_incomplete']:
        emp_ids = ", ".join([f"{e['employee_id']} ({e.get('employee_name', 'N/A')})" for e in alerts['training_incomplete']])
        recs.append((
            f"**Complete Training for {len(alerts['training_incomplete'])} Employee"
            f"{'s' if len(alerts['training_incomplete']) != 1 else ''}** — Cannot be scheduled without General Onboarding completion",
            f"*Affected Employees ({len(alerts['training_incomplete'])}): {emp_ids}*"
        ))

    if has_double_time and double_time_hours > 0:
        emp_ids = ", ".join([f"{e['employee_id']} ({e.get('employee_name', 'N/A')})" for e in alerts['double_time']])
        recs.append((
            f"**Eliminate Double Time Risk** — {double_time_hours:.1f} hours scheduled >12 hrs/day (or >8 on 7th day). "
            f"Affects {len(alerts['double_time'])} employee{'s' if len(alerts['double_time']) != 1 else ''}",
            f"*Affected Employees ({len(alerts['double_time'])}): {emp_ids}*"
        ))

    if has_daily_ot and daily_ot_hours > 5:
        emp_ids = ", ".join([f"{e['employee_id']} ({e.get('employee_name', 'N/A')})" for e in alerts['daily_ot']])
        recs.append((
            f"**Reduce Daily OT** — {daily_ot_hours:.1f} hours scheduled >8 hrs/day. "
            f"Redistribute to keep shifts at 8 hours or less",
            f"*Affected Employees ({len(alerts['daily_ot'])}): {emp_ids}*"
        ))

    if weekly_ot_hours > 0:
        emp_ids = ", ".join([f"{e['employee_id']} ({e.get('employee_name', 'N/A')})" for e in alerts['over_40']])
        recs.append((
            f"**Reduce Weekly OT** — Redistribute {weekly_ot_hours:.0f} hours to bring OT < 3%",
            f"*Affected Employees ({len(alerts['over_40'])}): {emp_ids}*"
        ))

    if alerts['under_32']:
        emp_ids = ", ".join([f"{e['employee_id']} ({e.get('employee_name', 'N/A')})" for e in alerts['under_32']])
        recs.append((
            f"**Increase Utilization** — {len(alerts['under_32'])} employee"
            f"{'s' if len(alerts['under_32']) != 1 else ''} < 32 hrs. Review availability / cross-train",
            f"*Affected Employees ({len(alerts['under_32'])}): {emp_ids}*"
        ))

    if fte_needed > len(results):
        gap = fte_needed - len(results)
        recs.append((f"**Address Staffing Gap** — Add {gap} FTE to meet demand without OT", None))

    if not recs:
        recs.append(("✅ **Site scheduling is well-optimized** — Continue current practices", None))

    # OT rules text
    ot_rules_text = "State-specific"
    if has_daily_ot and has_double_time:
        ot_rules_text = "CA-compliant (Daily OT + Double Time + Weekly OT)"
    elif has_daily_ot:
        ot_rules_text = f"{state}-compliant (Daily OT + Weekly OT)"
    else:
        ot_rules_text = "Weekly OT only"
    
    # Build markdown report
    markdown = f"""
# 🌐 Excellence Performance Center 🌐
## NBOT & Schedule Optimization Card
**{results[0]['customer_name']} - Location {location_id} ({location_name})** | **Region:** {region} | **State:** {state} | **Site Manager:** {results[0]['site_manager']} | **Week:** {start_date} – {end_date}

**OT Rules Applied:** {ot_rules_text}

---

## 📌 REQUIRED ACTIONS (Please see Employee Details Below)

"""
    
    for rec_text, rec_detail in recs:
        markdown += f"### 📌 {rec_text}\n"
        if rec_detail:
            markdown += f"{rec_detail}\n"
        markdown += "\n"

    markdown += f"""---

| Key Metric | Value | Status |
|:-------|:------|:-------|
| **Total Scheduled Hours** | {int(total_hours)} hours | Weekly capacity |
| **Employees Scheduled** | {len(results)} employees | Active headcount |
| **Average Hours per Employee (This Site)** | {avg_hours_this_site} hrs | Per employee at location |
| **Average Hours per Employee (All Sites)** | {avg_hours_all_sites} hrs | Total across all locations |
| **Total OT (non-overlap)** | **{total_ot_nonoverlap:.2f} hours ({total_ot_pct:.1f}%)** | {nbot_status} ({nbot_text}) |
| ├─ **Weekly OT (from regular hours >40)** | {weekly_ot_hours:.2f} hours | >40 hrs/week |
"""
    
    if has_daily_ot:
        markdown += f"""| ├─ **Daily OT ({state})** | {daily_ot_hours:.2f} hours | >8 hrs/day |
"""
    if has_double_time:
        markdown += f"""| └─ **Double Time ({state})** | {double_time_hours:.2f} hours | >12 hrs/day (or >8 on 7th day) |
"""
    if has_daily_ot:
        markdown += f"""| **Employees with Daily OT ({state})** | {len(alerts['daily_ot'])} ({daily_ot_emp_pct:.1f}%) | {'⚠️ Alert' if alerts['daily_ot'] else '🟢 Good'} |
"""
    if has_double_time:
        markdown += f"""| **Employees with Double Time ({state})** | {len(alerts['double_time'])} ({double_time_emp_pct:.1f}%) | {'🔴 Critical' if alerts['double_time'] else '🟢 Good'} |
"""
    
    markdown += f"""| **Employees >40 Hours** | {len(alerts['over_40'])} ({over_40_pct:.1f}%) | {'⚠️ Alert' if alerts['over_40'] else '🟢 Good'} |
| **Employees <32 Hours** | {len(alerts['under_32'])} ({under_32_pct:.1f}%) | {'🟡 Review' if alerts['under_32'] else '🟢 Good'} |
| **Capacity Status** | {len(results)} Employees | FTE Needed: {fte_hours} hrs/FTE → {fte_needed} FTE |
| **Capacity Assessment** | {capacity_status} | Gap: {capacity_gap} FTE |
| **Training Compliance** | {int(training_complete_pct)}% | {'🔴 ' + str(len(alerts['training_incomplete'])) + ' need training' if alerts['training_incomplete'] else '✅ All scheduled OK'} |

---

## 👮 EMPLOYEE DETAILS

**STATUS THRESHOLDS**

➖ **Tenure Risk:** 🔴 Critical (≤90d) | 🟠 High (≤180d) | 🟡 Medium (≤365d) | 🟢 Low (>365d)

➖ **Usage**: 🟢 36–40 hrs | 🟡 25–35 hrs | 🔴 <25 or >40 hrs
"""
    
    # State-specific legend
    if has_daily_ot and has_double_time:
        markdown += """**➖ OT Breakdown Legend (CA-compliant):**
- **W** = Weekly OT (regular hours converted once total week >40 @ 1.5×)
- **D** = Daily OT (9–12 hrs/day @ 1.5×)
- **DT** = Double Time (>12 hrs/day @ 2.0×; or >8 hrs on 7th day)

"""
    elif has_daily_ot:
        markdown += f"""**➖ OT Breakdown Legend ({state}):**
- **W** = Weekly OT (regular hours converted once total week >40 @ 1.5×)
- **D** = Daily OT (>8 hrs/day @ 1.5×)

"""
    else:
        markdown += """**➖ OT Breakdown Legend:**
- **W** = Weekly OT (regular hours converted once total week >40 @ 1.5×)

"""

    markdown += "*Usage Status is based on total hours across ALL sites, not just this location*\n\n"

    # Summary table (dynamic columns based on state)
    if has_daily_ot and has_double_time:
        markdown += """| Employee ID | Name | Tenure | Status | Hours (Site/All) | OT (W/D/DT) | Total OT | Usage | Training |
|:-----------:|:-----|:------:|:-------|:----------------:|:-----------:|:--------:|:-----:|:--------:|
"""
        for emp in results:
            tenure_display = f"{emp['tenure_days']}d {emp['tenure_icon']}"
            hours_display = f"{emp['hours_this_site']:.1f} / {emp['hours_all_sites']:.1f}"
            ot_breakdown = f"W:{emp['weekly_ot']:.1f} D:{emp['daily_ot']:.1f} DT:{emp['double_time']:.1f}"
            markdown += (
                f"| {emp['employee_id']} "
                f"| {emp.get('employee_name','')} "
                f"| {tenure_display} "
                f"| {emp['employee_status']} "
                f"| {hours_display} "
                f"| {ot_breakdown} "
                f"| {emp['total_ot_exposure']:.1f} "
                f"| {emp['usage_icon']} {emp['usage_status']} "
                f"| {emp['training_icon']} |\n"
            )
    elif has_daily_ot:
        markdown += """| Employee ID | Name | Tenure | Status | Hours (Site/All) | OT (W/D) | Total OT | Usage | Training |
|:-----------:|:-----|:------:|:-------|:----------------:|:--------:|:--------:|:-----:|:--------:|
"""
        for emp in results:
            tenure_display = f"{emp['tenure_days']}d {emp['tenure_icon']}"
            hours_display = f"{emp['hours_this_site']:.1f} / {emp['hours_all_sites']:.1f}"
            ot_breakdown = f"W:{emp['weekly_ot']:.1f} D:{emp['daily_ot']:.1f}"
            markdown += (
                f"| {emp['employee_id']} "
                f"| {emp.get('employee_name','')} "
                f"| {tenure_display} "
                f"| {emp['employee_status']} "
                f"| {hours_display} "
                f"| {ot_breakdown} "
                f"| {emp['total_ot_exposure']:.1f} "
                f"| {emp['usage_icon']} {emp['usage_status']} "
                f"| {emp['training_icon']} |\n"
            )
    else:
        markdown += """| Employee ID | Name | Tenure | Status | Hours (Site/All) | OT (W) | Total OT | Usage | Training |
|:-----------:|:-----|:------:|:-------|:----------------:|:------:|:--------:|:-----:|:--------:|
"""
        for emp in results:
            tenure_display = f"{emp['tenure_days']}d {emp['tenure_icon']}"
            hours_display = f"{emp['hours_this_site']:.1f} / {emp['hours_all_sites']:.1f}"
            ot_breakdown = f"W:{emp['weekly_ot']:.1f}"
            markdown += (
                f"| {emp['employee_id']} "
                f"| {emp.get('employee_name','')} "
                f"| {tenure_display} "
                f"| {emp['employee_status']} "
                f"| {hours_display} "
                f"| {ot_breakdown} "
                f"| {emp['total_ot_exposure']:.1f} "
                f"| {emp['usage_icon']} {emp['usage_status']} "
                f"| {emp['training_icon']} |\n"
            )

    markdown += "\n\n[↩ Back to Site Matrix](#-all-sites-in-pareto-80)\n"

    # Detailed schedules
    if employees_with_ot_details:
        markdown += """

---

## 📅 Detailed Daily Schedules for Employees with Scheduled OT

"""
        if has_daily_ot and has_double_time:
            markdown += """**Per-row classification (CA-compliant, non-overlap)**  
- **Regular**: straight-time **after** Daily OT / DT allocation  
- **D (Daily OT)**: 9–12 hrs/day @ 1.5× (or first 8 on 7th day)  
- **DT (Double Time)**: >12 hrs/day @ 2.0× (or >8 on 7th day)  
- **W (Weekly OT)**: regular hours converted, from last day backward, once **weekly total >40** @ 1.5×

"""
        elif has_daily_ot:
            markdown += f"""**Per-row classification ({state}, non-overlap)**  
- **Regular**: straight-time **after** Daily OT allocation  
- **D (Daily OT)**: >8 hrs/day @ 1.5×  
- **W (Weekly OT)**: regular hours converted, from last day backward, once **weekly total >40** @ 1.5×

"""
        else:
            markdown += """**Per-row classification**  
- **Regular**: straight-time  
- **W (Weekly OT)**: regular hours converted, from last day backward, once **weekly total >40** @ 1.5×

"""
        
        for empd in employees_with_ot_details:
            markdown += f"### 👤 {empd['employee_name']} (ID: {empd['employee_id']})\n"
            markdown += f"**Total Weekly Hours (this site):** {empd['weekly_hours']}\n\n"
            
            # Dynamic table headers based on state
            if has_daily_ot and has_double_time:
                markdown += "| Date | Hours Scheduled | Regular | D | DT | W | Explanation |\n"
                markdown += "|:-----|-------------:|-------:|--:|---:|--:|:------------|\n"
                for r in empd['daily_breakdown']:
                    expl = []
                    if r["double_time"] > 0: expl.append("DT for hours >12 (or >8 on 7th day).")
                    if r["daily_ot"] > 0: expl.append("D for hours 9–12 (or first 8 on 7th day).")
                    if r["weekly_ot"] > 0: expl.append("W from regular once week >40.")
                    if not expl: expl.append("All within regular time.")
                    markdown += (
                        f"| {r['date']} "
                        f"| {r['total']:.2f} "
                        f"| {r['regular']:.2f} "
                        f"| {r['daily_ot']:.2f} "
                        f"| {r['double_time']:.2f} "
                        f"| {r['weekly_ot']:.2f} "
                        f"| {' '.join(expl)} |\n"
                    )
                t = empd["totals"]
                markdown += (
                    f"| **Totals** | **{t['total_hours']:.2f}** | **{t['regular']:.2f}** | "
                    f"**{t['daily_ot']:.2f}** | **{t['double_time']:.2f}** | **{t['weekly_ot']:.2f}** |  |\n\n"
                )
            elif has_daily_ot:
                markdown += "| Date | Hours Scheduled | Regular | D | W | Explanation |\n"
                markdown += "|:-----|-------------:|-------:|--:|--:|:------------|\n"
                for r in empd['daily_breakdown']:
                    expl = []
                    if r["daily_ot"] > 0: expl.append("D for hours >8.")
                    if r["weekly_ot"] > 0: expl.append("W from regular once week >40.")
                    if not expl: expl.append("All within regular time.")
                    markdown += (
                        f"| {r['date']} "
                        f"| {r['total']:.2f} "
                        f"| {r['regular']:.2f} "
                        f"| {r['daily_ot']:.2f} "
                        f"| {r['weekly_ot']:.2f} "
                        f"| {' '.join(expl)} |\n"
                    )
                t = empd["totals"]
                markdown += (
                    f"| **Totals** | **{t['total_hours']:.2f}** | **{t['regular']:.2f}** | "
                    f"**{t['daily_ot']:.2f}** | **{t['weekly_ot']:.2f}** |  |\n\n"
                )
            else:
                markdown += "| Date | Hours Scheduled | Regular | W | Explanation |\n"
                markdown += "|:-----|-------------:|-------:|--:|:------------|\n"
                for r in empd['daily_breakdown']:
                    expl = []
                    if r["weekly_ot"] > 0: expl.append("W from regular once week >40.")
                    if not expl: expl.append("All within regular time.")
                    markdown += (
                        f"| {r['date']} "
                        f"| {r['total']:.2f} "
                        f"| {r['regular']:.2f} "
                        f"| {r['weekly_ot']:.2f} "
                        f"| {' '.join(expl)} |\n"
                    )
                t = empd["totals"]
                markdown += (
                    f"| **Totals** | **{t['total_hours']:.2f}** | **{t['regular']:.2f}** | "
                    f"**{t['weekly_ot']:.2f}** |  |\n\n"
                )

    if daily_error:
        markdown += f"\n> Debug Note: {daily_error}\n"

    return markdown