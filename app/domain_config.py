from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml  # ensure `pyyaml` is in your pyproject dependencies

# ============================================================
# Paths & Core Config Load
# ============================================================

# This file lives in app/, config is in app/config/agents.yaml
BASE_DIR = Path(__file__).resolve().parent
AGENT_CONFIG_PATH = BASE_DIR / "config" / "agents.yaml"


def _load_config() -> Dict[str, Any]:
    """Load the full agents configuration from YAML."""
    if not AGENT_CONFIG_PATH.exists():
        raise FileNotFoundError(f"Agent config not found at {AGENT_CONFIG_PATH}")
    with AGENT_CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_domain_block(domain_key: str = "nexus_command") -> Dict[str, Any]:
    """Return the configuration block for a given domain key."""
    cfg = _load_config()
    try:
        return cfg["domains"][domain_key]
    except KeyError as e:
        raise KeyError(f"Domain '{domain_key}' not found in agents.yaml") from e


# ============================================================
# Public Helpers for Prompts / UI
# ============================================================

def get_agent_roster(domain_key: str = "nexus_command") -> List[Tuple[str, str]]:
    """
    Returns a list of (nickname, description_string) for the greeting UI.

    Example element:
      ("Atlas",
       "AnalyticsAgent — historical performance analytics, overtime %, hours mix, KPI trends")
    """
    domain = get_domain_block(domain_key)
    agents = domain.get("agents", [])
    roster: List[Tuple[str, str]] = []

    for agent in agents:
        nickname = (agent.get("nickname") or "").strip()
        official_name = (agent.get("official_name") or "").strip()
        description = (agent.get("description") or "").strip()

        if not nickname or not description:
            # Skip malformed entries
            continue

        desc_full = f"{official_name} — {description}" if official_name else description
        roster.append((nickname, desc_full))

    return roster


def get_domain_overview(domain_key: str = "nexus_command") -> str:
    """Return the domain overview text (for instructions / system prompt)."""
    domain = get_domain_block(domain_key)
    return (domain.get("domain_overview") or "").strip()


def get_domain_name(domain_key: str = "nexus_command") -> str:
    """Return the human-readable domain name (e.g. 'Nexus Command')."""
    domain = get_domain_block(domain_key)
    return (domain.get("domain_name") or domain_key).strip()


# ============================================================
# Routing Engine: Agent Index & Cue Map
# ============================================================

def _build_agent_index(
    domain_key: str = "nexus_command",
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, set[str]]]:
    """
    Build:
      - agents_by_id: {agent_id -> agent_dict}
      - cue_map: {cue_string_lower -> set(agent_id)}

    agents.yaml structure (excerpt reminder):

    domains:
      nexus_command:
        agents:
          - id: atlas
            nickname: "Atlas"
            official_name: "AnalyticsAgent"
            description: "..."
            cues:
              - "historical"
              - "last week"
              - "hours worked"
    """
    domain = get_domain_block(domain_key)
    agents = domain.get("agents", [])

    agents_by_id: Dict[str, Dict[str, Any]] = {}
    cue_map: Dict[str, set[str]] = defaultdict(set)

    for agent in agents:
        agent_id = (agent.get("id") or "").strip()
        if not agent_id:
            continue

        agents_by_id[agent_id] = agent

        for cue in agent.get("cues", []) or []:
            cue_norm = (cue or "").strip().lower()
            if not cue_norm:
                continue
            cue_map[cue_norm].add(agent_id)

    return agents_by_id, cue_map


def _score_agents_by_input(
    user_input: str,
    domain_key: str = "nexus_command",
) -> Dict[str, float]:
    """
    Score agents based on cue matches found in the user input.

    Scoring logic:
      - Each cue that appears in the text contributes to every agent that owns it.
      - Contribution is weighted by 1 / (# of agents sharing that cue),
        so unique cues are more powerful than shared ones.
    """
    text = user_input.lower()
    _, cue_map = _build_agent_index(domain_key=domain_key)

    scores: Dict[str, float] = {}

    for cue, agent_ids in cue_map.items():
        if cue in text:
            # Unique cues are stronger than shared cues
            weight = 1.0 / float(len(agent_ids)) if agent_ids else 0.0
            for agent_id in agent_ids:
                scores[agent_id] = scores.get(agent_id, 0.0) + weight

    return scores


