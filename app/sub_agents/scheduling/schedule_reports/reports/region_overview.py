"""Region Overview Report - Regional overview with Pareto analysis."""

from jinja2 import Template
from collections import Counter
from ..common import (
    BQ_DATA_PROJECT_ID,
    BQ_DATASET_ID,
    execute_query,
    get_nbot_status,
    get_nbot_icon,
)


def generate_region_overview(
    region: str,
    start_date: str,
    end_date: str
) -> str:
    """Generate enhanced region-level overview report with Pareto analysis."""
    
    # SQL to aggregate by customer within region
    sql = f"""
WITH EmployeeWeeklyHours AS (
  SELECT
    customer_code,
    location_id,
    employee_id,
    SUM(scheduled_hours) AS weekly_hours
  FROM `{BQ_DATA_PROJECT_ID}.{BQ_DATASET_ID}.APEX_NWS`
  WHERE region = '{region}'
    AND scheduled_date BETWEEN '{start_date}' AND '{end_date}'
  GROUP BY customer_code, location_id, employee_id
),
CustomerSummary AS (
  SELECT
    customer_code,
    COUNT(DISTINCT location_id) AS location_count,
    COUNT(DISTINCT employee_id) AS employee_count,
    SUM(weekly_hours) AS total_hours,
    SUM(CASE WHEN weekly_hours > 40 THEN weekly_hours - 40 ELSE 0 END) AS ot_hours
  FROM EmployeeWeeklyHours
  GROUP BY customer_code
)
SELECT
  cs.customer_code,
  ANY_VALUE(n.customer_name) AS customer_name,
  ANY_VALUE(n.region) AS region,
  cs.location_count,
  cs.employee_count,
  cs.total_hours,
  cs.ot_hours,
  ROUND(SAFE_DIVIDE(cs.ot_hours, cs.total_hours) * 100, 1) AS ot_percentage,
  CAST(CEILING(cs.total_hours / 36) AS INT64) AS fte_needed,
  CAST(cs.employee_count AS INT64) - CAST(CEILING(cs.total_hours / 36) AS INT64) AS variance,
  CASE
    WHEN ROUND(SAFE_DIVIDE(cs.ot_hours, cs.total_hours) * 100, 1) >= 3 THEN 'high_risk'
    WHEN ROUND(SAFE_DIVIDE(cs.ot_hours, cs.total_hours) * 100, 1) >= 1 THEN 'medium_risk'
    ELSE 'low_risk'
  END AS risk_category
FROM CustomerSummary cs
LEFT JOIN `{BQ_DATA_PROJECT_ID}.{BQ_DATASET_ID}.APEX_NWS` n
  ON cs.customer_code = n.customer_code 
  AND n.region = '{region}'
  AND n.scheduled_date BETWEEN '{start_date}' AND '{end_date}'
GROUP BY cs.customer_code, cs.location_count, cs.employee_count, cs.total_hours, cs.ot_hours
ORDER BY ot_percentage DESC
"""
    
    # Execute query
    try:
        results = execute_query(sql)
    except Exception as e:
        return str(e)
    
    if not results:
        return f"No data found for region={region}, dates={start_date} to {end_date}"
    
    # PARETO CALCULATION
    results_sorted = sorted(results, key=lambda x: float(x.get('ot_hours', 0) or 0), reverse=True)
    
    total_ot_all = sum(float(r.get('ot_hours', 0) or 0) for r in results_sorted)
    cumulative_ot = 0
    
    for idx, customer in enumerate(results_sorted, 1):
        customer['ot_rank'] = idx
        ot_hours = float(customer.get('ot_hours', 0) or 0)
        cumulative_ot += ot_hours
        customer['ot_cum_pct'] = round((cumulative_ot / total_ot_all * 100), 1) if total_ot_all > 0 else 0
        customer['pareto_80_flag'] = 'Yes' if customer['ot_cum_pct'] <= 80 else 'No'
    
    results = results_sorted
    
    # SECOND QUERY: Get employee-level details
    employee_sql = f"""
WITH EmployeeWeekly AS (
  SELECT
    employee_id,
    ANY_VALUE(employee_name) AS employee_name,
    ANY_VALUE(employee_status) AS employee_status,
    ANY_VALUE(employee_date_started) AS employee_date_started,
    ANY_VALUE(customer_code) AS primary_customer,
    ANY_VALUE(customer_name) AS customer_name,
    SUM(scheduled_hours) AS weekly_hours,
    DATE_DIFF(CURRENT_DATE(), ANY_VALUE(employee_date_started), DAY) AS tenure_days,
    MAX(CASE 
      WHEN course_name = 'ONB101-ALL: Metro One LPSG - General Onboarding (All Employees)' 
           AND course_completion_date IS NOT NULL THEN 1
      ELSE 0
    END) AS has_training
  FROM `{BQ_DATA_PROJECT_ID}.{BQ_DATASET_ID}.APEX_NWS`
  WHERE region = '{region}'
    AND scheduled_date BETWEEN '{start_date}' AND '{end_date}'
  GROUP BY employee_id
)
SELECT
  employee_id,
  employee_name,
  employee_status,
  primary_customer,
  customer_name,
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
    total_customers = len(results)
    total_locations = sum(r['location_count'] for r in results)
    total_hours = sum(r['total_hours'] for r in results)
    total_ot = sum(r['ot_hours'] for r in results)
    overall_ot_pct = round((total_ot / total_hours * 100) if total_hours > 0 else 0, 1)
    total_fte_needed = sum(r['fte_needed'] for r in results)
    
    total_employees = len(employee_results) if employee_results else 0
    avg_hours = round(total_hours / total_employees, 1) if total_employees > 0 else 0
    
    # Add active status breakdown from employee results
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
    
    # Categorize customers by risk
    high_risk = [r for r in results if r['risk_category'] == 'high_risk']
    medium_risk = [r for r in results if r['risk_category'] == 'medium_risk']
    low_risk = [r for r in results if r['risk_category'] == 'low_risk']
    understaffed = [r for r in results if r['variance'] < 0]
    overstaffed = [r for r in results if r['variance'] > 1]
    
    # Add NBOT icons to each customer
    for customer in results:
        customer['nbot_icon'] = get_nbot_icon(customer['ot_percentage'] if customer['ot_percentage'] is not None else 0)
    
    # Calculate employee-level aggregations
    training_incomplete_by_customer = {}
    if employee_results:
        for emp in employee_results:
            if emp['training_status'] == 'Not Completed':
                cust = emp['customer_name']
                if cust not in training_incomplete_by_customer:
                    training_incomplete_by_customer[cust] = []
                training_incomplete_by_customer[cust].append(emp['employee_name'])
        
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
        training_incomplete_by_customer = {}
        util_optimal = util_suboptimal = util_critical = util_under_25 = util_over_40 = 0
        tenure_critical = tenure_high = tenure_medium = tenure_low = 0
        training_complete = training_incomplete = 0
    
    employees_with_ot = len([e for e in employee_results if e['weekly_hours'] > 40]) if employee_results else 0
    
    # Region Health Status
    if overall_ot_pct >= 3 or len(high_risk) > total_customers * 0.4:
        region_health_status = "🔴 Needs Attention"
    elif overall_ot_pct >= 1 or len(high_risk) > 0:
        region_health_status = "🟡 Monitor"
    else:
        region_health_status = "🟢 Healthy"
    
    # Pareto metrics
    pareto_customers = [cust for cust in results if cust['pareto_80_flag'] == 'Yes']
    pareto_ot_hours = sum(float(cust.get('ot_hours', 0) or 0) for cust in pareto_customers)

    # Risk Flags
    risk_flags = []
    
    if overall_ot_pct >= 3:
        risk_flags.append(f"🚨 High Regional OT ({overall_ot_pct:.1f}%) — Exceeds 3% threshold")
    
    if len(high_risk) > total_customers * 0.3:
        risk_flags.append(f"🔴 Multiple Critical Customers — {len(high_risk)} of {total_customers} customers exceed 3% OT")
    
    if training_incomplete > 0:
        risk_flags.append(f"⚠️ Training Non-Compliance — {training_incomplete} employees across {len(training_incomplete_by_customer)} customers need training")
    
    if tenure_critical > total_employees * 0.15:
        risk_flags.append(f"📉 High Attrition Risk — {tenure_critical} employees ({round(tenure_critical/total_employees*100, 1)}%) in critical tenure window")
    
    if len(understaffed) > total_customers * 0.3:
        risk_flags.append(f"📊 Widespread Understaffing — {len(understaffed)} customers below FTE requirements")
    
    if len(pareto_customers) <= 5 and len(pareto_customers) > 0:
        risk_flags.append(f"📊 High OT Concentration — Only {len(pareto_customers)} customer{'s' if len(pareto_customers) != 1 else ''} drive 80% of regional OT")
    
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
        customers_list = ", ".join([f"{cust['customer_name']}" for cust in top_3_high])
        urgent_recs.append(
            f"**Reduce OT at Critical Customers** — {customers_list} exceed 3% OT. Immediate regional support required."
        )
    
    if training_incomplete > 0 and len(training_incomplete_by_customer) > 0:
        urgent_recs.append(
            f"**Complete Training Compliance** — {training_incomplete} employees across {len(training_incomplete_by_customer)} customers need General Onboarding."
        )
    
    if tenure_critical > 10:
        urgent_recs.append(
            f"**Launch Regional Retention Campaign** — {tenure_critical} employees at critical attrition risk (≤90 days tenure). Deploy regional retention resources."
        )
    
    # IMPORTANT
    if len(understaffed) > 0:
        important_recs.append(
            f"**Address Regional Staffing Gaps** — {len(understaffed)} customers are understaffed. Consider regional resource pool or hiring initiative."
        )
    
    if len(medium_risk) > 0:
        important_recs.append(
            f"**Monitor Moderate OT Customers** — {len(medium_risk)} customers at 1-3% OT. Provide proactive regional support."
        )
    
    if util_under_25 > total_employees * 0.1:
        important_recs.append(
            f"**Optimize Underutilized Employees** — {util_under_25} employees scheduled <25 hours. Explore cross-customer deployment opportunities."
        )
    
    if len(overstaffed) > 0:
        important_recs.append(
            f"**Rebalance Regional Capacity** — {len(overstaffed)} customers have excess capacity. Consider regional resource redistribution."
        )
    
    if not urgent_recs and not important_recs:
        urgent_recs.append("✅ Regional operations are well-balanced across all customers — Continue current practices")
    
    # What's Working Well
    working_well = []
    
    if len(low_risk) > total_customers * 0.5:
        working_well.append(f"**{len(low_risk)} customers ({round(len(low_risk)/total_customers*100, 1)}%)** operating with healthy OT levels (<1%)")
    
    if util_optimal > total_employees * 0.5:
        working_well.append(f"**{util_optimal} employees ({round(util_optimal/total_employees*100, 1)}%)** optimally scheduled (36-40 hrs)")
    
    if training_complete == total_employees:
        working_well.append("**100% regional training compliance** — All scheduled employees have completed General Onboarding")
    elif training_complete > total_employees * 0.90:
        working_well.append(f"**Strong training compliance** — {round(training_complete/total_employees*100, 1)}% of regional employees trained")
    
    if tenure_low > total_employees * 0.5:
        working_well.append(f"**Stable regional workforce** — {tenure_low} employees ({round(tenure_low/total_employees*100, 1)}%) with 1+ year tenure")
    
    if not working_well:
        working_well.append("Review regional operational practices for improvement opportunities")
    
    # Build context
    context = {
        'region': results[0]['region'],
        'start_date': start_date,
        'end_date': end_date,
        'total_customers': total_customers,
        'total_locations': total_locations,
        'total_employees': total_employees,
        'active_count': active_count,
        'active_bench_count': active_bench_count,
        'inactive_bench_count': inactive_bench_count,
        'other_statuses': other_statuses,
        'total_hours': f"{total_hours:,.2f}",
        'total_hours_raw': total_hours,
        'avg_hours': avg_hours,
        'total_ot': f"{total_ot:,.2f}",
        'total_ot_raw': total_ot,
        'overall_ot_pct': overall_ot_pct,
        'overall_nbot': overall_nbot,
        'nbot_status_text': nbot_status_text,
        'total_fte_needed': total_fte_needed,
        'region_health_status': region_health_status,
        'capacity_status': capacity_status,
        'high_risk': high_risk,
        'medium_risk': medium_risk,
        'low_risk': low_risk,
        'understaffed': understaffed,
        'employees_with_ot': employees_with_ot,
        'customers': results,
        'training_incomplete_by_customer': training_incomplete_by_customer,
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
        'pareto_customers': pareto_customers,
        'pareto_count': len(pareto_customers),
        'pareto_pct': round((len(pareto_customers) / total_customers * 100), 1) if total_customers > 0 else 0,
        'pareto_ot_hours': f"{pareto_ot_hours:,.2f}"
    }

    # Render template
    template = Template("""
