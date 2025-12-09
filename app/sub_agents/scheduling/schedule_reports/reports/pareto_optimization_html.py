"""Pareto Optimization Report - HTML version with interactive features."""
"""Pareto Optimization Report - HTML version with interactive features."""

from typing import List, Dict, Optional
from datetime import datetime

# Import HTML component builders  
from ..common.html_components import (
    get_industrial_chrome_css,
    get_javascript,
    build_header,
    build_metadata_cards,
    build_navigation_buttons,
    build_status_badge,
    build_info_box,
    build_table_with_controls,
)

# Import data functions
from ..common import (
    BQ_DATA_PROJECT_ID,
    BQ_DATASET_ID,
    execute_query,
    get_nbot_status,
    calculate_ot_for_sites,
)
from ..common.ot_calculations import calculate_employee_ot


def generate_pareto_optimization_html(
    start_date: str,
    end_date: str,
    mode: str,
    customer_code: Optional[int] = None,
    region: Optional[str] = None,
    selected_locations: Optional[List[str]] = None
) -> str:
    """
    Generate Pareto Optimization Report in HTML format with interactive features.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        mode: 'customer' or 'region'
        customer_code: Customer code (required for customer mode)
        region: Region name (required for region mode)
        selected_locations: Optional list of location IDs to include in detailed cards
    
    Returns:
        Complete HTML document as string
    """
    
    if mode == 'customer':
        return _generate_customer_report_html(
            customer_code, start_date, end_date, selected_locations
        )
    elif mode == 'region':
        return _generate_region_report_html(
            region, start_date, end_date, selected_locations
        )
    else:
        return f"<html><body><h1>Error</h1><p>Invalid mode: {mode}</p></body></html>"


def _generate_customer_report_html(
    customer_code: int,
    start_date: str,
    end_date: str,
    selected_locations: Optional[List[str]] = None
) -> str:
    """Generate customer-level Pareto report in HTML."""
    
    # Query data
    customer_code_filter = f"CONCAT('', customer_code) = '{customer_code}'"
    
    sql = f"""
SELECT
  location_id,
  state,
  ANY_VALUE(customer_code) AS customer_code,
  ANY_VALUE(city) AS city,
  ANY_VALUE(location_name) AS location_name,
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
        return f"<html><body><h1>Error</h1><p>{str(e)}</p></body></html>"
    
    if not results:
        return f"<html><body><h1>No Data</h1><p>No data found for customer_code={customer_code}</p></body></html>"
    
    # Store all sites
    all_sites = results.copy()
    
    # Get daily hours for OT calculation - WITH MIDNIGHT SPLITTING
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
    
    PARSE_TIME('%I:%M%p', REPLACE(REPLACE(start, 'a', 'AM'), 'p', 'PM')) AS start_time,
    PARSE_TIME('%I:%M%p', REPLACE(REPLACE(`end`, 'a', 'AM'), 'p', 'PM')) AS end_time,
    
    CASE 
      WHEN PARSE_TIME('%I:%M%p', REPLACE(REPLACE(start, 'a', 'AM'), 'p', 'PM')) >= 
           PARSE_TIME('%I:%M%p', REPLACE(REPLACE(`end`, 'a', 'AM'), 'p', 'PM')) 
      THEN TRUE 
      ELSE FALSE 
    END AS crosses_midnight,
    
    CASE
      WHEN PARSE_TIME('%I:%M%p', REPLACE(REPLACE(start, 'a', 'AM'), 'p', 'PM')) >= 
           PARSE_TIME('%I:%M%p', REPLACE(REPLACE(`end`, 'a', 'AM'), 'p', 'PM')) THEN
        EXTRACT(HOUR FROM PARSE_TIME('%I:%M%p', REPLACE(REPLACE(`end`, 'a', 'AM'), 'p', 'PM'))) +
        EXTRACT(MINUTE FROM PARSE_TIME('%I:%M%p', REPLACE(REPLACE(`end`, 'a', 'AM'), 'p', 'PM'))) / 60.0
      ELSE 
        0.0
    END AS hours_on_next_date,
    
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
        return f"<html><body><h1>Error</h1><p>Daily query failed: {str(e)}</p></body></html>"
    
    # Calculate OT
    calculate_ot_for_sites(results, daily_rows)
    calculate_ot_for_sites(all_sites, daily_rows)
    
    # Perform Pareto analysis
    pareto_sites, total_sites = _perform_pareto_analysis(results)
    
    # Get customer name
    customer_name = results[0]['customer_name'] if results else "Unknown Customer"
    
    # Build HTML report
    return _build_html_report(
        pareto_sites=pareto_sites,
        all_sites=all_sites,
        total_sites=total_sites,
        selected_locations=selected_locations,
        start_date=start_date,
        end_date=end_date,
        customer_name=customer_name,
        scope_type=f"Customer {customer_code}",
        mode='customer',
        region=None  # ← ADD THIS (customer mode doesn't use region)
    )


def _generate_region_report_html(
    region: str,
    start_date: str,
    end_date: str,
    selected_locations: Optional[List[str]] = None
) -> str:
    """Generate region-level Pareto report in HTML."""
    
    sql = f"""
SELECT
  location_id,
  state,
  ANY_VALUE(customer_code) AS customer_code,
  ANY_VALUE(city) AS city,
  ANY_VALUE(location_name) AS location_name,
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
        return f"<html><body><h1>Error</h1><p>{str(e)}</p></body></html>"
    
    if not results:
        return f"<html><body><h1>No Data</h1><p>No data found for region={region}</p></body></html>"
    
    all_sites = results.copy()
    
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
    
    PARSE_TIME('%I:%M%p', REPLACE(REPLACE(start, 'a', 'AM'), 'p', 'PM')) AS start_time,
    PARSE_TIME('%I:%M%p', REPLACE(REPLACE(`end`, 'a', 'AM'), 'p', 'PM')) AS end_time,
    
    CASE 
      WHEN PARSE_TIME('%I:%M%p', REPLACE(REPLACE(start, 'a', 'AM'), 'p', 'PM')) >= 
           PARSE_TIME('%I:%M%p', REPLACE(REPLACE(`end`, 'a', 'AM'), 'p', 'PM')) 
      THEN TRUE 
      ELSE FALSE 
    END AS crosses_midnight,
    
    CASE
      WHEN PARSE_TIME('%I:%M%p', REPLACE(REPLACE(start, 'a', 'AM'), 'p', 'PM')) >= 
           PARSE_TIME('%I:%M%p', REPLACE(REPLACE(`end`, 'a', 'AM'), 'p', 'PM')) THEN
        EXTRACT(HOUR FROM PARSE_TIME('%I:%M%p', REPLACE(REPLACE(`end`, 'a', 'AM'), 'p', 'PM'))) +
        EXTRACT(MINUTE FROM PARSE_TIME('%I:%M%p', REPLACE(REPLACE(`end`, 'a', 'AM'), 'p', 'PM'))) / 60.0
      ELSE 
        0.0
    END AS hours_on_next_date,
    
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
        return f"<html><body><h1>Error</h1><p>Daily query failed: {str(e)}</p></body></html>"
    
    calculate_ot_for_sites(results, daily_rows)
    calculate_ot_for_sites(all_sites, daily_rows)
    
    pareto_sites, total_sites = _perform_pareto_analysis(results)
    
    return _build_html_report(
        pareto_sites=pareto_sites,
        all_sites=all_sites,
        total_sites=total_sites,
        selected_locations=selected_locations,
        start_date=start_date,
        end_date=end_date,
        customer_name=f"Region: {region}",
        scope_type=f"All sites in {region} region",
        mode='region',
        region=region  # ← ADD THIS (pass the actual region)
    )


def _perform_pareto_analysis(results: List[Dict]) -> tuple:
    """Perform Pareto 80/20 analysis on sites."""
    
    results_sorted = sorted(
        results, 
        key=lambda x: float(x.get('total_ot_exposure', 0) or 0), 
        reverse=True
    )
    
    total_ot_all = sum(float(r.get('total_ot_exposure', 0) or 0) for r in results_sorted)
    
    cumulative_ot = 0
    pareto_sites = []
    previous_cum_pct = 0  # Track previous cumulative percentage
    
    for idx, site in enumerate(results_sorted, 1):
        ot_exposure = float(site.get('total_ot_exposure', 0) or 0)
        cumulative_ot += ot_exposure
        site['ot_rank'] = idx
        site['ot_cum_pct'] = round((cumulative_ot / total_ot_all * 100), 1) if total_ot_all > 0 else 0
        
        ot_pct = site.get('ot_percentage', 0) or 0
        if ot_pct < 1:
            site['nbot_text'] = 'GREEN'
        elif ot_pct < 3:
            site['nbot_text'] = 'YELLOW'
        else:
            site['nbot_text'] = 'RED'
        
        # Include site if:
        # 1. Cumulative <= 80% (standard Pareto logic)
        # 2. OR previous cumulative < 80% (ensures we reach at least 80%)
        if site['ot_cum_pct'] <= 80 or previous_cum_pct < 80:
            pareto_sites.append(site)
        
        previous_cum_pct = site['ot_cum_pct']
    
    return pareto_sites, len(results_sorted)


def _build_html_report(
    pareto_sites: List[Dict],
    all_sites: List[Dict],
    total_sites: int,
    selected_locations: Optional[List[str]],
    start_date: str,
    end_date: str,
    customer_name: str,
    scope_type: str,
    mode: str,
    region: Optional[str] = None  # ← ADD THIS
) -> str:
    """Build complete HTML report."""
    
    pareto_count = len(pareto_sites)
    
    # Calculate metrics
    overall_metrics = _calculate_overall_metrics(all_sites)
    pareto_metrics = _calculate_pareto_metrics(pareto_sites, all_sites)
    
    # Get timestamp in CST (Central Standard Time = UTC-6)
    from datetime import timezone, timedelta
    cst = timezone(timedelta(hours=-6))
    timestamp = datetime.now(cst).strftime("%Y-%m-%d %H:%M:%S CST")
    
    # 👈 ADD DATES TO EVERY SITE FOR EMPLOYEE QUERIES
    for site in pareto_sites:
        site['start_date'] = start_date
        site['end_date'] = end_date
    
    # Build sections
    header_html = build_header(customer_name, start_date, end_date, scope_type, timestamp)
    
    metadata_cards = _build_metadata_cards(overall_metrics, pareto_count, total_sites, pareto_sites)
    
    # Priority sites display (shown directly, not in section)
    priority_display_html = _build_priority_sites_display(pareto_sites)
    
    # Navigation sections - include Speed to Post for region mode
    nav_sections = [
        {'id': 'section-pareto-matrix', 'label': '🎯 Pareto Analysis'},
        {'id': 'section-site-details', 'label': '🏢 Site Details'},
    ]
    
    # Add Speed to Post for region mode only
    if mode == 'region':
        nav_sections.append({'id': 'section-speed-to-post', 'label': '📊 Speed to Post'})
    
    nav_sections.append({'id': 'section-recommendations', 'label': '💡 Recommendations'})
    
    # Build custom navigation cards (Option 2: Modern Cards with Descriptions)
    navigation_html = f"""
    <div class="nav-cards-container">
        <a href="#section-pareto-matrix" class="nav-card pareto">
            <span class="nav-card-icon">🎯</span>
            <div class="nav-card-title">Pareto Analysis</div>
            <div class="nav-card-desc">80/20 OT breakdown by site</div>
        </a>
        <a href="#section-site-details" class="nav-card site-details">
            <span class="nav-card-icon">🏢</span>
            <div class="nav-card-title">Site Details</div>
            <div class="nav-card-desc">Location deep-dive & employees</div>
        </a>
        <a href="#section-site-capacity" class="nav-card site-capacity">
            <span class="nav-card-icon">📈</span>
            <div class="nav-card-title">Site Capacity</div>
            <div class="nav-card-desc">Staffing levels & utilization</div>
        </a>
        {"" if mode != 'region' else '''
        <a href="#section-speed-to-post" class="nav-card speed-to-post">
            <span class="nav-card-icon">📊</span>
            <div class="nav-card-title">Speed to Post</div>
            <div class="nav-card-desc">Onboarding & training tracking</div>
        </a>
        '''}
        <a href="#section-recommendations" class="nav-card recommendations">
            <span class="nav-card-icon">💡</span>
            <div class="nav-card-title">Recommendations</div>
            <div class="nav-card-desc">Strategic action items</div>
        </a>
    </div>
    """
    
    # Build Pareto section
    pareto_section_html = _build_pareto_section(
        pareto_sites, 
        overall_metrics, 
        pareto_metrics,
        mode
    )
    
    # Build site details section
    site_details_html = _build_site_details_section(pareto_sites, selected_locations)
    
    # Build recommendations section
    recommendations_html = _build_recommendations_section(pareto_sites)
    
    # Build Site Capacity section (both modes)
    # Extract Pareto site IDs (sites that contribute to 80% of OT)
    pareto_site_ids = [str(site['location_id']) for site in pareto_sites] if pareto_sites else []
    site_capacity_html = _build_site_capacity_section(all_sites, pareto_site_ids)
    
    # Build Speed to Post section (region mode only)
    speed_to_post_html = ""
    if mode == 'region':
        speed_to_post_html = _build_speed_to_post_section(region)
    
    # Custom navigation card styles (Option 2: Modern Cards with Descriptions)
    nav_card_css = """
    <style>
    /* Hide default nav-buttons if present */
    .nav-buttons { display: none !important; }
    
    /* Modern Card Navigation */
    .nav-cards-container {
        display: flex;
        gap: 15px;
        flex-wrap: nowrap;
        justify-content: stretch;
        padding: 16px 20px;
        margin: 20px 0;
        background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%);
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    
    .nav-card {
        background: linear-gradient(145deg, #1e293b 0%, #334155 100%);
        border-radius: 12px;
        padding: 14px 20px;
        min-width: 0;
        flex: 1 1 0;
        text-align: center;
        cursor: pointer;
        transition: all 0.3s ease;
        border: 2px solid transparent;
        text-decoration: none;
    }
    
    .nav-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 12px 30px rgba(0, 0, 0, 0.4);
    }
    
    .nav-card-icon {
        font-size: 1.8em;
        margin-bottom: 6px;
        display: block;
    }
    
    .nav-card-title {
        color: white;
        font-weight: 700;
        font-size: 1em;
        margin-bottom: 4px;
    }
    
    .nav-card-desc {
        color: #94a3b8;
        font-size: 0.8em;
        line-height: 1.4;
    }
    
    /* Pareto - Red accent */
    .nav-card.pareto {
        border-top: 4px solid #dc2626;
    }
    .nav-card.pareto:hover {
        border-color: #dc2626;
        box-shadow: 0 12px 30px rgba(220, 38, 38, 0.3);
    }
    
    /* Site Details - Blue accent */
    .nav-card.site-details {
        border-top: 4px solid #3b82f6;
    }
    .nav-card.site-details:hover {
        border-color: #3b82f6;
        box-shadow: 0 12px 30px rgba(59, 130, 246, 0.3);
    }
    
    /* Speed to Post - Purple accent */
    .nav-card.speed-to-post {
        border-top: 4px solid #a855f7;
    }
    .nav-card.speed-to-post:hover {
        border-color: #a855f7;
        box-shadow: 0 12px 30px rgba(168, 85, 247, 0.3);
    }
    
    /* Site Capacity - Orange accent */
    .nav-card.site-capacity {
        border-top: 4px solid #f59e0b;
    }
    .nav-card.site-capacity:hover {
        border-color: #f59e0b;
        box-shadow: 0 12px 30px rgba(245, 158, 11, 0.3);
    }
    
    /* Recommendations - Green accent */
    .nav-card.recommendations {
        border-top: 4px solid #10b981;
    }
    .nav-card.recommendations:hover {
        border-color: #10b981;
        box-shadow: 0 12px 30px rgba(16, 185, 129, 0.3);
    }
    </style>
    """
    
    # Assemble complete HTML
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pareto Optimization Report - {customer_name}</title>
    {get_industrial_chrome_css()}
    {nav_card_css}
</head>
<body>
    <div class="report-container">
        {header_html}
        {metadata_cards}
        {priority_display_html}
        {navigation_html}
        {pareto_section_html}
        {site_details_html}
        {site_capacity_html}
        {speed_to_post_html}
        {recommendations_html}
    </div>
    {get_javascript()}
