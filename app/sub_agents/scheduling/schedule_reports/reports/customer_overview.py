"""Customer Overview Report - Customer-level overview with CA Daily/Double OT and Pareto analysis."""

from jinja2 import Template
from collections import Counter
from ..common import (
    BQ_DATA_PROJECT_ID,
    BQ_DATASET_ID,
    execute_query,
    get_nbot_status,
    get_nbot_icon,
)


def generate_customer_overview(
    customer_code: int,
    start_date: str,
    end_date: str
) -> str:
    """Generate enhanced customer-level overview report with CA Daily/Double OT and Pareto analysis."""
    
    # SQL Query with CA Daily/Double OT Calculations
    sql = f"""
WITH DailyHours AS (
  SELECT
    location_id,
    state,
    employee_id,
    scheduled_date,
    SUM(scheduled_hours) AS daily_hours
  FROM `{BQ_DATA_PROJECT_ID}.{BQ_DATASET_ID}.APEX_NWS`
  WHERE CAST(customer_code AS STRING) = '{customer_code}'
    AND scheduled_date BETWEEN '{start_date}' AND '{end_date}'
  GROUP BY location_id, state, employee_id, scheduled_date
),
DailyOTCalculations AS (
  SELECT
    location_id,
    state,
    employee_id,
    scheduled_date,
    daily_hours,
    CASE 
      WHEN daily_hours > 8 AND daily_hours <= 12 THEN daily_hours - 8
      WHEN daily_hours > 12 THEN 4
      ELSE 0
    END AS daily_ot_hours,
    CASE 
      WHEN daily_hours > 12 THEN daily_hours - 12
      ELSE 0
    END AS double_time_hours
  FROM DailyHours
),
EmployeeOTByLocation AS (
  SELECT
    location_id,
    state,
    employee_id,
    MAX(daily_hours) AS max_daily_hours,
    COUNTIF(daily_hours > 8) AS days_over_8,
    SUM(daily_ot_hours) AS total_daily_ot,
    SUM(double_time_hours) AS total_double_time
  FROM DailyOTCalculations
  GROUP BY location_id, state, employee_id
),
EmployeeWeeklyHours AS (
  SELECT
    location_id,
    state,
    employee_id,
    SUM(scheduled_hours) AS weekly_hours
  FROM `{BQ_DATA_PROJECT_ID}.{BQ_DATASET_ID}.APEX_NWS`
  WHERE CAST(customer_code AS STRING) = '{customer_code}'
    AND scheduled_date BETWEEN '{start_date}' AND '{end_date}'
  GROUP BY location_id, state, employee_id
),
LocationSummary AS (
  SELECT
    ewh.location_id,
    ewh.state,
    COUNT(DISTINCT ewh.employee_id) AS employee_count,
    SUM(ewh.weekly_hours) AS total_hours,
    SUM(CASE WHEN ewh.weekly_hours > 40 THEN ewh.weekly_hours - 40 ELSE 0 END) AS weekly_ot_hours,
    SUM(COALESCE(eot.total_daily_ot, 0)) AS daily_ot_hours,
    SUM(COALESCE(eot.total_double_time, 0)) AS double_time_hours
  FROM EmployeeWeeklyHours ewh
  LEFT JOIN EmployeeOTByLocation eot 
    ON ewh.location_id = eot.location_id 
    AND ewh.state = eot.state
    AND ewh.employee_id = eot.employee_id
  GROUP BY ewh.location_id, ewh.state
)
SELECT
  ls.location_id,
  ls.state,
  ANY_VALUE(n.site_manager) AS site_manager,
  ANY_VALUE(n.customer_name) AS customer_name,
  ls.employee_count,
  ls.total_hours,
  ls.weekly_ot_hours,

  CASE WHEN ls.state = 'CA' THEN ls.daily_ot_hours ELSE 0 END AS daily_ot_hours,
  CASE WHEN ls.state = 'CA' THEN ls.double_time_hours ELSE 0 END AS double_time_hours,

  (
    ls.weekly_ot_hours
    + CASE WHEN ls.state = 'CA' THEN ls.daily_ot_hours ELSE 0 END
    + CASE WHEN ls.state = 'CA' THEN ls.double_time_hours ELSE 0 END
  ) AS total_ot_exposure,

  ROUND(SAFE_DIVIDE(
    (
      ls.weekly_ot_hours
      + CASE WHEN ls.state = 'CA' THEN ls.daily_ot_hours ELSE 0 END
      + CASE WHEN ls.state = 'CA' THEN ls.double_time_hours ELSE 0 END
    ),
    ls.total_hours
  ) * 100, 1) AS ot_percentage,

  CASE 
    WHEN ls.state = 'CA' THEN CAST(CEILING(ls.total_hours / 32) AS INT64)
    ELSE CAST(CEILING(ls.total_hours / 36) AS INT64)
  END AS fte_needed,

  CAST(ls.employee_count AS INT64) - CASE 
    WHEN ls.state = 'CA' THEN CAST(CEILING(ls.total_hours / 32) AS INT64)
    ELSE CAST(CEILING(ls.total_hours / 36) AS INT64)
  END AS variance,

  CASE
    WHEN ROUND(SAFE_DIVIDE(
      (
        ls.weekly_ot_hours
        + CASE WHEN ls.state = 'CA' THEN ls.daily_ot_hours ELSE 0 END
        + CASE WHEN ls.state = 'CA' THEN ls.double_time_hours ELSE 0 END
      ),
      ls.total_hours
    ) * 100, 1) >= 3 THEN 'high_risk'
    WHEN ROUND(SAFE_DIVIDE(
      (
        ls.weekly_ot_hours
        + CASE WHEN ls.state = 'CA' THEN ls.daily_ot_hours ELSE 0 END
        + CASE WHEN ls.state = 'CA' THEN ls.double_time_hours ELSE 0 END
      ),
      ls.total_hours
    ) * 100, 1) >= 1 THEN 'medium_risk'
    ELSE 'low_risk'
  END AS risk_category
FROM LocationSummary ls
LEFT JOIN `{BQ_DATA_PROJECT_ID}.{BQ_DATASET_ID}.APEX_NWS` n
  ON ls.location_id = n.location_id 
  AND ls.state = n.state
  AND CAST(n.customer_code AS STRING) = '{customer_code}'
  AND n.scheduled_date BETWEEN '{start_date}' AND '{end_date}'
GROUP BY
  ls.location_id, ls.state, ls.employee_count, ls.total_hours,
  ls.weekly_ot_hours, ls.daily_ot_hours, ls.double_time_hours
ORDER BY ot_percentage DESC
"""
    
    # Execute query
    try:
        results = execute_query(sql)
    except Exception as e:
        return str(e)
    
    if not results:
        return f"No data found for customer_code={customer_code}, dates={start_date} to {end_date}"
    
    # Sanity guard: non-CA rows must not carry Daily/DT into totals
    for r in results:
        if r.get("state") != "CA":
            if abs(float(r.get("total_ot_exposure", 0) or 0) - float(r.get("weekly_ot_hours", 0) or 0)) > 1e-6:
                return (
                    "Inconsistent OT aggregation detected for non-CA location "
                    f"{r.get('location_id')}: total_ot_exposure={r.get('total_ot_exposure')} "
                    f"vs weekly_ot_hours={r.get('weekly_ot_hours')}. Please re-run."
                )
  
    # PARETO CALCULATION (by Total OT Exposure)
    results_sorted = sorted(results, key=lambda x: float(x.get('total_ot_exposure', 0) or 0), reverse=True)
    
    total_ot_all = sum(float(r.get('total_ot_exposure', 0) or 0) for r in results_sorted)
    cumulative_ot = 0
    
    for idx, loc in enumerate(results_sorted, 1):
        loc['ot_rank'] = idx
        ot_exposure = float(loc.get('total_ot_exposure', 0) or 0)
        cumulative_ot += ot_exposure
        loc['ot_cum_pct'] = round((cumulative_ot / total_ot_all * 100), 1) if total_ot_all > 0 else 0
        loc['pareto_80_flag'] = 'Yes' if loc['ot_cum_pct'] <= 80 else 'No'
    
    results = results_sorted
    
    # SECOND QUERY: Employee-level details
    employee_sql = f"""
WITH EmployeeWeekly AS (
  SELECT
    employee_id,
    ANY_VALUE(employee_name) AS employee_name,
    ANY_VALUE(employee_status) AS employee_status,
    ANY_VALUE(employee_date_started) AS employee_date_started,
    ANY_VALUE(location_id) AS primary_location,
    ANY_VALUE(state) AS state,
    SUM(scheduled_hours) AS weekly_hours,
    DATE_DIFF(CURRENT_DATE(), ANY_VALUE(employee_date_started), DAY) AS tenure_days,
    MAX(CASE 
      WHEN course_name = 'ONB101-ALL: Metro One LPSG - General Onboarding (All Employees)' 
           AND course_completion_date IS NOT NULL THEN 1
      ELSE 0
    END) AS has_training
  FROM `{BQ_DATA_PROJECT_ID}.{BQ_DATASET_ID}.APEX_NWS`
  WHERE CAST(customer_code AS STRING) = '{customer_code}'
    AND scheduled_date BETWEEN '{start_date}' AND '{end_date}'
  GROUP BY employee_id
)
SELECT
  employee_id,
  employee_name,
  employee_status,
  primary_location,
  state,
  weekly_hours,
  tenure_days,
  CASE WHEN has_training = 1 THEN 'Completed' ELSE 'Not Completed' END AS training_status,
  CASE 
    WHEN tenure_days <= 90 THEN 'Critical'
    WHEN tenure_days <= 179 THEN 'High'
    WHEN tenure_days <= 365 THEN 'Medium'
    ELSE 'Low'
  END AS tenure_risk,
  CASE
    WHEN weekly_hours >= 36 AND weekly_hours <= 40 THEN 'Optimal'
    WHEN weekly_hours BETWEEN 25 AND 35 THEN 'Sub-Optimal'
    ELSE 'Critical'
  END AS utilization_status
FROM EmployeeWeekly
ORDER BY tenure_days ASC
"""
    
    try:
        employee_results = execute_query(employee_sql)
    except Exception:
        employee_results = []
    
    # Calculate aggregate metrics
    total_locations = len(results)
    total_hours = sum(r['total_hours'] for r in results)
    
    total_weekly_ot = sum(r['weekly_ot_hours'] for r in results)
    total_daily_ot = sum(r['daily_ot_hours'] for r in results)
    total_double_time = sum(r['double_time_hours'] for r in results)
    total_ot_exposure = total_weekly_ot + total_daily_ot + total_double_time
    
    overall_ot_pct = round((total_ot_exposure / total_hours * 100) if total_hours > 0 else 0, 1)
    total_fte_needed = sum(r['fte_needed'] for r in results)
    
    total_employees = len(employee_results) if employee_results else 0
    avg_hours = round(total_hours / total_employees, 1) if total_employees > 0 else 0
    
    has_california = any(r['state'] == 'CA' for r in results)
    
    # Add active status breakdown
    if employee_results:
        status_counts = Counter([e['employee_status'] for e in employee_results if e.get('employee_status')])
        
        active_count = status_counts.get('Active', 0)
        active_bench_count = status_counts.get('Active - Bench', 0)
        inactive_bench_count = status_counts.get('Inactive - Bench', 0)
        other_statuses = {k: v for k, v in status_counts.items() if k not in ['Active', 'Active - Bench', 'Inactive - Bench']}
    else:
        active_count = active_bench_count = inactive_bench_count = 0
        other_statuses = {}
    
    overall_nbot, nbot_status_text = get_nbot_status(overall_ot_pct)
    
    # Categorize locations by risk
    high_risk = [r for r in results if r['risk_category'] == 'high_risk']
    medium_risk = [r for r in results if r['risk_category'] == 'medium_risk']
    low_risk = [r for r in results if r['risk_category'] == 'low_risk']
    understaffed = [r for r in results if r['variance'] < 0]
    overstaffed = [r for r in results if r['variance'] > 1]
    
    ca_locations_daily_ot = [r for r in results if r['state'] == 'CA' and r['daily_ot_hours'] > 0]
    ca_locations_double_time = [r for r in results if r['state'] == 'CA' and r['double_time_hours'] > 0]
    
    # Add NBOT icons to each location
    for loc in results:
        loc['nbot_icon'] = get_nbot_icon(loc['ot_percentage'] if loc['ot_percentage'] is not None else 0)
    
    # Calculate employee-level aggregations
    training_incomplete_by_loc = {}
    if employee_results:
        for emp in employee_results:
            if emp['training_status'] == 'Not Completed':
                loc = emp['primary_location']
                if loc not in training_incomplete_by_loc:
                    training_incomplete_by_loc[loc] = []
                training_incomplete_by_loc[loc].append(emp['employee_name'])
        
        util_optimal = len([e for e in employee_results if e['utilization_status'] == 'Optimal'])
        util_suboptimal = len([e for e in employee_results if e['utilization_status'] == 'Sub-Optimal'])
        util_critical = len([e for e in employee_results if e['utilization_status'] == 'Critical'])
        util_under_25 = len([e for e in employee_results if e['weekly_hours'] < 25])
        util_over_40 = len([e for e in employee_results if e['weekly_hours'] > 40])
        
        tenure_critical = len([e for e in employee_results if e['tenure_risk'] == 'Critical'])
        tenure_high = len([e for e in employee_results if e['tenure_risk'] == 'High'])
        tenure_medium = len([e for e in employee_results if e['tenure_risk'] == 'Medium'])
        tenure_low = len([e for e in employee_results if e['tenure_risk'] == 'Low'])
        
        training_complete = len([e for e in employee_results if e['training_status'] == 'Completed'])
        training_incomplete = len([e for e in employee_results if e['training_status'] == 'Not Completed'])
    else:
        training_incomplete_by_loc = {}
        util_optimal = util_suboptimal = util_critical = util_under_25 = util_over_40 = 0
        tenure_critical = tenure_high = tenure_medium = tenure_low = 0
        training_complete = training_incomplete = 0
    
    # Customer Health Status
    if overall_ot_pct >= 3 or len(high_risk) > total_locations * 0.4:
        customer_health_status = "🔴 Needs Attention"
    elif overall_ot_pct >= 1 or len(high_risk) > 0:
        customer_health_status = "🟡 Monitor"
    else:
        customer_health_status = "🟢 Healthy"
    
    # Pareto metrics
    pareto_locations = [loc for loc in results if loc['pareto_80_flag'] == 'Yes']
    pareto_ot_hours = sum(float(loc.get('total_ot_exposure', 0) or 0) for loc in pareto_locations)
    
    employees_with_ot = len([e for e in employee_results if e['weekly_hours'] > 40]) if employee_results else 0
    
    # Risk Flags
    risk_flags = []
    
    if overall_ot_pct >= 3:
        risk_flags.append(f"🚨 High Customer-Wide OT ({overall_ot_pct:.1f}%) — Exceeds 3% threshold")
    
    if has_california and total_double_time > 0:
        risk_flags.append(f"🔴 Double Time Risk (CA) — {total_double_time:.1f} hours scheduled >12 hrs/day across {len(ca_locations_double_time)} location{'s' if len(ca_locations_double_time) != 1 else ''}")
    
    if has_california and total_daily_ot > total_hours * 0.05:
        risk_flags.append(f"🟡 Daily OT Risk (CA) — {total_daily_ot:.1f} hours scheduled >8 hrs/day across {len(ca_locations_daily_ot)} location{'s' if len(ca_locations_daily_ot) != 1 else ''}")
    
    if len(high_risk) > total_locations * 0.3:
        risk_flags.append(f"🔴 Multiple Critical Sites — {len(high_risk)} of {total_locations} locations exceed 3% OT")
    
    if training_incomplete > 0:
        risk_flags.append(f"⚠️ Training Non-Compliance — {training_incomplete} employees across {len(training_incomplete_by_loc)} locations need training")
    
    if tenure_critical > total_employees * 0.15:
        risk_flags.append(f"📉 High Attrition Risk — {tenure_critical} employees ({round(tenure_critical/total_employees*100, 1)}%) in critical tenure window")
    
    if len(understaffed) > total_locations * 0.3:
        risk_flags.append(f"📊 Widespread Understaffing — {len(understaffed)} locations below FTE requirements")
    
    if len(pareto_locations) <= 5 and len(pareto_locations) > 0:
        risk_flags.append(f"📊 High OT Concentration — Only {len(pareto_locations)} location{'s' if len(pareto_locations) != 1 else ''} drive 80% of OT")
    
    # Capacity Status
    if abs(total_fte_needed - total_employees) <= total_locations * 0.5:
        capacity_status = "Balanced"
    elif total_fte_needed > total_employees:
        capacity_status = f"Understaffed ({total_fte_needed - total_employees} FTE short)"
    else:
        capacity_status = f"Overstaffed ({total_employees - total_fte_needed} FTE excess)"

    # Recommendations
    urgent_recs = []
    important_recs = []
    
    # URGENT
    if len(high_risk) > 0:
        top_3_high = high_risk[:3]
        locations_list = ", ".join([f"Location {loc['location_id']}" for loc in top_3_high])
        urgent_recs.append(
            f"**Reduce OT at Critical Sites** — {locations_list} exceed 3% OT. Immediate schedule rebalancing required."
        )
    
    if has_california and total_double_time > 0:
        urgent_recs.append(
            f"**Eliminate Double Time Risk (CA)** — {total_double_time:.1f} hours scheduled >12 hrs/day across {len(ca_locations_double_time)} location{'s' if len(ca_locations_double_time) != 1 else ''}."
        )
    
    if training_incomplete > 0 and len(training_incomplete_by_loc) > 0:
        urgent_recs.append(
            f"**Complete Training Compliance** — {training_incomplete} employees across {len(training_incomplete_by_loc)} locations need General Onboarding."
        )
    
    if tenure_critical > 10:
        urgent_recs.append(
            f"**Launch Retention Campaign** — {tenure_critical} employees at critical attrition risk (≤90 days tenure). Schedule site manager check-ins."
        )
    
    # IMPORTANT
    if has_california and total_daily_ot > 50:
        important_recs.append(
            f"**Reduce Daily OT (CA)** — {total_daily_ot:.1f} hours scheduled >8 hrs/day across {len(ca_locations_daily_ot)} location{'s' if len(ca_locations_daily_ot) != 1 else ''}. Redistribute to keep shifts at 8 hours or less."
        )
    
    if len(understaffed) > 0:
        important_recs.append(
            f"**Address Staffing Gaps** — {len(understaffed)} locations are understaffed. Consider cross-site deployment or new hires."
        )
    
    if len(medium_risk) > 0:
        important_recs.append(
            f"**Monitor Moderate OT Sites** — {len(medium_risk)} locations at 1-3% OT. Prevent escalation to critical."
        )
    
    if util_under_25 > total_employees * 0.1:
        important_recs.append(
            f"**Optimize Underutilized Employees** — {util_under_25} employees scheduled <25 hours. Review availability and cross-training."
        )
    
    if len(overstaffed) > 0:
        important_recs.append(
            f"**Rebalance Overstaffed Sites** — {len(overstaffed)} locations have excess capacity. Consider redistribution."
        )
    
    if not urgent_recs and not important_recs:
        urgent_recs.append("✅ Customer operations are well-balanced across all locations — Continue current practices")
    
    # What's Working Well
    working_well = []
    
    if len(low_risk) > total_locations * 0.5:
        working_well.append(f"**{len(low_risk)} locations ({round(len(low_risk)/total_locations*100, 1)}%)** operating with healthy OT levels (<1%)")
    
    if util_optimal > total_employees * 0.5:
        working_well.append(f"**{util_optimal} employees ({round(util_optimal/total_employees*100, 1)}%)** optimally scheduled (36-40 hrs)")
    
    if training_complete == total_employees:
        working_well.append("**100% training compliance** — All scheduled employees have completed General Onboarding")
    elif training_complete > total_employees * 0.90:
        working_well.append(f"**Strong training compliance** — {round(training_complete/total_employees*100, 1)}% of employees trained")
    
    if tenure_low > total_employees * 0.5:
        working_well.append(f"**Stable workforce** — {tenure_low} employees ({round(tenure_low/total_employees*100, 1)}%) with 1+ year tenure")
    
    if not working_well:
        working_well.append("Review operational practices for improvement opportunities")
    
    # Build context
    context = {
        'customer_name': results[0]['customer_name'],
        'customer_code': customer_code,
        'start_date': start_date,
        'end_date': end_date,
        'total_locations': total_locations,
        'total_employees': total_employees,
        'active_count': active_count,
        'active_bench_count': active_bench_count,
        'inactive_bench_count': inactive_bench_count,
        'other_statuses': other_statuses,
        'total_hours': f"{total_hours:,.2f}",
        'total_hours_raw': total_hours,
        'avg_hours': avg_hours,
        'total_ot': f"{total_ot_exposure:,.2f}",
        'total_ot_raw': total_ot_exposure,
        'overall_ot_pct': overall_ot_pct,
        'overall_nbot': overall_nbot,
        'nbot_status_text': nbot_status_text,
        'total_fte_needed': total_fte_needed,
        'customer_health_status': customer_health_status,
        'capacity_status': capacity_status,
        'high_risk': high_risk,
        'medium_risk': medium_risk,
        'low_risk': low_risk,
        'understaffed': understaffed,
        'employees_with_ot': employees_with_ot,
        'locations': results,
        'training_incomplete_by_loc': training_incomplete_by_loc,
        'util_optimal': util_optimal,
        'util_suboptimal': util_suboptimal,
        'util_under_25': util_under_25,
        'util_over_40': util_over_40,
        'util_optimal_pct': round((util_optimal / total_employees * 100), 1) if total_employees > 0 else 0,
        'util_under_25_pct': round((util_under_25 / total_employees * 100), 1) if total_employees > 0 else 0,
        'util_over_40_pct': round((util_over_40 / total_employees * 100), 1) if total_employees > 0 else 0,
        'tenure_critical': tenure_critical,
        'tenure_high': tenure_high,
        'tenure_low': tenure_low,
        'tenure_critical_pct': round((tenure_critical / total_employees * 100), 1) if total_employees > 0 else 0,
        'tenure_high_pct': round((tenure_high / total_employees * 100), 1) if total_employees > 0 else 0,
        'training_complete': training_complete,
        'training_incomplete': training_incomplete,
        'training_complete_pct': round((training_complete / total_employees * 100), 1) if total_employees > 0 else 0,
        'training_incomplete_pct': round((training_incomplete / total_employees * 100), 1) if total_employees > 0 else 0,
        'risk_flags': risk_flags,
        'urgent_recs': urgent_recs,
        'important_recs': important_recs,
        'working_well': working_well,
        'pareto_locations': pareto_locations,
        'pareto_count': len(pareto_locations),
        'pareto_pct': round((len(pareto_locations) / total_locations * 100), 1) if total_locations > 0 else 0,
        'pareto_ot_hours': f"{pareto_ot_hours:,.2f}",
        'has_california': has_california,
        'total_weekly_ot': f"{total_weekly_ot:,.2f}",
        'total_daily_ot': f"{total_daily_ot:,.2f}",
        'total_double_time': f"{total_double_time:,.2f}",
        'total_weekly_ot_raw': total_weekly_ot,
        'total_daily_ot_raw': total_daily_ot,
        'total_double_time_raw': total_double_time,
        'ca_locations_daily_ot': len(ca_locations_daily_ot),
        'ca_locations_double_time': len(ca_locations_double_time),
    }

    # Render template
    template = Template("""
# 🌐 Excellence Performance Center 🌐
## Customer Schedule Analysis
**{{ customer_name }}** | **Customer Code:** {{ customer_code }} | **Week:** {{ start_date }} – {{ end_date }}

---

## 📋 EXECUTIVE SUMMARY

{% if overall_ot_pct >= 3 %}
⚠️ **SCHEDULE REBALANCING REQUIRED** — Customer-wide OT at {{ overall_ot_pct }}% exceeds 3% threshold. {{ employees_with_ot }} employee{{ 's' if employees_with_ot != 1 else '' }} scheduled over 40 hours ({{ total_ot }} OT hours). **Action:** Redistribute hours across {{ total_locations }} locations to eliminate overtime.
{% elif overall_ot_pct >= 1 %}
⚠️ **SCHEDULE OPTIMIZATION NEEDED** — Customer-wide OT at {{ overall_ot_pct }}% approaching threshold. {{ employees_with_ot }} employee{{ 's' if employees_with_ot != 1 else '' }} scheduled over 40 hours ({{ total_ot }} OT hours). **Action:** Review schedules at high-risk locations.
{% else %}
✅ **SCHEDULES WELL-BALANCED** — Customer-wide OT at {{ overall_ot_pct }}% is excellent (below 1% threshold). Continue current practices.
{% endif %}

{% if has_california %}
{% if ca_locations_double_time > 0 %}
**🔴 DOUBLE TIME ALERT (CA):** {{ ca_locations_double_time }} location{{ 's' if ca_locations_double_time != 1 else '' }} with double time exposure ({{ total_double_time }} hours >12 hrs/day). **Action:** Reduce daily hours immediately — Double time is extremely costly.
{% endif %}
{% if ca_locations_daily_ot > 0 %}
**🟡 DAILY OT ALERT (CA):** {{ ca_locations_daily_ot }} location{{ 's' if ca_locations_daily_ot != 1 else '' }} with daily OT exposure ({{ total_daily_ot }} hours >8 hrs/day). **Action:** Redistribute to keep shifts at 8 hours or less.
{% endif %}
{% endif %}

{% if training_incomplete > 0 %}
**⚠️ COMPLIANCE ALERT:** {{ training_incomplete }} employee{{ 's' if training_incomplete != 1 else '' }} across {{ training_incomplete_by_loc|length }} location{{ 's' if training_incomplete_by_loc|length != 1 else '' }} scheduled WITHOUT required General Onboarding training. **Action:** Complete training immediately or remove from schedule (compliance requirement).
{% else %}
**✅ TRAINING COMPLIANCE:** All scheduled employees have completed required General Onboarding training.
{% endif %}

{% if tenure_critical > 10 %}
**⚠️ RETENTION RISK:** {{ tenure_critical }} employee{{ 's' if tenure_critical != 1 else '' }} ({{ tenure_critical_pct }}%) in critical tenure window (≤90 days). **Action:** Deploy retention campaign across affected locations.
{% endif %}

**Customer Health:** {{ customer_health_status }} | **Pareto Focus:** {{ pareto_count }} location{{ 's' if pareto_count != 1 else '' }} ({{ pareto_pct }}%) drive 80% of OT

---

### 📊 KEY FINDINGS

| Metric | Value | Status |
|:-------|:------|:-------|
| ⚠️ Customer OT Exposure | {{ overall_ot_pct }}% | {{ nbot_status_text }} |
| ├─ Weekly OT | {{ total_weekly_ot }} | >40 hrs/week |
{% if has_california -%}
| ├─ Daily OT (CA) | {{ total_daily_ot }} | >8 hrs/day |
| └─ Double Time (CA) | {{ total_double_time }} | >12 hrs/day |
{% endif -%}
| 📍 Locations | {{ total_locations }} | {% if high_risk|length > 0 %}{{ high_risk|length }} at risk{% else %}All healthy{% endif %} |
| 👮 Employees | {{ total_employees }} | {{ total_hours }} hrs |
| 👮👮 Capacity (FTE) Needed Status | {{ total_fte_needed }} needed | {{ capacity_status }} |
| 📈 Locations in Pareto 80% | {{ pareto_count }} locations | {{ pareto_pct }}% of sites |

**Analysis:**
- **Total OT Performance:** {{ overall_ot_pct }}% — {{ nbot_status_text }}
{% if has_california -%}
- **CA OT Breakdown:** Weekly {{ total_weekly_ot }}, Daily {{ total_daily_ot }}, Double Time {{ total_double_time }}
{% endif -%}
- **OT Concentration:** {{ pareto_count }} location{{ 's' if pareto_count != 1 else '' }} ({{ pareto_pct }}%) account for 80% of overtime ({{ pareto_ot_hours }} hours)
- **Active Portfolio:** {{ total_locations }} sites with {{ total_employees }} employees
- **Total Hours Scheduled:** {{ total_hours }} hours across all locations
- **High-Risk Sites:** {{ high_risk|length }} location{{ 's' if high_risk|length != 1 else '' }} exceed{{ '' if high_risk|length != 1 else 's' }} 3% OT threshold

{% if risk_flags and risk_flags|length > 0 -%}
### Risk Indicators
{% for flag in risk_flags -%}
- {{ flag }}
{% endfor -%}
{% endif %}

{% if (urgent_recs|length + important_recs|length) > 1 -%}
### REQUIRED ACTIONS

{% for rec in urgent_recs -%}
{{ loop.index }}. {{ rec }}
{% endfor -%}
{% for rec in important_recs -%}
{{ urgent_recs|length + loop.index }}. {{ rec }}
{% endfor -%}

{% if pareto_count <= 5 and pareto_count > 0 -%}
**🎯 Pareto Strategy:** Focus improvement efforts on {{ pareto_count }} location{{ 's' if pareto_count != 1 else '' }} (marked with ☑️) — these drive 80% of customer OT. Reducing OT here will have the greatest impact.
{% endif -%}
{% elif urgent_recs|length == 1 -%}
### REQUIRED ACTIONS

1. {{ urgent_recs[0] }}
{% endif %}

{% if working_well and working_well|length > 0 -%}
### WHAT'S WORKING WELL
{% for item in working_well -%}
- {{ item }}
{% endfor -%}
{% endif %}

---

## 📊 CUSTOMER KEY METRICS

| Metric | Value |
|:----------------------|----------:|
| Active Locations | {{ total_locations }} |
| Total Employees | {{ total_employees }} |
| - Active Status | {{ active_count }} |
| - Active Bench Status | {{ active_bench_count }} |
{% if inactive_bench_count > 0 -%}
| - Inactive Bench Status | {{ inactive_bench_count }} |
{% endif -%}
{% for status, count in other_statuses.items() -%}
| - {{ status }} | {{ count }} |
{% endfor -%}
| Total Weekly Hours | {{ total_hours }} |
| Average Hours per Employee | {{ avg_hours }} |
| Total OT Exposure | {{ total_ot }} |
| ├─ Weekly OT | {{ total_weekly_ot }} |
{% if has_california -%}
| ├─ Daily OT (CA) | {{ total_daily_ot }} |
| └─ Double Time (CA) | {{ total_double_time }} |
{% endif -%}
| Overall OT % | {{ overall_ot_pct }}% |
| Overall NBOT Status | {{ overall_nbot }} |
| Total FTE Needed | {{ total_fte_needed }} |

---

## 📅 HOURS BREAKDOWN (CUSTOMER-WIDE)

| Category | Hours | % of Total | Visual Impact |
|:---------|------:|:----------:|:--------------|
| Regular Hours | {{ "{:,.2f}".format(total_hours_raw - total_ot_raw) }} | {{ (100 - overall_ot_pct)|round(1) }}% | ████████████████████ |
| **Total OT Exposure** | **{{ total_ot }}** | **{{ overall_ot_pct }}%** | {% if overall_ot_pct >= 3 %}██████░░░░░░░░░░░░░░{% elif overall_ot_pct >= 1 %}███░░░░░░░░░░░░░░░░░{% else %}█░░░░░░░░░░░░░░░░░░░{% endif %} |
| ├─ Weekly OT (>40 hrs/wk) | {{ total_weekly_ot }} | {{ "%.1f"|format((total_weekly_ot_raw / total_hours_raw * 100) if total_hours_raw > 0 else 0) }}% | {% if (total_weekly_ot_raw / total_hours_raw * 100) >= 2 %}████░░░░░░░░░░░░░░░░{% elif (total_weekly_ot_raw / total_hours_raw * 100) >= 1 %}██░░░░░░░░░░░░░░░░░░{% else %}█░░░░░░░░░░░░░░░░░░░{% endif %} |
{% if has_california -%}
| ├─ Daily OT (>8 hrs/day CA) | {{ total_daily_ot }} | {{ "%.1f"|format((total_daily_ot_raw / total_hours_raw * 100) if total_hours_raw > 0 else 0) }}% | {% if (total_daily_ot_raw / total_hours_raw * 100) >= 2 %}████░░░░░░░░░░░░░░░░{% elif (total_daily_ot_raw / total_hours_raw * 100) >= 1 %}██░░░░░░░░░░░░░░░░░░{% else %}█░░░░░░░░░░░░░░░░░░░{% endif %} |
| └─ Double Time (>12 hrs/day CA) | {{ total_double_time }} | {{ "%.1f"|format((total_double_time_raw / total_hours_raw * 100) if total_hours_raw > 0 else 0) }}% | {% if (total_double_time_raw / total_hours_raw * 100) >= 1 %}██░░░░░░░░░░░░░░░░░░{% else %}█░░░░░░░░░░░░░░░░░░░{% endif %} |
{% endif -%}

### 💡 OT Insights:

{% if pareto_count <= 5 -%}
**📊 High Concentration:** {{ pareto_count }} location{{ 's' if pareto_count != 1 else '' }} ({{ pareto_pct }}%) generate 80% of all OT ({{ pareto_ot_hours }} hours) — Focused intervention strategy will yield maximum ROI.
{% else -%}
**📊 Distributed OT:** OT spread across {{ pareto_count }} locations ({{ pareto_pct }}%) — Requires broader intervention strategy across multiple sites.
{% endif %}

{% if has_california -%}
{% set weekly_ot_pct_of_total = (total_weekly_ot_raw / total_ot_raw * 100)|round(1) if total_ot_raw > 0 else 0 %}
{% set daily_ot_pct_of_total = (total_daily_ot_raw / total_ot_raw * 100)|round(1) if total_ot_raw > 0 else 0 %}
{% set double_time_pct_of_total = (total_double_time_raw / total_ot_raw * 100)|round(1) if total_ot_raw > 0 else 0 %}

**🏛️ California OT Composition:**
- Weekly OT accounts for {{ weekly_ot_pct_of_total }}% of total OT exposure
- Daily OT accounts for {{ daily_ot_pct_of_total }}% of total OT exposure ({{ ca_locations_daily_ot }} CA location{{ 's' if ca_locations_daily_ot != 1 else '' }})
- Double Time accounts for {{ double_time_pct_of_total }}% of total OT exposure ({{ ca_locations_double_time }} CA location{{ 's' if ca_locations_double_time != 1 else '' }})
{% if double_time_pct_of_total > 10 -%}
- ⚠️ **Critical:** Double time represents {{ double_time_pct_of_total }}% of OT — This is the most expensive OT type and should be eliminated immediately
{% endif %}
{% endif %}

{% if employees_with_ot > 0 -%}
**👥 Employee Impact:** {{ employees_with_ot }} employee{{ 's' if employees_with_ot != 1 else '' }} ({{ "%.1f"|format((employees_with_ot / total_employees * 100) if total_employees > 0 else 0) }}%) scheduled for overtime — Consider workload redistribution or additional hiring.
{% else -%}
**✅ Optimal Scheduling:** All employees scheduled within regular hours — Excellent balance maintained.
{% endif %}

{% if high_risk|length > 0 -%}
**🎯 Priority Sites:** {{ high_risk|length }} critical location{{ 's' if high_risk|length != 1 else '' }} ({{ "%.1f"|format((high_risk|length / total_locations * 100) if total_locations > 0 else 0) }}%) require immediate intervention — Focus resources here first.
{% endif %}

{% if understaffed|length > 0 -%}
**📉 Capacity Gap:** {{ understaffed|length }} location{{ 's' if understaffed|length != 1 else '' }} understaffed — Gap total: {{ understaffed|sum(attribute='variance')|abs }} FTE — Staffing increase needed to eliminate OT pressure.
{% endif %}
---

## 🚨 CUSTOMER-WIDE ALERTS

{% if has_california and ca_locations_double_time > 0 %}
### 🔴 Locations with Double Time Risk (CA): ➖➤ {{ ca_locations_double_time }}
📌 **Action Required** ➡️ Reduce daily hours immediately - Double time is extremely costly

{% for loc in locations if loc.state == 'CA' and loc.double_time_hours > 0 -%}
- **Location {{ loc.location_id }}** ({{ loc.state }}) — {{ loc.double_time_hours|round(1) }} DT hours — {{ loc.ot_percentage }}% total OT — Site Manager: {{ loc.site_manager }} {% if loc.pareto_80_flag == 'Yes' %}☑️ *Pareto 80%*{% endif %}
{% endfor %}
---
{% endif %}

{% if has_california and ca_locations_daily_ot > 0 %}
### 🟡 Locations with Daily OT Risk (CA): ➖➤ {{ ca_locations_daily_ot }}
📌 **Action Required** ➡️ Redistribute to keep shifts at 8 hours or less

{% for loc in locations if loc.state == 'CA' and loc.daily_ot_hours > 0 -%}
- **Location {{ loc.location_id }}** ({{ loc.state }}) — {{ loc.daily_ot_hours|round(1) }} daily OT hours — {{ loc.ot_percentage }}% total OT — Site Manager: {{ loc.site_manager }} {% if loc.pareto_80_flag == 'Yes' %}☑️ *Pareto 80%*{% endif %}
{% endfor %}
---
{% endif %}

{% if high_risk|length > 0 %}
### 🔴 High Risk Locations (OT ≥3%): ➖➤ {{ high_risk|length }}
📌 **Action Required** ➡️ Immediate schedule rebalancing or staffing increase

{% for loc in high_risk -%}
- **Location {{ loc.location_id }}** ({{ loc.state }}) — {{ loc.ot_percentage }}% OT — Site Manager: {{ loc.site_manager }} — Total {{ loc.total_ot_exposure|round(1) }} OT hours {% if loc.state == 'CA' %}(W:{{ loc.weekly_ot_hours|round(1) }} D:{{ loc.daily_ot_hours|round(1) }} DT:{{ loc.double_time_hours|round(1) }}){% endif %} {% if loc.pareto_80_flag == 'Yes' %}☑️ *Pareto 80%*{% endif %}
{% endfor %}
---
{% endif %}

{% if medium_risk|length > 0 %}
### 🟡 Medium Risk Locations (OT 1-3%): ➖➤ {{ medium_risk|length }}
📌 **Action Required** ➡️ Monitor and prevent escalation

{% for loc in medium_risk -%}
- **Location {{ loc.location_id }}** ({{ loc.state }}) — {{ loc.ot_percentage }}% OT — Site Manager: {{ loc.site_manager }} {% if loc.pareto_80_flag == 'Yes' %}☑️ *Pareto 80%*{% endif %}
{% endfor %}
---
{% endif %}

{% if understaffed|length > 0 %}
### 📉 Understaffed Locations (FTE Gap): ➖➤ {{ understaffed|length }}
📌 **Action Required** ➡️ Increase staffing or redistribute resources

{% for loc in understaffed -%}
- **Location {{ loc.location_id }}** — {{ loc.employee_count }} employees vs {{ loc.fte_needed }} FTE needed ({{ loc.variance }} gap) {% if loc.pareto_80_flag == 'Yes' %}☑️ *Pareto 80%*{% endif %}
{% endfor %}
---
{% endif %}

---

## 📍 LOCATION PERFORMANCE SUMMARY (Pareto Ranked by OT Exposure)

**Status Thresholds:**

- **OT Risk:** 🔴 High (≥3%) | 🟡 Medium (1-3%) | 🟢 Low (<1%)

- **☑️ = Pareto 80%** (Priority Focus Areas — these locations drive 80% of customer overtime)

{% if has_california %}
| Rank | Location | State | Site Manager | Employees | Hours | OT Breakdown | Total OT | OT % | NBOT | FTE | Variance | Cum OT % | Pareto |
|:-----:|:--------:|:-----:|:-------------|:----------:|------:|:-------------|:--------:|-----:|:----:|----:|:---------:|---------:|:------:|
{% for loc in locations -%}
| {{ loc.ot_rank }} | {{ loc.location_id }} | {{ loc.state }} | {{ loc.site_manager }} | {{ loc.employee_count }} | {{ loc.total_hours|round(1) }} | {% if loc.state == 'CA' %}W:{{ loc.weekly_ot_hours|round(1) }} D:{{ loc.daily_ot_hours|round(1) }} DT:{{ loc.double_time_hours|round(1) }}{% else %}W:{{ loc.weekly_ot_hours|round(1) }}{% endif %} | {{ loc.total_ot_exposure|round(1) }} | {{ loc.ot_percentage }}% | {{ loc.nbot_icon }} | {{ loc.fte_needed }} | {{ loc.variance }} | {{ loc.ot_cum_pct }}% | {% if loc.pareto_80_flag == 'Yes' %}☑️{% endif %} |
{% endfor %}
{% else %}
| Rank | Location | State | Site Manager | Employees | Hours | Weekly OT | Total OT | OT % | NBOT | FTE | Variance | Cum OT % | Pareto |
|:-----:|:--------:|:-----:|:-------------|:----------:|------:|----------:|:--------:|-----:|:----:|----:|:---------:|---------:|:------:|
{% for loc in locations -%}
| {{ loc.ot_rank }} | {{ loc.location_id }} | {{ loc.state }} | {{ loc.site_manager }} | {{ loc.employee_count }} | {{ loc.total_hours|round(1) }} | {{ loc.weekly_ot_hours|round(1) }} | {{ loc.total_ot_exposure|round(1) }} | {{ loc.ot_percentage }}% | {{ loc.nbot_icon }} | {{ loc.fte_needed }} | {{ loc.variance }} | {{ loc.ot_cum_pct }}% | {% if loc.pareto_80_flag == 'Yes' %}☑️{% endif %} |
{% endfor %}
{% endif %}

**📊 Pareto Analysis:** The {{ pareto_count }} location{{ 's' if pareto_count != 1 else '' }} marked with ☑️ account for 80% of all customer overtime. Focus improvement efforts here for maximum ROI.

---

{% if training_incomplete_by_loc|length > 0 %}
## ⚠️ TRAINING COMPLIANCE

### General Onboarding Training NOT Completed: ➖➤ {{ training_incomplete_by_loc|length }} Location{{ 's' if training_incomplete_by_loc|length != 1 else '' }}
📌 **Action Required** ➡️ Complete training or remove from schedule (compliance requirement)

{% for loc_id, emp_names in training_incomplete_by_loc.items() -%}
- **Location {{ loc_id }}** — {{ emp_names|length }} employee{{ 's' if emp_names|length != 1 else '' }}
  - Employees: {{ emp_names|join(', ') }}
{% endfor %}
---
{% endif %}

##  WORKFORCE UTILIZATION SUMMARY

| Utilization Status | Employee Count | % of Workforce |
|:-------------------|---------------:|---------------:|
| 🟢 Optimal (36-40 hrs) | {{ util_optimal }} | {{ util_optimal_pct }}% |
| 🟡 Sub-Optimal (25-35 hrs) | {{ util_suboptimal }} | {{ "%.1f"|format((util_suboptimal / total_employees * 100) if total_employees > 0 else 0) }}% |
| 🔴 Under-utilized (<25 hrs) | {{ util_under_25 }} | {{ util_under_25_pct }}% |
| 🔴 Over-utilized (>40 hrs) | {{ util_over_40 }} | {{ util_over_40_pct }}% |

---

##  TRAINING COMPLIANCE

| Training Status | Employee Count | % of Workforce |
|:----------------|---------------:|---------------:|
| ✅ Completed | {{ training_complete }} | {{ training_complete_pct }}% |
| ⚠️ Not Completed | {{ training_incomplete }} | {{ training_incomplete_pct }}% |

{% if training_incomplete > 0 -%}
**Action Required:** {{ training_incomplete }} employee{{ 's' if training_incomplete != 1 else '' }} across {{ training_incomplete_by_loc|length }} location{{ 's' if training_incomplete_by_loc|length != 1 else '' }} need General Onboarding completion
{% endif %}

---

##  TENURE RISK ANALYSIS

| Tenure Status | Employee Count | % of Workforce |
|:--------------|---------------:|---------------:|
| 🔴 Critical (≤90 days) | {{ tenure_critical }} | {{ tenure_critical_pct }}% |
| 🟠 High (91-179 days) | {{ tenure_high }} | {{ tenure_high_pct }}% |
| 🟡 Medium (180-365 days) | {{ (total_employees - tenure_critical - tenure_high - tenure_low) }} | {{ "%.1f"|format(((total_employees - tenure_critical - tenure_high - tenure_low) / total_employees * 100) if total_employees > 0 else 0) }}% |
| 🟢 Low (>365 days) | {{ tenure_low }} | {{ "%.1f"|format((tenure_low / total_employees * 100) if total_employees > 0 else 0) }}% |

---

## 🧾 CUSTOMER HEALTH SUMMARY

✅ **Total scheduled capacity:** {{ total_hours }} hours across {{ total_employees }} employees at {{ total_locations }} locations  
✅ **Overall OT Status:** {{ overall_nbot }} ({{ overall_ot_pct }}% total OT exposure rate)  
{% if has_california -%}
📊 **CA OT Breakdown:** Weekly {{ total_weekly_ot }}, Daily {{ total_daily_ot }}, Double Time {{ total_double_time }}  
{% endif -%}
📊 **FTE Alignment:** {{ total_fte_needed }} FTE needed — {{ capacity_status }}  
📊 **Pareto Focus:** {{ pareto_count }} location{{ 's' if pareto_count != 1 else '' }} ({{ pareto_pct }}%) account for 80% of OT — {{ pareto_ot_hours }} hours  
{% if high_risk|length == 0 and medium_risk|length == 0 -%}
🎯 **Performance:** All locations operating within healthy parameters  
{% endif %}
{% if training_complete == total_employees -%}
✅ **Training Compliance:** 100% — All scheduled employees trained  
{% endif %}
{% if tenure_low > total_employees * 0.5 -%}
✅ **Workforce Stability:** Strong retention with {{ "%.1f"|format((tenure_low / total_employees * 100) if total_employees > 0 else 0) }}% tenured employees  
{% endif %}
""")
    
    return template.render(**context)