# 🌐 Excellence Performance Center 🌐
## Region Schedule Analysis
**Region: {{ region }}** | **Week:** {{ start_date }} – {{ end_date }}

---

## 📋 EXECUTIVE SUMMARY

{% if overall_ot_pct >= 3 %}
🔴 **Schedule Rebalancing Required** — Regional OT at {{ overall_ot_pct }}% exceeds 3% threshold. {{ employees_with_ot }} employee{{ 's' if employees_with_ot != 1 else '' }} scheduled over 40 hours ({{ total_ot }} OT hours). **Action:** Deploy regional resources to redistribute hours across {{ total_customers }} customers.
{% elif overall_ot_pct >= 1 %}
🟡 **Schedules Optimization Needed** — Regional OT at {{ overall_ot_pct }}% approaching threshold. {{ employees_with_ot }} employee{{ 's' if employees_with_ot != 1 else '' }} scheduled over 40 hours ({{ total_ot }} OT hours). **Action:** Focus regional support on high-risk customers.
{% else %}
🟢 **SCHEDULES Well-Balanced** — Regional OT at {{ overall_ot_pct }}% is excellent (below 1% threshold). Continue current regional practices.
{% endif %}

{% if high_risk|length > 0 %}
- **High-Risk Customers:** {{ high_risk|length }} customer{{ 's' if high_risk|length != 1 else '' }} exceed{{ '' if high_risk|length != 1 else 's' }} 3% OT threshold — **Action:** Intervention required
{% endif %}