</body>
</html>
"""
    
    return html


def _calculate_overall_metrics(all_sites: List[Dict]) -> Dict:
    """Calculate overall portfolio metrics."""
    total_hours = sum(float(s.get('total_hours', 0) or 0) for s in all_sites)
    total_ot = sum(float(s.get('total_ot_exposure', 0) or 0) for s in all_sites)
    total_employees = sum(int(s.get('employee_count', 0) or 0) for s in all_sites)
    ot_pct = round((total_ot / total_hours * 100), 1) if total_hours > 0 else 0.0
    
    nbot_status, nbot_text = get_nbot_status(ot_pct)
    
    return {
        'total_sites': len(all_sites),
        'total_employees': total_employees,
        'total_hours': total_hours,
        'total_ot': total_ot,
        'ot_pct': ot_pct,
        'nbot_status': nbot_status,
        'nbot_text': nbot_text,
    }


def _calculate_pareto_metrics(pareto_sites: List[Dict], all_sites: List[Dict]) -> Dict:
    """Calculate Pareto 80% metrics."""
    pareto_ot = sum(float(s.get('total_ot_exposure', 0) or 0) for s in pareto_sites)
    pareto_hours = sum(float(s.get('total_hours', 0) or 0) for s in pareto_sites)
    pareto_employees = sum(int(s.get('employee_count', 0) or 0) for s in pareto_sites)
    pareto_ot_pct = round((pareto_ot / pareto_hours * 100), 1) if pareto_hours > 0 else 0.0
    
    total_ot = sum(float(s.get('total_ot_exposure', 0) or 0) for s in all_sites)
    
    return {
        'count': len(pareto_sites),
        'employees': pareto_employees,
        'hours': pareto_hours,
        'ot': pareto_ot,
        'ot_pct': pareto_ot_pct,
        'ot_share': round((pareto_ot / total_ot * 100), 1) if total_ot > 0 else 0
    }


def _build_metadata_cards(overall: Dict, pareto_count: int, total_sites: int, pareto_sites: List[Dict]) -> str:
    """Build metadata cards."""
    
    # Calculate Pareto OT metrics
    pareto_ot_hours = sum(float(s.get('total_ot_exposure', 0) or 0) for s in pareto_sites)
    pareto_share_pct = round((pareto_ot_hours / overall['total_ot'] * 100), 1) if overall['total_ot'] > 0 else 0
    
    # Determine conditional class for Total OT Exposure %
    ot_pct = overall['ot_pct']
    if ot_pct < 1:
        ot_class = 'ot-good'
    elif ot_pct < 2:
        ot_class = 'ot-warning'
    else:
        ot_class = 'ot-critical'
    
    cards = [
        {'label': 'TOTAL PORTFOLIO', 'value': f"{total_sites} sites"},
        {'label': 'TOTAL EMPLOYEES', 'value': str(overall['total_employees'])},
        {'label': 'TOTAL SCHEDULED HOURS', 'value': f"{overall['total_hours']:.1f} hrs"},
        {'label': 'TOTAL OT EXPOSURE HRS', 'value': f"{overall['total_ot']:.1f} hrs"},
        {'label': 'TOTAL OT EXPOSURE %', 'value': f"{ot_pct:.1f}%", 'class': ot_class},
        {'label': 'PARETO SITES', 'value': f"{pareto_count} ({round(pareto_count/total_sites*100, 1)}%)"},
        {'label': 'PARETO OT SHARE HRS (%)', 'value': f"{pareto_ot_hours:.1f} hrs ({pareto_share_pct}%)"},
    ]
    
    return build_metadata_cards(cards)

def _build_priority_sites_display(pareto_sites: List[Dict]) -> str:
    """Build priority sites banner and cards (displayed directly, no section wrapper)."""
    
    if not pareto_sites:
        return ""
    
    # Build priority banner
    priority_banner = f"""
    <div class="priority-title-container">
        <span class="warning-icon">⚠️</span>
        <div class="priority-title">PRIORITY SITES FOR OPTIMIZATION</div>
        <span class="warning-icon">⚠️</span>
    </div>
    """
    
    # Build site cards grid
    site_cards_html = _build_site_cards_grid(pareto_sites)
    
    # Return direct HTML (no section wrapper)
    return f"""
    {priority_banner}
    {site_cards_html}
    """

def _build_pareto_section(
    pareto_sites: List[Dict],
    overall: Dict,
    pareto: Dict,
    mode: str
) -> str:
    """Build Pareto Analysis section - table only (priority content removed)."""
    
    # Build executive summary
    summary_html = f"""
    <div class="section-inner">
        {build_info_box(
            "Executive Summary",
            f"Pareto Analysis identifies <strong>{pareto['count']} sites ({round(pareto['count']/(overall['total_sites'])*100, 1)}%)</strong> "
            f"that drive <strong>80% of overtime</strong> ({pareto['ot']:.1f} hours). "
            f"Overall portfolio OT: <strong>{overall['ot_pct']}%</strong> {build_status_badge(overall['nbot_text'])}. "
            f"Focus optimization efforts on these high-impact sites for maximum ROI.",
            'default'
        )}
        
        <h3>📋 DETAILED PARETO MATRIX</h3>
    """
    
    # Build Pareto table
    table_html = _build_pareto_table(pareto_sites, mode)
    
    summary_html += f"""
        {table_html}
    </div>
    """
    
    return f"""
    <div id="section-pareto-matrix" class="section expanded">
        <div class="section-header" onclick="toggleSection('section-pareto-matrix')">
            <span class="section-toggle">▶</span>
            <span class="section-title">🎯 PARETO ANALYSIS | 80%</span>
        </div>
        <div class="section-content">
            {summary_html}
        </div>
    </div>
    """


def _build_site_cards_grid(pareto_sites: List[Dict]) -> str:
    """Build grid of site navigation cards."""
    if not pareto_sites:
        return ""
    
    cards_html = ""
    for site in pareto_sites[:20]:  # Show top 20 in cards
        location_id = site['location_id']
        rank = site['ot_rank']
        ot_pct = site.get('ot_percentage', 0) or 0
        ot_hours = site.get('total_ot_exposure', 0) or 0
        state = site.get('state', 'N/A')
        city = site.get('city', '')
        
        card_class = 'critical' if ot_pct >= 3 else 'warning' if ot_pct >= 1 else ''
        
        # Build site display with location name (city is already in location_name)
        location_name = site.get('location_name', '')
        site_display = f"Site <span style='color: #dc2626; font-weight: 900;'>{location_id}</span>"
        
        # Location name (smaller font, below site number) - includes city and address
        location_name_display = f"<div style='font-size: 0.75em; color: #374151; margin-top: 2px;'>{location_name}</div>" if location_name else ""
        
        cards_html += f"""
        <div class="site-card {card_class}" onclick="navigateToSite('{location_id}')">
            <div class="site-rank-badge">Priority #{rank}</div>
            <div class="site-card-header">
                <div class="site-number">{site_display}{location_name_display}</div>
                <div class="site-location">{state}</div>
            </div>
            <div class="site-stats">
                <div class="stat-item">
                    <div class="stat-label">OT Hours</div>
                    <div class="stat-value" style="color: #dc2626;">{ot_hours:.1f}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">OT %</div>
                    <div class="stat-value" style="color: #dc2626;">{ot_pct:.1f}%</div>
                </div>
            </div>
            <button class="site-card-button">View Details →</button>
        </div>
        """
    
    return f"""
    <div class="site-cards-grid">
        {cards_html}
    </div>
    """


def _build_pareto_table(pareto_sites: List[Dict], mode: str) -> str:
    """Build Pareto analysis table."""
    
    if mode == 'region':
        headers = ['RANK', 'SITE', 'CUSTOMER', 'STATE', 'REGION', 'EMPLOYEES', 
                   'TOTAL HOURS', 'OT HOURS', 'OT %', 'CUM-OT %', 'NBOT']
    else:
        headers = ['RANK', 'SITE', 'STATE', 'REGION', 'EMPLOYEES', 
                   'TOTAL HOURS', 'OT HOURS', 'OT %', 'CUM-OT %', 'NBOT']
    
    rows = []
    for site in pareto_sites:
        location_id = site['location_id']
        rank = site['ot_rank']
        city = site.get('city', '')
        state = site.get('state', 'N/A')
        region = site.get('region', 'N/A')
        employees = site.get('employee_count', 0)
        total_hours = site.get('total_hours', 0)
        ot_hours = site.get('total_ot_exposure', 0)
        ot_pct = site.get('ot_percentage', 0)
        cum_pct = site.get('ot_cum_pct', 0)
        nbot = site.get('nbot_text', 'GREEN')
        
        site_link = f'<a href="#subsection-{location_id}" style="font-weight: 900; color: var(--accent);">{location_id}</a>'
        nbot_badge = build_status_badge(nbot)
        
        # Use city under site number instead of state
        city_display = city if city else state  # Fallback to state if city is empty
        
        row = [
            f'<div style="text-align: center; font-weight: 900;">{rank}</div>',
            f'<div style="text-align: center;">{site_link}<br><span style="font-size: 9px; color: var(--muted);">{city_display}</span></div>',
        ]
        
        if mode == 'region':
            customer_name = site.get('customer_name', 'N/A')
            row.append(f'<div style="text-align: center; font-size: 10px;">{customer_name}</div>')
        
        row.extend([
            f'<div style="text-align: center;">{state}</div>',
            f'<div style="text-align: center;">{region}</div>',
            f'<div style="text-align: right;">{employees}</div>',
            f'<div style="text-align: right;">{total_hours:.0f}</div>',
            f'<div style="text-align: right; font-weight: 900; color: {"var(--danger)" if ot_pct >= 3 else "var(--warning)" if ot_pct >= 1 else "var(--text)"};">{ot_hours:.1f}</div>',
            f'<div style="text-align: right; font-weight: 900; color: {"var(--danger)" if ot_pct >= 3 else "var(--warning)" if ot_pct >= 1 else "var(--text)"};">{ot_pct:.1f}%</div>',
            f'<div style="text-align: right;">{cum_pct:.1f}%</div>',
            f'<div style="text-align: center;">{nbot_badge}</div>',
        ])
        
        rows.append(row)
    
    table_html = build_table_with_controls(
        table_id='pareto-table',
        search_box_id='pareto-search',
        headers=headers,
        rows=rows,
        export_filename='pareto_analysis.csv'
    )
    
    # Add status threshold legend
    legend_html = f"""
    <div style="margin-top: 10px; padding: 10px 15px; background: linear-gradient(145deg, #f9fafb 0%, #f3f4f6 100%); border-radius: 8px; border: 1px solid #e5e7eb; text-align: center;">
        <strong style="color: #1f2937; font-size: 0.9em;">Status Thresholds:</strong> 
        <span style="margin: 0 8px;">
            <span class="status-badge badge-red">RED</span> High (≥3%)
        </span>
        <span style="color: #3b82f6; font-weight: 900;">|</span>
        <span style="margin: 0 8px;">
            <span class="status-badge badge-yellow">YEL</span> Medium (1-3%)
        </span>
        <span style="color: #3b82f6; font-weight: 900;">|</span>
        <span style="margin: 0 8px;">
            <span class="status-badge badge-green">GRN</span> Low (&lt;1%)
        </span>
    </div>
    """
    
    return table_html + legend_html


def _build_site_details_section(pareto_sites: List[Dict], selected_locations: Optional[List[str]]) -> str:
    """Build site details section with collapsible subsections."""
    
    subsections_html = ""
    
    for site in pareto_sites:
        location_id = site['location_id']
        
        # Skip if not selected (when selection is provided)
        if selected_locations and str(location_id) not in selected_locations:
            continue
        
        subsections_html += _build_site_subsection(site)
    
    if not subsections_html:
        subsections_html = build_info_box(
            "No Sites Selected",
            "Select specific sites from the Pareto Analysis table above to view detailed optimization cards.",
            'default'
        )
    
    return f"""
    <div id="section-site-details" class="section">
        <div class="section-header" onclick="toggleSection('section-site-details')">
            <span class="section-toggle">▶</span>
            <span class="section-title">🏢 SITE DETAILS & OPTIMIZATION CARDS</span>
        </div>
        <div class="section-content">
            <div class="section-inner">
                <a href="#section-pareto-matrix" class="back-to-top">↑ Back to Pareto Matrix</a>
                {subsections_html}
            </div>
        </div>
    </div>
    """


def _build_site_subsection(site: Dict) -> str:
    """Build individual site subsection."""
    location_id = site['location_id']
    rank = site['ot_rank']
    city = site.get('city', '')
    state = site.get('state', 'N/A')
    region = site.get('region', 'N/A')
    ot_pct = site.get('ot_percentage', 0) or 0
    ot_hours = site.get('total_ot_exposure', 0) or 0
    total_hours = site.get('total_hours', 0) or 0
    employees = site.get('employee_count', 0) or 0
    
    # Site OT values are already correct from calculate_ot_for_sites() 
    # (which now receives midnight-split data)
    
    header_class = 'critical' if ot_pct >= 3 else 'warning' if ot_pct >= 1 else ''
    pill_class = 'critical' if ot_pct >= 3 else 'warning' if ot_pct >= 1 else 'good'
    
    # Build context cards
    context_html = f"""
    <div class="context-grid">
        <div class="context-card">
            <div class="context-label">City</div>
            <div class="context-value">{city if city else 'N/A'}</div>
        </div>
        <div class="context-card">
            <div class="context-label">State</div>
            <div class="context-value">{state}</div>
        </div>
        <div class="context-card">
            <div class="context-label">Employees</div>
            <div class="context-value">{employees}</div>
        </div>
        <div class="context-card">
            <div class="context-label">Total Hours</div>
            <div class="context-value">{total_hours:.0f}</div>
        </div>
        <div class="context-card {header_class}-card">
            <div class="context-label">OT Exposure</div>
            <div class="context-value">{ot_hours:.1f} hrs</div>
        </div>
        <div class="context-card {header_class}-card">
            <div class="context-label">OT Percentage</div>
            <div class="context-value">{ot_pct:.1f}%</div>
        </div>
    </div>
    """
    
    # Build action items
    actions_html = _build_action_items(site)
    
    # Build employee summary
    employee_html = _build_employee_summary(site)
    
    # Build site display with city
    site_display = f"Site {location_id}"
    if city:
        site_display += f", {city}"
    site_display += f" - {state}"
    
    return f"""
    <div id="subsection-{location_id}" class="site-subsection">
        <div class="subsection-header {header_class}" onclick="toggleSubsection('{location_id}')">
            <span class="subsection-toggle">▶</span>
            <span class="subsection-title">
                Priority #{rank} | 📍 {site_display}
            </span>
            <div class="quick-stats">
                <span class="quick-stat-pill {pill_class}">{ot_hours:.1f} hrs OT</span>
                <span class="quick-stat-pill {pill_class}">{ot_pct:.1f}%</span>
            </div>
        </div>
        <div class="subsection-content">
            <div class="subsection-inner">
                <a href="#section-pareto-matrix" class="back-to-top">↑ Back to Pareto Matrix</a>
                
                {context_html}
                
                <div class="priority-title-container" style="margin-top: 20px; margin-bottom: 20px;">
                    <span class="warning-icon">⚠️</span>
                    <div class="priority-title" style="font-size: 1.2em;">ACTION ITEMS</div>
                    <span class="warning-icon">⚠️</span>
                </div>
                {actions_html}
                
                <h4>Employee Summary</h4>
                {employee_html}
            </div>
        </div>
    </div>
    """


def _build_action_items(site: Dict) -> str:
    """Build action items for site - WITH REAL DATA including employee details."""
    location_id = site['location_id']
    ot_pct = site.get('ot_percentage', 0) or 0
    weekly_ot = site.get('weekly_ot_hours', 0) or 0
    daily_ot = site.get('daily_ot_hours', 0) or 0
    double_time = site.get('double_time_hours', 0) or 0
    state = site.get('state', '')
    start_date = site.get('start_date')
    end_date = site.get('end_date')
    
    actions = []
    
    # Get employee-level OT details
    customer_code = site.get('customer_code')
    employee_ot_details = _get_employee_ot_breakdown(location_id, start_date, end_date, state, customer_code)
    
    # Critical OT action
    if ot_pct >= 3:
        details_html = f'Target: Reduce to <1% OT (GREEN status). Current exposure: {site.get("total_ot_exposure", 0):.1f} hours.'
        
        # Add employee breakdown if available
        if employee_ot_details['daily_ot_employees'] or employee_ot_details['weekly_ot_employees']:
            details_html += '<br><br><strong>Affected Employees:</strong><ul style="margin: 8px 0 0 20px; line-height: 1.8;">'
            
            # Show top daily OT offenders
            for emp in employee_ot_details['daily_ot_employees'][:3]:
                date_list = ', '.join([d['date'].strftime('%Y-%m-%d') if hasattr(d['date'], 'strftime') else str(d['date']) for d in emp['dates'][:3]])
                if len(emp['dates']) > 3:
                    date_list += f" (+{len(emp['dates'])-3} more)"
                details_html += f"<li><strong>Emp {emp['id']}</strong> ({emp['name']}): Remove {emp['total_ot']:.1f} hrs daily OT on {date_list}</li>"
            
            # Show top weekly OT offenders
            for emp in employee_ot_details['weekly_ot_employees'][:2]:
                details_html += f"<li><strong>Emp {emp['id']}</strong> ({emp['name']}): Remove {emp['ot_hours']:.1f} hrs weekly OT (worked {emp['weekly_hours']:.1f} hrs)</li>"
            
            details_html += '</ul>'
        
        actions.append({
            'class': 'action-critical',
            'icon': '🚨',
            'title': 'CRITICAL: Reduce OT Immediately',
            'description': f'Site OT is {ot_pct:.1f}% (RED status). Immediate action required.',
            'details': details_html
        })
    elif ot_pct >= 1:
        actions.append({
            'class': 'action-warning',
            'icon': '⚠️',
            'title': 'WARNING: Monitor OT Closely',
            'description': f'Site OT is {ot_pct:.1f}% (YELLOW status). Trend toward critical.',
            'details': 'Target: Reduce to <1% OT (GREEN status). Implement preventive measures before reaching RED status.'
        })
    
    # CA Daily OT action
    if daily_ot > 0 and state == 'CA':
        details_html = 'Review shift lengths. Consider splitting long shifts across multiple days.'
        
        # Add employee breakdown
        if employee_ot_details['daily_ot_employees']:
            details_html += '<br><br><strong>Employees with Daily OT:</strong><ul style="margin: 8px 0 0 20px; line-height: 1.8;">'
            for emp in employee_ot_details['daily_ot_employees'][:5]:
                date_list = ', '.join([d['date'].strftime('%Y-%m-%d') if hasattr(d['date'], 'strftime') else str(d['date']) for d in emp['dates'][:5]])
                if len(emp['dates']) > 5:
                    date_list += f" (+{len(emp['dates'])-5} more)"
                details_html += f"<li><strong>Emp {emp['id']}</strong> ({emp['name']}): {emp['total_ot']:.1f} hrs on {date_list}</li>"
            details_html += '</ul>'
        
        actions.append({
            'class': 'action-warning',
            'icon': '⏰',
            'title': 'California Daily OT Detected',
            'description': f'{daily_ot:.1f} hours of CA Daily OT (1.5x rate for hours 9-12).',
            'details': details_html
        })
    
    # CA Double Time action
    if double_time > 0 and state == 'CA':
        details_html = 'URGENT: Eliminate shifts >12 hours. This is the most expensive OT.'
        
        # Add employee breakdown
        if employee_ot_details['double_time_employees']:
            details_html += '<br><br><strong>Employees with Double Time:</strong><ul style="margin: 8px 0 0 20px; line-height: 1.8;">'
            for emp in employee_ot_details['double_time_employees']:
                date_list = ', '.join([d['date'].strftime('%Y-%m-%d') if hasattr(d['date'], 'strftime') else str(d['date']) for d in emp['dates'][:5]])
                if len(emp['dates']) > 5:
                    date_list += f" (+{len(emp['dates'])-5} more)"
                details_html += f"<li><strong>Emp {emp['id']}</strong> ({emp['name']}): {emp['total_dt']:.1f} hrs on {date_list}</li>"
            details_html += '</ul>'
        
        actions.append({
            'class': 'action-critical',
            'icon': '💰',
            'title': 'CA Double Time - Highest Cost',
            'description': f'{double_time:.1f} hours of CA Double Time (2.0x rate for hours 13+).',
            'details': details_html
        })
    
    # Weekly OT action
    if weekly_ot > 0:
        actions.append({
            'class': 'action-info',
            'icon': '📊',
            'title': 'Weekly OT Optimization',
            'description': f'{weekly_ot:.1f} hours of standard weekly OT (hours 41+).',
            'details': 'Redistribute hours or add capacity to stay within 40 hrs/employee/week.'
        })
    
    # Staffing action
    fte_needed = site.get('fte_needed', 0)
    employee_count = site.get('employee_count', 0)
    total_hours = site.get('total_hours', 0) or 0
    
    if fte_needed > employee_count:
        gap = fte_needed - employee_count
        
        # Determine hours per week for FTE calc (32 for CA, 36 for others)
        hrs_per_week = 32 if state == 'CA' else 36
        
        actions.append({
            'class': 'action-info',
            'icon': '👥',
            'title': f'Staffing Gap: {gap} FTE Needed',
            'description': f'Current: {employee_count} employees | Optimal: {fte_needed} FTE (based on {total_hours:.0f} hrs ÷ {hrs_per_week} hrs/week).',
            'details': ''
        })
    
    # Build HTML
    if not actions:
        return build_info_box(
            "No Critical Actions",
            "Site is performing well with minimal OT exposure.",
            'success'
        )
    
    actions_html = ""
    for action in actions:
        actions_html += f"""
        <div class="action-item {action['class']}">
            <div class="action-icon">{action['icon']}</div>
            <div class="action-content">
                <div class="action-title">{action['title']}</div>
                <div class="action-description">{action['description']}</div>
                <div class="action-details">{action['details']}</div>
            </div>
        </div>
        """
    
    return f'<div class="actions-container">{actions_html}</div>'


def _build_employee_summary(site: Dict) -> str:
    """Build employee summary for site - WITH ACTUAL DATA including capacity analysis."""
    import json  # For tooltip data serialization
    
    location_id = site['location_id']
    start_date = site.get('start_date')
    end_date = site.get('end_date')
    state = site.get('state', 'N/A')
    
    if not start_date or not end_date:
        return build_info_box(
            "No Date Range",
            "Date range not available for employee query.",
            'default'
        )
    
    # Get customer_code from site - CONVERT TO STRING
    customer_code = site.get('customer_code')
    customer_filter = f"AND CONCAT('', customer_code) = '{customer_code}'" if customer_code else ""
    
    # Comprehensive employee data query - QUERY ALL SITES for hours_all_sites
    employee_sql = f"""
    WITH EmployeesAtSite AS (
      SELECT DISTINCT employee_id
      FROM `{BQ_DATA_PROJECT_ID}.{BQ_DATASET_ID}.APEX_NWS`
      WHERE location_id = '{location_id}'
        {customer_filter}
        AND scheduled_date BETWEEN '{start_date}' AND '{end_date}'
    ),
    EmployeeWeeklyData AS (
      SELECT
        employee_id,
        ANY_VALUE(employee_name) AS employee_name,
        ANY_VALUE(employee_status) AS employee_status,
        ANY_VALUE(employee_date_started) AS employee_date_started,
        -- Hours at THIS site only
        SUM(IF(location_id = '{location_id}', scheduled_hours, 0)) AS hours_this_site,
        -- Hours across ALL sites (no location filter)
        SUM(scheduled_hours) AS hours_all_sites,
        -- Count of distinct sites
        COUNT(DISTINCT location_id) AS site_count,
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
        {customer_filter}
        AND employee_id IN (SELECT employee_id FROM EmployeesAtSite)
      GROUP BY employee_id
    )
    SELECT * FROM EmployeeWeeklyData
    ORDER BY tenure_days ASC
    """
    
    try:
        employees = execute_query(employee_sql)
        
        if not employees:
            return build_info_box(
                "No Employee Data",
                "No employee schedules found for this site.",
                'default'
            )
        
        # NEW: Query OTHER sites for hover tooltip
        other_sites_sql = f"""
        WITH EmployeesAtThisSite AS (
          SELECT DISTINCT employee_id
          FROM `{BQ_DATA_PROJECT_ID}.{BQ_DATASET_ID}.APEX_NWS`
          WHERE location_id = '{location_id}'
            {customer_filter}
            AND scheduled_date BETWEEN '{start_date}' AND '{end_date}'
        )
        SELECT
          employee_id,
          location_id,
          ANY_VALUE(location_name) AS location_name,
          ANY_VALUE(city) AS city,
          ANY_VALUE(state) AS site_state,
          SUM(scheduled_hours) AS hours_at_site
        FROM `{BQ_DATA_PROJECT_ID}.{BQ_DATASET_ID}.APEX_NWS`
        WHERE scheduled_date BETWEEN '{start_date}' AND '{end_date}'
          {customer_filter}
          AND employee_id IN (SELECT employee_id FROM EmployeesAtThisSite)
          AND location_id != '{location_id}'
        GROUP BY employee_id, location_id
        ORDER BY employee_id, hours_at_site DESC
        """
        
        other_sites_data = execute_query(other_sites_sql)
        
        # Build lookup: employee_id -> list of other sites
        other_sites_by_employee = {}
        for row in other_sites_data:
            emp_id = row['employee_id']
            if emp_id not in other_sites_by_employee:
                other_sites_by_employee[emp_id] = []
            other_sites_by_employee[emp_id].append({
                'location_id': row['location_id'],
                'location_name': row['location_name'] or row['city'] or 'Unknown',
                'city': row['city'] or '',
                'state': row['site_state'] or '',
                'hours': float(row['hours_at_site'] or 0)
            })
        
        # Get daily hours for OT calculations - WITH MIDNIGHT SPLITTING
        daily_sql = f"""
        WITH EmployeesAtThisSite AS (
          -- First identify employees who work at this site
          SELECT DISTINCT employee_id
          FROM `{BQ_DATA_PROJECT_ID}.{BQ_DATASET_ID}.APEX_NWS`
          WHERE location_id = '{location_id}'
            {customer_filter}
            AND scheduled_date BETWEEN '{start_date}' AND '{end_date}'
        ),
        ShiftSegments AS (
          SELECT
            employee_id,
            scheduled_date,
            start,
            `end`,
            scheduled_hours,
            
            PARSE_TIME('%I:%M%p', REPLACE(REPLACE(start, 'a', 'AM'), 'p', 'PM')) AS start_time,
            PARSE_TIME('%I:%M%p', REPLACE(REPLACE(`end`, 'a', 'AM'), 'p', 'PM')) AS end_time,
            
            CASE 
              WHEN PARSE_TIME('%I:%M%p', REPLACE(REPLACE(start, 'a', 'AM'), 'p', 'PM')) >= 
                   PARSE_TIME('%I:%M%p', REPLACE(REPLACE(`end`, 'a', 'AM'), 'p', 'PM')) 
              THEN TRUE 
              ELSE FALSE 
            END AS crosses_midnight,
            
            CASE
              WHEN PARSE_TIME('%I:%M%p', REPLACE(REPLACE(start, 'a', 'AM'), 'p', 'PM')) >= 
                   PARSE_TIME('%I:%M%p', REPLACE(REPLACE(`end`, 'a', 'AM'), 'p', 'PM')) THEN
                EXTRACT(HOUR FROM PARSE_TIME('%I:%M%p', REPLACE(REPLACE(`end`, 'a', 'AM'), 'p', 'PM'))) +
                EXTRACT(MINUTE FROM PARSE_TIME('%I:%M%p', REPLACE(REPLACE(`end`, 'a', 'AM'), 'p', 'PM'))) / 60.0
              ELSE 
                0.0
            END AS hours_on_next_date,
            
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
          WHERE scheduled_date BETWEEN '{start_date}' AND '{end_date}'
            {customer_filter}
            AND employee_id IN (SELECT employee_id FROM EmployeesAtThisSite)
        ),
        ExpandedShifts AS (
          SELECT
            employee_id,
            scheduled_date AS workday_date,
            hours_on_scheduled_date AS daily_hours
          FROM ShiftSegments
          WHERE hours_on_scheduled_date > 0
          
          UNION ALL
          
          SELECT
            employee_id,
            DATE_ADD(scheduled_date, INTERVAL 1 DAY) AS workday_date,
            hours_on_next_date AS daily_hours
          FROM ShiftSegments
          WHERE crosses_midnight AND hours_on_next_date > 0
        )
        SELECT
          employee_id,
          workday_date AS scheduled_date,
          SUM(daily_hours) AS daily_hours
        FROM ExpandedShifts
        GROUP BY employee_id, workday_date
        ORDER BY employee_id, workday_date
        """
        
        daily_rows = execute_query(daily_sql)
        
        # Calculate OT for each employee
        from collections import defaultdict, OrderedDict
        by_emp = defaultdict(lambda: OrderedDict())
        
        for r in daily_rows:
            eid = r['employee_id']
            by_emp[eid][str(r['scheduled_date'])] = float(r.get('daily_hours') or 0.0)
        
        # Calculate day-of-week hours for each employee (ALL SITES COMBINED)
        from datetime import datetime
        day_of_week_hours = defaultdict(lambda: defaultdict(float))
        by_emp_total = defaultdict(lambda: OrderedDict())
        
        for r in daily_rows:
            eid = r['employee_id']
            date_str = str(r['scheduled_date'])
            hours = float(r.get('daily_hours') or 0.0)
            
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            day_index = (date_obj.weekday() + 1) % 7
            
            # Aggregate total hours per day-of-week (ALL sites)
            day_of_week_hours[eid][day_index] += hours
            
            # Aggregate total hours per date (for OT calculation)
            if date_str in by_emp_total[eid]:
                by_emp_total[eid][date_str] += hours
            else:
                by_emp_total[eid][date_str] = hours
        
        # Calculate OT per employee
        has_daily_ot_rules = state in ['CA', 'AK', 'NV', 'CO']
        
        for emp in employees:
            eid = emp['employee_id']
            if eid not in by_emp:
                emp['weekly_ot'] = emp['daily_ot'] = emp['double_time'] = 0.0
                continue
            
            # Use the proper CA-compliant OT calculation function
            ot_result = calculate_employee_ot(
                employee_id=eid,
                daily_hours=by_emp[eid],
                state=state
            )
            
            emp['weekly_ot'] = ot_result['weekly_ot']
            emp['daily_ot'] = ot_result['daily_ot']
            emp['double_time'] = ot_result['double_time']
        
        # Build employee table rows with centered headers
        headers = [
            'ID', 
            'NAME', 
            'TENURE', 
            'STATUS', 
            'SCHEDULED<br>HOURS<br>(SITE/ALL)', 
            'SCHEDULED<br>OT<br>(W/D/DT)', 
            'SCHEDULED<br>TOTAL OT',
            'AVAILABLE<br>CAPACITY',
            'DAY AVAILABILITY',
            'USAGE', 
            'TRAINING'
        ]
        rows = []
        
        day_abbrev = ['Su', 'M', 'T', 'W', 'Th', 'F', 'Sa']
        
        for emp in employees:
            eid = emp['employee_id']
            
            # Tenure badge
            tenure_days = emp.get('tenure_days', 0)
            if tenure_days <= 90:
                tenure_badge = f'<span style="background: #dc2626; color: white; padding: 2px 6px; border-radius: 4px; font-size: 9px; font-weight: 900;">RED</span>'
            elif tenure_days <= 180:
                tenure_badge = f'<span style="background: #f59e0b; color: white; padding: 2px 6px; border-radius: 4px; font-size: 9px; font-weight: 900;">YEL</span>'
            else:
                tenure_badge = f'<span style="background: #10b981; color: white; padding: 2px 6px; border-radius: 4px; font-size: 9px; font-weight: 900;">GRN</span>'
            
            tenure_display = f'<div style="text-align: center;">{tenure_days}d {tenure_badge}</div>'
            
            # Usage badge with tooltip showing range
            usage_status = emp.get('usage_status', 'Sub-Optimal')
            if usage_status == 'Optimal':
                usage_badge = f'<span style="background: #10b981; color: white; padding: 2px 6px; border-radius: 4px; font-size: 9px; font-weight: 900;">GRN</span> Optimal<br><span style="font-size: 9px; color: #6b7280;">(36-40 h/wk)</span>'
            elif usage_status == 'Sub-Optimal':
                usage_badge = f'<span style="background: #f59e0b; color: white; padding: 2px 6px; border-radius: 4px; font-size: 9px; font-weight: 900;">YEL</span> Sub-Optimal<br><span style="font-size: 9px; color: #6b7280;">(25-35 h/wk)</span>'
            else:
                usage_badge = f'<span style="background: #dc2626; color: white; padding: 2px 6px; border-radius: 4px; font-size: 9px; font-weight: 900;">RED</span> Critical<br><span style="font-size: 9px; color: #6b7280;">(&lt;25 or &gt;40 h/wk)</span>'
            
            # Training icon
            training_status = emp.get('training_status', 'Not Completed')
            training_icon = '✅' if training_status == 'Completed' else '❌'
            
            # OT breakdown with color coding
            weekly = emp.get('weekly_ot', 0.0)
            daily = emp.get('daily_ot', 0.0)
            double = emp.get('double_time', 0.0)
            
            w_color = 'color: #dc2626; font-weight: 900;' if weekly > 0 else ''
            d_color = 'color: #dc2626; font-weight: 900;' if daily > 0 else ''
            dt_color = 'color: #dc2626; font-weight: 900;' if double > 0 else ''
            
            if state == 'CA':
                ot_display = f"W:<span style='{w_color}'>{weekly:.1f}</span><br>D:<span style='{d_color}'>{daily:.1f}</span><br>DT:<span style='{dt_color}'>{double:.1f}</span>"
            elif state in ['AK', 'NV', 'CO']:
                ot_display = f"W:<span style='{w_color}'>{weekly:.1f}</span><br>D:<span style='{d_color}'>{daily:.1f}</span>"
            else:
                ot_display = f"W:<span style='{w_color}'>{weekly:.1f}</span>"
            
            total_ot = weekly + daily + double
            total_ot_color = 'color: #dc2626; font-weight: 900;' if total_ot > 0 else 'font-weight: 900;'
            
            # Get values for display
            hours_this_site = float(emp.get('hours_this_site', 0))
            hours_all_sites = float(emp.get('hours_all_sites', 0))
            site_count = int(emp.get('site_count', 1))
            
            # Build hover tooltip for other sites
            other_sites = other_sites_by_employee.get(eid, [])
            has_other_sites = len(other_sites) > 0
            
            # Build tooltip data as JSON for JavaScript-based tooltip
            import json
            
            if has_other_sites:
                # Get this site's location info for tooltip
                this_site_city = site.get('city', '') or ''
                this_site_location_name = site.get('location_name', '') or ''
                
                # Build tooltip data structure
                tooltip_data = {
                    'site_count': site_count,
                    'this_site': {
                        'location_id': location_id,
                        'location_name': this_site_location_name[:40],
                        'city': this_site_city,
                        'state': state,
                        'hours': round(hours_this_site, 1)
                    },
                    'other_sites': [
                        {
                            'location_id': site_info['location_id'],
                            'location_name': (site_info['location_name'] or '')[:40],
                            'city': site_info.get('city', '') or '',
                            'state': site_info['state'] or '',
                            'hours': round(site_info['hours'], 1)
                        }
                        for site_info in other_sites[:5]
                    ],
                    'more_count': max(0, len(other_sites) - 5),
                    'total_hours': round(hours_all_sites, 1)
                }
                
                # Escape for HTML attribute
                tooltip_json = json.dumps(tooltip_data).replace('"', '&quot;')
                
                hours_display = f'''<div class="hours-cell has-tooltip" data-tooltip="{tooltip_json}" style="cursor:pointer;position:relative;">
                    <span style="font-weight:700;">{hours_this_site:.1f}</span> / <span style="color:#3b82f6;font-weight:900;">{hours_all_sites:.1f}</span>
                    <span style="display:inline-block;background:#3b82f6;color:white;font-size:9px;padding:1px 4px;border-radius:3px;margin-left:4px;">+{site_count-1}</span>
                </div>'''
            else:
                hours_display = f"{hours_this_site:.1f} / {hours_all_sites:.1f}"
            
            # Calculate available capacity (40 hour limit) - BASED ON ALL SITES
            available_capacity = 40.0 - hours_all_sites
            
            if available_capacity > 0:
                capacity_display = f"<span style='color: #10b981; font-weight: 700;'>+{available_capacity:.1f}</span>"
            elif available_capacity == 0:
                capacity_display = f"<span style='color: #3b82f6; font-weight: 700;'>At Cap</span>"
            else:
                capacity_display = f"<span style='color: #dc2626; font-weight: 700;'>{available_capacity:.1f}</span>"
            
            # Build day availability string with aligned days and proper logic
            day_availability_parts = []
            
            # Check if employee has available capacity (under 40 hours total)
            has_capacity = hours_all_sites < 40.0
            
            for day_idx in range(7):
                hours = day_of_week_hours[eid].get(day_idx, 0.0)
                day_label = day_abbrev[day_idx]
                
                if hours > 0:
                    # Day is scheduled - check if it has overtime
                    if has_daily_ot_rules and hours > 8.0:
                        # RED BOX for OT days (>8 hours in CA/AK/NV/CO)
                        day_availability_parts.append(
                            f'<span style="display: inline-block; width: 45px; background: #dc2626; color: white; padding: 2px 4px; border-radius: 3px; font-weight: 700; text-align: center;">{day_label}:{hours:.1f}</span>'
                        )
                    else:
                        # Regular scheduled hours (≤8)
                        day_availability_parts.append(
                            f'<span style="display: inline-block; width: 45px; text-align: center;">{day_label}:{hours:.0f}</span>'
                        )
                else:
                    # Day is NOT scheduled
                    if has_capacity:
                        # GREEN BOX for available days (only when employee has capacity)
                        day_availability_parts.append(
                            f'<span style="display: inline-block; width: 45px; background: #10b981; color: white; padding: 2px 4px; border-radius: 3px; text-align: center;">{day_label}:–</span>'
                        )
                    else:
                        # Regular display (no green) when employee is at/over capacity
                        day_availability_parts.append(
                            f'<span style="display: inline-block; width: 45px; text-align: center; color: #9ca3af;">{day_label}:–</span>'
                        )
            
            # Keep all days in a single row
            day_availability = " ".join(day_availability_parts)
            
            # Make employee name clickable
            emp_name = emp.get("employee_name", "N/A")
            emp_name_link = f'<a href="#employee-detail-{location_id}-{eid}" style="color: #2563eb; text-decoration: none; font-weight: 600;">{emp_name}</a>'
            
            row = [
                f'<div style="text-align: center;">{eid}</div>',
                f'<div>{emp_name_link}</div>',
                tenure_display,
                f'<div style="text-align: center;">{emp["employee_status"]}</div>',
                f'<div style="text-align: center;">{hours_display}</div>',
                f'<div style="text-align: center; font-family: monospace; font-size: 11px;">{ot_display}</div>',
                f'<div style="text-align: center; {total_ot_color}">{total_ot:.1f}</div>',
                f'<div style="text-align: center;">{capacity_display}</div>',
                f'<div style="text-align: center; font-family: monospace; font-size: 12px; line-height: 1.6;">{day_availability}</div>',
                f'<div style="text-align: center;">{usage_badge}</div>',
                f'<div style="text-align: center; font-size: 16px;">{training_icon}</div>',
            ]
            rows.append(row)
        
        # CSS and JavaScript for tooltip (rendered via JS, not inline HTML)
        tooltip_css = """
        <style>
        /* Tooltip container - rendered by JS */
        #employee-tooltip-container {
            display: none;
            position: fixed;
            z-index: 10000;
            background: #0f172a;
            border: 2px solid #3b82f6;
            border-radius: 8px;
            padding: 12px;
            min-width: 420px;
            max-width: 500px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            pointer-events: none;
        }
        #employee-tooltip-container::before {
            content: '';
            position: absolute;
            left: -10px;
            top: 50%;
            transform: translateY(-50%);
            border-width: 8px;
            border-style: solid;
            border-color: transparent #3b82f6 transparent transparent;
        }
        .hours-cell.has-tooltip {
            cursor: pointer;
        }
        </style>
        
        <!-- Global tooltip container -->
        <div id="employee-tooltip-container"></div>
        
        <script>
        (function() {
            const tooltipContainer = document.getElementById('employee-tooltip-container');
            
            function showTooltip(e) {
                const cell = e.currentTarget;
                const data = JSON.parse(cell.getAttribute('data-tooltip'));
                
                if (!data) return;
                
                // Build tooltip HTML - include location name/city
                let otherRows = '';
                data.other_sites.forEach(site => {
                    // Combine location_name and city for display
                    const locationDisplay = site.location_name || site.city || '';
                    otherRows += '<tr style="background:#1e293b;"><td style="padding:6px 8px;border-bottom:1px solid #374151;color:#e5e7eb;">' + site.location_id + '</td><td style="padding:6px 8px;border-bottom:1px solid #374151;color:#cbd5e1;">' + locationDisplay + '</td><td style="padding:6px 8px;border-bottom:1px solid #374151;color:#e5e7eb;">' + site.state + '</td><td style="padding:6px 8px;border-bottom:1px solid #374151;text-align:right;font-weight:700;color:#f59e0b;">' + site.hours + '</td></tr>';
                });
                
                if (data.more_count > 0) {
                    otherRows += '<tr><td colspan="4" style="padding:6px 8px;color:#9ca3af;font-style:italic;background:#0f172a;">...and ' + data.more_count + ' more</td></tr>';
                }
                
                // Build THIS SITE location display
                const thisSiteLocation = data.this_site.location_name || data.this_site.city || 'THIS SITE';
                
                tooltipContainer.innerHTML = `
                    <div style="font-weight:700;margin-bottom:10px;color:#3b82f6;font-size:13px;">📍 Scheduled at ${data.site_count} Sites</div>
                    <table style="width:100%;font-size:11px;border-collapse:collapse;table-layout:fixed;">
                        <colgroup>
                            <col style="width:50px;">
                            <col style="width:220px;">
                            <col style="width:35px;">
                            <col style="width:45px;">
                        </colgroup>
                        <thead><tr style="background:#374151;color:white;"><th style="padding:6px 8px;text-align:left;font-weight:700;">Site</th><th style="padding:6px 8px;text-align:left;font-weight:700;">Location</th><th style="padding:6px 8px;text-align:left;font-weight:700;">ST</th><th style="padding:6px 8px;text-align:right;font-weight:700;">Hrs</th></tr></thead>
                        <tbody>
                            <tr style="background:linear-gradient(145deg, #3b82f6 0%, #2563eb 100%);">
                                <td style="padding:8px;font-weight:900;color:white;">${data.this_site.location_id}</td>
                                <td style="padding:8px;color:white;word-wrap:break-word;"><span style="font-weight:700;">${thisSiteLocation}</span><br><span style="font-size:9px;opacity:0.8;">⭐ THIS SITE</span></td>
                                <td style="padding:8px;color:white;font-weight:600;">${data.this_site.state}</td>
                                <td style="padding:8px;text-align:right;color:#fef08a;font-weight:900;font-size:12px;">${data.this_site.hours}</td>
                            </tr>
                            ${otherRows}
                        </tbody>
                        <tfoot><tr style="background:#374151;"><td colspan="3" style="padding:8px;color:white;font-weight:700;">TOTAL</td><td style="padding:8px;text-align:right;color:#10b981;font-weight:900;font-size:12px;">${data.total_hours}</td></tr></tfoot>
                    </table>
                `;
                
                // Position tooltip
                const rect = cell.getBoundingClientRect();
                tooltipContainer.style.left = (rect.right + 10) + 'px';
                tooltipContainer.style.top = (rect.top + rect.height/2) + 'px';
                tooltipContainer.style.transform = 'translateY(-50%)';
                tooltipContainer.style.display = 'block';
            }
            
            function hideTooltip() {
                tooltipContainer.style.display = 'none';
            }
            
            // Attach event listeners (use event delegation for sorting compatibility)
            document.addEventListener('mouseover', function(e) {
                const cell = e.target.closest('.hours-cell.has-tooltip');
                if (cell && cell.getAttribute('data-tooltip')) {
                    showTooltip({ currentTarget: cell });
                }
            });
            
            document.addEventListener('mouseout', function(e) {
                const cell = e.target.closest('.hours-cell.has-tooltip');
                if (cell) {
                    hideTooltip();
                }
            });
        })();
        </script>
        """
        
        # Use build_table_with_controls for search, sort, and export features
        table_html = build_table_with_controls(
            table_id=f'employee-table-{location_id}',
            search_box_id=f'employee-search-{location_id}',
            headers=headers,
            rows=rows,
            export_filename=f'employee_schedule_site_{location_id}.csv'
        )
        
        # Build detailed employee schedules
        employee_schedules_html = _build_employee_schedules(employees, by_emp, state, location_id)
        
        # Add legend for day availability
        legend_html = """
        <div style="margin-top: 10px; padding: 10px 15px; background: linear-gradient(145deg, #f9fafb 0%, #f3f4f6 100%); border-radius: 8px; border: 1px solid #e5e7eb;">
            <strong style="color: #1f2937; font-size: 0.9em;">Day Availability Legend:</strong>
            <span style="margin-left: 15px; color: #6b7280;">
                <span style="background: #10b981; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">Day:–</span> = Available day (employee has capacity)
            </span>
            <span style="margin-left: 15px; color: #6b7280;">
                Day:8 = Regular hours (≤8 hrs)
            </span>
            <span style="margin-left: 15px; color: #6b7280;">
                <span style="background: #dc2626; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">Day:10</span> = Daily OT (>8 hrs in CA/AK/NV/CO)
            </span>
            <span style="margin-left: 15px; color: #9ca3af;">
                Day:– = Not scheduled (no capacity)
            </span>
        </div>
        """
        
        return f"""
        {tooltip_css}
        <div style="background: white; padding: 0; margin-top: 16px;">
            <h4 style="margin-bottom: 12px;">👥 Employee Schedule ({len(employees)} employees)</h4>
            {table_html}
            {legend_html}
            {employee_schedules_html}
        </div>
        """
        
    except Exception as e:
        return build_info_box(
            "Error Loading Employee Data",
            f"Failed to load employee schedules: {str(e)}",
            'critical'
        )

def _build_employee_schedules(employees: List[Dict], by_emp: Dict, state: str, location_id: str) -> str:
    """Build detailed daily schedules for each employee."""
    
    if not by_emp:
        return ""
    
    from datetime import datetime
    
    def _d(s: str) -> datetime:
        return datetime.strptime(s, "%Y-%m-%d")
    
    has_daily_ot_rules = state in ['CA', 'AK', 'NV', 'CO']
    has_double_time = state == 'CA'
    
    schedules_html = """
    <div style="margin-top: 40px; border-top: 3px solid #3b82f6; padding-top: 20px;">
        <h3 style="color: #1f2937; margin-bottom: 20px;">📅 Detailed Employee Schedules</h3>
        <p style="color: #6b7280; margin-bottom: 30px;">
            <strong>Legend:</strong> 
            <span style="margin-right: 15px;">Regular = Straight time</span>
            <span style="margin-right: 15px;">D = Daily OT (hrs 9-12)</span>
            <span style="margin-right: 15px;">DT = Double Time (hrs 13+)</span>
            <span>W = Weekly OT (regular hrs converted once week >40)</span>
        </p>
    """
    
    for emp in employees:
        eid = emp['employee_id']
        emp_name = emp.get('employee_name', f'Employee {eid}')
        
        if eid not in by_emp:
            continue
        
        days = sorted(by_emp[eid].keys(), key=_d)
        
        # Calculate daily breakdown
        per_day = []
        for day_str in days:
            hours = by_emp[eid][day_str]
            
            regular = 0.0
            daily_ot = 0.0
            double_t = 0.0
            
            if has_daily_ot_rules:
                if has_double_time:
                    # CA: 1-8 regular, 9-12 daily OT, 13+ double time
                    if hours > 12.0:
                        double_t = hours - 12.0
                        daily_ot = 4.0
                        regular = 8.0
                    elif hours > 8.0:
                        daily_ot = hours - 8.0
                        regular = 8.0
                    else:
                        regular = hours
                else:
                    # AK, NV, CO: 1-8 regular, 9+ daily OT
                    if hours > 8.0:
                        daily_ot = hours - 8.0
                        regular = 8.0
                    else:
                        regular = hours
            else:
                # No daily OT rules
                regular = hours
            
            per_day.append({
                "date": day_str,
                "total": round(hours, 2),
                "regular": round(regular, 2),
                "daily_ot": round(daily_ot, 2),
                "double_time": round(double_t, 2),
                "weekly_ot": 0.0,
            })
        
        # Calculate weekly OT (convert regular hours from last day backward)
        total_week_hours = sum(r["total"] for r in per_day)
        hours_over_40 = max(0.0, total_week_hours - 40.0)
        
        remaining = hours_over_40
        for r in reversed(per_day):
            if remaining <= 0.0:
                break
            take = min(remaining, r["regular"])
            r["regular"] = round(r["regular"] - take, 2)
            r["weekly_ot"] = round(r["weekly_ot"] + take, 2)
            remaining -= take
        
        # Build table for this employee
        totals_regular = sum(r["regular"] for r in per_day)
        totals_daily_ot = sum(r["daily_ot"] for r in per_day)
        totals_double_time = sum(r["double_time"] for r in per_day)
        totals_weekly_ot = sum(r["weekly_ot"] for r in per_day)
        
        schedules_html += f"""
        <div id="employee-detail-{location_id}-{eid}" style="margin-bottom: 30px; border: 2px solid #e5e7eb; border-radius: 8px; padding: 20px; background: linear-gradient(145deg, #ffffff 0%, #f9fafb 100%);">
            <h4 style="color: #1f2937; margin-bottom: 10px;">
                👤 {emp_name} (ID: {eid})
            </h4>
            <p style="color: #6b7280; margin-bottom: 15px;">
                <strong>Total Weekly Hours (this site):</strong> {total_week_hours:.1f}
            </p>
            
            <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                <thead style="background: linear-gradient(145deg, #374151 0%, #1f2937 100%); color: white;">
                    <tr>
                        <th style="padding: 10px; border: 1px solid #4b5563; text-align: left;">DATE</th>
                        <th style="padding: 10px; border: 1px solid #4b5563; text-align: center;">HOURS SCHEDULED</th>
                        <th style="padding: 10px; border: 1px solid #4b5563; text-align: center;">REGULAR</th>
        """
        
        if has_daily_ot_rules:
            schedules_html += """<th style="padding: 10px; border: 1px solid #4b5563; text-align: center;">D</th>"""
        
        if has_double_time:
            schedules_html += """<th style="padding: 10px; border: 1px solid #4b5563; text-align: center;">DT</th>"""
        
        schedules_html += """
                        <th style="padding: 10px; border: 1px solid #4b5563; text-align: center;">W</th>
                        <th style="padding: 10px; border: 1px solid #4b5563; text-align: left;">EXPLANATION</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        # Build rows
        for r in per_day:
            expl = []
            if r["double_time"] > 0:
                expl.append("DT for hours >12.")
            if r["daily_ot"] > 0:
                expl.append("D for hours 9-12." if has_double_time else "D for hours >8.")
            if r["weekly_ot"] > 0:
                expl.append("W from regular once week >40.")
            if not expl:
                expl.append("All within regular time.")
            
            schedules_html += f"""
                    <tr style="background: white;">
                        <td style="padding: 8px; border: 1px solid #e5e7eb;">{r['date']}</td>
                        <td style="padding: 8px; border: 1px solid #e5e7eb; text-align: center; font-weight: 700;">{r['total']:.2f}</td>
                        <td style="padding: 8px; border: 1px solid #e5e7eb; text-align: center;">{r['regular']:.2f}</td>
            """
            
            if has_daily_ot_rules:
                daily_color = 'color: #f59e0b; font-weight: 700;' if r['daily_ot'] > 0 else ''
                schedules_html += f"""<td style="padding: 8px; border: 1px solid #e5e7eb; text-align: center; {daily_color}">{r['daily_ot']:.2f}</td>"""
            
            if has_double_time:
                dt_color = 'color: #dc2626; font-weight: 700;' if r['double_time'] > 0 else ''
                schedules_html += f"""<td style="padding: 8px; border: 1px solid #e5e7eb; text-align: center; {dt_color}">{r['double_time']:.2f}</td>"""
            
            w_color = 'color: #3b82f6; font-weight: 700;' if r['weekly_ot'] > 0 else ''
            schedules_html += f"""
                        <td style="padding: 8px; border: 1px solid #e5e7eb; text-align: center; {w_color}">{r['weekly_ot']:.2f}</td>
                        <td style="padding: 8px; border: 1px solid #e5e7eb; color: #6b7280; font-style: italic;">{' '.join(expl)}</td>
                    </tr>
            """
        
        # Totals row
        schedules_html += f"""
                    <tr style="background: linear-gradient(145deg, #f3f4f6 0%, #e5e7eb 100%); font-weight: 700;">
                        <td style="padding: 8px; border: 1px solid #4b5563;">Totals</td>
                        <td style="padding: 8px; border: 1px solid #4b5563; text-align: center;">{total_week_hours:.2f}</td>
                        <td style="padding: 8px; border: 1px solid #4b5563; text-align: center;">{totals_regular:.2f}</td>
        """
        
        if has_daily_ot_rules:
            schedules_html += f"""<td style="padding: 8px; border: 1px solid #4b5563; text-align: center; color: #f59e0b;">{totals_daily_ot:.2f}</td>"""
        
        if has_double_time:
            schedules_html += f"""<td style="padding: 8px; border: 1px solid #4b5563; text-align: center; color: #dc2626;">{totals_double_time:.2f}</td>"""
        
        schedules_html += f"""
                        <td style="padding: 8px; border: 1px solid #4b5563; text-align: center; color: #3b82f6;">{totals_weekly_ot:.2f}</td>
                        <td style="padding: 8px; border: 1px solid #4b5563;"></td>
                    </tr>
                </tbody>
            </table>
            <div style="margin-top: 10px; text-align: right;">
                <a href="#employee-table-{location_id}" style="color: #2563eb; text-decoration: none; font-size: 12px;">↑ Back to Employee Summary</a>
            </div>
        </div>
        """
    
    schedules_html += "</div>"
    return schedules_html

