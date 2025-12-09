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

"""Scheduling Agent for EPC Analytics.

-- Uses NL2SQL for database queries
-- Uses NL2Py for further analytics
"""

# ============================================================
# 📦 Imports
# ------------------------------------------------------------
import os
from datetime import date

from google.genai import types
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import load_artifacts
from typing import Optional, List

# Sub-agents (children)
from .prompts import return_instructions_root
from .tools import call_db_agent, call_ds_agent, export_report_to_file, export_pareto_html_report

# Standard Reports - Import from new modular structure
from .schedule_reports.reports import (
    generate_site_health,
    generate_customer_overview,
    generate_region_overview,
    generate_optimization_card,
    generate_pareto_optimization,
)

date_today = date.today()


# ============================================================
# 🔀 Standard Report Router
# ------------------------------------------------------------
def generate_standard_report(
    report_id: str,
    customer_code: Optional[int] = None,        # ✅ Add Optional
    location_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    region: Optional[str] = None,
    selected_locations: Optional[List[str]] = None,
    analysis_mode: Optional[str] = None
) -> str:
    """
    Generate a pre-optimized standard report.
    
    Available Reports:
        - 'site_health': Individual site health analysis
        - 'customer_overview': Customer-level overview with Pareto analysis
        - 'region_overview': Regional overview with Pareto analysis
        - 'optimization_card': Detailed site optimization card
        - 'pareto_optimization': Multi-site Pareto analysis with optimization cards
    
    Args:
        report_id: Type of report to generate
        customer_code: Customer identifier
        location_id: Site/location identifier
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        region: Region identifier
        selected_locations: List of location IDs for pareto_optimization
        analysis_mode: 'customer' or 'region' for pareto_optimization
    
    Returns:
        Formatted markdown report
    """
    
    # Route to appropriate report function
    if report_id == 'site_health':
        if not all([customer_code, location_id, start_date, end_date]):
            return "Missing required parameters: customer_code, location_id, start_date, end_date"
        return generate_site_health(customer_code, location_id, start_date, end_date)
    
    elif report_id == 'customer_overview':
        if not all([customer_code, start_date, end_date]):
            return "Missing required parameters: customer_code, start_date, end_date"
        return generate_customer_overview(customer_code, start_date, end_date)
    
    elif report_id == 'region_overview':
        if not all([region, start_date, end_date]):
            return "Missing required parameters: region, start_date, end_date"
        return generate_region_overview(region, start_date, end_date)
    
    elif report_id == 'optimization_card':
        if not all([customer_code, location_id, start_date, end_date]):
            return "Missing required parameters: customer_code, location_id, start_date, end_date"
        return generate_optimization_card(customer_code, location_id, start_date, end_date)
    
    elif report_id == 'pareto_optimization':
        if not all([start_date, end_date, analysis_mode]):
            return "Missing required parameters: start_date, end_date, analysis_mode"
        
        if analysis_mode not in ['customer', 'region']:
            return "analysis_mode must be 'customer' or 'region'"
        
        if analysis_mode == 'customer' and not customer_code:
            return "Missing required parameter: customer_code (required for customer mode)"
        
        if analysis_mode == 'region' and not region:
            return "Missing required parameter: region (required for region mode)"
        
        return generate_pareto_optimization(
            start_date=start_date,
            end_date=end_date,
            mode=analysis_mode,
            customer_code=customer_code,
            region=region,
            selected_locations=selected_locations
        )
    
    else:
        return (
            f"Report '{report_id}' not implemented. "
            f"Available: site_health, customer_overview, region_overview, "
            f"optimization_card, pareto_optimization"
        )


# ============================================================
# ⚙️ Callback: setup_before_agent_call
# ------------------------------------------------------------
def setup_before_agent_call(callback_context: CallbackContext):
    """Initialize Scheduling Agent with database context."""
    if "database_settings" not in callback_context.state:
        callback_context.state["all_db_settings"] = {"use_database": "BigQuery"}
        
        # ACTUAL SCHEMA - from your database
        actual_schema = """
TABLE: APEX_NWS
Description: Workforce scheduling data with employee shifts, locations, and training records

COLUMNS:
- employee_id (INTEGER, NULLABLE): Unique employee identifier
- employee_name (STRING, NULLABLE): Full name of employee
- job_classification (STRING, NULLABLE): Employee job classification/role
- employee_status (STRING, NULLABLE): Active, Inactive, Bench, etc.
- scheduled_date (DATE, NULLABLE): Date of the scheduled shift
- scheduled_hours (FLOAT, NULLABLE): Number of hours scheduled for this shift
- start (STRING, NULLABLE): Shift start time (format: "HH:MMa/p")
- end (STRING, NULLABLE): Shift end time (format: "HH:MMa/p")
- customer_code (STRING, NULLABLE): Customer identifier code
- customer_name (STRING, NULLABLE): Name of the customer
- location_id (STRING, NULLABLE): Unique location/site identifier
- location_name (STRING, NULLABLE): Name of the location/site
- city (STRING, NULLABLE): City where location is located
- address (STRING, NULLABLE): Street address of location
- region (STRING, NULLABLE): Geographic region
- state (STRING, NULLABLE): US State code (e.g., CA, AZ, TX)
- site_manager (STRING, NULLABLE): Name of site manager
- performance_manager (STRING, NULLABLE): Name of performance manager
- workforce_admin (STRING, NULLABLE): Name of workforce administrator
- recruiter (STRING, NULLABLE): Name of recruiter
- employee_date_started (DATE, NULLABLE): Employee start date
- last_day_paid (STRING, NULLABLE): Last day employee was paid
- course (FLOAT, NULLABLE): Course identifier
- course_name (STRING, NULLABLE): Name of training course
- course_completion_date (STRING, NULLABLE): Date course was completed

IMPORTANT NOTES:
- location_name, city, and state ARE AVAILABLE and should be used for location queries
- Multiple employees can work at multiple locations
- Shifts can cross midnight (start time > end time)
- California (CA) has special overtime rules (daily OT >8hrs, double time >12hrs)

EXAMPLE QUERIES:
- Get all locations for customer: SELECT DISTINCT location_id, location_name, city, state FROM APEX_NWS WHERE customer_code = '10117'
- Get employee schedule: SELECT employee_id, employee_name, scheduled_date, scheduled_hours, start, end FROM APEX_NWS WHERE employee_id = 208135
"""
        
        callback_context.state["database_settings"] = {
            "bq_schema_and_samples": actual_schema
        }

    schema = callback_context.state["database_settings"]["bq_schema_and_samples"]

    callback_context._invocation_context.agent.instruction = (
        return_instructions_root()
        + f"""

--------- The BigQuery schema of the relevant data (with sample rows) ---------
{schema}

"""
    )


# ============================================================
# 🤖 Scheduling Agent Definition
# ------------------------------------------------------------
agent = Agent(
    model=os.getenv("SCHEDULING_AGENT_MODEL"),
    name="scheduling_agent",
    instruction=return_instructions_root(),
    global_instruction=(
        f"""
        You are the Scheduling Agent under EPC.
        Focus on workforce scheduling KPIs: lateness, absenteeism,
        shift coverage, and scheduling risk.
        Today's date: {date_today}
        """
    ),
    sub_agents=[],
    tools=[
        call_db_agent,
        call_ds_agent,
        load_artifacts,
        generate_standard_report,
        export_report_to_file,
        export_pareto_html_report
    ],
    before_agent_callback=setup_before_agent_call,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.6,
    ),
)