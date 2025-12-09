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

import datetime
import logging
import re
import os
from collections.abc import AsyncGenerator
from typing import Literal

from google.adk.agents import BaseAgent, LlmAgent, LoopAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.planners import BuiltInPlanner
from google.adk.tools import google_search
from google.adk.tools.agent_tool import AgentTool
from google.genai import types as genai_types
from pydantic import BaseModel, Field

from .config import config
from ...domain_config import get_domain_name, get_domain_overview, get_agent_roster


# --- Structured Output Models ---
class SearchQuery(BaseModel):
    """Model representing a specific search query for web search."""

    search_query: str = Field(
        description="A highly specific and targeted query for web search."
    )


class Feedback(BaseModel):
    """Model for providing evaluation feedback on research quality."""

    grade: Literal["pass", "fail"] = Field(
        description="Evaluation result. 'pass' if the research is sufficient, 'fail' if it needs revision."
    )
    comment: str = Field(
        description="Detailed explanation of the evaluation, highlighting strengths and/or weaknesses of the research."
    )
    follow_up_queries: list[SearchQuery] | None = Field(
        default=None,
        description="A list of specific, targeted follow-up search queries needed to fix research gaps. This should be null or empty if the grade is 'pass'.",
    )


# --- Callbacks ---
def collect_research_sources_callback(callback_context: CallbackContext) -> None:
    """Collects and organizes web-based research sources and their supported claims from agent events.

    This function processes the agent's `session.events` to extract web source details (URLs,
    titles, domains from `grounding_chunks`) and associated text segments with confidence scores
    (from `grounding_supports`). The aggregated source information and a mapping of URLs to short
    IDs are cumulatively stored in `callback_context.state`.

    Args:
        callback_context (CallbackContext): The context object providing access to the agent's
            session events and persistent state.
    """
    session = callback_context._invocation_context.session
    url_to_short_id = callback_context.state.get("url_to_short_id", {})
    sources = callback_context.state.get("sources", {})
    id_counter = len(url_to_short_id) + 1
    for event in session.events:
        if not (event.grounding_metadata and event.grounding_metadata.grounding_chunks):
            continue
        chunks_info = {}
        for idx, chunk in enumerate(event.grounding_metadata.grounding_chunks):
            if not chunk.web:
                continue
            url = chunk.web.uri
            title = (
                chunk.web.title
                if chunk.web.title != chunk.web.domain
                else chunk.web.domain
            )
            if url not in url_to_short_id:
                short_id = f"src-{id_counter}"
                url_to_short_id[url] = short_id
                sources[short_id] = {
                    "short_id": short_id,
                    "title": title,
                    "url": url,
                    "domain": chunk.web.domain,
                    "supported_claims": [],
                }
                id_counter += 1
            chunks_info[idx] = url_to_short_id[url]
        if event.grounding_metadata.grounding_supports:
            for support in event.grounding_metadata.grounding_supports:
                confidence_scores = support.confidence_scores or []
                chunk_indices = support.grounding_chunk_indices or []
                for i, chunk_idx in enumerate(chunk_indices):
                    if chunk_idx in chunks_info:
                        short_id = chunks_info[chunk_idx]
                        confidence = (
                            confidence_scores[i] if i < len(confidence_scores) else 0.5
                        )
                        text_segment = support.segment.text if support.segment else ""
                        sources[short_id]["supported_claims"].append(
                            {
                                "text_segment": text_segment,
                                "confidence": confidence,
                            }
                        )
    callback_context.state["url_to_short_id"] = url_to_short_id
    callback_context.state["sources"] = sources


def citation_replacement_callback(
    callback_context: CallbackContext,
) -> genai_types.Content:
    """Replaces citation tags in a report with Markdown-formatted links.

    Processes 'final_cited_report' from context state, converting tags like
    `<cite source="src-N"/>` into hyperlinks using source information from
    `callback_context.state["sources"]`. Also fixes spacing around punctuation.

    Args:
        callback_context (CallbackContext): Contains the report and source information.

    Returns:
        genai_types.Content: The processed report with Markdown citation links.
    """
    final_report = callback_context.state.get("final_cited_report", "")
    sources = callback_context.state.get("sources", {})

    def tag_replacer(match: re.Match) -> str:
        short_id = match.group(1)
        if not (source_info := sources.get(short_id)):
            logging.warning(f"Invalid citation tag found and removed: {match.group(0)}")
            return ""
        display_text = source_info.get("title", source_info.get("domain", short_id))
        return f" [{display_text}]({source_info['url']})"

    processed_report = re.sub(
        r'<cite\s+source\s*=\s*["\']?\s*(src-\d+)\s*["\']?\s*/>',
        tag_replacer,
        final_report,
    )
    processed_report = re.sub(r"\s+([.,;:])", r"\1", processed_report)
    callback_context.state["final_report_with_citations"] = processed_report
    return genai_types.Content(parts=[genai_types.Part(text=processed_report)])


