"""Shared constants and configuration for scheduling reports."""

import os

# Environment variables
BQ_DATA_PROJECT_ID = os.getenv('BQ_DATA_PROJECT_ID')
BQ_DATASET_ID = os.getenv('BQ_DATASET_ID')
BQ_COMPUTE_PROJECT_ID = os.getenv('BQ_COMPUTE_PROJECT_ID')

# Status icons
TENURE_ICONS = {
    'Critical Risk': '🔴',
    'High Risk': '🟠',
    'Medium Risk': '🟡',
    'Low Risk': '🟢'
}

USAGE_ICONS = {
    'Optimal': '🟢',
    'Sub-Optimal': '🟡',
    'Critical': '🔴'
}

TRAINING_ICONS = {
    'Completed': '✅',
    'Not Completed': '⚠️'
}

# NBOT status thresholds
NBOT_RED_THRESHOLD = 3.0      # >= 3% OT
NBOT_YELLOW_THRESHOLD = 1.0   # >= 1% OT

# FTE hours by state
FTE_HOURS = {
    'CA': 32,  # California standard
    'default': 36  # All other states
}

# OT rule states
STATES_WITH_DAILY_OT = ['CA', 'AK', 'NV', 'CO']
STATES_WITH_DOUBLE_TIME = ['CA']

# Utilization thresholds
OPTIMAL_HOURS_MIN = 36
OPTIMAL_HOURS_MAX = 40
SUBOPTIMAL_HOURS_MIN = 25
SUBOPTIMAL_HOURS_MAX = 35

# Tenure risk thresholds (days)
CRITICAL_TENURE_DAYS = 90
HIGH_RISK_TENURE_DAYS = 179
MEDIUM_RISK_TENURE_DAYS = 365

# Training course identifier
GENERAL_ONBOARDING_COURSE = 'ONB101-ALL: Metro One LPSG - General Onboarding (All Employees)'


def get_nbot_status(ot_percentage: float) -> tuple:
    """
    Get NBOT status icon and text based on OT percentage.
    
    Args:
        ot_percentage: OT percentage (0-100)
    
    Returns:
        Tuple of (icon_with_status, status_text)
        Example: ('🟢 GREEN', 'Acceptable')
    """
    if ot_percentage < NBOT_YELLOW_THRESHOLD:
        return '🟢 GREEN', 'Acceptable'
    elif ot_percentage < NBOT_RED_THRESHOLD:
        return '🟡 YELLOW', 'At Risk'
    else:
        return '🔴 RED', 'Critical'


def get_nbot_icon(ot_percentage: float) -> str:
    """Get just the NBOT icon based on OT percentage."""
    if ot_percentage < NBOT_YELLOW_THRESHOLD:
        return '🟢'
    elif ot_percentage < NBOT_RED_THRESHOLD:
        return '🟡'
    else:
        return '🔴'


def get_fte_hours(state: str) -> int:
    """Get FTE hours for a given state."""
    return FTE_HOURS.get(state, FTE_HOURS['default'])


def has_daily_ot_rules(state: str) -> bool:
    """Check if state has daily OT rules."""
    return state in STATES_WITH_DAILY_OT


def has_double_time_rules(state: str) -> bool:
    """Check if state has double time rules."""
    return state in STATES_WITH_DOUBLE_TIME