{% if training_incomplete > 0 %}
**⚠️ Training Compliance:** {{ training_incomplete }} employee{{ 's' if training_incomplete != 1 else '' }} across {{ training_incomplete_by_customer|length }} customer{{ 's' if training_incomplete_by_customer|length != 1 else '' }} scheduled WITHOUT required General Onboarding training. **Action:** Deploy regional training support immediately (compliance requirement).
{% else %}
**✅ Training Compliance:** All scheduled employees across the region have completed required General Onboarding training.
{% endif %}

{% if tenure_critical > 10 %}
**⚠️ Retention Risk:** {{ tenure_critical }} employee{{ 's' if tenure_critical != 1 else '' }} ({{ tenure_critical_pct }}%) in critical tenure window (≤90 days). **Action:** Launch coordinated regional retention campaign.
{% endif %}

- **Pareto Analysis:** {{ pareto_count }} customer{{ 's' if pareto_count != 1 else '' }} ({{ pareto_pct }}%) drive 80% of regional OT ({{ pareto_ot_hours }} hours)
- **Regional Capacity Analysis:** {{ total_employees }} employees deployed vs {{ total_fte_needed }} FTE needed (36 hrs/FTE standard) — Gap: {{ capacity_status }}

{% if understaffed|length > 0 and overstaffed|length > 0 %}
- **Capacity Imbalance:** {{ understaffed|length }} customer{{ 's' if understaffed|length != 1 else '' }} understaffed, {{ overstaffed|length }} customer{{ 's' if overstaffed|length != 1 else '' }} running under capacity — **Opportunity:** Redistribute resources regionally
{% elif understaffed|length > 0 %}
- **Understaffed Customers:** {{ understaffed|length }} customer{{ 's' if understaffed|length != 1 else '' }} below FTE requirements — **Action:** Regional resource reallocation needed
{% elif overstaffed|length > 0 %}
- **Under-Capacity Customers:** {{ overstaffed|length }} customer{{ 's' if overstaffed|length != 1 else '' }} running with excess capacity — **Opportunity:** Redeploy resources to other customers
{% endif %}

