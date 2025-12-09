"""Pareto Optimization Report - Multi-site Pareto analysis with detailed optimization cards."""

from typing import List, Dict, Optional
from ..common import (
    BQ_DATA_PROJECT_ID,
    BQ_DATASET_ID,
    execute_query,
    get_nbot_status,
    get_nbot_icon,
    get_fte_hours,
    calculate_ot_for_sites,
)
from .optimization_card import generate_optimization_card


def generate_pareto_optimization(
    start_date: str,
    end_date: str,
    mode: str,
    customer_code: Optional[int] = None,
    region: Optional[str] = None,
    selected_locations: Optional[List[str]] = None
) -> str:
    """
    Pareto analysis ALWAYS by SITE.
    
    Modes:
        - 'customer': Analyze all sites within a customer
        - 'region': Analyze all sites across all customers in a region
    
    Output:
        1. Pareto Analysis Summary (all sites in Pareto 80%)
        2. Full Optimization Cards for selected sites
    """
    
    if mode == 'customer':
        return _analyze_sites_for_customer(
            customer_code, start_date, end_date, selected_locations
        )
    elif mode == 'region':
        return _analyze_sites_for_region(
            region, start_date, end_date, selected_locations
        )
    else:
        return f"Invalid mode: {mode}. Must be 'customer' or 'region'"