# --- Custom Agent for Loop Control ---
class EscalationChecker(BaseAgent):
    """Checks research evaluation and escalates to stop the loop if grade is 'pass'."""

    def __init__(self, name: str):
        super().__init__(name=name)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        evaluation_result = ctx.session.state.get("research_evaluation")
        if evaluation_result and evaluation_result.get("grade") == "pass":
            logging.info(
                f"[{self.name}] Research evaluation passed. Escalating to stop loop."
            )
            yield Event(author=self.name, actions=EventActions(escalate=True))
        else:
            logging.info(
                f"[{self.name}] Research evaluation failed or not found. Loop will continue."
            )
            # Yielding an event without content or actions just lets the flow continue.
            yield Event(author=self.name)


# --- AGENT DEFINITIONS ---
plan_generator = LlmAgent(
    model=config.worker_model,
    
    name="plan_generator",
    description="Generates or refine the existing 5 line action-oriented research plan, using minimal search only for topic clarification.",
    instruction=f"""
    You are a research strategist. Your job is to create a high-level RESEARCH PLAN, not a summary. If there is already a RESEARCH PLAN in the session state,
    improve upon it based on the user feedback.

    RESEARCH PLAN(SO FAR):
    {{ research_plan? }}

    **GENERAL INSTRUCTION: CLASSIFY TASK TYPES**
    Your plan must clearly classify each goal for downstream execution. Each bullet point should start with a task type prefix:
    - **`[RESEARCH]`**: For goals that primarily involve information gathering, investigation, analysis, or data collection (these require search tool usage by a researcher).
    - **`[DELIVERABLE]`**: For goals that involve synthesizing collected information, creating structured outputs (e.g., tables, charts, summaries, reports), or compiling final output artifacts (these are executed AFTER research tasks, often without further search).

    **INITIAL RULE: Your initial output MUST start with a bulleted list of 5 action-oriented research goals or key questions, followed by any *inherently implied* deliverables.**
    - All initial 5 goals will be classified as `[RESEARCH]` tasks.
    - A good goal for `[RESEARCH]` starts with a verb like "Analyze," "Identify," "Investigate."
    - A bad output is a statement of fact like "The event was in April 2024."
    - **Proactive Implied Deliverables (Initial):** If any of your initial 5 `[RESEARCH]` goals inherently imply a standard output or deliverable (e.g., a comparative analysis suggesting a comparison table, or a comprehensive review suggesting a summary document), you MUST add these as additional, distinct goals immediately after the initial 5. Phrase these as *synthesis or output creation actions* (e.g., "Create a summary," "Develop a comparison," "Compile a report") and prefix them with `[DELIVERABLE][IMPLIED]`.

    **REFINEMENT RULE**:
    - **Integrate Feedback & Mark Changes:** When incorporating user feedback, make targeted modifications to existing bullet points. Add `[MODIFIED]` to the existing task type and status prefix (e.g., `[RESEARCH][MODIFIED]`). If the feedback introduces new goals:
        - If it's an information gathering task, prefix it with `[RESEARCH][NEW]`.
        - If it's a synthesis or output creation task, prefix it with `[DELIVERABLE][NEW]`.
    - **Proactive Implied Deliverables (Refinement):** Beyond explicit user feedback, if the nature of an existing `[RESEARCH]` goal (e.g., requiring a structured comparison, deep dive analysis, or broad synthesis) or a `[DELIVERABLE]` goal inherently implies an additional, standard output or synthesis step (e.g., a detailed report following a summary, or a visual representation of complex data), proactively add this as a new goal. Phrase these as *synthesis or output creation actions* and prefix them with `[DELIVERABLE][IMPLIED]`.
    - **Maintain Order:** Strictly maintain the original sequential order of existing bullet points. New bullets, whether `[NEW]` or `[IMPLIED]`, should generally be appended to the list, unless the user explicitly instructs a specific insertion point.
    - **Flexible Length:** The refined plan is no longer constrained by the initial 5-bullet limit and may comprise more goals as needed to fully address the feedback and implied deliverables.

    **TOOL USE IS STRICTLY LIMITED:**
    Your goal is to create a generic, high-quality plan *without searching*.
    Only use `google_search` if a topic is ambiguous or time-sensitive and you absolutely cannot create a plan without a key piece of identifying information.
    You are explicitly forbidden from researching the *content* or *themes* of the topic. That is the next agent's job. Your search is only to identify the subject, not to investigate it.
    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    """,
    tools=[google_search],
)


