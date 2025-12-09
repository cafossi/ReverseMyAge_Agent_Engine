"""Database Agent: get data from database (BigQuery) using NL2SQL."""

# ============================================================
# 📦 Imports
# ============================================================

import os
import re
import json
import hashlib
from datetime import date, datetime
from typing import Any, Dict, Optional

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import BaseTool, ToolContext
from google.adk.tools.bigquery import BigQueryToolset
from google.adk.tools.bigquery.config import BigQueryToolConfig, WriteMode
from google.genai import types

from . import tools
from .chase_sql import chase_db_tools
from .prompts import return_instructions_bigquery

# ============================================================
# 🔧 Config: NL2SQL strategy
# ============================================================

NL2SQL_METHOD = os.getenv("NL2SQL_METHOD", "BASELINE")

# BigQuery built-in tools in ADK
ADK_BUILTIN_BQ_EXECUTE_SQL_TOOL = "execute_sql"

# ============================================================
# ⚙️ Callback: initialize database settings
# ============================================================

def setup_before_agent_call(callback_context: CallbackContext) -> None:
    """Setup the agent."""
    if "database_settings" not in callback_context.state:
        callback_context.state["database_settings"] = tools.get_database_settings()

# ============================================================
# 🔹 JSON serialization helper
# ============================================================

def json_serial(obj):
    """JSON serializer for objects not serializable by default."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

# ============================================================
# Helper: Serialize BigQuery rows
# ============================================================

def serialize_bigquery_results(rows):
    """Safely serialize BigQuery results containing date/datetime objects."""
    try:
        serialized = json.dumps(rows, default=json_serial)
        return json.loads(serialized)
    except Exception as e:
        print(f"Warning: Failed to serialize BigQuery results: {e}")
        return rows

# ============================================================
# 🔹 Updated: Clear-and-replace result storage (ADK State-safe)
# ============================================================

def store_results_in_context(
    tool: BaseTool,
    args: Dict[str, Any],
    tool_context: ToolContext,
    tool_response: Dict
) -> Optional[Dict]:
    """
    Store BigQuery results in tool_context.state with clear-and-replace logic.
    Uses plain dict-style assignment to avoid AttributeErrors.
    """
    if tool.name != ADK_BUILTIN_BQ_EXECUTE_SQL_TOOL:
        return None

    # 1) Clear previous query-related keys
    for key in ("query_result", "last_query", "query_metadata"):
        if key in tool_context.state:
            tool_context.state[key] = None

    status = tool_response.get("status", "").upper()
    if status == "SUCCESS":
        rows = tool_response.get("rows") or []
        serialized_rows = serialize_bigquery_results(rows)
        query = args.get("query", "")

        # 2) Store new clean data
        tool_context.state["query_result"] = serialized_rows
        tool_context.state["last_query"] = query
        tool_context.state["query_metadata"] = {
            "row_count": len(serialized_rows),
            "status": "success",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "query_hash": hashlib.md5(query.encode()).hexdigest()[:8] if query else None,
        }

        print(f"[ADK][BQ] Stored {len(serialized_rows)} rows "
              f"(hash={tool_context.state['query_metadata']['query_hash']})")
    else:
        # 3) Save error state
        tool_context.state["query_result"] = None
        tool_context.state["query_metadata"] = {
            "status": "failed",
            "error": tool_response.get("error", "Unknown error"),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        print(f"[ADK][BQ] Query failed: {tool_response.get('error', 'Unknown')}")

    return None

# ============================================================
# SQL Validator — Enforces Schema Lock (MOVED BEFORE CLASS)
# ============================================================

def validate_sql(query: str) -> str:
    """Enhanced validation with better JOIN and forbidden table detection."""
    q = query.lower().strip()
    
    # Remove comments and normalize whitespace
    q_clean = re.sub(r'--.*?\n', ' ', q)
    q_clean = re.sub(r'/\*.*?\*/', ' ', q_clean, flags=re.DOTALL)
    q_clean = re.sub(r'\s+', ' ', q_clean).strip()
    
    # 1) Block all JOIN patterns (enhanced detection)
    join_patterns = [' join ', ' inner join ', ' left join ', ' right join ', ' full join ', ' cross join ']
    for join_pattern in join_patterns:
        if join_pattern in q_clean:
            raise ValueError(f"❌ INVALID QUERY: {join_pattern.strip().upper()} detected. Only flat table APEX_NWS is allowed.")
    
    # 2) Block forbidden table references
    forbidden_tables = ['employees', 'schedules', 'locations', 'customers', 'employee_table', 'schedule_table']
    for table in forbidden_tables:
        if table in q_clean:
            raise ValueError(f"❌ INVALID QUERY: References forbidden table '{table}'. Only APEX_NWS exists.")
    
    # 3) Ensure correct table reference
    if "APEX_Performance_DataMart.APEX_NWS" not in q_clean:
        raise ValueError(
            "❌ INVALID QUERY: Query must reference ONLY `APEX_Performance_DataMart.APEX_NWS`."
        )

    return query

# ============================================================
# Validated BigQuery Toolset Configuration
# ============================================================

bigquery_tool_filter = [ADK_BUILTIN_BQ_EXECUTE_SQL_TOOL]
bigquery_tool_config = BigQueryToolConfig(
    write_mode=WriteMode.BLOCKED,
    max_query_result_rows=10000
)

class ValidatedBigQueryToolset(BigQueryToolset):
    def execute_sql(self, query: str, project_id: str, **kwargs):
        # Validate before execution
        try:
            validated_query = validate_sql(query)
            return super().execute_sql(validated_query, project_id, **kwargs)
        except ValueError as e:
            return {
                "status": "VALIDATION_FAILED",
                "error": str(e),
                "rows": []
            }

validated_bigquery_toolset = ValidatedBigQueryToolset(
    tool_filter=bigquery_tool_filter,
    bigquery_tool_config=bigquery_tool_config
)

# ============================================================
# 🤖 Agent: BigQuery (NL2SQL + validation)
# ============================================================

database_agent = Agent(
    model=os.getenv("BIGQUERY_AGENT_MODEL"),
    name="database_agent",
    instruction=return_instructions_bigquery(),
    tools=[
        (
            chase_db_tools.initial_bq_nl2sql
            if NL2SQL_METHOD == "CHASE"
            else tools.initial_bq_nl2sql
        ),
        validated_bigquery_toolset,
    ],
    before_agent_callback=setup_before_agent_call,
    after_tool_callback=store_results_in_context,
    generate_content_config=types.GenerateContentConfig(temperature=0.01),
)