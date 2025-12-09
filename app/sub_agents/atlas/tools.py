# Copyright 2025 Google LLC
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

"""Top level tools for the data multi-agent.

- call_db_agent: routes NL intent to the DB (NL2SQL) agent
- call_ds_agent: routes analysis to the DS (NL2Py) agent
- Includes Phase-1 guard to reject obvious SQL pasted into call_db_agent
"""

# ============================================================
# 📦 Imports
# ============================================================

import logging
import re

from google.adk.tools import ToolContext
from google.adk.tools.agent_tool import AgentTool

from .sub_agents import ds_agent, db_agent

logger = logging.getLogger(__name__)


# ============================================================
# 🔒 SQL Guard (Phase 1)
# ------------------------------------------------------------
# Conservative detector for SQL-like input:
# - SQL keyword at start (SELECT, INSERT, UPDATE, DELETE, WITH)
# - backtick-qualified identifiers (e.g., `project.dataset.table`)
# - trailing semicolon
# - SQL-style comment starts (--, #, /*)
# ============================================================

RAW_SQL_PATTERN = re.compile(
    r"^\s*(SELECT|INSERT|UPDATE|DELETE|WITH)\b|`[^`]+`\.[^`\s]+|;\s*$|^\s*(--|#|/\*)",
    re.IGNORECASE | re.DOTALL
)

# Toggle behavior: in Phase 1 we hard-reject when SQL is detected.
STRICT_REJECT_SQL = True


# ============================================================
# 🛠️ Tool: call_db_agent
# ------------------------------------------------------------
# Executes the Database (NL2SQL) sub-agent.
# Fetches structured query results from BigQuery or other DBs.
# Stores output in `tool_context.state["db_agent_output"]`
# and mirrors into `tool_context.state["query_result"]`.
# ============================================================

async def call_db_agent(question: str, tool_context: ToolContext):
    """Executes the Database (NL2SQL) sub-agent."""

    # Guard: empty input
    if not question or not question.strip():
        return {"error": "Empty question provided"}

    use_db = tool_context.state.get("all_db_settings", {}).get("use_database", "Unknown")

    # Phase 1: detect and reject SQL-like input so root agent reformulates as NL
    if RAW_SQL_PATTERN.search(question):
        logger.error("❌ SQL detected in call_db_agent; rejecting. Sample: %r", question[:150])
        if STRICT_REJECT_SQL:
            return {
                "error": "SQL syntax detected",
                "message": "call_db_agent requires a natural-language question, not SQL.",
                "hint": "Root agent should reformulate as an NL request (intent only).",
            }
        else:
            # Optional future behavior (Phase 2): auto-rewrite as NL intent prompt
            nl_intent = (
                "Generate correct BigQuery SQL from the natural-language intent below. "
                "Apply NBOT rules (Total Hours = SUM(counter_hours); OT via counter_type list). "
                "Use only the allowed dataset and schema. "
                f"Intent: {question}"
            )
            question = nl_intent  # proceed with rewritten intent

    logger.info("call_db_agent → database: %s, question: %s", use_db, question[:120])

    agent_tool = AgentTool(agent=db_agent)
    db_agent_output = await agent_tool.run_async(
        args={"request": question},
        tool_context=tool_context,
    )

    # Persist outputs for downstream tools (e.g., DS agent)
    tool_context.state["db_agent_output"] = db_agent_output
    # NOTE: rows live in tool_context.state["query_result"] (set by run_bigquery_validation)
    return db_agent_output


# ============================================================
# 🛠️ Tool: call_ds_agent
# ------------------------------------------------------------
# Executes the Data Science (NL2Py) sub-agent.
# Uses `tool_context.state["query_result"]` to perform analysis.
# Stores output in `tool_context.state["ds_agent_output"]`.
# ============================================================

async def call_ds_agent(question: str, tool_context: ToolContext):
    """Executes the Data Science (NL2Py) sub-agent. Falls back to DB if needed."""

    if question == "N/A":
        # Surface the latest DB output if user asks for summarization only
        return tool_context.state.get("db_agent_output", {
            "error": "No database output available"
        })

    # Ensure data is available for analysis
    if not tool_context.state.get("query_result"):
        logger.warning("No query_result found → fetching from db_agent first")
        db_query = f"Retrieve relevant data for: {question}"
        await call_db_agent(db_query, tool_context)

        if not tool_context.state.get("query_result"):
            return {
                "error": "Failed to fetch data from database",
                "details": "The db_agent did not return results.",
            }

    input_data = tool_context.state["query_result"]
    if not input_data:
        return {
            "error": "No data available for analysis",
            "details": "query_result is empty.",
        }

    # Package the question with the retrieved data for DS agent
    question_with_data = f"""
Question to answer: {question}

Actual data to analyze (from previous DB step):
{input_data}
""".strip()

    agent_tool = AgentTool(agent=ds_agent)
    ds_agent_output = await agent_tool.run_async(
        args={"request": question_with_data},
        tool_context=tool_context,
    )

    tool_context.state["ds_agent_output"] = ds_agent_output
    return ds_agent_output


# ============================================================
# 🛠️ Tool: export_report_to_file
# ------------------------------------------------------------
# Exports NBOT standard reports to PDF or HTML format
# ============================================================

from typing import Optional

async def export_report_to_file(
    report_id: str,
    format: str,
    customer_code: Optional[int] = None,
    customer_name: Optional[str] = None,
    location_number: Optional[str] = None,
    region: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tool_context: Optional[ToolContext] = None
) -> dict:
    """
    Export an NBOT standard report to HTML or PDF format.
    
    Args:
        report_id: Type of report ('nbot_site_analysis', 'nbot_region_analysis', 
                   'nbot_customer_analysis', 'nbot_company_by_region', 'nbot_company_by_customer')
        format: Export format ('html' or 'pdf')
        customer_code: Customer code (for site and customer analysis)
        customer_name: Customer name (alternative to customer_code)
        location_number: Location number (for site analysis only)
        region: Region name (for region analysis)
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    
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
            'customer_name': customer_name,
            'location_number': location_number,
            'region': region,
            'start_date': start_date,
            'end_date': end_date
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
        return {
            "error": str(e),
            "success": False,
            "message": f"❌ Failed to generate report: {str(e)}"
        }