def _build_recommendations_section(pareto_sites: List[Dict]) -> str:
    """Build recommendations section."""
    
    critical_count = len([s for s in pareto_sites if s.get('ot_percentage', 0) >= 3])
    warning_count = len([s for s in pareto_sites if 1 <= s.get('ot_percentage', 0) < 3])
    
    recommendations_html = f"""
    <div class="section-inner">
        <h3>🎯 STRATEGIC RECOMMENDATIONS</h3>
        
        {build_info_box(
            "Priority Actions",
            f"<strong>{critical_count} sites</strong> require immediate intervention (≥3% OT). "
            f"<strong>{warning_count} sites</strong> need monitoring (1-3% OT). "
            f"Focus resources on highest-ranked sites for maximum impact.",
            'critical' if critical_count > 0 else 'warning'
        )}
        
        <h4>Recommended Actions</h4>
        <div class="actions-container">
            <div class="action-item action-critical">
                <div class="action-icon">🚨</div>
                <div class="action-content">
                    <div class="action-title">Immediate: Address Critical Sites</div>
                    <div class="action-description">
                        Review top 5 Pareto sites for quick wins. Analyze root causes and implement 
                        corrective actions within 1 week.
                    </div>
                </div>
            </div>
            <div class="action-item action-warning">
                <div class="action-icon">📊</div>
                <div class="action-content">
                    <div class="action-title">Short-term: Optimize Scheduling</div>
                    <div class="action-description">
                        Redistribute workload across warning-status sites. Evaluate cross-training 
                        opportunities and flexible scheduling options.
                    </div>
                </div>
            </div>
            <div class="action-item action-info">
                <div class="action-icon">💡</div>
                <div class="action-content">
                    <div class="action-title">Long-term: Capacity Planning</div>
                    <div class="action-description">
                        Conduct ROI analysis on permanent staffing increases vs. sustained OT costs. 
                        Consider seasonal hiring patterns.
                    </div>
                </div>
            </div>
        </div>
        
        <h4>Success Metrics</h4>
        <ul style="margin-left: 24px; line-height: 2;">
            <li><strong>Primary Goal:</strong> Reduce OT% in top 10 Pareto sites by 25% within 30 days</li>
            <li><strong>Secondary Goal:</strong> Bring all RED status sites to YELLOW within 60 days</li>
            <li><strong>Tertiary Goal:</strong> Maintain GREEN status for current low-OT sites</li>
        </ul>
    </div>
    """
    
    return f"""
    <div id="section-recommendations" class="section">
        <div class="section-header" onclick="toggleSection('section-recommendations')">
            <span class="section-toggle">▶</span>
            <span class="section-title">💡 RECOMMENDATIONS</span>
        </div>
        <div class="section-content">
            {recommendations_html}
        </div>
    </div>
    """


