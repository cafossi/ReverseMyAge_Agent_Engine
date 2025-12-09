

"""Data Science Agent V2: generate nl2py and use code interpreter to run the code."""

# ============================================================
# 📦 Imports
# ------------------------------------------------------------

import os
from google.adk.code_executors import VertexAiCodeExecutor
from google.adk.agents import Agent
from .prompts import return_instructions_ds


# ============================================================
# 🤖 Root Data Science Agent
# ------------------------------------------------------------
# instruction:  DS-specific system prompt
# code_executor:stateful Vertex code interpreter (enables NL2Py execution)
# ============================================================

root_agent = Agent(
    model=os.getenv("ANALYTICS_AGENT_MODEL"),
    name="data_science_agent",
    instruction=return_instructions_ds(),
    code_executor=VertexAiCodeExecutor(
        optimize_data_file=True,
        stateful=True,
    ),
)
