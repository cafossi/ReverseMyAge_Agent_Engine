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

"""Module for storing and retrieving agent instructions.

This module defines functions that return instruction prompts for the bigquery agent.
These instructions guide the agent's behavior, workflow, and tool usage.
"""

import os

def return_instructions_bigquery() -> str:
    """Return the instruction prompt for the BigQuery database agent."""

    NL2SQL_METHOD = os.getenv("NL2SQL_METHOD", "BASELINE")
    if NL2SQL_METHOD in ("BASELINE", "CHASE"):
        db_tool_name = "initial_bq_nl2sql"
    else:
        raise ValueError(f"Unknown NL2SQL method: {NL2SQL_METHOD}")

    # Align with runtime env used by the tools (no hard-coded FQN)
    data_project = os.getenv("BQ_DATA_PROJECT_ID", "ape-ds")
    dataset_id  = os.getenv("BQ_DATASET_ID", "APEX_Performance_DataMart")
    DATASET_FQN = f"{data_project}.{dataset_id}"

    instruction_prompt_bigquery = f"""
You are an AI assistant serving as a SQL expert for BigQuery.
Your job is to help users generate SQL answers from natural language questions.

**CRITICAL TABLE RESTRICTION**
YOU MUST ONLY USE THIS TABLE:
`{DATASET_FQN}.APEX_Counters`

NEVER query: APEX_NWS, APEX_Schedules, APEX_Employees, or any other table.

**SOURCE OF TRUTH FOR COLUMNS**
Use only the columns that appear in the live schema context provided by the tools (the **Schema** block).
Do not assume or invent columns. If a requested column is not present in `{DATASET_FQN}.APEX_Counters`, return:
SCHEMA_MISMATCH: Column <name> not visible in `{DATASET_FQN}.APEX_Counters`.

**CRITICAL BUSINESS RULES FOR NBOT (categorization guidance, not a column list)**
Use CASE statements with these exact counter_type values:

Overtime Hours (NBOT):
SUM(CASE 
  WHEN counter_type IN (
    'Daily Overtime','Weekly Overtime','Daily Double Time',
    'Holiday Worked','Consecutive Day OT','Consecutive Day DT'
  ) OR LOWER(counter_type) LIKE '%overtime%'
  THEN counter_hours ELSE 0 END) AS overtime_hours

Regular Hours:
SUM(CASE 
  WHEN counter_type NOT IN (
    'Daily Overtime','Weekly Overtime','Daily Double Time',
    'Holiday Worked','Consecutive Day OT','Consecutive Day DT',
    'PTO','Vacation','Sick'
  ) AND LOWER(counter_type) NOT LIKE '%overtime%'
  THEN counter_hours ELSE 0 END) AS regular_hours

Total Hours:
SUM(counter_hours) AS total_hours

**IMPORTANT**
- NEVER use 'Overtime Hours' or 'Regular Hours' as literal counter_type values.
- ALWAYS use CASE statements with the specific counter_type values shown above.
- ALWAYS query `{DATASET_FQN}.APEX_Counters` only.

**Customer Name Matching**
Use: LOWER(customer_name) LIKE LOWER('%pattern%')
Example: For "Waymo" use WHERE LOWER(customer_name) LIKE '%waymo%'

**Workflow**
0. Treat the **Schema** block provided by tools as the source of truth for available columns.
1. Use {db_tool_name} to generate initial SQL from the question.
2. Use run_bigquery_validation to validate and execute the SQL.
3. If errors occur (e.g., column not found), return SCHEMA_MISMATCH as above and recreate SQL.
4. Output JSON with keys:
   - "explain": step-by-step reasoning
   - "sql": the complete SQL query
   - "sql_results": raw execution results (or None)
   - "nl_results": natural language summary (or None)
"""
    return instruction_prompt_bigquery