# =============================
# 🔧 EXPORT FUNCTION
# =============================

def export_pareto_html_report(
    start_date: str,
    end_date: str,
    mode: str,
    output_path: str,
    customer_code: Optional[int] = None,
    region: Optional[str] = None,
    selected_locations: Optional[List[str]] = None
) -> str:
    """
    Generate and save Pareto report as HTML file.
    
    Returns:
        Path to saved HTML file
    """
    html_content = generate_pareto_optimization_html(
        start_date=start_date,
        end_date=end_date,
        mode=mode,
        customer_code=customer_code,
        region=region,
        selected_locations=selected_locations
    )
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return output_path

def _build_site_capacity_section(all_sites: List[Dict], pareto_site_ids: List[str] = None) -> str:
    """Build Site Capacity Analysis section with KPI cards, visualizations, site cards, and table.
    
    Args:
        all_sites: List of all site dictionaries with capacity data
        pareto_site_ids: List of site IDs that are in the Pareto analysis (80/20 sites)
    
    Returns:
        HTML string for Site Capacity section
    """
    
    if not all_sites:
        return ""
    
    # Convert pareto_site_ids to a set for O(1) lookup
    pareto_set = set(str(sid) for sid in (pareto_site_ids or []))
    
    # Calculate capacity metrics for each site
    capacity_sites = []
    for site in all_sites:
        state = site.get('state', '')
        total_hours = float(site.get('total_hours', 0) or 0)
        employee_count = int(site.get('employee_count', 0) or 0)
        fte_needed = int(site.get('fte_needed', 0) or 0)
        ot_hours = float(site.get('total_ot_exposure', 0) or 0)
        ot_pct = float(site.get('ot_percentage', 0) or 0)
        
        # Target hours per week (32 for CA, 36 for others)
        target_hrs = 32 if state == 'CA' else 36
        
        # Calculate gap and utilization
        gap = employee_count - fte_needed
        avg_hrs_per_emp = round(total_hours / employee_count, 1) if employee_count > 0 else 0
        utilization = round((avg_hrs_per_emp / target_hrs) * 100, 1) if target_hrs > 0 else 0
        
        # Determine status
        if gap < 0:
            capacity_status = 'understaffed'
            capacity_icon = '🔴'
        elif gap <= 1:
            capacity_status = 'optimal'
            capacity_icon = '✅'
        else:
            capacity_status = 'overstaffed'
            capacity_icon = '🔵'
        
        capacity_sites.append({
            **site,
            'target_hrs': target_hrs,
            'gap': gap,
            'avg_hrs_per_emp': avg_hrs_per_emp,
            'utilization': utilization,
            'capacity_status': capacity_status,
            'capacity_icon': capacity_icon,
            'ot_hours': ot_hours,
            'ot_pct': ot_pct,
            'in_pareto': str(site.get('location_id', '')) in pareto_set,
        })
    
    # Sort by gap (most understaffed first)
    capacity_sites.sort(key=lambda x: x['gap'])
    
    # Calculate summary metrics
    total_sites = len(capacity_sites)
    understaffed_sites = [s for s in capacity_sites if s['capacity_status'] == 'understaffed']
    optimal_sites = [s for s in capacity_sites if s['capacity_status'] == 'optimal']
    overstaffed_sites = [s for s in capacity_sites if s['capacity_status'] == 'overstaffed']
    
    understaffed_count = len(understaffed_sites)
    optimal_count = len(optimal_sites)
    overstaffed_count = len(overstaffed_sites)
    
    total_gap = sum(s['gap'] for s in capacity_sites)
    avg_utilization = round(sum(s['utilization'] for s in capacity_sites) / total_sites, 1) if total_sites > 0 else 0
    
    # Calculate percentages
    understaffed_pct = round(understaffed_count / total_sites * 100, 1) if total_sites > 0 else 0
    optimal_pct = round(optimal_count / total_sites * 100, 1) if total_sites > 0 else 0
    overstaffed_pct = round(overstaffed_count / total_sites * 100, 1) if total_sites > 0 else 0
    
    # SVG Donut Chart calculations removed - visualizations disabled
    
    # Build KPI cards
    kpi_cards_html = f"""
    <div style="display: grid; grid-template-columns: repeat(6, 1fr); gap: 15px; margin-bottom: 25px;">
        <!-- Total Sites -->
        <div style="background: linear-gradient(145deg, #1e40af 0%, #3b82f6 100%); padding: 20px 15px; border-radius: 12px; text-align: center; box-shadow: 0 4px 15px rgba(30, 64, 175, 0.3);">
            <div style="color: rgba(255,255,255,0.8); font-size: 0.7em; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Total Sites</div>
            <div style="color: white; font-size: 2.2em; font-weight: 900;">{total_sites}</div>
            <div style="color: rgba(255,255,255,0.6); font-size: 0.7em; margin-top: 4px;">In Portfolio</div>
        </div>
        
        <!-- Understaffed -->
        <div style="background: linear-gradient(145deg, #dc2626 0%, #ef4444 100%); padding: 20px 15px; border-radius: 12px; text-align: center; box-shadow: 0 4px 15px rgba(220, 38, 38, 0.3);">
            <div style="color: rgba(255,255,255,0.8); font-size: 0.7em; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Sites Understaffed 🔴</div>
            <div style="color: white; font-size: 2.2em; font-weight: 900;">{understaffed_count}</div>
            <div style="color: rgba(255,255,255,0.6); font-size: 0.75em; margin-top: 4px;">{understaffed_pct}% of sites</div>
        </div>
        
        <!-- Optimal -->
        <div style="background: linear-gradient(145deg, #059669 0%, #10b981 100%); padding: 20px 15px; border-radius: 12px; text-align: center; box-shadow: 0 4px 15px rgba(5, 150, 105, 0.3);">
            <div style="color: rgba(255,255,255,0.8); font-size: 0.7em; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Sites Optimal ✅</div>
            <div style="color: white; font-size: 2.2em; font-weight: 900;">{optimal_count}</div>
            <div style="color: rgba(255,255,255,0.6); font-size: 0.75em; margin-top: 4px;">{optimal_pct}% of sites</div>
        </div>
        
        <!-- Overstaffed -->
        <div style="background: linear-gradient(145deg, #2563eb 0%, #3b82f6 100%); padding: 20px 15px; border-radius: 12px; text-align: center; box-shadow: 0 4px 15px rgba(37, 99, 235, 0.3);">
            <div style="color: rgba(255,255,255,0.8); font-size: 0.7em; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Sites Overstaffed 🔵</div>
            <div style="color: white; font-size: 2.2em; font-weight: 900;">{overstaffed_count}</div>
            <div style="color: rgba(255,255,255,0.6); font-size: 0.75em; margin-top: 4px;">{overstaffed_pct}% of sites</div>
        </div>
        
        <!-- Total FTE Gap -->
        <div style="background: linear-gradient(145deg, #7c3aed 0%, #a855f7 100%); padding: 20px 15px; border-radius: 12px; text-align: center; box-shadow: 0 4px 15px rgba(124, 58, 237, 0.3);">
            <div style="color: rgba(255,255,255,0.8); font-size: 0.7em; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Calculated Net FTE Gap</div>
            <div style="color: white; font-size: 2.2em; font-weight: 900;">{total_gap:+d}</div>
            <div style="color: rgba(255,255,255,0.6); font-size: 0.75em; margin-top: 4px;">{"Understaffed" if total_gap < 0 else "Overstaffed" if total_gap > 0 else "Balanced"}</div>
        </div>
        
        <!-- Avg Utilization -->
        <div style="background: linear-gradient(145deg, #ea580c 0%, #fb923c 100%); padding: 20px 15px; border-radius: 12px; text-align: center; box-shadow: 0 4px 15px rgba(234, 88, 12, 0.3);">
            <div style="color: rgba(255,255,255,0.8); font-size: 0.7em; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Avg Utilization</div>
            <div style="color: white; font-size: 2.2em; font-weight: 900;">{avg_utilization}%</div>
            <div style="color: rgba(255,255,255,0.6); font-size: 0.75em; margin-top: 4px;">Target: 80-100%</div>
        </div>
    </div>
    """
    
    # Visualizations removed per user request
    
    # Build site cards (only understaffed)
    site_cards_html = ""
    if understaffed_sites:
        cards_inner = ""
        for site in understaffed_sites[:12]:  # Show top 12 understaffed
            location_id = site['location_id']
            state = site.get('state', 'N/A')
            city = site.get('city', '')
            location_name = site.get('location_name', '')
            total_hours = site.get('total_hours', 0)
            ot_hours = site.get('ot_hours', 0)
            ot_pct = site.get('ot_pct', 0)
            employee_count = site.get('employee_count', 0)
            fte_needed = site.get('fte_needed', 0)
            target_hrs = site.get('target_hrs', 36)
            gap = site.get('gap', 0)
            avg_hrs = site.get('avg_hrs_per_emp', 0)
            utilization = site.get('utilization', 0)
            
            cards_inner += f"""
            <div class="site-card" style="background: linear-gradient(145deg, #ffffff 0%, #f1f5f9 100%); border-radius: 12px; cursor: pointer; transition: all 0.3s ease; position: relative; overflow: hidden; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2); border-left: 6px solid #dc2626;" onclick="navigateToSite('{location_id}')">
                <div style="position: absolute; top: 0; left: 0; right: 0; background: linear-gradient(145deg, #7f1d1d 0%, #991b1b 100%); color: white; padding: 8px 12px; font-size: 0.75em; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;">🔴 Understaffed</div>
                <div style="padding: 45px 15px 10px 15px; display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <div style="font-size: 1em; color: #1f2937;">Site <span style="color: #dc2626; font-weight: 900; font-size: 1.3em;">{location_id}</span></div>
                        <div style="font-size: 0.75em; color: #374151; margin-top: 2px; line-height: 1.3;">{location_name if location_name else city}</div>
                    </div>
                    <div style="font-size: 1.1em; font-weight: 900; color: #1f2937;">{state}</div>
                </div>
                <div style="padding: 10px 15px; display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                    <div style="background: #f8fafc; padding: 8px 10px; border-radius: 6px; text-align: center;">
                        <div style="font-size: 0.65em; color: #6b7280; text-transform: uppercase;">Hours Scheduled</div>
                        <div style="font-size: 1.1em; font-weight: 700; color: #1f2937;">{total_hours:,.0f}</div>
                    </div>
                    <div style="background: #f8fafc; padding: 8px 10px; border-radius: 6px; text-align: center;">
                        <div style="font-size: 0.65em; color: #6b7280; text-transform: uppercase;">Scheduled OT Hours</div>
                        <div style="font-size: 1.1em; font-weight: 700; color: #dc2626;">{ot_hours:,.1f}</div>
                        <div style="font-size: 0.6em; color: #dc2626;">{ot_pct:.1f}%</div>
                    </div>
                    <div style="background: #f8fafc; padding: 8px 10px; border-radius: 6px; text-align: center;">
                        <div style="font-size: 0.65em; color: #6b7280; text-transform: uppercase;">Current Employee Count</div>
                        <div style="font-size: 1.1em; font-weight: 700; color: #1f2937;">{employee_count}</div>
                    </div>
                    <div style="background: #f8fafc; padding: 8px 10px; border-radius: 6px; text-align: center;">
                        <div style="font-size: 0.65em; color: #6b7280; text-transform: uppercase;">Calculated FTE Needed</div>
                        <div style="font-size: 1.1em; font-weight: 700; color: #1f2937;">{fte_needed}</div>
                        <div style="font-size: 0.6em; color: #9ca3af;">({target_hrs} hrs/wk)</div>
                    </div>
                    <div style="background: #f8fafc; padding: 8px 10px; border-radius: 6px; text-align: center;">
                        <div style="font-size: 0.65em; color: #6b7280; text-transform: uppercase;">Additional Employees Needed</div>
                        <div style="font-size: 1.1em; font-weight: 700; color: #dc2626;">{gap}</div>
                    </div>
                    <div style="background: #f8fafc; padding: 8px 10px; border-radius: 6px; text-align: center;">
                        <div style="font-size: 0.65em; color: #6b7280; text-transform: uppercase;">Current Avg Hrs/Emp</div>
                        <div style="font-size: 1.1em; font-weight: 700; color: #dc2626;">{avg_hrs:.1f}</div>
                    </div>
                </div>
                <div style="padding: 0 15px 10px 15px;">
                    <div style="display: block; text-align: center; padding: 6px 12px; border-radius: 6px; font-size: 0.8em; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; background: linear-gradient(145deg, #fef2f2 0%, #fee2e2 100%); color: #dc2626; border: 2px solid #fecaca;">
                        🔴 Understaffed ({utilization:.0f}% Utilization)
                    </div>
                </div>
                <div style="display: flex; align-items: center; justify-content: center; gap: 8px; padding: 12px; background: {'linear-gradient(145deg, #fef3c7 0%, #fde68a 100%)' if site.get('in_pareto') else 'linear-gradient(145deg, #f3f4f6 0%, #e5e7eb 100%)'}; border-top: 1px solid #e5e7eb;">
                    <span style="font-size: 1.1em;">{'🎯' if site.get('in_pareto') else '◯'}</span>
                    <span style="font-weight: 700; font-size: 0.85em; color: {'#92400e' if site.get('in_pareto') else '#6b7280'}; text-transform: uppercase; letter-spacing: 1px;">
                        In Pareto: {'Yes' if site.get('in_pareto') else 'No'}
                    </span>
                </div>
            </div>
            """
        
        site_cards_html = f"""
        <div style="margin-bottom: 25px;">
            <div style="display: flex; align-items: center; justify-content: center; gap: 15px; margin-bottom: 20px; padding: 12px 20px; background: linear-gradient(145deg, #374151 0%, #1f2937 100%); border-radius: 8px;">
                <span style="font-size: 1.5em;">⚠️</span>
                <div style="color: #fbbf24; font-size: 1.3em; font-weight: 900; text-transform: uppercase; letter-spacing: 2px;">Sites Requiring Additional Staffing</div>
                <span style="font-size: 1.5em;">⚠️</span>
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px;">
                {cards_inner}
            </div>
        </div>
        """
    
    # Build unique values for filters
    unique_sites = sorted(set(str(s['location_id']) for s in capacity_sites))
    unique_locations = sorted(set(s.get('location_name', s.get('city', '')) for s in capacity_sites if s.get('location_name') or s.get('city')))
    unique_states = sorted(set(s.get('state', '') for s in capacity_sites if s.get('state')))
    
    site_options = ''.join([f'<option value="{s}">{s}</option>' for s in unique_sites])
    location_options = ''.join([f'<option value="{loc}">{loc[:30]}...</option>' if len(loc) > 30 else f'<option value="{loc}">{loc}</option>' for loc in unique_locations])
    state_options = ''.join([f'<option value="{s}">{s}</option>' for s in unique_states])
    
    # Build table rows
    table_rows = ""
    for site in capacity_sites:
        location_id = site['location_id']
        location_name = site.get('location_name', site.get('city', 'N/A'))
        state = site.get('state', 'N/A')
        total_hours = site.get('total_hours', 0)
        ot_hours = site.get('ot_hours', 0)
        ot_pct = site.get('ot_pct', 0)
        employee_count = site.get('employee_count', 0)
        fte_needed = site.get('fte_needed', 0)
        gap = site.get('gap', 0)
        avg_hrs = site.get('avg_hrs_per_emp', 0)
        utilization = site.get('utilization', 0)
        status = site.get('capacity_status', 'optimal')
        icon = site.get('capacity_icon', '✅')
        
        # Color coding
        gap_color = '#dc2626' if gap < 0 else '#10b981' if gap <= 1 else '#3b82f6'
        util_color = '#dc2626' if utilization > 100 else '#10b981' if utilization >= 80 else '#3b82f6'
        
        # Utilization bar
        bar_width = min(utilization, 150)  # Cap at 150% for display
        bar_class = 'util-low' if utilization > 100 else 'util-optimal' if utilization >= 80 else 'util-high'
        bar_bg = '#dc2626' if utilization > 100 else '#10b981' if utilization >= 80 else '#3b82f6'
        
        # Status badge
        if status == 'understaffed':
            badge_style = 'background: #fef2f2; color: #dc2626; border: 1px solid #fecaca;'
        elif status == 'optimal':
            badge_style = 'background: #ecfdf5; color: #059669; border: 1px solid #a7f3d0;'
        else:
            badge_style = 'background: #eff6ff; color: #2563eb; border: 1px solid #bfdbfe;'
        
        in_pareto = site.get('in_pareto', False)
        pareto_display = '🎯 Yes' if in_pareto else 'No'
        pareto_style = 'background: #fef3c7; color: #92400e; font-weight: 700;' if in_pareto else 'color: #9ca3af;'
        
        table_rows += f"""
        <tr data-status="{status}" data-site="{location_id}" data-location="{location_name}" data-state="{state}" data-pareto="{'yes' if in_pareto else 'no'}">
            <td style="padding: 12px 10px; border-bottom: 1px solid #e5e7eb; background: white;"><a href="#subsection-{location_id}" style="color: #2563eb; font-weight: 700; text-decoration: none;">{location_id}</a></td>
            <td style="padding: 12px 10px; border-bottom: 1px solid #e5e7eb; background: white; font-size: 0.85em;">{location_name[:25]}{'...' if len(str(location_name)) > 25 else ''}</td>
            <td style="padding: 12px 10px; border-bottom: 1px solid #e5e7eb; background: white; text-align: center;">{state}</td>
            <td style="padding: 12px 10px; border-bottom: 1px solid #e5e7eb; background: white; text-align: right;">{total_hours:,.0f}</td>
            <td style="padding: 12px 10px; border-bottom: 1px solid #e5e7eb; background: white; text-align: right; color: #dc2626; font-weight: 600;">{ot_hours:,.1f}</td>
            <td style="padding: 12px 10px; border-bottom: 1px solid #e5e7eb; background: white; text-align: right; color: #dc2626;">{ot_pct:.1f}%</td>
            <td style="padding: 12px 10px; border-bottom: 1px solid #e5e7eb; background: white; text-align: center;">{employee_count}</td>
            <td style="padding: 12px 10px; border-bottom: 1px solid #e5e7eb; background: white; text-align: center;">{fte_needed}</td>
            <td style="padding: 12px 10px; border-bottom: 1px solid #e5e7eb; background: white; text-align: center; color: {gap_color}; font-weight: 700;">{gap:+d}</td>
            <td style="padding: 12px 10px; border-bottom: 1px solid #e5e7eb; background: white; text-align: right; color: {util_color}; font-weight: 600;">{avg_hrs:.1f}</td>
            <td style="padding: 12px 10px; border-bottom: 1px solid #e5e7eb; background: white;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <div style="width: 80px; height: 20px; background: #e5e7eb; border-radius: 4px; overflow: hidden;">
                        <div style="height: 100%; width: {min(bar_width, 100)}%; background: {bar_bg}; border-radius: 4px;"></div>
                    </div>
                    <span style="color: {util_color}; font-weight: 600; font-size: 0.85em;">{utilization:.0f}%</span>
                </div>
            </td>
            <td style="padding: 12px 10px; border-bottom: 1px solid #e5e7eb; background: white; text-align: center;">
                <span style="display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 0.75em; font-weight: 700; text-transform: uppercase; {badge_style}">{icon} {status.title()}</span>
            </td>
            <td style="padding: 12px 10px; border-bottom: 1px solid #e5e7eb; background: white; text-align: center;">
                <span style="padding: 4px 10px; border-radius: 6px; font-size: 0.8em; {pareto_style}">{pareto_display}</span>
            </td>
        </tr>
        """
    
    # Filter and table HTML
    filter_table_html = f"""
    <h3 style="color: white; margin-bottom: 15px;">📋 Detailed Capacity Matrix</h3>
    
    <div style="margin-bottom: 20px; padding: 15px; background: linear-gradient(145deg, #f9fafb 0%, #f3f4f6 100%); border-radius: 8px; border: 2px solid #3b82f6;">
        <div style="display: flex; flex-wrap: wrap; gap: 15px; align-items: center; justify-content: space-between;">
            <div style="display: flex; flex-wrap: wrap; gap: 10px; align-items: center;">
                <div>
                    <label style="font-weight: 700; color: #1f2937; font-size: 0.85em; display: block; margin-bottom: 4px;">Status:</label>
                    <select id="capacity-status-filter" onchange="filterCapacityTable()" style="padding: 8px 12px; border-radius: 6px; border: 2px solid #3b82f6; background: white; font-weight: 600; cursor: pointer; min-width: 150px;">
                        <option value="all">All Status</option>
                        <option value="understaffed">🔴 Understaffed</option>
                        <option value="optimal">✅ Optimal</option>
                        <option value="overstaffed">🔵 Overstaffed</option>
                    </select>
                </div>
                <div>
                    <label style="font-weight: 700; color: #1f2937; font-size: 0.85em; display: block; margin-bottom: 4px;">Site:</label>
                    <select id="capacity-site-filter" onchange="filterCapacityTable()" style="padding: 8px 12px; border-radius: 6px; border: 2px solid #3b82f6; background: white; font-weight: 600; cursor: pointer; min-width: 120px;">
                        <option value="all">All Sites</option>
                        {site_options}
                    </select>
                </div>
                <div>
                    <label style="font-weight: 700; color: #1f2937; font-size: 0.85em; display: block; margin-bottom: 4px;">Location:</label>
                    <select id="capacity-location-filter" onchange="filterCapacityTable()" style="padding: 8px 12px; border-radius: 6px; border: 2px solid #3b82f6; background: white; font-weight: 600; cursor: pointer; min-width: 180px;">
                        <option value="all">All Locations</option>
                        {location_options}
                    </select>
                </div>
                <div>
                    <label style="font-weight: 700; color: #1f2937; font-size: 0.85em; display: block; margin-bottom: 4px;">State:</label>
                    <select id="capacity-state-filter" onchange="filterCapacityTable()" style="padding: 8px 12px; border-radius: 6px; border: 2px solid #3b82f6; background: white; font-weight: 600; cursor: pointer; min-width: 100px;">
                        <option value="all">All States</option>
                        {state_options}
                    </select>
                </div>
                <div>
                    <label style="font-weight: 700; color: #1f2937; font-size: 0.85em; display: block; margin-bottom: 4px;">In Pareto:</label>
                    <select id="capacity-pareto-filter" onchange="filterCapacityTable()" style="padding: 8px 12px; border-radius: 6px; border: 2px solid #f59e0b; background: white; font-weight: 600; cursor: pointer; min-width: 120px;">
                        <option value="all">All Sites</option>
                        <option value="yes">🎯 Yes (80/20)</option>
                        <option value="no">No</option>
                    </select>
                </div>
            </div>
            <div id="capacity-counter" style="background: linear-gradient(145deg, #1e40af 0%, #3b82f6 100%); color: white; padding: 8px 16px; border-radius: 8px; font-weight: 700; font-size: 0.95em;">
                👥 Showing: <span id="capacity-visible-count">{total_sites}</span> / {total_sites}
            </div>
        </div>
    </div>
    
    <div style="overflow-x: auto; background: white; border-radius: 12px; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);">
        <table id="capacity-table" style="width: 100%; border-collapse: collapse; font-size: 0.9em;">
            <thead style="background: linear-gradient(145deg, #374151 0%, #1f2937 100%);">
                <tr>
                    <th style="color: white; padding: 14px 10px; text-align: left; font-weight: 700; text-transform: uppercase; font-size: 0.75em; cursor: pointer;" onclick="sortCapacityTable(0)">Site ⇅</th>
                    <th style="color: white; padding: 14px 10px; text-align: left; font-weight: 700; text-transform: uppercase; font-size: 0.75em; cursor: pointer;" onclick="sortCapacityTable(1)">Location ⇅</th>
                    <th style="color: white; padding: 14px 10px; text-align: center; font-weight: 700; text-transform: uppercase; font-size: 0.75em; cursor: pointer;" onclick="sortCapacityTable(2)">State ⇅</th>
                    <th style="color: white; padding: 14px 10px; text-align: right; font-weight: 700; text-transform: uppercase; font-size: 0.75em; cursor: pointer;" onclick="sortCapacityTable(3)">Hours ⇅</th>
                    <th style="color: white; padding: 14px 10px; text-align: right; font-weight: 700; text-transform: uppercase; font-size: 0.75em; cursor: pointer;" onclick="sortCapacityTable(4)">OT Hrs ⇅</th>
                    <th style="color: white; padding: 14px 10px; text-align: right; font-weight: 700; text-transform: uppercase; font-size: 0.75em; cursor: pointer;" onclick="sortCapacityTable(5)">OT % ⇅</th>
                    <th style="color: white; padding: 14px 10px; text-align: center; font-weight: 700; text-transform: uppercase; font-size: 0.75em; cursor: pointer;" onclick="sortCapacityTable(6)">Emps ⇅</th>
                    <th style="color: white; padding: 14px 10px; text-align: center; font-weight: 700; text-transform: uppercase; font-size: 0.75em; cursor: pointer;" onclick="sortCapacityTable(7)">FTE ⇅</th>
                    <th style="color: white; padding: 14px 10px; text-align: center; font-weight: 700; text-transform: uppercase; font-size: 0.75em; cursor: pointer;" onclick="sortCapacityTable(8)">Gap ⇅</th>
                    <th style="color: white; padding: 14px 10px; text-align: right; font-weight: 700; text-transform: uppercase; font-size: 0.75em; cursor: pointer;" onclick="sortCapacityTable(9)">Avg Hrs ⇅</th>
                    <th style="color: white; padding: 14px 10px; text-align: left; font-weight: 700; text-transform: uppercase; font-size: 0.75em; cursor: pointer;" onclick="sortCapacityTable(10)">Utilization ⇅</th>
                    <th style="color: white; padding: 14px 10px; text-align: center; font-weight: 700; text-transform: uppercase; font-size: 0.75em; cursor: pointer;" onclick="sortCapacityTable(11)">Status ⇅</th>
                    <th style="color: white; padding: 14px 10px; text-align: center; font-weight: 700; text-transform: uppercase; font-size: 0.75em; cursor: pointer;" onclick="sortCapacityTable(12)">Pareto ⇅</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </div>
    
    <div style="margin-top: 15px; padding: 12px 15px; background: linear-gradient(145deg, #f9fafb 0%, #f3f4f6 100%); border-radius: 8px; border: 1px solid #e5e7eb;">
        <strong style="color: #1f2937; font-size: 0.9em;">Status Thresholds:</strong>
        <span style="margin-left: 15px;"><span style="background: #fef2f2; color: #dc2626; padding: 3px 8px; border-radius: 4px; font-weight: 700; font-size: 0.8em;">🔴 Understaffed</span> Gap &lt; 0 (Utilization &gt;100%)</span>
        <span style="margin-left: 15px;"><span style="background: #ecfdf5; color: #059669; padding: 3px 8px; border-radius: 4px; font-weight: 700; font-size: 0.8em;">✅ Optimal</span> Gap 0 to +1 (Utilization 80-100%)</span>
        <span style="margin-left: 15px;"><span style="background: #eff6ff; color: #2563eb; padding: 3px 8px; border-radius: 4px; font-weight: 700; font-size: 0.8em;">🔵 Overstaffed</span> Gap &gt; +1 (Utilization &lt;80%)</span>
    </div>
    """
    
    # JavaScript for filtering
    filter_js = """
    <script>
    // Track sort state for each column
    let capacitySortState = {};
    
    function sortCapacityTable(columnIndex) {
        const table = document.getElementById('capacity-table');
        const tbody = table.getElementsByTagName('tbody')[0];
        const rows = Array.from(tbody.getElementsByTagName('tr'));
        
        // Toggle sort direction
        capacitySortState[columnIndex] = !capacitySortState[columnIndex];
        const ascending = capacitySortState[columnIndex];
        
        // Numeric columns: Hours(3), OT Hrs(4), OT %(5), Emps(6), FTE(7), Gap(8), Avg Hrs(9), Utilization(10)
        const numericColumns = [3, 4, 5, 6, 7, 8, 9, 10];
        const isNumeric = numericColumns.includes(columnIndex);
        
        rows.sort((a, b) => {
            let aVal = a.cells[columnIndex].textContent.trim();
            let bVal = b.cells[columnIndex].textContent.trim();
            
            if (isNumeric) {
                // Extract numeric value (remove %, commas, +/- signs for comparison)
                aVal = parseFloat(aVal.replace(/[,%+]/g, '').replace(/[^0-9.-]/g, '')) || 0;
                bVal = parseFloat(bVal.replace(/[,%+]/g, '').replace(/[^0-9.-]/g, '')) || 0;
                return ascending ? aVal - bVal : bVal - aVal;
            } else {
                // String comparison
                return ascending ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
            }
        });
        
        // Re-append sorted rows
        rows.forEach(row => tbody.appendChild(row));
    }
    
    function filterCapacityTable() {
        const statusFilter = document.getElementById('capacity-status-filter').value;
        const siteFilter = document.getElementById('capacity-site-filter').value;
        const locationFilter = document.getElementById('capacity-location-filter').value;
        const stateFilter = document.getElementById('capacity-state-filter').value;
        const paretoFilter = document.getElementById('capacity-pareto-filter').value;
        
        const table = document.getElementById('capacity-table');
        const rows = table.getElementsByTagName('tbody')[0].getElementsByTagName('tr');
        
        let visibleCount = 0;
        
        for (let i = 0; i < rows.length; i++) {
            const row = rows[i];
            const rowStatus = row.getAttribute('data-status');
            const rowSite = row.getAttribute('data-site');
            const rowLocation = row.getAttribute('data-location');
            const rowState = row.getAttribute('data-state');
            const rowPareto = row.getAttribute('data-pareto');
            
            let showRow = true;
            
            if (statusFilter !== 'all' && rowStatus !== statusFilter) {
                showRow = false;
            }
            if (siteFilter !== 'all' && rowSite !== siteFilter) {
                showRow = false;
            }
            if (locationFilter !== 'all' && rowLocation !== locationFilter) {
                showRow = false;
            }
            if (stateFilter !== 'all' && rowState !== stateFilter) {
                showRow = false;
            }
            if (paretoFilter !== 'all' && rowPareto !== paretoFilter) {
                showRow = false;
            }
            
            row.style.display = showRow ? '' : 'none';
            if (showRow) visibleCount++;
        }
        
        // Update counter
        document.getElementById('capacity-visible-count').textContent = visibleCount;
        
        // Update counter color
        const counter = document.getElementById('capacity-counter');
        const totalCount = rows.length;
        if (visibleCount === 0) {
            counter.style.background = 'linear-gradient(145deg, #6b7280 0%, #9ca3af 100%)';
        } else if (visibleCount < totalCount * 0.25) {
            counter.style.background = 'linear-gradient(145deg, #dc2626 0%, #ef4444 100%)';
        } else if (visibleCount < totalCount * 0.5) {
            counter.style.background = 'linear-gradient(145deg, #f59e0b 0%, #fbbf24 100%)';
        } else {
            counter.style.background = 'linear-gradient(145deg, #1e40af 0%, #3b82f6 100%)';
        }
    }
    </script>
    """
    
    # Assemble complete section
    return f"""
    <div id="section-site-capacity" class="section">
        <div class="section-header" onclick="toggleSection('section-site-capacity')">
            <span class="section-toggle">▶</span>
            <span class="section-title">📈 SITE CAPACITY ANALYSIS</span>
        </div>
        <div class="section-content">
            <div class="section-inner">
                {kpi_cards_html}
                {site_cards_html}
                {filter_table_html}
            </div>
        </div>
    </div>
    {filter_js}
    """