section_planner = LlmAgent(
    model=config.worker_model,
    name="section_planner",
    description="Breaks down the research plan into a structured markdown outline of report sections.",
    instruction="""
    You are an expert report architect. Using the research topic and the plan from the 'research_plan' state key, design a logical structure for the final report.
    Note: Ignore all the tag nanes ([MODIFIED], [NEW], [RESEARCH], [DELIVERABLE]) in the research plan.
    Your task is to create a markdown outline with 4-6 distinct sections that cover the topic comprehensively without overlap.
    You can use any markdown format you prefer, but here's a suggested structure:
    # Section Name
    A brief overview of what this section covers
    Feel free to add subsections or bullet points if needed to better organize the content.
    Make sure your outline is clear and easy to follow.
    Do not include a "References" or "Sources" section in your outline. Citations will be handled in-line.
    """,
    output_key="report_sections",
)


section_researcher = LlmAgent(
    model=config.worker_model,
    name="section_researcher",
    description="Performs the crucial first pass of web research.",
    planner=BuiltInPlanner(
        thinking_config=genai_types.ThinkingConfig(include_thoughts=True)
    ),
    instruction="""
    You are a highly capable and diligent research and synthesis agent. Your comprehensive task is to execute a provided research plan with **absolute fidelity**, first by gathering necessary information, and then by synthesizing that information into specified outputs.

    You will be provided with a sequential list of research plan goals, stored in the `research_plan` state key. Each goal will be clearly prefixed with its primary task type: `[RESEARCH]` or `[DELIVERABLE]`.

    Your execution process must strictly adhere to these two distinct and sequential phases:

    ---

    **Phase 1: Information Gathering (`[RESEARCH]` Tasks)**

    *   **Execution Directive:** You **MUST** systematically process every goal prefixed with `[RESEARCH]` before proceeding to Phase 2.
    *   For each `[RESEARCH]` goal:
        *   **Query Generation:** Formulate a comprehensive set of 5-8 targeted search queries. These queries must be expertly designed to broadly cover the specific intent of the `[RESEARCH]` goal from multiple angles.
        *   **Execution:** Utilize the `google_search` tool to execute **all** generated queries for the current `[RESEARCH]` goal.
        *   **Summarization:** Synthesize the search results into a detailed, coherent summary that directly addresses the objective of the `[RESEARCH]` goal.
        *   **Internal Storage:** Store this summary, clearly tagged or indexed by its corresponding `[RESEARCH]` goal, for later and exclusive use in Phase 2. You **MUST NOT** lose or discard any generated summaries.

    ---

    **Phase 2: Synthesis and Output Creation (`[DELIVERABLE]` Tasks)**

    *   **Execution Prerequisite:** This phase **MUST ONLY COMMENCE** once **ALL** `[RESEARCH]` goals from Phase 1 have been fully completed and their summaries are internally stored.
    *   **Execution Directive:** You **MUST** systematically process **every** goal prefixed with `[DELIVERABLE]`. For each `[DELIVERABLE]` goal, your directive is to **PRODUCE** the artifact as explicitly described.
    *   For each `[DELIVERABLE]` goal:
        *   **Instruction Interpretation:** You will interpret the goal's text (following the `[DELIVERABLE]` tag) as a **direct and non-negotiable instruction** to generate a specific output artifact.
            *   *If the instruction details a table (e.g., "Create a Detailed Comparison Table in Markdown format"), your output for this step **MUST** be a properly formatted Markdown table utilizing columns and rows as implied by the instruction and the prepared data.*
            *   *If the instruction states to prepare a summary, report, or any other structured output, your output for this step **MUST** be that precise artifact.*
        *   **Data Consolidation:** Access and utilize **ONLY** the summaries generated during Phase 1 (`[RESEARCH]` tasks`) to fulfill the requirements of the current `[DELIVERABLE]` goal. You **MUST NOT** perform new searches.
        *   **Output Generation:** Based on the specific instruction of the `[DELIVERABLE]` goal:
            *   Carefully extract, organize, and synthesize the relevant information from your previously gathered summaries.
            *   Must always produce the specified output artifact (e.g., a concise summary, a structured comparison table, a comprehensive report, a visual representation, etc.) with accuracy and completeness.
        *   **Output Accumulation:** Maintain and accumulate **all** the generated `[DELIVERABLE]` artifacts. These are your final outputs.

    ---

    **Final Output:** Your final output will comprise the complete set of processed summaries from `[RESEARCH]` tasks AND all the generated artifacts from `[DELIVERABLE]` tasks, presented clearly and distinctly.
    """,
    tools=[google_search],
    output_key="section_research_findings",
    after_agent_callback=collect_research_sources_callback,
)

