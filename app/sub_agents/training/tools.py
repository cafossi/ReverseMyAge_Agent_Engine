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
# 🛠️ Tool: call_research_agent
# ------------------------------------------------------------
# Executes the Compliance Research sub-agent.
# Searches for state-specific training compliance news.
# Stores output in `tool_context.state["research_agent_output"]`.
# ============================================================

async def call_research_agent(research_question: str, tool_context: ToolContext):
    """Executes the Compliance Research sub-agent.
    
    Searches for state-specific training compliance news, regulatory updates,
    and industry developments relevant to the security services sector.
    
    Args:
        research_question: Natural language research request (e.g., 
            "Research compliance training news for Texas" or 
            "Find recent security guard training requirements for Central South Region")
        tool_context: Tool context for state management
        
    Returns:
        Research findings with compliance news, regulatory updates, and recommendations
    """
    from .sub_agents.research.agent import research_agent
    
    logger.info(f"call_research_agent → research request: {research_question}")

    agent_tool = AgentTool(agent=research_agent)
    research_output = await agent_tool.run_async(
        args={"request": research_question}, tool_context=tool_context
    )

    # Save output
    tool_context.state["research_agent_output"] = research_output
    logger.info(f"Research completed: {len(str(research_output))} characters")
    
    return research_output