def _query_speed_to_post_data(region: str) -> tuple:
    """Query unscheduled employees data from APEX_NWS_Unscheduled table.
    
    Returns:
        Tuple of (ready_to_post_employees, pending_m1la_employees)
    """
    
    sql = f"""
WITH AllUnscheduled AS (
  SELECT
    region,
    employee_id,
    employee_name,
    employee_date_started,
    
    -- Training Completion Date
    MAX(IF(course_name = 'ONB101-ALL: Metro One LPSG - General Onboarding (All Employees)',
           course_completion_date, NULL)) AS m1la_completion_date,
    
    -- Training Status
    CASE 
      WHEN MAX(IF(course_name = 'ONB101-ALL: Metro One LPSG - General Onboarding (All Employees)',
                  course_completion_date, NULL)) IS NOT NULL 
      THEN 'Ready to Post'
      ELSE 'Pending M1LA'
    END AS training_status,
    
    -- Timeline Calculations
    DATE_DIFF(CURRENT_DATE(), employee_date_started, DAY) AS days_from_hire,
    
    -- Days to Complete Training (NULL if not complete)
    DATE_DIFF(
      MAX(IF(course_name = 'ONB101-ALL: Metro One LPSG - General Onboarding (All Employees)',
             course_completion_date, NULL)),
      employee_date_started,
      DAY
    ) AS days_to_training_complete,
    
    -- Aging (days since training complete - NULL if training not complete)
    DATE_DIFF(
      CURRENT_DATE(),
      MAX(IF(course_name = 'ONB101-ALL: Metro One LPSG - General Onboarding (All Employees)',
             course_completion_date, NULL)),
      DAY
    ) AS aging_days,
    
    -- Aging Category (BASED ON DAYS FROM START DATE)
    CASE 
      WHEN DATE_DIFF(CURRENT_DATE(), employee_date_started, DAY) >= 22 
      THEN '⚠️ Potential Dropout'
      WHEN DATE_DIFF(CURRENT_DATE(), employee_date_started, DAY) >= 14 
      THEN '🔴 Critical'
      WHEN DATE_DIFF(CURRENT_DATE(), employee_date_started, DAY) >= 7 
      THEN '🟡 Alert'
      ELSE '🟢 Normal'
    END AS aging_status
    
  FROM `{BQ_DATA_PROJECT_ID}.{BQ_DATASET_ID}.APEX_NWS_Unscheduled`
  WHERE region = '{region}'
  GROUP BY 
    region, employee_id, employee_name, employee_date_started
)
SELECT * FROM AllUnscheduled
ORDER BY 
  CASE 
    WHEN training_status = 'Ready to Post' THEN 1
    ELSE 2
  END,
  aging_days DESC NULLS LAST,
  region, 
  employee_id
"""
    
    try:
        all_data = execute_query(sql)
    except Exception as e:
        return [], []
    
    if not all_data:
        return [], []
    
    # Split into two groups
    ready_to_post = [emp for emp in all_data if emp.get('training_status') == 'Ready to Post']
    pending_m1la = [emp for emp in all_data if emp.get('training_status') == 'Pending M1LA']
    
    return ready_to_post, pending_m1la

