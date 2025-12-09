"""Common utilities and constants for scheduling reports."""

from .constants import (
    BQ_DATA_PROJECT_ID,
    BQ_DATASET_ID,
    BQ_COMPUTE_PROJECT_ID,
    TENURE_ICONS,
    USAGE_ICONS,
    TRAINING_ICONS,
    NBOT_RED_THRESHOLD,
    NBOT_YELLOW_THRESHOLD,
    FTE_HOURS,
    STATES_WITH_DAILY_OT,
    STATES_WITH_DOUBLE_TIME,
    OPTIMAL_HOURS_MIN,
    OPTIMAL_HOURS_MAX,
    SUBOPTIMAL_HOURS_MIN,
    SUBOPTIMAL_HOURS_MAX,
    CRITICAL_TENURE_DAYS,
    HIGH_RISK_TENURE_DAYS,
    MEDIUM_RISK_TENURE_DAYS,
    GENERAL_ONBOARDING_COURSE,
    get_nbot_status,
    get_nbot_icon,
    get_fte_hours,
    has_daily_ot_rules,
    has_double_time_rules,
)

from .ot_calculations import (
    calculate_ot_for_sites,
    calculate_employee_ot,
)

from .utils import (
    execute_query,
    add_status_icons,
    calculate_capacity,
    format_hours,
    format_percentage,
    categorize_alerts,
    safe_divide,
    round_percent,
)

from .filename_utils import (
    generate_pareto_optimization_filename,
)

__all__ = [
    # Constants
    'BQ_DATA_PROJECT_ID',
    'BQ_DATASET_ID',
    'BQ_COMPUTE_PROJECT_ID',
    'TENURE_ICONS',
    'USAGE_ICONS',
    'TRAINING_ICONS',
    'NBOT_RED_THRESHOLD',
    'NBOT_YELLOW_THRESHOLD',
    'FTE_HOURS',
    'STATES_WITH_DAILY_OT',
    'STATES_WITH_DOUBLE_TIME',
    'OPTIMAL_HOURS_MIN',
    'OPTIMAL_HOURS_MAX',
    'SUBOPTIMAL_HOURS_MIN',
    'SUBOPTIMAL_HOURS_MAX',
    'CRITICAL_TENURE_DAYS',
    'HIGH_RISK_TENURE_DAYS',
    'MEDIUM_RISK_TENURE_DAYS',
    'GENERAL_ONBOARDING_COURSE',
    'get_nbot_status',
    'get_nbot_icon',
    'get_fte_hours',
    'has_daily_ot_rules',
    'has_double_time_rules',
    # OT Calculations
    'calculate_ot_for_sites',
    'calculate_employee_ot',
    # Utils
    'execute_query',
    'add_status_icons',
    'calculate_capacity',
    'format_hours',
    'format_percentage',
    'categorize_alerts',
    'safe_divide',
    'round_percent',
    # Filename Utils
   'generate_pareto_optimization_filename',
]