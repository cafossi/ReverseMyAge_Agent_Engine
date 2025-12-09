"""
SME Agent — Subject-Matter Expert framework (nickname: Amanda)
Multi-domain company knowledge assistant covering:
- HR policies, scheduling, company history, news, training, and operations
"""

import os
from google.genai import types
from google.adk.agents import Agent
from .prompts import return_instructions_sme
from .tools import (
    # Domain-specific query tools
    query_hr_policy,
    list_available_policies,
    get_hr_contact_info,
    # Generic multi-domain query tool (CRITICAL for cross-domain search)
    rag_query,
    # Knowledge base management tools
    list_corpora,
    create_corpus,
    add_data,
    get_corpus_info,
    delete_corpus,
    delete_document,
    # Document upload tools
    upload_and_add_document,
    add_text_as_document,
)

# Employee data query tools (structured data from BigQuery)
from .employee_tools import (
    get_employee_info,
    get_employee_count,
    get_management_hierarchy,
    list_unique_values,
)

# ============================================================
# 🤖 SME Agent Definition
# ------------------------------------------------------------

SME_MODEL = os.getenv("SME_AGENT_MODEL")  # REQUIRED in your env

agent = Agent(
    model=SME_MODEL,
    name="sme_agent",                   # internal orchestrator name

    description=(
        "Amanda — Company SME (Subject-Matter Expert) Agent. "
        "Authoritative knowledge source for all company information: "
        "HR policies, scheduling rules, company history, news, training materials, "
        "operational procedures, and client protocols. "
        "Uses BigQuery vector search for semantic retrieval across multiple knowledge bases."
    ),
    
    tools=[
        # Domain-specific tools (convenience wrappers)
        query_hr_policy,              # Quick HR policy lookup
        list_available_policies,      # Browse HR sections
        get_hr_contact_info,          # HR escalation contact
        
        # Generic multi-domain query (PRIMARY TOOL for cross-domain search)
        rag_query,                    # Query ANY corpus by name
        
        # Employee data query tools (structured BigQuery data)
        get_employee_info,            # Query employee details
        get_employee_count,           # Count employees with filters/grouping
        get_management_hierarchy,     # Get manager-employee relationships
        list_unique_values,           # List unique values for exploration
        
        # Document upload tools (for adding content to knowledge base)
        upload_and_add_document,      # Upload file directly from chat
        add_text_as_document,         # Add pasted text as document
        
        # Knowledge base management (admin functions)
        list_corpora,                 # List all knowledge bases
        create_corpus,                # Create new knowledge base
        add_data,                     # Add documents from GCS paths
        get_corpus_info,              # View corpus contents
        delete_corpus,                # Remove knowledge base
        delete_document,              # Remove specific document
    ],
    
    instruction=return_instructions_sme(),
    
    generate_content_config=types.GenerateContentConfig(
        temperature=0.6,              # Balanced: factual but slightly creative
        candidate_count=1,            # Single response
        top_p=0.9,                    # Nucleus sampling for coherence
        top_k=40,                     # Consider top 40 tokens
    ),
)