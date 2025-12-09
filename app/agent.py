# app/agent.py
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

"""Nexus Command – Root Orchestrator Agent (Nexus Chief Agent).

This is the Tier-3 executive orchestrator for the Nexus Command domain.

Responsibilities:
- Understand Carlos's intent at a strategic level.
- Select the best specialist agent (Atlas, Maestro, Aegis, etc.) based on cues.
- Provide strategic framing before delegation (context → plan → outcome).
- Coordinate multi-agent flows when problems span multiple domains.
"""

from __future__ import annotations

# ============================================================
# 📦 Imports
# ============================================================
import os
from datetime import date


from typing import Any, Dict, List, Optional

from google.genai import types
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import load_artifacts

# 🔑 Dynamic domain metadata (from YAML)
from .domain_config import get_domain_block, get_domain_name

# 🎭 Root prompts (greeting + behavioral contract)
from .prompts import (
    return_instructions_root,
    return_greeting_template,
    return_greeting_compact,
)

# ============================================================
# 🧩 Sub-Agents (current concrete implementations)
# ------------------------------------------------------------
# NOTE:
# For now we re-use your existing EPC sub-agents and map them
# to the new conceptual Nexus roles:
#   - Atlas   → NBOT / historical analytics
#   - Maestro → Scheduling / capacity planning
#   - Aegis   → Training & compliance
#   - Scout   → (TO-BE: Google Trends / external signals)
#   - Sage    → sage / deep intel (Implemented)
#   - Pulse   → Touch points / communications
#   - Lexi    → SME / Vertex RAG
#   - Quanta  → (TO-BE: BigQuery SME)
#   - Gears   → (TO-BE: Automation agent)
#   - Sentinel→ (TO-BE: Monitoring agent)
#
# You can later point each name to its own ADK agent module.
# For now we wire the ones you already have.

from .sub_agents.atlas.agent import agent as atlas_agent          # Atlas
from .sub_agents.scheduling.agent import agent as maestro_agent  # Maestro
from .sub_agents.training.agent import agent as aegis_agent      # Aegis
from .sub_agents.sage.agent import agent as sage_agent     # Sage
from .sub_agents.touch_points.agent import agent as pulse_agent  # Pulse
from .sub_agents.sme.agent import agent as lexi_agent            # Lexi

# TODO (future):
# from .sub_agents.trends.agent import agent as scout_agent      # Scout (Google Trends)
# from .sub_agents.bigquery_sme.agent import agent as quanta_agent
# from .sub_agents.automation.agent import agent as gears_agent
# from .sub_agents.monitor.agent import agent as sentinel_agent

# ============================================================
# 🗺️ Domain Config & Agent Cue Map
# ============================================================

DOMAIN_KEY = "nexus_command"
DOMAIN_META: Dict[str, Any] = get_domain_block(DOMAIN_KEY)
DOMAIN_NAME: str = get_domain_name(DOMAIN_KEY)
date_today = date.today()