- **OT Risk Thresholds:** 🔴 High (≥3%) | 🟡 Medium (1-3%) | 🟢 Low (<1%)

---

### 📊 KEY FINDINGS

| Metric | Value | Status |
|:-------|:------|:-------|
| 🔴 Regional OT | {{ overall_ot_pct }}% | {{ nbot_status_text }} |
| 🧑‍💼🧑‍💼 Active Customers | {{ total_customers }} | {% if high_risk|length > 0 %}{{ high_risk|length }} at risk{% else %}All healthy{% endif %} |
| 📍 Total Locations | {{ total_locations }} | Across region |
| 👮 Employees | {{ total_employees }} | {{ total_hours }} hrs |
| 👮👮 Capacity (FTE) Needed Status | {{ total_fte_needed }} needed | {{ capacity_status }} |
| 📈 Customers in Pareto 80% | {{ pareto_count }} customers | {{ pareto_pct }}% of portfolio |

**Analysis:**
- **Regional OT Performance:** {{ overall_ot_pct }}% — {{ nbot_status_text }}
- **OT Concentration:** {{ pareto_count }} customer{{ 's' if pareto_count != 1 else '' }} ({{ pareto_pct }}%) account for 80% of regional overtime ({{ pareto_ot_hours }} hours)
- **Regional Portfolio:** {{ total_customers }} customers with {{ total_locations }} locations
- **Total Hours Scheduled:** {{ total_hours }} hours across region
- **High-Risk Customers:** {{ high_risk|length }} customer{{ 's' if high_risk|length != 1 else '' }} exceed{{ '' if high_risk|length != 1 else 's' }} 3% OT threshold