def _build_speed_to_post_section(region: str) -> str:
    """Build Speed to Post Portfolio section for regional report - UNIFIED MATRIX.
    
    Args:
        region: Region name to filter unscheduled employees
    
    Returns:
        HTML string for Speed to Post section
    """
    
    # Query data
    ready_to_post, pending_m1la = _query_speed_to_post_data(region)
    
    # If no data, return empty
    if not ready_to_post and not pending_m1la:
        return ""
    
    # COMBINE ALL EMPLOYEES into one list
    all_employees = ready_to_post + pending_m1la
    
    # ⚠️ FILTER OUT EMPLOYEES OLDER THAN 90 DAYS (3 months)
    all_employees = [emp for emp in all_employees if emp.get('days_from_hire', 0) <= 90]
    ready_to_post = [emp for emp in ready_to_post if emp.get('days_from_hire', 0) <= 90]
    pending_m1la = [emp for emp in pending_m1la if emp.get('days_from_hire', 0) <= 90]
    
    # Calculate summary metrics (after filtering)
    total_unscheduled = len(all_employees)
    pending_count = len(pending_m1la)
    ready_count = len(ready_to_post)
    
    # Count aging categories (ALL employees based on days from start date)
    dropout_count = len([e for e in all_employees if e.get('days_from_hire', 0) >= 22])
    critical_count = len([e for e in all_employees if 14 <= e.get('days_from_hire', 0) < 22])
    alert_count = len([e for e in all_employees if 7 <= e.get('days_from_hire', 0) < 14])
    normal_count = len([e for e in all_employees if e.get('days_from_hire', 0) < 7])
    
    # Calculate averages (Ready to Post only)
    if ready_to_post:
        avg_days_hire = round(sum(e.get('days_from_hire', 0) for e in ready_to_post) / len(ready_to_post), 1)
        avg_days_training = round(sum(e.get('days_to_training_complete', 0) for e in ready_to_post) / len(ready_to_post), 1)
        avg_aging = round(sum(e.get('aging_days', 0) for e in ready_to_post) / len(ready_to_post), 1)
    else:
        avg_days_hire = avg_days_training = avg_aging = 0.0
    
    # Calculate percentages for charts
    pending_pct = round(pending_count/total_unscheduled*100, 1) if total_unscheduled > 0 else 0
    ready_pct = round(ready_count/total_unscheduled*100, 1) if total_unscheduled > 0 else 0
    
    # Calculate aging percentages (based on total, not just ready)
    dropout_pct = round(dropout_count/total_unscheduled*100, 1) if total_unscheduled > 0 else 0
    critical_pct = round(critical_count/total_unscheduled*100, 1) if total_unscheduled > 0 else 0
    alert_pct = round(alert_count/total_unscheduled*100, 1) if total_unscheduled > 0 else 0
    normal_pct = round(normal_count/total_unscheduled*100, 1) if total_unscheduled > 0 else 0
    
    # SVG Donut Chart calculations
    donut_radius = 70
    donut_circumference = 2 * 3.14159 * donut_radius
    ready_dash = (ready_pct / 100) * donut_circumference
    pending_dash = (pending_pct / 100) * donut_circumference
    
    # Build summary cards with KPI cards + visualizations
    summary_cards_html = f"""
    <!-- ROW 1: KPI CARDS -->
    <div style="display: grid; grid-template-columns: repeat(6, 1fr); gap: 15px; margin-bottom: 25px;">
        <!-- Total Unscheduled -->
        <div style="background: linear-gradient(145deg, #1e40af 0%, #3b82f6 100%); padding: 20px 15px; border-radius: 12px; text-align: center; box-shadow: 0 4px 15px rgba(30, 64, 175, 0.3);">
            <div style="color: rgba(255,255,255,0.8); font-size: 0.7em; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Total Unscheduled</div>
            <div style="color: white; font-size: 2.2em; font-weight: 900;">{total_unscheduled}</div>
            <div style="color: rgba(255,255,255,0.6); font-size: 0.7em; margin-top: 4px;">Last 90 Days</div>
        </div>
        
        <!-- Pending M1LA -->
        <div style="background: linear-gradient(145deg, #6b7280 0%, #9ca3af 100%); padding: 20px 15px; border-radius: 12px; text-align: center; box-shadow: 0 4px 15px rgba(107, 114, 128, 0.3);">
            <div style="color: rgba(255,255,255,0.8); font-size: 0.7em; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Pending M1LA</div>
            <div style="color: white; font-size: 2.2em; font-weight: 900;">{pending_count}</div>
            <div style="color: rgba(255,255,255,0.6); font-size: 0.75em; margin-top: 4px;">{pending_pct}% of total</div>
        </div>
        
        <!-- Ready to Post -->
        <div style="background: linear-gradient(145deg, #059669 0%, #10b981 100%); padding: 20px 15px; border-radius: 12px; text-align: center; box-shadow: 0 4px 15px rgba(5, 150, 105, 0.3);">
            <div style="color: rgba(255,255,255,0.8); font-size: 0.7em; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Ready to Post ⚡</div>
            <div style="color: white; font-size: 2.2em; font-weight: 900;">{ready_count}</div>
            <div style="color: rgba(255,255,255,0.6); font-size: 0.75em; margin-top: 4px;">{ready_pct}% of total</div>
        </div>
        
        <!-- Avg Days from Start -->
        <div style="background: linear-gradient(145deg, #7c3aed 0%, #a855f7 100%); padding: 20px 15px; border-radius: 12px; text-align: center; box-shadow: 0 4px 15px rgba(124, 58, 237, 0.3);">
            <div style="color: rgba(255,255,255,0.8); font-size: 0.7em; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Avg Days from Start</div>
            <div style="color: white; font-size: 2.2em; font-weight: 900;">{avg_days_hire}</div>
            <div style="color: rgba(255,255,255,0.6); font-size: 0.75em; margin-top: 4px;">days</div>
        </div>
        
        <!-- Avg Speed to Training -->
        <div style="background: linear-gradient(145deg, #0891b2 0%, #22d3ee 100%); padding: 20px 15px; border-radius: 12px; text-align: center; box-shadow: 0 4px 15px rgba(8, 145, 178, 0.3);">
            <div style="color: rgba(255,255,255,0.8); font-size: 0.7em; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Avg Speed to Training</div>
            <div style="color: white; font-size: 2.2em; font-weight: 900;">{avg_days_training}</div>
            <div style="color: rgba(255,255,255,0.6); font-size: 0.75em; margin-top: 4px;">days</div>
        </div>
        
        <!-- Avg Aging -->
        <div style="background: linear-gradient(145deg, #dc2626 0%, #f87171 100%); padding: 20px 15px; border-radius: 12px; text-align: center; box-shadow: 0 4px 15px rgba(220, 38, 38, 0.3);">
            <div style="color: rgba(255,255,255,0.8); font-size: 0.7em; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Avg Aging</div>
            <div style="color: white; font-size: 2.2em; font-weight: 900;">{avg_aging}</div>
            <div style="color: rgba(255,255,255,0.6); font-size: 0.75em; margin-top: 4px;">days post-training</div>
        </div>
    </div>
    
    <!-- ROW 2: VISUALIZATIONS -->
    <div style="display: grid; grid-template-columns: 1fr 1.5fr; gap: 20px; margin-bottom: 30px;">
        
        <!-- LEFT: Training Status Donut Chart -->
        <div style="background: linear-gradient(145deg, #1e293b 0%, #334155 100%); padding: 25px; border-radius: 16px; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);">
            <h4 style="color: white; margin: 0 0 20px 0; font-size: 1em; text-transform: uppercase; letter-spacing: 1px; text-align: center;">📊 Training Status</h4>
            
            <div style="display: flex; align-items: center; justify-content: center; gap: 30px;">
                <!-- SVG Donut -->
                <svg width="180" height="180" viewBox="0 0 180 180">
                    <!-- Background circle -->
                    <circle cx="90" cy="90" r="{donut_radius}" fill="none" stroke="#374151" stroke-width="20"/>
                    
                    <!-- Ready to Post (Green) - starts from top -->
                    <circle cx="90" cy="90" r="{donut_radius}" fill="none" 
                            stroke="#10b981" stroke-width="20"
                            stroke-dasharray="{ready_dash} {donut_circumference}"
                            stroke-dashoffset="0"
                            transform="rotate(-90 90 90)"
                            style="transition: stroke-dasharray 0.5s ease;"/>
                    
                    <!-- Pending (Gray) - continues after ready -->
                    <circle cx="90" cy="90" r="{donut_radius}" fill="none" 
                            stroke="#6b7280" stroke-width="20"
                            stroke-dasharray="{pending_dash} {donut_circumference}"
                            stroke-dashoffset="-{ready_dash}"
                            transform="rotate(-90 90 90)"
                            style="transition: stroke-dasharray 0.5s ease;"/>
                    
                    <!-- Center text -->
                    <text x="90" y="82" text-anchor="middle" fill="white" font-size="28" font-weight="900">{total_unscheduled}</text>
                    <text x="90" y="105" text-anchor="middle" fill="#9ca3af" font-size="12">TOTAL</text>
                </svg>
                
                <!-- Legend -->
                <div style="display: flex; flex-direction: column; gap: 15px;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <div style="width: 16px; height: 16px; background: #10b981; border-radius: 4px;"></div>
                        <div>
                            <div style="color: white; font-weight: 700; font-size: 1.1em;">{ready_count}</div>
                            <div style="color: #9ca3af; font-size: 0.8em;">Ready ({ready_pct}%)</div>
                        </div>
                    </div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <div style="width: 16px; height: 16px; background: #6b7280; border-radius: 4px;"></div>
                        <div>
                            <div style="color: white; font-weight: 700; font-size: 1.1em;">{pending_count}</div>
                            <div style="color: #9ca3af; font-size: 0.8em;">Pending ({pending_pct}%)</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- RIGHT: Aging Distribution Bar Chart -->
        <div style="background: linear-gradient(145deg, #1e293b 0%, #334155 100%); padding: 25px; border-radius: 16px; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);">
            <h4 style="color: white; margin: 0 0 20px 0; font-size: 1em; text-transform: uppercase; letter-spacing: 1px; text-align: center;">⚠️ Aging Distribution (Days from Start Date)</h4>
            
            <div style="display: flex; flex-direction: column; gap: 12px;">
                <!-- Normal (0-6) -->
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="width: 120px; color: #9ca3af; font-size: 0.85em; text-align: right;">🟢 Normal (0-6)</div>
                    <div style="flex: 1; background: #374151; border-radius: 6px; height: 32px; overflow: hidden; position: relative;">
                        <div style="background: linear-gradient(90deg, #059669 0%, #10b981 100%); height: 100%; width: {normal_pct}%; border-radius: 6px; transition: width 0.5s ease; display: flex; align-items: center; justify-content: flex-end; padding-right: 10px; min-width: 50px;">
                            <span style="color: white; font-weight: 700; font-size: 0.85em;">{normal_count}</span>
                        </div>
                    </div>
                    <div style="width: 50px; color: #10b981; font-weight: 700; font-size: 0.9em;">{normal_pct}%</div>
                </div>
                
                <!-- Alert (7-13) -->
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="width: 120px; color: #9ca3af; font-size: 0.85em; text-align: right;">🟡 Alert (7-13)</div>
                    <div style="flex: 1; background: #374151; border-radius: 6px; height: 32px; overflow: hidden; position: relative;">
                        <div style="background: linear-gradient(90deg, #d97706 0%, #f59e0b 100%); height: 100%; width: {alert_pct}%; border-radius: 6px; transition: width 0.5s ease; display: flex; align-items: center; justify-content: flex-end; padding-right: 10px; min-width: 50px;">
                            <span style="color: white; font-weight: 700; font-size: 0.85em;">{alert_count}</span>
                        </div>
                    </div>
                    <div style="width: 50px; color: #f59e0b; font-weight: 700; font-size: 0.9em;">{alert_pct}%</div>
                </div>
                
                <!-- Critical (14-21) -->
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="width: 120px; color: #9ca3af; font-size: 0.85em; text-align: right;">🔴 Critical (14-21)</div>
                    <div style="flex: 1; background: #374151; border-radius: 6px; height: 32px; overflow: hidden; position: relative;">
                        <div style="background: linear-gradient(90deg, #dc2626 0%, #ef4444 100%); height: 100%; width: {critical_pct}%; border-radius: 6px; transition: width 0.5s ease; display: flex; align-items: center; justify-content: flex-end; padding-right: 10px; min-width: 50px;">
                            <span style="color: white; font-weight: 700; font-size: 0.85em;">{critical_count}</span>
                        </div>
                    </div>
                    <div style="width: 50px; color: #ef4444; font-weight: 700; font-size: 0.9em;">{critical_pct}%</div>
                </div>
                
                <!-- Potential Dropout (22+) -->
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="width: 120px; color: #9ca3af; font-size: 0.85em; text-align: right;">⚠️ Dropout (22+)</div>
                    <div style="flex: 1; background: #374151; border-radius: 6px; height: 32px; overflow: hidden; position: relative;">
                        <div style="background: linear-gradient(90deg, #7f1d1d 0%, #991b1b 100%); height: 100%; width: {dropout_pct}%; border-radius: 6px; transition: width 0.5s ease; display: flex; align-items: center; justify-content: flex-end; padding-right: 10px; min-width: 50px;">
                            <span style="color: white; font-weight: 700; font-size: 0.85em;">{dropout_count}</span>
                        </div>
                    </div>
                    <div style="width: 50px; color: #991b1b; font-weight: 700; font-size: 0.9em;">{dropout_pct}%</div>
                </div>
            </div>
            
            <!-- Action callout if dropout/critical > 0 -->
            {"" if (dropout_count + critical_count) == 0 else f'''
            <div style="margin-top: 20px; padding: 12px 16px; background: linear-gradient(145deg, #7f1d1d 0%, #991b1b 100%); border-radius: 8px; display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.3em;">⚠️</span>
                <span style="color: white; font-weight: 600; font-size: 0.9em;">{dropout_count + critical_count} employees need immediate attention</span>
            </div>
            '''}
        </div>
    </div>
    """
    
    # Build warning banner (FLASHING RED) - standalone styling
    if dropout_count > 0 or critical_count > 0:
        warning_html = f"""
        <div class="flash-warning" style="display: flex; align-items: center; justify-content: center; gap: 15px; padding: 16px 24px; margin-bottom: 20px; background: linear-gradient(145deg, #dc2626 0%, #991b1b 100%); border-radius: 12px; box-shadow: 0 4px 15px rgba(220, 38, 38, 0.4);">
            <span style="font-size: 1.5em;">⚠️</span>
            <div style="color: white; font-weight: 700; font-size: 1.1em; text-transform: uppercase; letter-spacing: 0.5px;">
                NOTE: {dropout_count + critical_count} employees require immediate engagement or disposition decision
            </div>
            <span style="font-size: 1.5em;">⚠️</span>
        </div>
        """
    else:
        warning_html = ""
    
    # Build UNIFIED matrix table
    unified_headers = [
        'REGION',
        'EMP ID',
        'NAME',
        'EMPLOYEE START DATE',
        'SPEED TO TRAINING',
        '<span class="flash-header">DAYS FROM START DATE</span>',
        'STATUS'
    ]
    
    unified_rows = []
    for emp in all_employees:
        emp_id = emp.get('employee_id', 'N/A')
        emp_name = emp.get('employee_name', 'N/A')
        region_name = emp.get('region', 'N/A')
        start_date = emp.get('employee_date_started', 'N/A')
        days_from_start = emp.get('days_from_hire', 0)
        days_to_training = emp.get('days_to_training_complete')
        aging_status = emp.get('aging_status', 'N/A')
        training_complete = days_to_training is not None
        
        # Calculate Speed to Training status (COMPLETE or OPEN)
        if training_complete:
            # Training complete - show COMPLETE with days as subtitle
            if days_to_training == 1:
                speed_badge = f'<div style="text-align: center;"><span style="background: #10b981; color: white; padding: 4px 10px; border-radius: 4px; font-weight: 900; font-size: 0.9em;">COMPLETE</span><br><span style="font-size: 0.75em; color: #10b981; font-weight: 600;">{days_to_training} day</span></div>'
            elif days_to_training <= 3:
                speed_badge = f'<div style="text-align: center;"><span style="background: #f59e0b; color: white; padding: 4px 10px; border-radius: 4px; font-weight: 900; font-size: 0.9em;">COMPLETE</span><br><span style="font-size: 0.75em; color: #f59e0b; font-weight: 600;">{days_to_training} days</span></div>'
            else:
                speed_badge = f'<div style="text-align: center;"><span style="background: #dc2626; color: white; padding: 4px 10px; border-radius: 4px; font-weight: 900; font-size: 0.9em;">COMPLETE</span><br><span style="font-size: 0.75em; color: #dc2626; font-weight: 600;">{days_to_training} days</span></div>'
        else:
            # Training NOT complete - show FLASHING "OPEN"
            speed_badge = '<div style="text-align: center;"><span class="flash-open" style="background: #6b7280; color: white; padding: 4px 10px; border-radius: 4px; font-weight: 900; font-size: 0.9em;">OPEN</span><br><span style="font-size: 0.75em; color: #6b7280; font-weight: 600;">In Progress</span></div>'
        
        # Color code DAYS FROM START DATE (for ALL employees)
        if days_from_start >= 22:
            aging_color = 'color: #7f1d1d; font-weight: 900;'
        elif days_from_start >= 14:
            aging_color = 'color: #dc2626; font-weight: 900;'
        elif days_from_start >= 7:
            aging_color = 'color: #f59e0b; font-weight: 700;'
        else:
            aging_color = 'color: #10b981; font-weight: 600;'
        
        aging_display = f'<div style="text-align: right; {aging_color}">{days_from_start}</div>'
        
        row = [
            f'<div style="text-align: center;">{region_name}</div>',
            f'<div style="text-align: center;">{emp_id}</div>',
            f'<div>{emp_name}</div>',
            f'<div style="text-align: center;">{start_date}</div>',
            f'<div style="text-align: center;">{speed_badge}</div>',
            aging_display,
            f'<div style="text-align: center;">{aging_status}</div>',
        ]
        unified_rows.append(row)
    
    # Add aging filter dropdown BEFORE the table (MULTI-SELECT) with counters
    aging_filter_html = f"""
    <div style="margin-bottom: 20px; padding: 15px; background: linear-gradient(145deg, #f9fafb 0%, #f3f4f6 100%); border-radius: 8px; border: 2px solid #3b82f6;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 10px;">
            <label style="font-weight: 700; color: #1f2937;">Filter by Aging Status (hold Ctrl/Cmd for multiple):</label>
            <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                <div id="filter-counter" style="background: linear-gradient(145deg, #1e40af 0%, #3b82f6 100%); color: white; padding: 8px 16px; border-radius: 8px; font-weight: 700; font-size: 0.95em; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    👥 Showing: <span id="visible-count">{total_unscheduled}</span> / <span id="total-count">{total_unscheduled}</span>
                </div>
                <div id="training-counter" style="background: linear-gradient(145deg, #059669 0%, #10b981 100%); color: white; padding: 8px 16px; border-radius: 8px; font-weight: 700; font-size: 0.95em; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    ✅ Training Complete: <span id="training-complete-count">{ready_count}</span> / <span id="training-visible-count">{total_unscheduled}</span> (<span id="training-pct">{round(ready_count/total_unscheduled*100, 0) if total_unscheduled > 0 else 0}</span>%)
                </div>
            </div>
        </div>
        <select id="aging-filter" multiple onchange="filterByAging()" style="padding: 8px 12px; border-radius: 6px; border: 2px solid #3b82f6; background: white; font-weight: 600; cursor: pointer; min-height: 150px; width: 100%;">
            <option value="all" selected>All Employees</option>
            <option value="dropout">⚠️ Potential Dropout (≥22 days)</option>
            <option value="critical">🔴 Critical (14-21 days)</option>
            <option value="alert">🟡 Alert (7-13 days)</option>
            <option value="normal">🟢 Normal (0-6 days)</option>
        </select>
    </div>
    """
    
    unified_table_html = f"""
    <h3>📊 UNIFIED SPEED TO POST MATRIX</h3>
    {aging_filter_html}
    {build_table_with_controls(
        table_id='speed-to-post-unified',
        search_box_id='speed-to-post-unified-search',
        headers=unified_headers,
        rows=unified_rows,
        export_filename=f'speed_to_post_unified_{region}.csv'
    )}
    
    <div class="legend" style="margin-top: 10px; padding: 10px 15px; background: linear-gradient(145deg, #f9fafb 0%, #f3f4f6 100%); border-radius: 8px; border: 1px solid #e5e7eb;">
        <div style="margin-bottom: 10px;">
            <strong style="color: #1f2937; font-size: 0.9em;">Speed to Training Status:</strong>
            <span style="margin-left: 15px;"><span style="background: #10b981; color: white; padding: 3px 8px; border-radius: 3px; font-weight: 700;">COMPLETE</span> = Training finished</span>
            <span style="margin-left: 15px;">Color indicates speed: <span style="color: #10b981; font-weight: 700;">Green (1 day)</span>, <span style="color: #f59e0b; font-weight: 700;">Yellow (2-3 days)</span>, <span style="color: #dc2626; font-weight: 700;">Red (4+ days)</span></span>
            <span style="margin-left: 15px;"><span style="background: #6b7280; color: white; padding: 3px 8px; border-radius: 3px; font-weight: 700;">OPEN</span> = Training in progress (flashing)</span>
        </div>
        <div style="margin-bottom: 10px;">
            <strong style="color: #1f2937; font-size: 0.9em;">Days from Start Date (Aging):</strong>
            <span style="margin-left: 15px; color: #10b981; font-weight: 700;">Green (0-6 days)</span>
            <span style="margin-left: 10px; color: #3b82f6;">|</span>
            <span style="margin-left: 10px; color: #f59e0b; font-weight: 700;">Yellow (7-13 days)</span>
            <span style="margin-left: 10px; color: #3b82f6;">|</span>
            <span style="margin-left: 10px; color: #dc2626; font-weight: 700;">Red (14-21 days)</span>
            <span style="margin-left: 10px; color: #3b82f6;">|</span>
            <span style="margin-left: 10px; color: #7f1d1d; font-weight: 700;">Dark Red (≥22 days)</span>
        </div>
        <div>
            <strong style="color: #1f2937; font-size: 0.9em;">Status Categories:</strong>
            <span style="margin-left: 15px;">⚠️ Potential Dropout (≥22 days) - ENGAGE OR DISPOSITION</span>
            <span style="margin-left: 10px; color: #3b82f6;">|</span>
            <span style="margin-left: 10px;">🔴 Critical (14-21 days)</span>
            <span style="margin-left: 10px; color: #3b82f6;">|</span>
            <span style="margin-left: 10px;">🟡 Alert (7-13 days)</span>
            <span style="margin-left: 10px; color: #3b82f6;">|</span>
            <span style="margin-left: 10px;">🟢 Normal (0-6 days)</span>
        </div>
    </div>
    </div>
    """
    
    # Add CSS for flashing animations
    flash_css = """
    <style>
    @keyframes flash-attention {
        0%, 100% { color: #1f2937; text-shadow: 0 0 5px rgba(59, 130, 246, 0.3); }
        50% { color: #dc2626; text-shadow: 0 0 10px rgba(220, 38, 38, 0.6); }
    }
    .flash-header {
        animation: flash-attention 2s ease-in-out infinite;
        font-weight: 900;
    }
    @keyframes flash-open {
        0%, 100% { 
            background: #6b7280; 
            box-shadow: 0 0 5px rgba(107, 114, 128, 0.5);
        }
        50% { 
            background: #f59e0b; 
            box-shadow: 0 0 15px rgba(245, 158, 11, 0.8);
            transform: scale(1.05);
        }
    }
    .flash-open {
        animation: flash-open 1.5s ease-in-out infinite;
        display: inline-block;
    }
    @keyframes flash-warning {
        0%, 100% { 
            background: linear-gradient(145deg, #dc2626 0%, #991b1b 100%);
            box-shadow: 0 0 10px rgba(220, 38, 38, 0.5);
        }
        50% { 
            background: linear-gradient(145deg, #7f1d1d 0%, #450a0a 100%);
            box-shadow: 0 0 20px rgba(220, 38, 38, 0.9);
            transform: scale(1.02);
        }
    }
    .flash-warning {
        animation: flash-warning 1.5s ease-in-out infinite;
    }
    </style>
    """
    
    # Add JavaScript for aging filter (MULTI-SELECT) with both counters update
    filter_js = """
    <script>
    function filterByAging() {
        const select = document.getElementById('aging-filter');
        const selectedValues = Array.from(select.selectedOptions).map(opt => opt.value);
        const table = document.getElementById('speed-to-post-unified');
        const rows = table.getElementsByTagName('tbody')[0].getElementsByTagName('tr');
        
        // Counter elements
        const visibleCountEl = document.getElementById('visible-count');
        const counterEl = document.getElementById('filter-counter');
        const trainingCompleteEl = document.getElementById('training-complete-count');
        const trainingVisibleEl = document.getElementById('training-visible-count');
        const trainingPctEl = document.getElementById('training-pct');
        const trainingCounterEl = document.getElementById('training-counter');
        
        let visibleCount = 0;
        let trainingCompleteCount = 0;
        
        // If "All" is selected or nothing selected, show all rows
        if (selectedValues.includes('all') || selectedValues.length === 0) {
            for (let i = 0; i < rows.length; i++) {
                rows[i].style.display = '';
                visibleCount++;
                
                // Check if training is complete (look for "COMPLETE" in Speed to Training column)
                const trainingCell = rows[i].getElementsByTagName('td')[4]; // SPEED TO TRAINING column
                if (trainingCell && trainingCell.textContent.includes('COMPLETE')) {
                    trainingCompleteCount++;
                }
            }
            // Update counters
            updateCounters(visibleCount, trainingCompleteCount);
            return;
        }
        
        // Otherwise, check each row against selected filters
        for (let i = 0; i < rows.length; i++) {
            const statusCell = rows[i].getElementsByTagName('td')[6]; // STATUS column
            const statusText = statusCell.textContent.trim();
            
            let showRow = false;
            
            for (let value of selectedValues) {
                if (value === 'dropout' && statusText.includes('Potential Dropout')) {
                    showRow = true;
                    break;
                } else if (value === 'critical' && statusText.includes('Critical')) {
                    showRow = true;
                    break;
                } else if (value === 'alert' && statusText.includes('Alert')) {
                    showRow = true;
                    break;
                } else if (value === 'normal' && statusText.includes('Normal')) {
                    showRow = true;
                    break;
                }
            }
            
            rows[i].style.display = showRow ? '' : 'none';
            
            if (showRow) {
                visibleCount++;
                // Check if training is complete
                const trainingCell = rows[i].getElementsByTagName('td')[4]; // SPEED TO TRAINING column
                if (trainingCell && trainingCell.textContent.includes('COMPLETE')) {
                    trainingCompleteCount++;
                }
            }
        }
        
        // Update both counters
        updateCounters(visibleCount, trainingCompleteCount);
    }
    
    function updateCounters(visibleCount, trainingCompleteCount) {
        const visibleCountEl = document.getElementById('visible-count');
        const counterEl = document.getElementById('filter-counter');
        const trainingCompleteEl = document.getElementById('training-complete-count');
        const trainingVisibleEl = document.getElementById('training-visible-count');
        const trainingPctEl = document.getElementById('training-pct');
        const trainingCounterEl = document.getElementById('training-counter');
        const totalCount = parseInt(document.getElementById('total-count').textContent);
        
        // Update filter counter
        visibleCountEl.textContent = visibleCount;
        
        if (visibleCount === 0) {
            counterEl.style.background = 'linear-gradient(145deg, #6b7280 0%, #9ca3af 100%)';
        } else if (visibleCount < totalCount * 0.25) {
            counterEl.style.background = 'linear-gradient(145deg, #dc2626 0%, #ef4444 100%)';
        } else if (visibleCount < totalCount * 0.5) {
            counterEl.style.background = 'linear-gradient(145deg, #f59e0b 0%, #fbbf24 100%)';
        } else {
            counterEl.style.background = 'linear-gradient(145deg, #1e40af 0%, #3b82f6 100%)';
        }
        
        // Update training counter
        trainingCompleteEl.textContent = trainingCompleteCount;
        trainingVisibleEl.textContent = visibleCount;
        const trainingPct = visibleCount > 0 ? Math.round((trainingCompleteCount / visibleCount) * 100) : 0;
        trainingPctEl.textContent = trainingPct;
        
        // Color code training counter based on completion percentage
        if (visibleCount === 0) {
            trainingCounterEl.style.background = 'linear-gradient(145deg, #6b7280 0%, #9ca3af 100%)';
        } else if (trainingPct >= 80) {
            trainingCounterEl.style.background = 'linear-gradient(145deg, #059669 0%, #10b981 100%)'; // Green
        } else if (trainingPct >= 50) {
            trainingCounterEl.style.background = 'linear-gradient(145deg, #f59e0b 0%, #fbbf24 100%)'; // Yellow
        } else {
            trainingCounterEl.style.background = 'linear-gradient(145deg, #dc2626 0%, #ef4444 100%)'; // Red
        }
    }
    </script>
    """
    
    # Assemble complete section
    return f"""
    {flash_css}
    <div id="section-speed-to-post" class="section">
        <div class="section-header" onclick="toggleSection('section-speed-to-post')">
            <span class="section-toggle">▶</span>
            <span class="section-title">📊 SPEED TO POST PORTFOLIO | Filtered by Employees Who Started in the Last 3 Months</span>
        </div>
        <div class="section-content">
            <div class="section-inner">
                {summary_cards_html}
                {warning_html}
                {unified_table_html}
            </div>
        </div>
    </div>
    {filter_js}
    """