def _analyze_sites_for_customer(
    customer_code: int,
    start_date: str,
    end_date: str,
    selected_locations: Optional[List[str]] = None
) -> str:
    """Analyze all SITES within a customer using correct OT calculations."""
    
    # ✅ FIX: Apply same CONCAT fix to customer_code
    customer_code_filter = f"CONCAT('', customer_code) = '{customer_code}'"
    
    sql = f"""
SELECT
  location_id,
  state,
  ANY_VALUE(site_manager) AS site_manager,
  ANY_VALUE(customer_name) AS customer_name,
  ANY_VALUE(region) AS region,
  COUNT(DISTINCT employee_id) AS employee_count,
  SUM(scheduled_hours) AS total_hours,
  CASE 
    WHEN state = 'CA' THEN CAST(CEILING(SUM(scheduled_hours) / 32) AS INT64)
    ELSE CAST(CEILING(SUM(scheduled_hours) / 36) AS INT64)
  END AS fte_needed
FROM `{BQ_DATA_PROJECT_ID}.{BQ_DATASET_ID}.APEX_NWS`
WHERE {customer_code_filter}
  AND scheduled_date BETWEEN '{start_date}' AND '{end_date}'
GROUP BY location_id, state
"""
    
    try:
        results = execute_query(sql)
    except Exception as e:
        return str(e)
    
    if not results:
        return f"No data found for customer_code={customer_code}, dates={start_date} to {end_date}"
    
    # Store ALL sites before filtering
    all_sites = results.copy()
    
    # Get daily hours for OT calculation (only for this customer) - WITH MIDNIGHT SPLITTING
    daily_sql = f"""
WITH ShiftSegments AS (
  SELECT
    location_id,
    state,
    employee_id,
    scheduled_date,
    start,
    `end`,
    scheduled_hours,
    
    -- Convert "06:00a" / "02:00p" format to TIME
    PARSE_TIME('%I:%M%p', REPLACE(REPLACE(start, 'a', 'AM'), 'p', 'PM')) AS start_time,
    PARSE_TIME('%I:%M%p', REPLACE(REPLACE(`end`, 'a', 'AM'), 'p', 'PM')) AS end_time,
    
    -- Check if shift crosses midnight
    CASE 
      WHEN PARSE_TIME('%I:%M%p', REPLACE(REPLACE(start, 'a', 'AM'), 'p', 'PM')) >= 
           PARSE_TIME('%I:%M%p', REPLACE(REPLACE(`end`, 'a', 'AM'), 'p', 'PM')) 
      THEN TRUE 
      ELSE FALSE 
    END AS crosses_midnight,
    
    -- Calculate hours on next date FIRST
    CASE
      WHEN PARSE_TIME('%I:%M%p', REPLACE(REPLACE(start, 'a', 'AM'), 'p', 'PM')) >= 
           PARSE_TIME('%I:%M%p', REPLACE(REPLACE(`end`, 'a', 'AM'), 'p', 'PM')) THEN
        EXTRACT(HOUR FROM PARSE_TIME('%I:%M%p', REPLACE(REPLACE(`end`, 'a', 'AM'), 'p', 'PM'))) +
        EXTRACT(MINUTE FROM PARSE_TIME('%I:%M%p', REPLACE(REPLACE(`end`, 'a', 'AM'), 'p', 'PM'))) / 60.0
      ELSE 
        0.0
    END AS hours_on_next_date,
    
    -- Calculate hours on scheduled_date
    CASE
      WHEN PARSE_TIME('%I:%M%p', REPLACE(REPLACE(start, 'a', 'AM'), 'p', 'PM')) >= 
           PARSE_TIME('%I:%M%p', REPLACE(REPLACE(`end`, 'a', 'AM'), 'p', 'PM')) THEN
        scheduled_hours - (
          EXTRACT(HOUR FROM PARSE_TIME('%I:%M%p', REPLACE(REPLACE(`end`, 'a', 'AM'), 'p', 'PM'))) +
          EXTRACT(MINUTE FROM PARSE_TIME('%I:%M%p', REPLACE(REPLACE(`end`, 'a', 'AM'), 'p', 'PM'))) / 60.0
        )
      ELSE 
        scheduled_hours
    END AS hours_on_scheduled_date
    
  FROM `{BQ_DATA_PROJECT_ID}.{BQ_DATASET_ID}.APEX_NWS`
  WHERE {customer_code_filter}
    AND scheduled_date BETWEEN '{start_date}' AND '{end_date}'
),
ExpandedShifts AS (
  SELECT
    location_id,
    state,
    employee_id,
    scheduled_date AS workday_date,
    hours_on_scheduled_date AS daily_hours
  FROM ShiftSegments
  WHERE hours_on_scheduled_date > 0
  
  UNION ALL
  
  SELECT
    location_id,
    state,
    employee_id,
    DATE_ADD(scheduled_date, INTERVAL 1 DAY) AS workday_date,
    hours_on_next_date AS daily_hours
  FROM ShiftSegments
  WHERE crosses_midnight AND hours_on_next_date > 0
)
SELECT
  location_id,
  state,
  employee_id,
  workday_date AS scheduled_date,
  SUM(daily_hours) AS daily_hours
FROM ExpandedShifts
GROUP BY location_id, state, employee_id, workday_date
ORDER BY location_id, state, employee_id, workday_date
"""
    
    try:
        daily_rows = execute_query(daily_sql)
    except Exception as e:
        return f"Daily detail query failed: {str(e)}"
    
    # Calculate OT using optimization card logic
    calculate_ot_for_sites(results, daily_rows)
    calculate_ot_for_sites(all_sites, daily_rows)
    
    # Perform Pareto analysis
    pareto_sites, total_sites = _perform_pareto_site_analysis(results)
    
    # Generate combined report
    return _generate_pareto_optimization_report(
        pareto_sites=pareto_sites,
        total_sites=total_sites,
        all_sites=all_sites,
        selected_locations=selected_locations,
        start_date=start_date,
        end_date=end_date,
        mode='customer',
        customer_code=customer_code,
        region=None
    )


