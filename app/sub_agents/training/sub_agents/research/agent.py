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

"""Compliance Training News Research Agent for APEX Training System.

Uses web search to find state-specific compliance training news, 
regulatory updates, and industry developments.
"""

# ============================================================
# 📦 Imports
# ------------------------------------------------------------
import os
from datetime import date

from google.genai import types
from google.adk.agents import Agent
from google.adk.tools import web_search

from .prompts import return_instructions_research

date_today = date.today()


# ============================================================
# 🤖 Compliance Research Agent Definition
# ------------------------------------------------------------
research_agent = Agent(
    model=os.getenv("TRAINING_AGENT_MODEL"),
    name="compliance_research_agent",
    instruction=return_instructions_research(),
    global_instruction=(
        f"""
        You are a Compliance Research Specialist focused on security industry 
        training requirements, regulatory updates, and state-specific compliance news.
        Today's date: {date_today}
        """
    ),
    tools=[web_search],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.3,
    ),
)