def _build_agent_cue_map(domain_cfg: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Build a {agent_key: {nickname, id, cues[]}} map from YAML config.

    Each agent entry in agents.yaml can look like:

      - id: atlas
        nickname: "Atlas"
        official_name: "AnalyticsAgent"
        cues:
          - "historical"
          - "last week"
          - "overtime"

    We normalise cues to lowercase substrings for simple matching.
    """
    cue_map: Dict[str, Dict[str, Any]] = {}
    for agent_cfg in domain_cfg.get("agents", []):
        agent_id = (agent_cfg.get("id") or "").strip()
        nickname = (agent_cfg.get("nickname") or "").strip()
        cues = [c.lower() for c in agent_cfg.get("cues", []) if isinstance(c, str)]

        if not (agent_id or nickname) or not cues:
            continue

        key = (agent_id or nickname).lower()
        cue_map[key] = {
            "id": agent_id,
            "nickname": nickname,
            "cues": cues,
        }
    return cue_map


AGENT_CUE_MAP = _build_agent_cue_map(DOMAIN_META)

# Registry from logical agent key → concrete ADK Agent object
AGENT_REGISTRY: Dict[str, Agent] = {
    "atlas": atlas_agent,
    "maestro": maestro_agent,
    "aegis": aegis_agent,
    "sage": sage_agent,
    "pulse": pulse_agent,
    "lexi": lexi_agent,
    # "scout": scout_agent,
    # "quanta": quanta_agent,
    # "gears": gears_agent,
    # "sentinel": sentinel_agent,
}


# ============================================================
# ⚙️ Callback: setup_before_agent_call
# ============================================================

def setup_before_agent_call(callback_context: CallbackContext):
    """Setup Nexus Chief Agent before execution."""
    if "routing_info" not in callback_context.state:
        callback_context.state["routing_info"] = "nexus_orchestrator_initialized"


# ============================================================
# 🧠 Routing Logic (dynamic, YAML-driven)
# ============================================================

def _score_agent_for_query(agent_key: str, query_lc: str) -> int:
    """Return a simple relevance score = number of cue substrings matched."""
    agent_meta = AGENT_CUE_MAP.get(agent_key, {})
    cues: List[str] = agent_meta.get("cues", [])
    score = 0
    for cue in cues:
        if cue and cue in query_lc:
            score += 1
    return score


def _choose_best_agent_key(user_input: str) -> Optional[str]:
    """Choose the best agent key based on cue matches.

    - Returns agent_key (e.g., "atlas", "maestro") or None if ambiguous/none.
    - Only considers agents that exist in AGENT_REGISTRY.
    """
    if not user_input:
        return None

    q = user_input.lower()
    best_key: Optional[str] = None
    best_score = 0

    for agent_key in AGENT_REGISTRY.keys():
        score = _score_agent_for_query(agent_key, q)
        if score > best_score:
            best_score = score
            best_key = agent_key

    if best_score == 0:
        return None
    return best_key


def route_to_agent(user_input: str):
    """ADK Tool: Decide which specialist agent should handle this request.

    Returns:
        - An ADK Agent object (e.g., atlas_agent) when a clear match exists.
        - None when routing is ambiguous → the Nexus Chief Agent should ask
          *one* clarifying question instead of guessing.
    """
    best_key = _choose_best_agent_key(user_input)

    if best_key is None:
        # Ambiguous → let Nexus ask a clarifying question in natural language.
        return None

    agent_obj = AGENT_REGISTRY.get(best_key)
    return agent_obj


# ============================================================
# ⚡ Auto Greeting on Startup
# ============================================================

def greet_carlos_on_startup() -> str:
    """
    Returns the Nexus greeting message.
    Uses compact version if NEXUS_COMPACT_GREETING=1
    """
    use_compact = os.getenv("NEXUS_COMPACT_GREETING", "0") == "1"
    return return_greeting_compact() if use_compact else return_greeting_template()


# ============================================================
# 🤖 Root Orchestrator Agent Definition
# ============================================================

# User configuration
USER_NAME = os.getenv("NEXUS_USER_NAME", "Carlos")
USER_LOCATION = os.getenv("NEXUS_USER_LOCATION", "Dallas, TX")

# Pre-fetch weather for greeting (graceful degradation if unavailable)
from .utils.weather import get_weather_summary
WEATHER_SUMMARY = get_weather_summary(USER_LOCATION)

root_agent = Agent(
    model=os.getenv("ROOT_AGENT_MODEL"),
    name="nexus_root_orchestrator",
    instruction=return_instructions_root(
        user_name=USER_NAME,
        user_location=USER_LOCATION,
        weather_summary=WEATHER_SUMMARY,
    ),
    global_instruction=f"""
        You are the **Nexus Chief Agent** for the **{DOMAIN_NAME}** domain.

        - Today's date: {date_today}
        - User: {USER_NAME} (Location: {USER_LOCATION})
        - You report directly to {USER_NAME}.
        - You coordinate a team of specialised agents (Atlas, Maestro, Aegis, Scout,
          Sage, Pulse, Lexi, Quanta, Gears, Sentinel) as if they were a digital department.

        Use the `route_to_agent` tool to select the best specialist based on cues
        defined in the domain configuration (agents.yaml). When routing is ambiguous,
        ask one clarifying question instead of guessing.
        """,
    sub_agents=[
        atlas_agent,
        maestro_agent,
        aegis_agent,
        sage_agent,
        pulse_agent,
        lexi_agent,
        # scout_agent,
        # quanta_agent,
        # gears_agent,
        # sentinel_agent,
    ],
    tools=[
        route_to_agent,
        load_artifacts,
        # export_agent_report,  # when you re-enable the export tool
    ],
    before_agent_callback=setup_before_agent_call,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.7,
        candidate_count=1,
        top_p=0.9,
        top_k=40,
        response_modalities=["TEXT"],
    ),
)

# ============================================================
# 🧠 Initialize with Greeting (manual run)
# ============================================================

if __name__ == "__main__":
    print(greet_carlos_on_startup())
