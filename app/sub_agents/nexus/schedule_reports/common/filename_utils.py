# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Filename generation utilities for reports."""

from typing import Optional


def generate_pareto_optimization_filename(
    mode: str,
    scope_identifier: str,
    week_ending_date: str,
    extension: str = '.html'
) -> str:
    """
    Generate standardized filename for Pareto Optimization reports.
    
    Format: {Mode}_{Identifier}_OT_Optimization_WE_{Date}{extension}
    
    Examples:
        - Customer_WaymoLLC_OT_Optimization_WE_2025-11-22.html
        - Region_Southwest_OT_Optimization_WE_2025-11-22.html
    
    Args:
        mode: 'Customer' or 'Region'
        scope_identifier: Customer name/code or region name (spaces will be removed)
        week_ending_date: Week ending date in YYYY-MM-DD format
        extension: File extension (default: '.html')
    
    Returns:
        Standardized filename string
    """
    # Clean the identifier: remove spaces and special characters
    clean_identifier = scope_identifier.replace(' ', '').replace(',', '').replace('.', '')
    
    # Build filename
    filename = f"{mode}_{clean_identifier}_OT_Optimization_WE_{week_ending_date}{extension}"
    
    return filename