{% if risk_flags and risk_flags|length > 0 -%}
### Risk Indicators
{% for flag in risk_flags -%}
- {{ flag }}
{% endfor -%}
{% endif %}

{% if (urgent_recs|length + important_recs|length) > 1 -%}
### ➡️ REQUIRED ACTIONS

{% for rec in urgent_recs -%}
{{ loop.index }}. {{ rec }}
{% endfor -%}
{% for rec in important_recs -%}
{{ urgent_recs|length + loop.index }}. {{ rec }}
{% endfor -%}

{% if pareto_count <= 5 and pareto_count > 0 -%}
**🎯 Pareto Strategy:** Focus regional resources on {{ pareto_count }} customer{{ 's' if pareto_count != 1 else '' }} (marked with ☑️) — these drive 80% of regional OT. Maximum impact with focused regional intervention.
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

## 📊 REGIONAL KEY METRICS

| Metric | Value |
|:----------------------|----------:|
| Active Customers | {{ total_customers }} |
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
| Total Scheduled OT | {{ total_ot }} |
| Overall OT % | {{ overall_ot_pct }}% |
| Overall NBOT Status | {{ overall_nbot }} |
| Total FTE Needed (36 hrs) | {{ total_fte_needed }} |

---

## 📅 HOURS BREAKDOWN (REGION-WIDE)

| Category | Hours | % of Total | Visual Impact |
|:---------|------:|:----------:|:--------------|
| Regular Hours (≤40) | {{ "{:,.2f}".format(total_hours_raw - total_ot_raw) }} | {{ (100 - overall_ot_pct)|round(1) }}% | ████████████████████ |
| Scheduled Overtime (>40) | {{ total_ot }} | {{ overall_ot_pct }}% | {% if overall_ot_pct >= 3 %}██████░░░░░░░░░░░░░░{% elif overall_ot_pct >= 1 %}███░░░░░░░░░░░░░░░░░{% else %}█░░░░░░░░░░░░░░░░░░░{% endif %} |

