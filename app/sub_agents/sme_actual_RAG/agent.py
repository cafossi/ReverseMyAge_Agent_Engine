"""
SME Agent — Subject-Matter Expert framework (nickname: Amanda)
Current domain focus: HR Policy / Employee Handbook
"""

import os
from google.genai import types
from google.adk.agents import Agent
from .prompts import return_instructions_sme
from .tools import (
    query_hr_policy,
    list_available_policies,
    get_hr_contact_info,
    list_corpora,
    create_corpus,
    add_data,
    get_corpus_info,
    delete_corpus,
    delete_document,
)


# ============================================================
# 🤖 SME Agent Definition
# ------------------------------------------------------------

SME_MODEL = os.getenv("SME_AGENT_MODEL")  # REQUIRED in your env

agent = Agent(
    model=SME_MODEL,
    name="sme_agent",                   # internal orchestrator name

    description=(
        "SME Agent (Amanda) — Subject-Matter Expert for policy/handbook knowledge. "
        "Currently specialized in HR Policy; extensible to new SME domains."
    ),
    tools=[
        # Domain (HR) tools for now
        query_hr_policy,
        list_available_policies,
        get_hr_contact_info,
        # RAG admin tools
        list_corpora,
        create_corpus,
        add_data,
        get_corpus_info,
        delete_corpus,
        delete_document,
    ],
    instruction=return_instructions_sme(),
    generate_content_config=types.GenerateContentConfig(
        temperature=0.4,
        candidate_count=1,
        top_p=0.9,
        top_k=40,
    ),
)