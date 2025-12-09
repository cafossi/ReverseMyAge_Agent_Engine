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



"""Top level agent for data agent multi-agents.

-- it get data from database (e.g., BQ) using NL2SQL
-- then, it use NL2Py to do further data analysis as needed
"""

# ============================================================
# 📦 Imports
# ============================================================

import logging
from typing import Optional
from google.adk.tools import ToolContext
from google.adk.tools.agent_tool import AgentTool

from .sub_agents import ds_agent, db_agent

logger = logging.getLogger(__name__)


# ============================================================
# 🛠️ Tool: call_db_agent
# ------------------------------------------------------------
# Executes the Database (NL2SQL) sub-agent.
# Fetches structured query results from BigQuery or other DBs.
# Stores output in `tool_context.state["db_agent_output"]`.
# ============================================================

async def call_db_agent(question: str, tool_context: ToolContext):
    """Executes the Database (NL2SQL) sub-agent."""
    use_db = tool_context.state.get("all_db_settings", {}).get("use_database", "Unknown")
    logger.info(f"call_db_agent → using database: {use_db}")

    agent_tool = AgentTool(agent=db_agent)
    db_agent_output = await agent_tool.run_async(
        args={"request": question}, tool_context=tool_context
    )

    # Save output into both db_agent_output and query_result
    tool_context.state["db_agent_output"] = db_agent_output
    tool_context.state["query_result"] = db_agent_output
    return db_agent_output


 # ============================================================
# 🛠️ Tool: call_ds_agent
# ------------------------------------------------------------
# Executes the Data Science (NL2Py) sub-agent.
# Uses query results to perform analysis or modeling.
# Stores output in `tool_context.state["ds_agent_output"]`.
# ===========================================================   


async def call_ds_agent(question: str, tool_context: ToolContext):
    """Executes the Data Science (NL2Py) sub-agent.
    Falls back to DB call if no query_result exists.
    """

    if question == "N/A":
        return tool_context.state.get("db_agent_output", {
            "error": "No database output available"
        })

    # Ensure data is available
    if not tool_context.state.get("query_result"):
        logger.warning("No query_result found → fetching from db_agent first")
        db_query = f"Retrieve relevant data for: {question}"
        await call_db_agent(db_query, tool_context)

        if not tool_context.state.get("query_result"):
            return {
                "error": "Failed to fetch data from database",
                "details": "The db_agent did not return results."
            }

    # Now we have query_result
    input_data = tool_context.state["query_result"]

    if not input_data:
        return {
            "error": "No data available for analysis",
            "details": "query_result is empty."
        }

    question_with_data = f"""
Question: {question}

Data to analyze:
{input_data}
"""

    agent_tool = AgentTool(agent=ds_agent)
    ds_agent_output = await agent_tool.run_async(
        args={"request": question_with_data}, tool_context=tool_context
    )

    tool_context.state["ds_agent_output"] = ds_agent_output
    return ds_agent_output


# ============================================================
# 🛠️ Tool: generate_standard_report
# ------------------------------------------------------------
# Generates standard reports using the modular report system
# ============================================================

async def generate_standard_report(
    report_id: str,
    customer_code: Optional[int] = None,
    location_id: Optional[str] = None,
    region: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    selected_locations: Optional[list] = None,
    analysis_mode: Optional[str] = None,
    tool_context: Optional[ToolContext] = None
) -> dict:
    """
    Generate a standard report using the modular report system.
    
    Args:
        report_id: Type of report ('site_health', 'customer_overview', 'region_overview', 'optimization_card', 'pareto_optimization')
        customer_code: Customer identifier (required for site_health, customer_overview, optimization_card, pareto customer mode)
        location_id: Location identifier (required for site_health, optimization_card)
        region: Region identifier (required for region_overview, pareto region mode)
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        selected_locations: List of location IDs for pareto_optimization step 2
        analysis_mode: 'customer' or 'region' for pareto_optimization
        tool_context: Tool context
    
    Returns:
        Dictionary with markdown content or error message
    """
    
    try:
        # Import from modular structure
        from .schedule_reports.reports import (
            generate_site_health,
            generate_customer_overview,
            generate_region_overview,
            generate_optimization_card,
            generate_pareto_optimization,
        )
        
        # Route to appropriate report function
        if report_id == 'site_health':
            if not all([customer_code, location_id, start_date, end_date]):
                return {
                    "error": "Missing required parameters",
                    "details": "site_health requires: customer_code, location_id, start_date, end_date"
                }
            markdown_content = generate_site_health(customer_code, location_id, start_date, end_date)
        
        elif report_id == 'customer_overview':
            if not all([customer_code, start_date, end_date]):
                return {
                    "error": "Missing required parameters",
                    "details": "customer_overview requires: customer_code, start_date, end_date"
                }
            markdown_content = generate_customer_overview(customer_code, start_date, end_date)
        
        elif report_id == 'region_overview':
            if not all([region, start_date, end_date]):
                return {
                    "error": "Missing required parameters",
                    "details": "region_overview requires: region, start_date, end_date"
                }
            markdown_content = generate_region_overview(region, start_date, end_date)
        
        elif report_id == 'optimization_card':
            if not all([customer_code, location_id, start_date, end_date]):
                return {
                    "error": "Missing required parameters",
                    "details": "optimization_card requires: customer_code, location_id, start_date, end_date"
                }
            markdown_content = generate_optimization_card(customer_code, location_id, start_date, end_date)
        
        elif report_id == 'pareto_optimization':
            if not all([start_date, end_date, analysis_mode]):
                return {
                    "error": "Missing required parameters",
                    "details": "pareto_optimization requires: start_date, end_date, analysis_mode"
                }
            
            if analysis_mode not in ['customer', 'region']:
                return {
                    "error": "Invalid analysis_mode",
                    "details": "analysis_mode must be 'customer' or 'region'"
                }
            
            if analysis_mode == 'customer' and not customer_code:
                return {
                    "error": "Missing required parameter",
                    "details": "customer_code required for customer mode"
                }
            
            if analysis_mode == 'region' and not region:
                return {
                    "error": "Missing required parameter",
                    "details": "region required for region mode"
                }
            
            markdown_content = generate_pareto_optimization(
                start_date=start_date,
                end_date=end_date,
                mode=analysis_mode,
                customer_code=customer_code,
                region=region,
                selected_locations=selected_locations
            )
        
        else:
            return {
                "error": f"Unknown report_id: {report_id}",
                "details": "Available: site_health, customer_overview, region_overview, optimization_card, pareto_optimization"
            }
        
        # Return successful result
        return {
            "success": True,
            "report_type": report_id,
            "content": markdown_content
        }
    
    except Exception as e:
        logger.error(f"Report generation failed: {str(e)}")
        return {
            "error": "Report generation failed",
            "details": str(e),
            "success": False
        }