# ============================================================
# Public Routing API
# ============================================================

def return_routing_plan(
    user_input: str,
    domain_key: str = "nexus_command",
    min_confidence: float = 0.0,
) -> Dict[str, Any]:
    """
    Decide which agent should own the request, based on cue matching.

    Returns a dict like:

    {
      "decision": "atlas",           # or "clarify"/"ask_for_clarification"
      "confidence": 1.0,
      "reason": "Matched cues: ['historical', 'last week'] → Atlas",
      "selected_agent": {
          "id": "atlas",
          "nickname": "Atlas",
          "official_name": "AnalyticsAgent",
          "description": "...",
      },
      "candidates": [
          {"id": "atlas", ...},
          {"id": "maestro", ...},
      ],
    }
    """
    agents_by_id, cue_map = _build_agent_index(domain_key=domain_key)
    scores = _score_agents_by_input(user_input, domain_key=domain_key)

    # No cues matched at all → ask for clarification
    if not scores:
        return {
            "decision": "clarify",
            "confidence": 0.0,
            "reason": "No routing cues from agents.yaml matched the request.",
            "selected_agent": None,
            "candidates": [],
        }

    # Compute best score and top candidates
    best_score = max(scores.values())
    top_agents = [aid for aid, s in scores.items() if s == best_score]

    # Low-confidence case (optional behavior)
    if best_score < min_confidence:
        return {
            "decision": "clarify_low_signal",
            "confidence": best_score,
            "reason": (
                "Routing signal is weak; multiple agents have low, similar scores. "
                "Ask a clarifying question (e.g., 'Is this about schedules, research, "
                "training, automation, or monitoring?')."
            ),
            "selected_agent": None,
            "candidates": [
                {
                    "id": aid,
                    "nickname": agents_by_id.get(aid, {}).get("nickname"),
                    "official_name": agents_by_id.get(aid, {}).get("official_name"),
                    "description": agents_by_id.get(aid, {}).get("description"),
                    "score": scores.get(aid),
                }
                for aid in scores.keys()
            ],
        }

    # Ties between multiple agents with same top score → clarify
    if len(top_agents) > 1:
        return {
            "decision": "ask_for_clarification",
            "confidence": best_score,
            "reason": (
                "Multiple agents match this request with equal confidence: "
                + ", ".join(top_agents)
            ),
            "selected_agent": None,
            "candidates": [
                {
                    "id": aid,
                    "nickname": agents_by_id.get(aid, {}).get("nickname"),
                    "official_name": agents_by_id.get(aid, {}).get("official_name"),
                    "description": agents_by_id.get(aid, {}).get("description"),
                    "score": scores.get(aid),
                }
                for aid in top_agents
            ],
        }

    # Single clear winner
    best_id = top_agents[0]
    agent_cfg = agents_by_id.get(best_id, {})

    # Build a human-readable explanation with matching cues
    matched_cues: List[str] = []
    for cue, aid_set in cue_map.items():
        if best_id in aid_set and cue in user_input.lower():
            matched_cues.append(cue)

    reason_parts = []
    if matched_cues:
        reason_parts.append(f"Matched cues: {matched_cues}")
    reason_parts.append(f"Selected agent: {best_id}")

    return {
        "decision": best_id,
        "confidence": best_score,
        "reason": " | ".join(reason_parts),
        "selected_agent": {
            "id": best_id,
            "nickname": agent_cfg.get("nickname"),
            "official_name": agent_cfg.get("official_name"),
            "description": agent_cfg.get("description"),
        },
        "candidates": [
            {
                "id": best_id,
                "nickname": agent_cfg.get("nickname"),
                "official_name": agent_cfg.get("official_name"),
                "description": agent_cfg.get("description"),
                "score": best_score,
            }
        ],
    }