def _get_employee_ot_breakdown(location_id: str, start_date: str, end_date: str, state: str, customer_code=None) -> Dict:
    """Get detailed employee OT breakdown using midnight-to-midnight workday periods."""
    
    if not start_date or not end_date:
        return {'daily_ot_employees': [], 'weekly_ot_employees': [], 'double_time_employees': []}
    
    customer_filter = f"AND CONCAT('', customer_code) = '{customer_code}'" if customer_code else ""
    
    # NEW QUERY: Split overnight shifts at midnight (CORRECTED CALCULATION)
    employee_sql = f"""
    WITH ShiftSegments AS (
      SELECT
        employee_id,
        employee_name,
        job_classification,
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
        
        -- Calculate hours on next date FIRST (easier calculation)
        CASE
          WHEN PARSE_TIME('%I:%M%p', REPLACE(REPLACE(start, 'a', 'AM'), 'p', 'PM')) >= 
               PARSE_TIME('%I:%M%p', REPLACE(REPLACE(`end`, 'a', 'AM'), 'p', 'PM')) THEN
            -- Overnight: hours from midnight to end_time
            EXTRACT(HOUR FROM PARSE_TIME('%I:%M%p', REPLACE(REPLACE(`end`, 'a', 'AM'), 'p', 'PM'))) +
            EXTRACT(MINUTE FROM PARSE_TIME('%I:%M%p', REPLACE(REPLACE(`end`, 'a', 'AM'), 'p', 'PM'))) / 60.0
          ELSE 
            0.0
        END AS hours_on_next_date,
        
        -- Calculate hours on scheduled_date (remainder after next_date)
        CASE
          WHEN PARSE_TIME('%I:%M%p', REPLACE(REPLACE(start, 'a', 'AM'), 'p', 'PM')) >= 
               PARSE_TIME('%I:%M%p', REPLACE(REPLACE(`end`, 'a', 'AM'), 'p', 'PM')) THEN
            -- Overnight: scheduled_hours - hours_on_next_date
            scheduled_hours - (
              EXTRACT(HOUR FROM PARSE_TIME('%I:%M%p', REPLACE(REPLACE(`end`, 'a', 'AM'), 'p', 'PM'))) +
              EXTRACT(MINUTE FROM PARSE_TIME('%I:%M%p', REPLACE(REPLACE(`end`, 'a', 'AM'), 'p', 'PM'))) / 60.0
            )
          ELSE 
            scheduled_hours
        END AS hours_on_scheduled_date
        
      FROM `{BQ_DATA_PROJECT_ID}.{BQ_DATASET_ID}.APEX_NWS`
          WHERE location_id = '{location_id}'
            AND state = '{state}'
            {customer_filter}
            AND scheduled_date BETWEEN '{start_date}' AND '{end_date}'
        ),
    ExpandedShifts AS (
      SELECT
        employee_id,
        employee_name,
        job_classification,
        scheduled_date AS workday_date,
        hours_on_scheduled_date AS daily_hours
      FROM ShiftSegments
      WHERE hours_on_scheduled_date > 0
      
      UNION ALL
      
      SELECT
        employee_id,
        employee_name,
        job_classification,
        DATE_ADD(scheduled_date, INTERVAL 1 DAY) AS workday_date,
        hours_on_next_date AS daily_hours
      FROM ShiftSegments
      WHERE crosses_midnight AND hours_on_next_date > 0
    )
    SELECT
      employee_id,
      MAX(employee_name) AS employee_name,
      MAX(job_classification) AS job_classification,
      workday_date AS scheduled_date,
      SUM(daily_hours) AS daily_hours
    FROM ExpandedShifts
    GROUP BY employee_id, workday_date
    ORDER BY employee_id, workday_date
    """
    
    try:
        daily_data = execute_query(employee_sql)
    except Exception as e:
        return {'daily_ot_employees': [], 'weekly_ot_employees': [], 'double_time_employees': []}
    
    if not daily_data:
        return {'daily_ot_employees': [], 'weekly_ot_employees': [], 'double_time_employees': []}
    
    # Analyze OT by employee
    daily_ot_employees = []
    double_time_employees = []
    weekly_totals = {}
    
    for row in daily_data:
        emp_id = row['employee_id']
        emp_name = row['employee_name']
        date = row['scheduled_date']
        hours = float(row['daily_hours'])
        
        # Track for weekly totals
        if emp_id not in weekly_totals:
            weekly_totals[emp_id] = {'name': emp_name, 'total': 0, 'dates': []}
        weekly_totals[emp_id]['total'] += hours
        weekly_totals[emp_id]['dates'].append(date)
        
        # Daily OT (ONLY for CA, AK, NV, CO)
        # CA/AK/NV/CO: >8 hours = daily OT
        has_daily_ot_rules = state in ['CA', 'AK', 'NV', 'CO']
        
        if has_daily_ot_rules and hours > 8.0:
            daily_ot_hours = hours - 8.0
            
            # Find if employee already in list
            existing = next((e for e in daily_ot_employees if e['id'] == emp_id), None)
            if existing:
                existing['dates'].append({'date': date, 'hours': daily_ot_hours})
                existing['total_ot'] += daily_ot_hours
            else:
                daily_ot_employees.append({
                    'id': emp_id,
                    'name': emp_name,
                    'dates': [{'date': date, 'hours': daily_ot_hours}],
                    'total_ot': daily_ot_hours
                })
        
        # Double time (CA only: >12 hours)
        if state == 'CA' and hours > 12:
            double_time_hours = hours - 12
            existing = next((e for e in double_time_employees if e['id'] == emp_id), None)
            if existing:
                existing['dates'].append({'date': date, 'hours': double_time_hours})
                existing['total_dt'] += double_time_hours
            else:
                double_time_employees.append({
                    'id': emp_id,
                    'name': emp_name,
                    'dates': [{'date': date, 'hours': double_time_hours}],
                    'total_dt': double_time_hours
                })
    
    # Weekly OT (>40 hours)
    weekly_ot_employees = []
    for emp_id, data in weekly_totals.items():
        if data['total'] > 40:
            weekly_ot_hours = data['total'] - 40
            weekly_ot_employees.append({
                'id': emp_id,
                'name': data['name'],
                'weekly_hours': data['total'],
                'ot_hours': weekly_ot_hours
            })
    
    # Sort by OT amount (highest first)
    daily_ot_employees.sort(key=lambda x: x['total_ot'], reverse=True)
    double_time_employees.sort(key=lambda x: x['total_dt'], reverse=True)
    weekly_ot_employees.sort(key=lambda x: x['ot_hours'], reverse=True)
    
    return {
        'daily_ot_employees': daily_ot_employees[:5],  # Top 5
        'weekly_ot_employees': weekly_ot_employees[:5],  # Top 5
        'double_time_employees': double_time_employees[:5]  # Top 5
    }
    
    