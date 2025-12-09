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

"""
Touch Points Agent (Zuri) for EPC Analytics.

-- Uses NL2SQL for database queries
-- Uses NL2Py for further analytics
-- Routes BQML tasks only when explicitly requested
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

# Root prompt & tools for Touch Points
from .prompts import return_instructions_root
from .tools import call_db_agent, call_ds_agent,export_report_to_file

# Fast-track reports 
from .standard_reports import generate_standard_report

from .sub_agents.bigquery.tools import (
    get_database_settings as get_bq_database_settings,
)

date_today = date.today()


# ============================================================
# ⚙️ Callback: setup_before_agent_call
# ------------------------------------------------------------

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def setup_before_agent_call(callback_context: CallbackContext):
    """Setup the agent with safe schema handling + logging."""

    # Ensure database settings exist
    if "database_settings" not in callback_context.state:
        db_settings = {"use_database": "BigQuery"}
        callback_context.state["all_db_settings"] = db_settings

    if callback_context.state["all_db_settings"]["use_database"] == "BigQuery":
        callback_context.state["database_settings"] = get_bq_database_settings()
        db_settings = callback_context.state["database_settings"]

        # Schema selection with logging
        if db_settings.get("bq_ddl_schema"):
            schema = db_settings["bq_ddl_schema"]
            logger.info("✅ Using bq_ddl_schema")
        elif db_settings.get("bq_schema_and_samples"):
            schema = db_settings["bq_schema_and_samples"]
            logger.warning("⚠️ Fallback: Using bq_schema_and_samples")
        else:
            schema = "⚠️ No schema available"
            logger.error("❌ No schema found in database settings")

        # Update agent instruction
        callback_context._invocation_context.agent.instruction = (
            return_instructions_root()
            + f"""

    --------- The BigQuery schema of the relevant data with a few sample rows. ---------
    {schema}

    """
        )



# ============================================================
# 🤖 Touch Points Agent Definition
# ------------------------------------------------------------
agent = Agent(
    model=os.getenv("TP_AGENT_MODEL"),
    name="tp_agent",
    instruction=return_instructions_root(),
    global_instruction=(
        f"""
        You are the Touch Points (TP) Analytics Agent under EPC (codename: Zuri).
        Focus on customer interaction KPIs (volume, type mix, on-time closures, backlog,
        owner distribution, and Pareto hotspots) sourced exclusively from the APEX_TP dataset.
        Today's date: {date_today}
        """
    ),
    sub_agents=[],
    tools=[
        call_db_agent,
        call_ds_agent,
        generate_standard_report,
        load_artifacts,
        export_report_to_file,
    ],
    before_agent_callback=setup_before_agent_call,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.5,
    ),
)