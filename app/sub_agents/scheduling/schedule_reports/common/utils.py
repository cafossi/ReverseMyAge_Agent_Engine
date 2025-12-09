"""Shared utility functions for scheduling reports."""

from google.cloud import bigquery
from typing import List, Dict, Any
from .constants import (
    BQ_COMPUTE_PROJECT_ID,
    TENURE_ICONS,
    USAGE_ICONS,
    TRAINING_ICONS
)


# ============================================================
# 📊 DATABASE QUERY FUNCTIONS
# ------------------------------------------------------------
# Functions for executing BigQuery queries and retrieving data
# ============================================================

def execute_query(sql: str) -> List[Dict[str, Any]]:
    """
    Execute a BigQuery SQL query and return results as list of dicts.
    
    Args:
        sql: SQL query string
    
    Returns:
        List of dictionaries representing query results
    
    Raises:
        Exception: If query fails
    """
    try:
        client = bigquery.Client(project=BQ_COMPUTE_PROJECT_ID)
        results = client.query(sql).to_dataframe().to_dict(orient='records')
        return results
    except Exception as e:
        raise Exception(f"Query failed: {str(e)}\n\nSQL:\n{sql}")

# ============================================================
# 👤 EMPLOYEE STATUS FUNCTIONS
# ------------------------------------------------------------
# Functions for adding visual status indicators to employee records
# ============================================================


def add_status_icons(employee: Dict[str, Any]) -> None:
    """
    Add status icons to employee record in place.
    
    Args:
        employee: Employee dict to add icons to
    """
    employee['tenure_icon'] = TENURE_ICONS.get(employee.get('tenure_status', ''), '')
    employee['usage_icon'] = USAGE_ICONS.get(employee.get('usage_status', ''), '')
    employee['training_icon'] = TRAINING_ICONS.get(employee.get('training_status', ''), '')


# ============================================================
# 📐 CAPACITY & CALCULATION FUNCTIONS
# ------------------------------------------------------------
# Functions for calculating FTE needs and workforce capacity
# ============================================================

def calculate_capacity(total_hours: float, fte_hours: int) -> int:
    """
    Calculate FTE needed.
    
    Args:
        total_hours: Total scheduled hours
        fte_hours: Hours per FTE (32 for CA, 36 for others)
    
    Returns:
        FTE needed
    """
    fte_needed = int((total_hours + (fte_hours - 1e-4)) // fte_hours) if total_hours else 0
    return fte_needed

# ============================================================
# 🎨 FORMATTING FUNCTIONS
# ------------------------------------------------------------
# Functions for formatting numbers and percentages for display
# ============================================================

def format_hours(hours: float) -> str:
    """Format hours with proper precision."""
    return f"{hours:,.2f}"


def format_percentage(value: float) -> str:
    """Format percentage with one decimal place."""
    return f"{value:.1f}"


# ============================================================
# 🚨 ALERT CATEGORIZATION FUNCTIONS
# ------------------------------------------------------------
# Functions for identifying employees requiring attention
# ============================================================

def categorize_alerts(
    results: List[Dict],
    has_daily_ot: bool = False,
    has_double_time: bool = False
) -> Dict[str, List[Dict]]:
    """
    Categorize employees into alert groups.
    
    Args:
        results: List of employee records
        has_daily_ot: Whether state has daily OT rules
        has_double_time: Whether state has double time rules
    
    Returns:
        Dict mapping alert type to list of employees
    """
    alerts = {
        'over_40': [e for e in results if e.get('weekly_ot', 0) > 0],
        'under_32': [
            e for e in results 
            if e.get('employee_status') == 'Active' and e.get('hours_all_sites', 0) < 32
        ],
        'training_incomplete': [
            e for e in results 
            if e.get('training_status') == 'Not Completed'
        ],
        'critical_tenure': [
            e for e in results 
            if e.get('tenure_days', 999) <= 90
        ],
        'high_tenure': [
            e for e in results 
            if 91 <= e.get('tenure_days', 999) <= 179
        ],
    }
    
    # ✅ FIX: Use correct field names
    if has_daily_ot:
        alerts['daily_ot'] = [e for e in results if e.get('total_daily_ot', 0) > 0]
    else:
        alerts['daily_ot'] = []
    
    if has_double_time:
        alerts['double_time'] = [e for e in results if e.get('total_double_time', 0) > 0]
    else:
        alerts['double_time'] = []
    
    return alerts

# ============================================================
# 🧮 MATH UTILITY FUNCTIONS
# ------------------------------------------------------------
# Helper functions for safe mathematical operations
# ============================================================

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers, returning default if denominator is zero."""
    return numerator / denominator if denominator != 0 else default


def round_percent(value: float, decimals: int = 1) -> float:
    """Round a percentage value to specified decimal places."""
    return round(value, decimals)