**💡 Key Insight:** {% if pareto_count <= 5 %}{{ pareto_count }} customer{{ 's' if pareto_count != 1 else '' }} generate 80% of regional OT — High concentration enables focused regional intervention{% else %}OT distributed across {{ pareto_count }} customers — Requires broader regional strategy{% endif %}

---

## 🚨 REGIONAL ALERTS

{% if high_risk|length > 0 %}
### 🔴 High Risk Customers (OT ≥3%): ➖➤ {{ high_risk|length }}
📌 **Action Required** ➡️ Deploy regional support immediately

{% for cust in high_risk -%}
- **{{ cust.customer_name }}** (Code: {{ cust.customer_code }}) — {{ cust.ot_percentage }}% OT — {{ cust.location_count }} locations, {{ cust.employee_count }} employees — {{ cust.ot_hours|round(1) }} OT hours {% if cust.pareto_80_flag == 'Yes' %}☑️ *Pareto 80%*{% endif %}
{% endfor %}
---
{% endif %}

{% if medium_risk|length > 0 %}
### 🟡 Medium Risk Customers (OT 1-3%): ➖➤ {{ medium_risk|length }}
📌 **Action Required** ➡️ Proactive regional monitoring

{% for cust in medium_risk -%}
- **{{ cust.customer_name }}** (Code: {{ cust.customer_code }}) — {{ cust.ot_percentage }}% OT — {{ cust.location_count }} locations {% if cust.pareto_80_flag == 'Yes' %}☑️ *Pareto 80%*{% endif %}
{% endfor %}
---
{% endif %}

{% if understaffed|length > 0 %}
### 📉 Understaffed Customers (FTE Gap): ➖➤ {{ understaffed|length }}
📌 **Action Required** ➡️ Regional resource reallocation or hiring support

{% for cust in understaffed -%}
- **{{ cust.customer_name }}** — {{ cust.employee_count }} employees vs {{ cust.fte_needed }} FTE needed ({{ cust.variance }} gap) {% if cust.pareto_80_flag == 'Yes' %}☑️ *Pareto 80%*{% endif %}
{% endfor %}
---
{% endif %}

---

## 📍 CUSTOMER PERFORMANCE SUMMARY (Pareto Ranked by OT Hours)

**Status Thresholds:**
- **OT Risk:** 🔴 High (≥3%) | 🟡 Medium (1-3%) | 🟢 Low (<1%)

- **☑️ = Pareto 80%** (Regional Priority Focus Areas — these customers drive 80% of regional overtime)

| Rank | Code | Name | Locations | Employees | Hours | OT Hrs | OT % | NBOT | FTE REQ | FTE Needed | Cum-OT % | Pareto |
|:----:|:-------------:|:--------------|----------:|----------:|------:|---------:|-----:|:----:|----:|---------:|---------:|:------:|
{% for cust in customers -%}
| {{ cust.ot_rank }} | {{ cust.customer_code }} | {{ cust.customer_name }} | {{ cust.location_count }} | {{ cust.employee_count }} | {{ cust.total_hours|round(1) }} | {{ cust.ot_hours|round(1) }} | {{ cust.ot_percentage }}% | {{ cust.nbot_icon }} | {{ cust.fte_needed }} | {{ cust.variance }} | {{ cust.ot_cum_pct }}% | {% if cust.pareto_80_flag == 'Yes' %}☑️{% endif %} |
{% endfor %}

**📊 Pareto Analysis:** The {{ pareto_count }} customer{{ 's' if pareto_count != 1 else '' }} marked with ☑️ account for 80% of all regional overtime. Regional Manager should prioritize resources here for maximum ROI.

---

{% if training_incomplete_by_customer|length > 0 %}
## ⚠️ TRAINING COMPLIANCE ISSUES

