"""State-specific overtime calculation logic."""

from collections import defaultdict, OrderedDict
from datetime import datetime, date
from typing import List, Dict
from .constants import has_daily_ot_rules, has_double_time_rules


def calculate_ot_for_sites(results: List[Dict], daily_rows: List[Dict]) -> None:
    """
    Calculate OT for each site using state-specific rules.
    Modifies the results list in place.
    
    State-specific rules:
      • CA, AK, NV, CO: Daily OT rules apply (>8 hrs/day)
      • CA only: Double Time rules apply (>12 hrs/day or >8 on 7th day)
      • All states: Weekly OT applies (>40 hrs/week)
    
    Args:
        results: List of site records to calculate OT for
        daily_rows: List of daily hour records per employee
    """
    # Build daily map per site per employee - using composite key (location_id|state)
    by_site = defaultdict(lambda: defaultdict(lambda: OrderedDict()))
    
    for r in daily_rows:
        site_id = r['location_id']
        site_state = r.get('state', '')  # Get state from daily_rows
        site_key = f"{site_id}|{site_state}"  # Composite key
        emp_id = r['employee_id']
        by_site[site_key][emp_id][str(r['scheduled_date'])] = float(r.get('daily_hours') or 0.0)
    
    def _d(s: str) -> date:
        return datetime.strptime(s, "%Y-%m-%d").date()
    
    # Calculate OT for each site
    for site in results:
        site_id = site['location_id']
        state = site['state']
        site_key = f"{site_id}|{state}"  # Composite key to match daily_rows
        has_daily_ot = has_daily_ot_rules(state)
        has_double_time = has_double_time_rules(state)
        
        site_daily_ot = 0.0
        site_doubletime = 0.0
        site_weekly_ot = 0.0
        employees_with_ot = 0
        
        if site_key not in by_site:
            site['weekly_ot_hours'] = 0.0
            site['daily_ot_hours'] = 0.0
            site['double_time_hours'] = 0.0
            site['total_ot_exposure'] = 0.0
            site['ot_percentage'] = 0.0
            site['employees_with_ot'] = 0
            continue
        
        # Process each employee at this site
        for emp_id, days_dict in by_site[site_key].items():
            days = sorted(days_dict.keys(), key=_d)
            
            # Step 1: allocate D/DT per day
            per_day = []
            for idx, dstr in enumerate(days):
                hours = days_dict[dstr]
                
                daily_ot = 0.0
                double_t = 0.0
                regular = hours
                
                if has_daily_ot:
                    seventh = (len(days) >= 7 and idx == 6 and 
                              all(days_dict.get(days[k], 0) > 0.0 for k in range(0, 6)))
                    
                    if seventh and has_double_time:
                        daily_ot = min(hours, 8.0)
                        double_t = max(0.0, hours - 8.0)
                        regular = max(0.0, hours - daily_ot - double_t)
                    else:
                        if has_double_time:
                            double_t = max(0.0, hours - 12.0)
                        if hours > 8.0:
                            daily_ot = min(hours - 8.0, 4.0) if has_double_time else (hours - 8.0)
                        regular = max(0.0, hours - daily_ot - double_t)
                
                per_day.append({
                    "regular": regular,
                    "daily_ot": daily_ot,
                    "double_time": double_t,
                    "weekly_ot": 0.0,
                })
            
            total_week_hours = sum(days_dict.values())
            hours_over_40 = max(0.0, total_week_hours - 40.0)
            
            # Step 2: allocate WEEKLY OT by converting REGULAR hours from last day backward
            remaining = hours_over_40
            for r in reversed(per_day):
                if remaining <= 0.0:
                    break
                take = min(remaining, r["regular"])
                r["regular"] -= take
                r["weekly_ot"] += take
                remaining -= take
            
            # Add to site totals
            emp_daily_ot = sum(r["daily_ot"] for r in per_day)
            emp_doubletime = sum(r["double_time"] for r in per_day)
            emp_weekly_ot = sum(r["weekly_ot"] for r in per_day)
            
            site_daily_ot += emp_daily_ot
            site_doubletime += emp_doubletime
            site_weekly_ot += emp_weekly_ot
            
            if emp_weekly_ot > 0 or emp_daily_ot > 0 or emp_doubletime > 0:
                employees_with_ot += 1
        
        # Store in site record
        site['weekly_ot_hours'] = round(site_weekly_ot, 1)
        site['daily_ot_hours'] = round(site_daily_ot, 1) if has_daily_ot else 0.0
        site['double_time_hours'] = round(site_doubletime, 1) if has_double_time else 0.0
        site['total_ot_exposure'] = round(site_weekly_ot + site_daily_ot + site_doubletime, 1)
        site['ot_percentage'] = round((site['total_ot_exposure'] / site['total_hours'] * 100), 1) if site['total_hours'] > 0 else 0.0
        site['employees_with_ot'] = employees_with_ot


def calculate_employee_ot(
    employee_id: str,
    daily_hours: Dict[str, float],
    state: str
) -> Dict[str, float]:
    """
    Calculate OT breakdown for a single employee.
    
    Args:
        employee_id: Employee identifier
        daily_hours: Dict mapping date string to hours worked
        state: State code for OT rules
    
    Returns:
        Dict with keys: weekly_ot, daily_ot, double_time, total_ot_exposure
    """
    has_daily_ot = has_daily_ot_rules(state)
    has_double_time = has_double_time_rules(state)
    
    def _d(s: str) -> date:
        return datetime.strptime(s, "%Y-%m-%d").date()
    
    days = sorted(daily_hours.keys(), key=_d)
    
    # Step 1: allocate D/DT per day
    per_day = []
    for idx, dstr in enumerate(days):
        hours = daily_hours[dstr]
        
        daily_ot = 0.0
        double_t = 0.0
        regular = hours
        
        if has_daily_ot:
            seventh = (len(days) >= 7 and idx == 6 and 
                      all(daily_hours.get(days[k], 0) > 0.0 for k in range(0, 6)))
            
            if seventh and has_double_time:
                daily_ot = min(hours, 8.0)
                double_t = max(0.0, hours - 8.0)
                regular = max(0.0, hours - daily_ot - double_t)
            else:
                if has_double_time:
                    double_t = max(0.0, hours - 12.0)
                if hours > 8.0:
                    daily_ot = min(hours - 8.0, 4.0) if has_double_time else (hours - 8.0)
                regular = max(0.0, hours - daily_ot - double_t)
        
        per_day.append({
            "regular": regular,
            "daily_ot": daily_ot,
            "double_time": double_t,
            "weekly_ot": 0.0,
        })
    
    total_week_hours = sum(daily_hours.values())
    hours_over_40 = max(0.0, total_week_hours - 40.0)
    
    # Step 2: allocate WEEKLY OT
    remaining = hours_over_40
    for r in reversed(per_day):
        if remaining <= 0.0:
            break
        take = min(remaining, r["regular"])
        r["regular"] -= take
        r["weekly_ot"] += take
        remaining -= take
    
    # Return totals
    emp_daily_ot = round(sum(r["daily_ot"] for r in per_day), 2)
    emp_doubletime = round(sum(r["double_time"] for r in per_day), 2)
    emp_weekly_ot = round(sum(r["weekly_ot"] for r in per_day), 2)
    
    return {
        'weekly_ot': emp_weekly_ot,
        'daily_ot': emp_daily_ot,
        'double_time': emp_doubletime,
        'total_ot_exposure': round(emp_weekly_ot + emp_daily_ot + emp_doubletime, 2)
    }