# ============================================================
# 🛠️ Tool: export_report_to_file
# ------------------------------------------------------------
# Exports standard reports to PDF or HTML format
# ============================================================

async def export_report_to_file(
    report_id: str,
    format: str,
    customer_code: Optional[int] = None,
    location_id: Optional[str] = None,
    region: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    analysis_mode: Optional[str] = None,
    selected_locations: Optional[list] = None,
    tool_context: Optional[ToolContext] = None
) -> dict:
    """
    Export a standard report to HTML or PDF format.
    
    Args:
        report_id: Type of report ('site_health', 'customer_overview', 'region_overview', 'optimization_card', 'pareto_optimization')
        format: Export format ('html' or 'pdf')
        customer_code: Customer code (for site_health, customer_overview, optimization_card, pareto customer mode)
        location_id: Location ID (for site_health, optimization_card)
        region: Region name (for region_overview, pareto region mode)
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        analysis_mode: 'customer' or 'region' for pareto_optimization
        selected_locations: List of locations for pareto_optimization
    
    Returns:
        Dictionary with file path and download information
    """
    
    from .report_exporter import export_standard_report
    
    try:
        # Validate format
        if format.lower() not in ['html', 'pdf']:
            return {
                "error": f"Invalid format: {format}. Use 'html' or 'pdf'",
                "success": False
            }
        
        # Build kwargs
        kwargs = {
            'customer_code': customer_code,
            'location_id': location_id,
            'region': region,
            'start_date': start_date,
            'end_date': end_date,
            'analysis_mode': analysis_mode,
            'selected_locations': selected_locations
        }
        
        # Remove None values
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        
        # Generate report
        file_path = export_standard_report(
            report_id=report_id,
            format=format.lower(),
            **kwargs
        )
        
        return {
            "success": True,
            "file_path": file_path,
            "format": format.lower(),
            "report_id": report_id,
            "message": f"✅ {report_id.replace('_', ' ').title()} Report successfully generated as {format.upper()}!\n\n📁 File Location: {file_path}\n\nYou can access this file from the reports directory."
        }
        
    except Exception as e:
        logger.error(f"Export failed: {str(e)}")
        return {
            "error": str(e),
            "success": False,
            "message": f"❌ Failed to generate report: {str(e)}"
        }

# ============================================================
# 🛠️ Tool: export_pareto_html_report
# ------------------------------------------------------------
# Exports NEW HTML-based Pareto reports with interactive features
# ============================================================

async def export_pareto_html_report(
    start_date: str,
    end_date: str,
    mode: str,
    format: str = 'html',
    customer_code: Optional[int] = None,
    customer_name: Optional[str] = None,
    region: Optional[str] = None,
    selected_locations: Optional[list] = None,
    tool_context: Optional[ToolContext] = None
) -> dict:
    """
    Export NEW HTML-based Pareto Optimization Report with interactive features.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        mode: 'customer' or 'region'
        format: 'html' or 'pdf' (default: 'html')
        customer_code: Required for customer mode
        customer_name: Optional customer name (used for filename if provided)
        region: Required for region mode
        selected_locations: Optional list of location IDs
    
    Returns:
        Dictionary with file path and success status
    """
    
    from .report_exporter import export_pareto_html_report as export_func
    
    try:
        # Validate inputs
        if mode not in ['customer', 'region']:
            return {
                "error": "Invalid mode. Use 'customer' or 'region'",
                "success": False
            }
        
        if mode == 'customer' and not customer_code:
            return {
                "error": "customer_code required for customer mode",
                "success": False
            }
        
        if mode == 'region' and not region:
            return {
                "error": "region required for region mode",
                "success": False
            }
        
        # Generate report
        file_path = export_func(
            start_date=start_date,
            end_date=end_date,
            mode=mode,
            format=format.lower(),
            customer_code=customer_code,
            customer_name=customer_name,
            region=region,
            selected_locations=selected_locations
        )
        
        return {
            "success": True,
            "file_path": file_path,
            "format": format.lower(),
            "mode": mode,
            "message": f"✅ NEW HTML Pareto Report successfully generated!\n\n📁 File Location: {file_path}\n\n🎨 Features: Industrial chrome design, interactive sections, sortable tables, site cards\n\nOpen in browser to see interactive features!"
        }
        
    except Exception as e:
        logger.error(f"HTML Pareto export failed: {str(e)}")
        return {
            "error": str(e),
            "success": False,
            "message": f"❌ Failed to generate HTML report: {str(e)}"
        }