### General Onboarding Training NOT Completed: ➖➤ {{ training_incomplete_by_customer|length }} Customer{{ 's' if training_incomplete_by_customer|length != 1 else '' }}
📌 **Action Required** ➡️ Deploy regional training support

{% for cust_name, emp_names in training_incomplete_by_customer.items() -%}
- **{{ cust_name }}** — {{ emp_names|length }} employee{{ 's' if emp_names|length != 1 else '' }}
  - Employees: {{ emp_names|join(', ') }}
{% endfor %}
---
{% endif %}

## 👥 WORKFORCE UTILIZATION SUMMARY (REGION)

| Utilization Status | Employee Count | % of Workforce |
|:-------------------|---------------:|---------------:|
| 🟢 Optimal (36-40 hrs) | {{ util_optimal }} | {{ util_optimal_pct }}% |
| 🟡 Sub-Optimal (25-35 hrs) | {{ util_suboptimal }} | {{ "%.1f"|format((util_suboptimal / total_employees * 100) if total_employees > 0 else 0) }}% |
| 🔴 Under-utilized (<25 hrs) | {{ util_under_25 }} | {{ util_under_25_pct }}% |
| 🔴 Over-utilized (>40 hrs) | {{ util_over_40 }} | {{ util_over_40_pct }}% |

---

## 🎓 TRAINING COMPLIANCE (REGION)

| Training Status | Employee Count | % of Workforce |
|:----------------|---------------:|---------------:|
| ✅ Completed | {{ training_complete }} | {{ training_complete_pct }}% |
| ⚠️ Not Completed | {{ training_incomplete }} | {{ training_incomplete_pct }}% |

{% if training_incomplete > 0 -%}
**Action Required:** {{ training_incomplete }} employee{{ 's' if training_incomplete != 1 else '' }} across {{ training_incomplete_by_customer|length }} customer{{ 's' if training_incomplete_by_customer|length != 1 else '' }} need General Onboarding completion
{% endif %}

---

## 🔍 TENURE RISK ANALYSIS (REGION)

| Tenure Status | Employee Count | % of Workforce |
|:--------------|---------------:|---------------:|
| 🔴 Critical (≤90 days) | {{ tenure_critical }} | {{ tenure_critical_pct }}% |
| 🟠 High (91-179 days) | {{ tenure_high }} | {{ tenure_high_pct }}% |
| 🟡 Medium (180-365 days) | {{ (total_employees - tenure_critical - tenure_high - tenure_low) }} | {{ "%.1f"|format(((total_employees - tenure_critical - tenure_high - tenure_low) / total_employees * 100) if total_employees > 0 else 0) }}% |
| 🟢 Low (>365 days) | {{ tenure_low }} | {{ "%.1f"|format((tenure_low / total_employees * 100) if total_employees > 0 else 0) }}% |

---

## 🧾 REGION HEALTH SUMMARY

✅ **Total regional capacity:** {{ total_hours }} hours across {{ total_employees }} employees at {{ total_locations }} locations  
✅ **Regional OT Status:** {{ overall_nbot }} ({{ overall_ot_pct }}% overtime rate)  
📊 **FTE Alignment:** {{ total_fte_needed }} FTE needed — {{ capacity_status }}  
📊 **Pareto Focus:** {{ pareto_count }} customer{{ 's' if pareto_count != 1 else '' }} ({{ pareto_pct }}%) account for 80% of regional OT — {{ pareto_ot_hours }} hours  
🏢 **Customer Portfolio:** {{ total_customers }} active customers across the region  
{% if high_risk|length == 0 and medium_risk|length == 0 -%}
🎯 **Performance:** All customers operating within healthy parameters  
{% endif %}
{% if training_complete == total_employees -%}
✅ **Training Compliance:** 100% — All scheduled employees trained  
{% endif %}
{% if tenure_low > total_employees * 0.5 -%}
✅ **Workforce Stability:** Strong regional retention with {{ "%.1f"|format((tenure_low / total_employees * 100) if total_employees > 0 else 0) }}% tenured employees  
{% endif %}
""")
    
    return template.render(**context)