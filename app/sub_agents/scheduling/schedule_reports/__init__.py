"""Standard scheduling reports with pre-calculated SQL and templates."""

from typing import Optional, List
from .reports.customer_overview import generate_customer_overview
from .reports.region_overview import generate_region_overview
from .reports.optimization_card import generate_optimization_card
from .reports.pareto_optimization import generate_pareto_optimization


def generate_standard_report(
    report_id: str,
    customer_code: Optional[int] = None,
    location_id: Optional[str] = None,
    state: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    region: Optional[str] = None,
    selected_locations: Optional[List[str]] = None,
    analysis_mode: Optional[str] = None
) -> str:
    """
    Generate a pre-optimized standard report.
    
    Available report_ids:
        - 'customer_overview': Customer-level overview
        - 'region_overview': Regional overview
        - 'optimization_card': Detailed site optimization card (replaces site_health)
        - 'pareto_optimization': Pareto analysis with detailed cards
    
    Args:
        report_id: Type of report to generate
        customer_code: Customer code (required for most reports)
        location_id: Location ID (required for optimization_card)
        state: State code (required for optimization_card, e.g., 'CA', 'TX')
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        region: Region name (required for regional reports)
        selected_locations: List of location IDs for pareto analysis
        analysis_mode: 'customer' or 'region' for pareto analysis
    
    Returns:
        Formatted markdown report string
    """
    
    # Route to appropriate report generator
    if report_id == 'site_health':
        # DEPRECATED: Redirect users to optimization_card
        return "Error: 'site_health' is deprecated. Use 'optimization_card' instead (requires state parameter)."
    
    elif report_id == 'customer_overview':
        if not all([customer_code, start_date, end_date]):
            return "Missing required parameters: customer_code, start_date, end_date"
        return generate_customer_overview(customer_code, start_date, end_date)
    
    elif report_id == 'region_overview':
        if not all([region, start_date, end_date]):
            return "Missing required parameters: region, start_date, end_date"
        return generate_region_overview(region, start_date, end_date)
    
    elif report_id == 'optimization_card':
        if not all([customer_code, location_id, state, start_date, end_date]):
            return "Missing required parameters: customer_code, location_id, state, start_date, end_date"
        return generate_optimization_card(customer_code, location_id, state, start_date, end_date)
    
    elif report_id == 'pareto_optimization':
        if not all([start_date, end_date]):
            return "Missing required parameters: start_date, end_date"
        if not analysis_mode:
            return "Missing required parameter: analysis_mode ('customer' or 'region')"
        if analysis_mode == 'customer' and not customer_code:
            return "Missing required parameter: customer_code (for customer mode)"
        if analysis_mode == 'region' and not region:
            return "Missing required parameter: region (for region mode)"
        
        return generate_pareto_optimization(
            start_date=start_date,
            end_date=end_date,
            mode=analysis_mode,
            customer_code=customer_code,
            region=region,
            selected_locations=selected_locations
        )
    
    return f"Report '{report_id}' not implemented. Available: customer_overview, region_overview, optimization_card, pareto_optimization"


__all__ = [
    'generate_standard_report',
    'generate_customer_overview',
    'generate_region_overview',
    'generate_optimization_card',
    'generate_pareto_optimization'
]