def _analyze_sites_for_region(
    region: str,
    start_date: str,
    end_date: str,
    selected_locations: Optional[List[str]] = None
) -> str:
    """Analyze all SITES across all customers in a region."""
    
    sql = f"""
SELECT
  location_id,
  state,
  ANY_VALUE(customer_code) AS customer_code,
  ANY_VALUE(customer_name) AS customer_name,
  ANY_VALUE(site_manager) AS site_manager,
  ANY_VALUE(region) AS region,
  COUNT(DISTINCT employee_id) AS employee_count,
  SUM(scheduled_hours) AS total_hours,
  CASE 
    WHEN state = 'CA' THEN CAST(CEILING(SUM(scheduled_hours) / 32) AS INT64)
    ELSE CAST(CEILING(SUM(scheduled_hours) / 36) AS INT64)
  END AS fte_needed
FROM `{BQ_DATA_PROJECT_ID}.{BQ_DATASET_ID}.APEX_NWS`
WHERE region = '{region}'
  AND scheduled_date BETWEEN '{start_date}' AND '{end_date}'
GROUP BY location_id, state
"""
    
    try:
        results = execute_query(sql)
    except Exception as e:
        return str(e)
    
    if not results:
        return f"No data found for region={region}, dates={start_date} to {end_date}"
    
    # Store ALL sites before filtering
    all_sites = results.copy()
    
    # Get daily hours for OT calculation (only for this region) - WITH MIDNIGHT SPLITTING
    daily_sql = f"""
WITH ShiftSegments AS (
  SELECT
    location_id,
    state,
    employee_id,
    scheduled_date,
    start,
    `end`,
    scheduled_hours,
    
    -- Convert "06:00a" / "02:00p" format to TIME
    PARSE_TIME('%I:%M%p', REPLACE(REPLACE(start, 'a', 'AM'), 'p', 'PM')) AS start_time,
    PARSE_TIME('%I:%M%p', REPLACE(REPLACE(`end`, 'a', 'AM'), 'p', 'PM')) AS end_time,
    
    -- Check if shift crosses midnight
    CASE 
      WHEN PARSE_TIME('%I:%M%p', REPLACE(REPLACE(start, 'a', 'AM'), 'p', 'PM')) >= 
           PARSE_TIME('%I:%M%p', REPLACE(REPLACE(`end`, 'a', 'AM'), 'p', 'PM')) 
      THEN TRUE 
      ELSE FALSE 
    END AS crosses_midnight,
    
    -- Calculate hours on next date FIRST
    CASE
      WHEN PARSE_TIME('%I:%M%p', REPLACE(REPLACE(start, 'a', 'AM'), 'p', 'PM')) >= 
           PARSE_TIME('%I:%M%p', REPLACE(REPLACE(`end`, 'a', 'AM'), 'p', 'PM')) THEN
        EXTRACT(HOUR FROM PARSE_TIME('%I:%M%p', REPLACE(REPLACE(`end`, 'a', 'AM'), 'p', 'PM'))) +
        EXTRACT(MINUTE FROM PARSE_TIME('%I:%M%p', REPLACE(REPLACE(`end`, 'a', 'AM'), 'p', 'PM'))) / 60.0
      ELSE 
        0.0
    END AS hours_on_next_date,
    
    -- Calculate hours on scheduled_date
    CASE
      WHEN PARSE_TIME('%I:%M%p', REPLACE(REPLACE(start, 'a', 'AM'), 'p', 'PM')) >= 
           PARSE_TIME('%I:%M%p', REPLACE(REPLACE(`end`, 'a', 'AM'), 'p', 'PM')) THEN
        scheduled_hours - (
          EXTRACT(HOUR FROM PARSE_TIME('%I:%M%p', REPLACE(REPLACE(`end`, 'a', 'AM'), 'p', 'PM'))) +
          EXTRACT(MINUTE FROM PARSE_TIME('%I:%M%p', REPLACE(REPLACE(`end`, 'a', 'AM'), 'p', 'PM'))) / 60.0
        )
      ELSE 
        scheduled_hours
    END AS hours_on_scheduled_date
    
  FROM `{BQ_DATA_PROJECT_ID}.{BQ_DATASET_ID}.APEX_NWS`
  WHERE region = '{region}'
    AND scheduled_date BETWEEN '{start_date}' AND '{end_date}'
),
ExpandedShifts AS (
  SELECT
    location_id,
    state,
    employee_id,
    scheduled_date AS workday_date,
    hours_on_scheduled_date AS daily_hours
  FROM ShiftSegments
  WHERE hours_on_scheduled_date > 0
  
  UNION ALL
  
  SELECT
    location_id,
    state,
    employee_id,
    DATE_ADD(scheduled_date, INTERVAL 1 DAY) AS workday_date,
    hours_on_next_date AS daily_hours
  FROM ShiftSegments
  WHERE crosses_midnight AND hours_on_next_date > 0
)
SELECT
  location_id,
  state,
  employee_id,
  workday_date AS scheduled_date,
  SUM(daily_hours) AS daily_hours
FROM ExpandedShifts
GROUP BY location_id, state, employee_id, workday_date
ORDER BY location_id, state, employee_id, workday_date
"""
    
    try:
        daily_rows = execute_query(daily_sql)
    except Exception as e:
        return f"Daily detail query failed: {str(e)}"
    
    # Calculate OT using optimization card logic
    calculate_ot_for_sites(results, daily_rows)
    calculate_ot_for_sites(all_sites, daily_rows)
    
    # Perform Pareto analysis
    pareto_sites, total_sites = _perform_pareto_site_analysis(results)
    
    # Generate combined report
    return _generate_pareto_optimization_report(
        pareto_sites=pareto_sites,
        total_sites=total_sites,
        all_sites=all_sites,
        selected_locations=selected_locations,
        start_date=start_date,
        end_date=end_date,
        mode='region',
        customer_code=None,
        region=region
    )


