"""Individual report modules."""

from .customer_overview import generate_customer_overview
from .region_overview import generate_region_overview
from .optimization_card import generate_optimization_card
from .pareto_optimization import generate_pareto_optimization
from .pareto_optimization_html import generate_pareto_optimization_html 

__all__ = [
    'generate_customer_overview',
    'generate_region_overview',
    'generate_optimization_card',
    'generate_pareto_optimization',
    'generate_pareto_optimization_html',
]