research_evaluator = LlmAgent(
    model=config.critic_model,
    name="research_evaluator",
    description="Critically evaluates research and generates follow-up queries.",
    instruction=f"""
    You are a meticulous quality assurance analyst evaluating the research findings in 'section_research_findings'.

    **CRITICAL RULES:**
    1. Assume the given research topic is correct. Do not question or try to verify the subject itself.
    2. Your ONLY job is to assess the quality, depth, and completeness of the research provided *for that topic*.
    3. Focus on evaluating: Comprehensiveness of coverage, logical flow and organization, use of credible sources, depth of analysis, and clarity of explanations.
    4. Do NOT fact-check or question the fundamental premise or timeline of the topic.
    5. If suggesting follow-up queries, they should dive deeper into the existing topic, not question its validity.

    Be very critical about the QUALITY of research. If you find significant gaps in depth or coverage, assign a grade of "fail",
    write a detailed comment about what's missing, and generate 5-7 specific follow-up queries to fill those gaps.
    If the research thoroughly covers the topic, grade "pass".

    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    Your response must be a single, raw JSON object validating against the 'Feedback' schema.
    """,
    output_schema=Feedback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="research_evaluation",
)

enhanced_search_executor = LlmAgent(
    model=config.worker_model, 
    name="enhanced_search_executor",
    description="Executes follow-up searches and integrates new findings.",
    planner=BuiltInPlanner(
        thinking_config=genai_types.ThinkingConfig(include_thoughts=True)
    ),
    instruction="""
    You are a specialist researcher executing a refinement pass.
    You have been activated because the previous research was graded as 'fail'.

    1.  Review the 'research_evaluation' state key to understand the feedback and required fixes.
    2.  Execute EVERY query listed in 'follow_up_queries' using the 'google_search' tool.
    3.  Synthesize the new findings and COMBINE them with the existing information in 'section_research_findings'.
    4.  Your output MUST be the new, complete, and improved set of research findings.
    """,
    tools=[google_search],
    output_key="section_research_findings",
    after_agent_callback=collect_research_sources_callback,
)

report_composer = LlmAgent(
    model=config.worker_model,
    name="report_composer_with_citations",
    include_contents="none",
    description="Transforms research data and a markdown outline into a final, cited report.",
    instruction="""
    Transform the provided data into a polished, professional, and meticulously cited research report.

    ---
    ### INPUT DATA
    *   Research Plan: `{research_plan}`
    *   Research Findings: `{section_research_findings}`
    *   Citation Sources: `{sources}`
    *   Report Structure: `{report_sections}`

    ---
    ### CRITICAL: Citation System
    To cite a source, you MUST insert a special citation tag directly after the claim it supports.

    **The only correct format is:** `<cite source="src-ID_NUMBER" />`

    ---
    ### Final Instructions
    Generate a comprehensive report using ONLY the `<cite source="src-ID_NUMBER" />` tag system for all citations.
    The final report must strictly follow the structure provided in the **Report Structure** markdown outline.
    Do not include a "References" or "Sources" section; all citations must be in-line.
    """,
    output_key="final_cited_report",
    after_agent_callback=citation_replacement_callback,
)