def _perform_pareto_site_analysis(results: List[Dict]) -> tuple:
    """Perform Pareto 80/20 analysis on SITES."""
    
    # Sort by total OT exposure
    results_sorted = sorted(
        results, 
        key=lambda x: float(x.get('total_ot_exposure', 0) or 0), 
        reverse=True
    )
    
    total_ot_all = sum(float(r.get('total_ot_exposure', 0) or 0) for r in results_sorted)
    
    # Calculate Pareto 80%
    cumulative_ot = 0
    pareto_sites = []
    
    for idx, site in enumerate(results_sorted, 1):
        ot_exposure = float(site.get('total_ot_exposure', 0) or 0)
        cumulative_ot += ot_exposure
        site['ot_rank'] = idx
        site['ot_cum_pct'] = round((cumulative_ot / total_ot_all * 100), 1) if total_ot_all > 0 else 0
        
        # Add NBOT status
        ot_pct = site.get('ot_percentage', 0) or 0
        if ot_pct < 1:
            site['nbot_icon'] = '🟢'
            site['nbot_text'] = 'GREEN'
        elif ot_pct < 3:
            site['nbot_icon'] = '🟡'
            site['nbot_text'] = 'YELLOW'
        else:
            site['nbot_icon'] = '🔴'
            site['nbot_text'] = 'RED'
        
        if site['ot_cum_pct'] <= 80:
            pareto_sites.append(site)
    
    return pareto_sites, len(results_sorted)

def _generate_pareto_optimization_report(
    pareto_sites: List[Dict],
    total_sites: int,
    all_sites: List[Dict],
    selected_locations: Optional[List[str]],
    start_date: str,
    end_date: str,
    mode: str,
    customer_code: Optional[int],
    region: Optional[str]
) -> str:
    """Generate comprehensive Pareto Optimization Plan with Site Cards."""
    
    pareto_count = len(pareto_sites)
    
    # Header info
    if mode == 'customer':
        customer_name = pareto_sites[0]['customer_name'] if pareto_sites else "Unknown"
        header_line = f"**Customer:** {customer_name} (Code: {customer_code})"
        scope = f"All sites for Customer {customer_code}"
    else:
        header_line = f"**Region:** {region}"
        scope = f"All sites across all customers in {region}"
    
    # Calculate OVERALL metrics (all sites in scope)
    overall_total_hours = sum(float(s.get('total_hours', 0) or 0) for s in all_sites)
    overall_total_ot = sum(float(s.get('total_ot_exposure', 0) or 0) for s in all_sites)
    overall_weekly_ot = sum(float(s.get('weekly_ot_hours', 0) or 0) for s in all_sites)
    overall_daily_ot = sum(float(s.get('daily_ot_hours', 0) or 0) for s in all_sites)
    overall_double_time = sum(float(s.get('double_time_hours', 0) or 0) for s in all_sites)
    overall_ot_pct = round((overall_total_ot / overall_total_hours * 100), 1) if overall_total_hours > 0 else 0.0
    overall_employees = sum(int(s.get('employee_count', 0) or 0) for s in all_sites)
    overall_fte_needed = sum(int(s.get('fte_needed', 0) or 0) for s in all_sites)
    avg_hours = round(overall_total_hours / overall_employees, 1) if overall_employees > 0 else 0.0
    
    # Overall NBOT status
    overall_nbot, overall_nbot_text = get_nbot_status(overall_ot_pct)
    
    # Calculate PARETO metrics (Pareto 80% sites)
    pareto_ot_hours = sum(float(s.get('total_ot_exposure', 0) or 0) for s in pareto_sites)
    pareto_weekly_ot = sum(float(s.get('weekly_ot_hours', 0) or 0) for s in pareto_sites)
    pareto_daily_ot = sum(float(s.get('daily_ot_hours', 0) or 0) for s in pareto_sites)
    pareto_double_time = sum(float(s.get('double_time_hours', 0) or 0) for s in pareto_sites)
    pareto_total_hours = sum(float(s.get('total_hours', 0) or 0) for s in pareto_sites)
    pareto_employees = sum(int(s.get('employee_count', 0) or 0) for s in pareto_sites)
    pareto_ot_pct = round((pareto_ot_hours / pareto_total_hours * 100), 1) if pareto_total_hours > 0 else 0.0
    
    # Determine which sites to include
    if selected_locations:
        pareto_site_ids = [str(s['location_id']) for s in pareto_sites]
        valid_selections = [loc_id for loc_id in selected_locations if loc_id in pareto_site_ids]
        invalid_selections = [loc_id for loc_id in selected_locations if loc_id not in pareto_site_ids]
        
        if not valid_selections:
            return (
                f"❌ **Error:** None of the selected sites are in the Pareto 80% list.\n\n"
                f"**Selected:** {', '.join(selected_locations)}\n"
                f"**Available Pareto sites:** {', '.join(pareto_site_ids[:20])}"
                f"{'...' if len(pareto_site_ids) > 20 else ''}\n\n"
                f"Please re-run without selections to see the full Pareto analysis."
            )
        
        selected_sites = [s for s in pareto_sites if str(s['location_id']) in valid_selections]
        selected_count = len(selected_sites)
        
        # Calculate selected totals
        selected_ot = sum(float(s.get('total_ot_exposure', 0) or 0) for s in selected_sites)
        selected_weekly = sum(float(s.get('weekly_ot_hours', 0) or 0) for s in selected_sites)
        selected_daily = sum(float(s.get('daily_ot_hours', 0) or 0) for s in selected_sites)
        selected_double = sum(float(s.get('double_time_hours', 0) or 0) for s in selected_sites)
        selected_hours = sum(float(s.get('total_hours', 0) or 0) for s in selected_sites)
        selected_employees = sum(int(s.get('employee_count', 0) or 0) for s in selected_sites)
        selected_ot_pct = round((selected_ot / selected_hours * 100), 1) if selected_hours > 0 else 0.0
    else:
        # No selection provided - show prompt if > 10 sites
        if pareto_count > 10:
            selected_sites = []
            selected_count = 0
            selected_ot = 0
            selected_weekly = 0
            selected_daily = 0
            selected_double = 0
            selected_hours = 0
            selected_employees = 0
            selected_ot_pct = 0.0
        else:
            # Auto-include all if <= 10 sites
            selected_sites = pareto_sites
            selected_count = pareto_count
            selected_ot = pareto_ot_hours
            selected_weekly = pareto_weekly_ot
            selected_daily = pareto_daily_ot
            selected_double = pareto_double_time
            selected_hours = pareto_total_hours
            selected_employees = pareto_employees
            selected_ot_pct = pareto_ot_pct
    
    # Start building report
    markdown = f"""
# 🌐 Excellence Performance Center 🌐
## NBOT Optimization & Operational Health Report
{header_line} | **Week:** {start_date} – {end_date}

---

## 📋 EXECUTIVE SUMMARY

{overall_nbot} **Overall Status** — {scope} OT at {overall_ot_pct}% {'exceeds' if overall_ot_pct >= 3 else 'approaching' if overall_ot_pct >= 1 else 'below'} threshold.

**Pareto Analysis:** {pareto_count} site{'s' if pareto_count != 1 else ''} ({round(pareto_count/total_sites*100, 1)}%) drive 80% of OT ({pareto_ot_hours:.2f} hours). **Action:** Focus optimization efforts on these high-impact sites.
"""
    
    if selected_count > 0:
        markdown += f"""
**Sites Selected for Optimization:** {selected_count} site{'s' if selected_count != 1 else ''} included in this detailed analysis ({selected_ot:.2f} total OT hours).
"""
    
    markdown += """

---

### 📊 KEY FINDINGS

| Metric | Value | Status |
|:-------|:------|:-------|
"""
    
    if mode == 'region':
        # Count unique customers
        unique_customers = len(set(s.get('customer_code') for s in all_sites if s.get('customer_code')))
        markdown += f"| 🧑‍💼🧑‍💼 Active Customers | {unique_customers} | Across region |\n"
    
    markdown += f"""| 📍 Total Locations | {total_sites} | {scope} |
| 👮 Total Employees | {overall_employees} | {overall_total_hours:.2f} hrs |
| ⚠️ Overall OT | {overall_ot_pct}% | {overall_nbot_text} |
| 📈 Sites in Pareto 80% | {pareto_count} sites | {round(pareto_count/total_sites*100, 1)}% of portfolio |
| 👮👮 Capacity (FTE) Needed | {overall_fte_needed} FTE | 36 hrs/FTE standard |
"""
    
    if selected_count > 0:
        markdown += f"| 🎯 Sites in This Report | {selected_count} sites | Selected for detailed analysis |\n"
    
    markdown += """

**Analysis:**
"""
    
    markdown += f"- **Overall OT Performance:** {overall_ot_pct}% — {overall_nbot_text}\n"
    markdown += f"- **OT Concentration:** {pareto_count} site{'s' if pareto_count != 1 else ''} ({round(pareto_count/total_sites*100, 1)}%) account for 80% of overtime ({pareto_ot_hours:.2f} hours)\n"
    markdown += f"- **Total Portfolio:** {total_sites} sites with {overall_employees} employees\n"
    markdown += f"- **Total Hours Scheduled:** {overall_total_hours:.2f} hours across all sites\n"
    
    if selected_count > 0:
        markdown += f"- **Selected Sites Impact:** {selected_count} sites representing {selected_ot:.2f} OT hours ({round(selected_ot/overall_total_ot*100, 1) if overall_total_ot > 0 else 0}% of total OT)\n"
    
    markdown += f"""

---

## 📊 OVERALL METRICS

| Metric | Value |
|:----------------------|----------:|
| Total Sites | {total_sites} |
| Total Employees | {overall_employees} |
| Total Weekly Hours | {overall_total_hours:.2f} |
| Average Hours per Employee | {avg_hours} |
| Total Scheduled OT | {overall_total_ot:.2f} |
| ├─ Weekly OT | {overall_weekly_ot:.2f} |
| ├─ Daily OT | {overall_daily_ot:.2f} |
| └─ Double Time | {overall_double_time:.2f} |
| Overall OT % | {overall_ot_pct}% |
| Overall NBOT Status | {overall_nbot} |
| Total FTE Needed (36 hrs) | {overall_fte_needed} |

---

## 📊 PARETO METRICS | 80%

| Metric | Value |
|:----------------------|----------:|
| Sites in Pareto 80% | {pareto_count} ({round(pareto_count/total_sites*100, 1)}% of sites) |
| Total Employees | {pareto_employees} |
| Total Hours | {pareto_total_hours:.2f} |
| Total OT Exposure | {pareto_ot_hours:.2f} ({round(pareto_ot_hours/overall_total_ot*100, 1) if overall_total_ot > 0 else 0}% of total OT) |
| ├─ Weekly OT | {pareto_weekly_ot:.2f} |
| ├─ Daily OT | {pareto_daily_ot:.2f} |
| └─ Double Time | {pareto_double_time:.2f} |
| Pareto OT % | {pareto_ot_pct}% |
"""
    
    if selected_count > 0:
        markdown += f"""

---

## 📊 SELECTED SITES METRICS FOR OPTIMIZATION

| Metric | Value |
|:----------------------|----------:|
| Sites Included | {selected_count} ({round(selected_count/pareto_count*100, 1)}% of Pareto sites) |
| Total Employees | {selected_employees} |
| Total Hours | {selected_hours:.2f} |
| Total OT Exposure | {selected_ot:.2f} ({round(selected_ot/pareto_ot_hours*100, 1) if pareto_ot_hours > 0 else 0}% of Pareto OT) |
| ├─ Weekly OT | {selected_weekly:.2f} |
| ├─ Daily OT | {selected_daily:.2f} |
| └─ Double Time | {selected_double:.2f} |
| Selected Sites OT % | {selected_ot_pct}% |
"""
    
    regular_hours = pareto_total_hours - pareto_ot_hours
    regular_pct = 100 - pareto_ot_pct
    ot_visual = '██████░░░░░░░░░░░░░░' if pareto_ot_pct >= 3 else '███░░░░░░░░░░░░░░░░░' if pareto_ot_pct >= 1 else '█░░░░░░░░░░░░░░░░░░░'
    
    markdown += f"""

---

## 📅 HOURS BREAKDOWN (SELECTED PARETO SITES)

| Category | Hours | % of Total | Visual Impact |
|:---------|------:|:----------:|:--------------|
| Regular Hours | {regular_hours:.2f} | {regular_pct:.1f}% | ████████████████████ |
| Total OT Exposure | {pareto_ot_hours:.2f} | {pareto_ot_pct:.1f}% | {ot_visual} |

**💡 Key Insight:** {pareto_count} site{'s' if pareto_count != 1 else ''} ({round(pareto_count/total_sites*100, 1)}%) drive 80% of OT — Focused intervention will yield maximum ROI.

---

## 📍 SITES IN PARETO | 80%

**Status Thresholds:** 🔴 High (≥3%) | 🟡 Medium (1-3%) | 🟢 Low (<1%)

"""
    
    # ✅ FIXED: Removed City column from tables
    if mode == 'region':
        markdown += """| Rank | Site | Customer | State | Region | Employees | Total Hours | OT Hours | OT % | Cum-OT % | NBOT | Included |
|:----:|:-----|:---------|:------|:-------|----------:|------------:|---------:|-----:|---------:|:----:|:--------:|
"""
        for site in pareto_sites:
            included = "✅" if selected_sites and str(site['location_id']) in [str(s['location_id']) for s in selected_sites] else "❌"
            markdown += (
                f"| {site['ot_rank']} "
                f"| {site['location_id']} "
                f"| {site.get('customer_name', 'N/A')} "
                f"| {site.get('state', 'N/A')} "
                f"| {site.get('region', 'N/A')} "
                f"| {site.get('employee_count', 0)} "
                f"| {site.get('total_hours', 0):.0f} "
                f"| {site.get('total_ot_exposure', 0):.1f} "
                f"| {site.get('ot_percentage', 0):.1f}% "
                f"| {site.get('ot_cum_pct', 0):.1f}% "
                f"| {site['nbot_icon']} "
                f"| {included} |\n"
            )
    else:
        markdown += """| Rank | Site | State | Region | Employees | Total Hours | OT Hours | OT % | Cum-OT % | NBOT | Included IN OPTIMIZATION PLAN |
|:----:|:-----|:------|:-------|----------:|------------:|---------:|-----:|---------:|:----:|:--------:|
"""
        for site in pareto_sites:
            included = "✅" if selected_sites and str(site['location_id']) in [str(s['location_id']) for s in selected_sites] else "❌"
            markdown += (
                f"| {site['ot_rank']} "
                f"| {site['location_id']} "
                f"| {site.get('state', 'N/A')} "
                f"| {site.get('region', 'N/A')} "
                f"| {site.get('employee_count', 0)} "
                f"| {site.get('total_hours', 0):.0f} "
                f"| {site.get('total_ot_exposure', 0):.1f} "
                f"| {site.get('ot_percentage', 0):.1f}% "
                f"| {site.get('ot_cum_pct', 0):.1f}% "
                f"| {site['nbot_icon']} "
                f"| {included} |\n"
            )
    
    markdown += "\n**Note:** Sites marked ✅ have detailed optimization cards below.\n\n**📊 Pareto Analysis:** Sites in this table represent 80% of all OT hours. Focus optimization on these high-impact sites.\n\n---\n\n"

    # If no sites selected and > 10 pareto sites, show selection prompt
    if not selected_sites and pareto_count > 10:
        site_ids = [str(s['location_id']) for s in pareto_sites]
        top_10 = site_ids[:10]
        red_sites = [str(s['location_id']) for s in pareto_sites if s['nbot_text'] == 'RED']
        
        markdown += f"""
## 🎯 SITE SELECTION REQUIRED

There are {pareto_count} sites in the Pareto 80%. Please select which to include in detailed optimization cards.

**Selection Options:**

1. **Top 10 by OT Hours** (Recommended): {', '.join(top_10)}
2. **All RED Status** ({len(red_sites)} sites): {', '.join(red_sites[:10])}{'...' if len(red_sites) > 10 else ''}
3. **Custom Selection**: Specify site IDs from the table above

**To proceed, re-run with:**
```python
generate_standard_report(
    report_id='pareto_optimization',
    {'customer_code=' + str(customer_code) if mode == 'customer' else "region='" + region + "'"},
    start_date='{start_date}',
    end_date='{end_date}',
    analysis_mode='{mode}',
    selected_locations=['1001', '1002', '1005']  # Your site selection
)
```
"""
        return markdown
    
    # Generate detailed optimization cards for selected sites
    if selected_sites:
        markdown += """


"""
        
        for idx, site in enumerate(selected_sites, 1):
            site_id = site['location_id']
            
            markdown += f"""
---

## 📍 SITE {idx} OF {selected_count}: Location {site_id}

### Strategic Context
- **Rank:** #{site['ot_rank']} in Pareto analysis (out of {pareto_count} Pareto sites)
"""
            if mode == 'region':
                markdown += f"- **Customer:** {site.get('customer_name', 'N/A')}\n"
            
            # ✅ FIXED: Removed city reference
            markdown += f"""- **State:** {site.get('state', 'N/A')} | **Region:** {site.get('region', 'N/A')} | **Site Manager:** {site.get('site_manager', 'N/A')}
- **OT Hours:** {site.get('total_ot_exposure', 0):.1f} ({round(site.get('total_ot_exposure', 0) / pareto_ot_hours * 100, 1) if pareto_ot_hours > 0 else 0}% of Pareto OT)
- **OT %:** {site.get('ot_percentage', 0):.1f}% {site['nbot_icon']} {site['nbot_text']}
- **Cumulative OT Impact:** {site.get('ot_cum_pct', 0):.1f}% (this site + all sites ranked above)

---

"""
            
            # Generate full optimization card for this site
            try:
                # Determine customer_code for this site
                if mode == 'region':
                    site_customer_code = site.get('customer_code')
                else:
                    site_customer_code = customer_code
                
                # Get state for composite key
                site_state = site.get('state', 'N/A')
                
                card = generate_optimization_card(
                    site_customer_code,
                    site_id,
                    site_state,
                    start_date,
                    end_date
                )
                markdown += card
            except Exception as e:
                markdown += f"*Error generating detailed card: {str(e)}*\n\n"
            
            markdown += "\n\n═══════════════════════════════════════════════════════════\n"
        
        markdown += """
END OF REPORT
═══════════════════════════════════════════════════════════
"""
    
    return markdown