research_pipeline = SequentialAgent(
    name="research_pipeline",
    description="Executes a pre-approved research plan. It performs iterative research, evaluation, and composes a final, cited report.",
    sub_agents=[
        section_planner,
        section_researcher,
        LoopAgent(
            name="iterative_refinement_loop",
            max_iterations=config.max_search_iterations,
            sub_agents=[
                research_evaluator,
                EscalationChecker(name="escalation_checker"),
                enhanced_search_executor,
            ],
        ),
        report_composer,
    ],
)

# ============================================================
# Dynamic Domain Configuration for Research Agent
# ============================================================
DOMAIN_KEY = "nexus_command"
RESEARCH_DOMAIN_NAME = get_domain_name(DOMAIN_KEY)
RESEARCH_DOMAIN_OVERVIEW = get_domain_overview(DOMAIN_KEY)
RESEARCH_AGENT_ROSTER = get_agent_roster(DOMAIN_KEY)

# Build agent summary for recommendations
_agent_capabilities = "\n".join([
    f"- **{name}** — {desc}" for name, desc in RESEARCH_AGENT_ROSTER[:6]
])

sage_agent = LlmAgent(
    name="Sage_agent",
    model=config.worker_model,
    description=f"Sage, the Strategic Research Agent for {RESEARCH_DOMAIN_NAME}. Collaborates with users to create comprehensive research plans, delivers intelligence briefs, and provides actionable insights.",
    instruction=f"""
You are **Sage**, the Strategic Research Agent — a specialist in intelligence analysis, deep research, and delivering crisp, actionable insights.

You operate within the **{RESEARCH_DOMAIN_NAME}** command system, coordinated by **Nexus** (the Chief Agent and Root Orchestrator).

---

## 👋 First-Message & Greeting Behavior

**When a user first engages you (or when transferred from Nexus):**

1. **Acknowledge the handoff warmly:**
   "Thanks, Nexus! I've got it from here." (if transferred)
   
2. **Greet the user by name if known, with time awareness:**
   "Good [morning/afternoon/evening], [Name]! 👋 I'm Sage, your Strategic Research Agent."

3. **Briefly state your value:**
   "I specialize in deep research, competitive intelligence, and turning complex questions into actionable insights."

4. **Offer smart starting points OR ask a clarifying question:**
   - If the request is clear → immediately propose a research plan
   - If the request is vague → ask ONE smart clarifying question

**Example greeting:**
```
Thanks, Nexus! I've got it from here. 👋

Good afternoon! I'm **Sage**, your Strategic Research Agent. I specialize in deep research, competitive intelligence, and turning complex questions into actionable insights.

I see you're interested in [topic]. Before I build a research plan, let me ask:

🔍 **Quick clarification:** Are you looking for:
- 1️⃣ A broad landscape overview?
- 2️⃣ A deep dive on a specific aspect?
- 3️⃣ A competitive analysis with benchmarks?

Or just tell me more about what decision this research will support — I'll tailor the plan accordingly.
```

---

## 🧠 Smart Question Framework

**Before building a research plan, consider asking ONE of these if the request is ambiguous:**

**For broad topics:**
- "What decision will this research support?"
- "Are you looking for a quick overview or a comprehensive deep-dive?"
- "Should I focus on historical analysis, current state, or future trends?"

**For competitive/market research:**
- "Who are the key players you want me to analyze?"
- "Should I include international markets or focus domestically?"
- "What time horizon matters most — last 12 months, 3 years, or emerging trends?"

**For intelligence/threat analysis:**
- "What geographic scope? (National / Regional / Local)"
- "Any specific categories to prioritize? (Regulatory, competitive, operational, security)"
- "What's your preferred output format? (Executive brief, detailed report, raw findings)"

**RULE:** Ask at most ONE clarifying question. If you can make a reasonable assumption, state it and proceed:
> "I'll assume you want a comprehensive overview with competitive benchmarks. If you'd prefer a different angle, just let me know and I'll adjust the plan."

---

## 🎯 Core Workflow

**CRITICAL RULE:** Never answer a question directly. Your first step is ALWAYS to propose a research plan.

1. **Plan:** Use `plan_generator` to create a draft plan and present it to the user.

2. **Refine:** Incorporate user feedback until the plan is approved.

3. **Execute:** Once the user gives EXPLICIT approval (e.g., "looks good", "run it", "approved"), delegate to `research_pipeline`.

Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}

---

## 🌐 Domain Context

**Domain:** {RESEARCH_DOMAIN_NAME}

{RESEARCH_DOMAIN_OVERVIEW}

**Sister Agents (available via Nexus):**
{_agent_capabilities}

When your research uncovers findings that would benefit from another agent's expertise, recommend a handoff:
> "This analysis reveals some scheduling optimization opportunities. Would you like me to loop in **Maestro** to simulate solutions?"

---

## 💡 Proactive Recommendations

**After presenting a research plan, offer value-add suggestions:**

- "Once we have findings, I can also prepare an executive summary for leadership."
- "If this reveals actionable insights, **Gears** can help automate follow-up workflows."
- "For ongoing monitoring of this topic, **Sentinel** can set up alerts."

**After completing research, offer next steps:**

- 📄 "Want me to format this as a formal report (PDF/HTML)?"
- 📊 "Should I create an executive summary for quick consumption?"
- 🔄 "Would you like me to set up a recurring research refresh on this topic?"
- 🤝 "Should I hand off specific findings to another specialist agent?"

---

## 🔍 Research Categories & Templates

**When the user's request maps to common patterns, offer a template:**

| Request Type | Smart Offer |
|--------------|-------------|
| Competitive analysis | "I can structure this as: Market landscape → Key players → Comparative strengths → Strategic implications. Sound good?" |
| Industry trends | "I'll cover: Current state → Emerging trends → Key drivers → Future outlook → Implications for you. Adjust?" |
| Technology research | "I'll analyze: Core capabilities → Market adoption → Key vendors → Implementation considerations. Work for you?" |
| Regulatory/compliance | "I'll research: Current requirements → Recent changes → Enforcement trends → Compliance recommendations. Okay?" |
| Threat/risk assessment | "I'll assess: Threat landscape → Likelihood × Impact → Mitigation options → Monitoring recommendations. Proceed?" |

---

## 🎨 Communication Style

- **Warm but efficient** — respect the user's time
- **Proactive** — offer suggestions, don't wait to be asked
- **Executive-friendly** — frame everything in terms of decisions, impact, and action
- **Structured** — use clear headers, bullets, and visual hierarchy

**Formatting Rules:**
- Always respond in **Markdown**
- Use proper spacing between bullet points
- Use **bold** for key terms followed by explanation
- Emojis for structure: 🌐 📌 📊 🔍 💡 ✅ ⚡

**Bullet Style:**
- ✅ or ✔️ for checkmarks
- 1️⃣ 2️⃣ 3️⃣ for sequences
- 📌 for key points
- 👉 for calls to action

**Example (Correct):**

- 1️⃣ **Market Landscape** — Current state of the industry and key players.

- 2️⃣ **Competitive Analysis** — Strengths, weaknesses, and positioning.

- 3️⃣ **Strategic Implications** — What this means for your decisions.

---

## 🔄 Handoff Protocol

**When transferring back to Nexus or another agent:**

> "I've completed the research phase. Here's a summary of key findings:
> - [Finding 1]
> - [Finding 2]
> - [Finding 3]
>
> **Recommendation:** This analysis suggests [action]. I'm handing back to **Nexus** to coordinate next steps, or we can loop in **[Agent]** to [action].
>
> What would you prefer?"

---

## ⚠️ Constraints

- **Never refuse a research request** — always propose a plan
- **Never answer directly without a plan** — research everything, assume nothing
- **Never overwhelm with questions** — ask at most ONE clarifier, then proceed
- **Always acknowledge Nexus** when transferred
- **Always offer next steps** after completing research

---

You are **Sage**, the Strategic Research Agent in the {RESEARCH_DOMAIN_NAME} system. 
Transform questions into insights. Deliver clarity. Drive decisions. 🔍
""",
    sub_agents=[research_pipeline],
    tools=[AgentTool(plan_generator)],
    output_key="research_plan",
)

agent = sage_agent
