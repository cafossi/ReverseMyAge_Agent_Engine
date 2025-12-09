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

"""This file contains the tools used by the database agent."""


# ============================================================
# 📦 Imports
# ============================================================

import datetime
import logging
import os
import re

import numpy as np
import pandas as pd
from app.utils.utils import get_env_var
from google.adk.tools import ToolContext
from google.adk.tools.bigquery.client import get_bigquery_client
from google.cloud import bigquery
from google.genai import Client

from .chase_sql import chase_constants

# Assume that `BQ_COMPUTE_PROJECT_ID` and `BQ_DATA_PROJECT_ID` are set in the
# environment. See the `data_agent` README for more details.

dataset_id=get_env_var("BQ_DATASET_ID")
data_project = get_env_var("BQ_DATA_PROJECT_ID")
compute_project = get_env_var("BQ_COMPUTE_PROJECT_ID")
vertex_project = get_env_var("GOOGLE_CLOUD_PROJECT")
location = get_env_var("GOOGLE_CLOUD_LOCATION")
llm_client = Client(vertexai=True, project=vertex_project, location=location)

# ============================================================
# 📦 Max Rows
# ============================================================

MAX_NUM_ROWS = 400000


def _serialize_value_for_sql(value):
    """Serializes a Python value from a pandas DataFrame into a BigQuery SQL literal."""
    if pd.isna(value):
        return "NULL"
    if isinstance(value, str):
        # Escape single quotes and backslashes for SQL strings.
        return f"'{value.replace('\\', '\\\\').replace("'", "''")}'"
    if isinstance(value, bytes):
        return f"b'{value.decode('utf-8', 'replace').replace('\\', '\\\\').replace("'", "''")}'"
    if isinstance(value, (datetime.datetime, datetime.date, pd.Timestamp)):
        # Timestamps and datetimes need to be quoted.
        return f"'{value}'"
    if isinstance(value, (list, np.ndarray)):
        # Format arrays.
        return f"[{', '.join(_serialize_value_for_sql(v) for v in value)}]"
    if isinstance(value, dict):
        # For STRUCT, BQ expects ('val1', 'val2', ...).
        # The values() order from the dataframe should match the column order.
        return f"({', '.join(_serialize_value_for_sql(v) for v in value.values())})"
    return str(value)


database_settings = None


def get_database_settings():
    """Get database settings."""
    global database_settings
    if database_settings is None:
        database_settings = update_database_settings()
    return database_settings


def update_database_settings():
    """Update database settings."""
    global database_settings
    schema_and_samples = get_bigquery_schema_and_samples()
    database_settings = {
        "bq_data_project_id": get_env_var("BQ_DATA_PROJECT_ID"),
        "bq_dataset_id": get_env_var("BQ_DATASET_ID"),
        "bq_schema_and_samples": schema_and_samples,
        # Include ChaseSQL-specific constants.
        **chase_constants.chase_sql_constants_dict,
    }
    return database_settings


def get_bigquery_schema_and_samples():
    """Retrieves schema and sample values for the BigQuery dataset tables.
    Ensures fully-qualified table names are used (project.dataset.table).
    """
    client = get_bigquery_client(project=compute_project, credentials=None)
    dataset_ref = bigquery.DatasetReference(data_project, dataset_id)
    tables_context = {}

    for table in client.list_tables(dataset_ref):
        table_id = table.table_id
        fq_table_name = f"{data_project}.{dataset_id}.{table_id}"  # ✅ full name

        # Get schema
        table_info = client.get_table(fq_table_name)
        table_schema = [(field.name, field.field_type) for field in table_info.schema]

        # Get sample values
        sample_query = f"SELECT * FROM `{fq_table_name}` LIMIT 5"
        sample_df = client.query(sample_query).to_dataframe()
        sample_values = sample_df.to_dict(orient="list")
        for key in sample_values:
            sample_values[key] = [_serialize_value_for_sql(v) for v in sample_values[key]]

        # Store schema + examples
        tables_context[fq_table_name] = {
            "table_schema": table_schema,
            "example_values": sample_values,
        }

    return tables_context


def initial_bq_nl2sql(
    question: str,
    tool_context: ToolContext,
) -> str:
    # ✅ define the dataset FQN for the prompt
    DATASET_FQN = f"{data_project}.{dataset_id}"

    prompt_template = """
You are a BigQuery SQL expert tasked with answering user's questions about BigQuery tables by generating SQL queries in the GoogleSql dialect.  Your task is to write a Bigquery SQL query that answers the following question while using the provided context.

**Guidelines:**
- **Table Referencing:** Always use the full table name with the database prefix in the SQL statement.  Tables should be referred to using a fully qualified name with enclosed in backticks (`) e.g. `project_name.dataset_name.table_name`.  Table names are case sensitive.
- **Joins:** Join as few tables as possible. When joining tables, ensure all join columns are the same data type. Analyze the database and the table schema provided to understand the relationships between columns and tables.
- **Aggregations:**  Use all non-aggregated columns from the `SELECT` statement in the `GROUP BY` clause.
- **SQL Syntax:** Return syntactically and semantically correct SQL for BigQuery with proper relation mapping (i.e., project_id, owner, table, and column relation). Use SQL `AS` statement to assign a new name temporarily to a table column or even a table wherever needed. Always enclose subqueries and union queries in parentheses.
- **Column Usage:** Use *ONLY* the column names (column_name) mentioned in the Table Schema. Do *NOT* use any other column names. Associate `column_name` mentioned in the Table Schema only to the `table_name` specified under Table Schema.
- **FILTERS:** You should write query effectively  to reduce and minimize the total rows to be returned. For example, you can use filters (like `WHERE`, `HAVING`, etc. (like 'COUNT', 'SUM', etc.) in the SQL query.
- **LIMIT ROWS:**  The maximum number of rows returned should be less than {MAX_NUM_ROWS}.

**HARD CONSTRAINTS (must follow):**
- Only use tables from this dataset: `{DATASET_FQN}`.
- Only use the provided schema. Never invent or guess tables.
- Never reference external datasets (e.g., `bigquery-public-data.*`, `INFORMATION_SCHEMA`).
- If the question cannot be answered with the provided schema, return:
  SELECT 'TABLE_OUT_OF_SCOPE' AS error;

**Schema:**


The database structure is defined by the following table schemas (possibly with sample rows):

```
{SCHEMA}
```

**Natural language question:**

```
{QUESTION}
```

**Think Step-by-Step:** Carefully consider the schema, question, guidelines, and best practices outlined above to generate the correct BigQuery SQL.

   """

    bq_schema_and_samples = tool_context.state["database_settings"]["bq_schema_and_samples"]

    # ✅ include DATASET_FQN in format args
    prompt = prompt_template.format(
        MAX_NUM_ROWS=MAX_NUM_ROWS,
        SCHEMA=bq_schema_and_samples,
        QUESTION=question,
        DATASET_FQN=DATASET_FQN,
    )

    response = llm_client.models.generate_content(
        model=os.getenv("BASELINE_NL2SQL_MODEL"),
        contents=prompt,
        config={"temperature": 0.1},
    )

    sql = (response.text or "")
    sql = sql.replace("```sql", "").replace("```", "").strip()

    # ✅ runtime guard: block out-of-scope datasets
    if "bigquery-public-data" in sql or "INFORMATION_SCHEMA" in sql:
        sql = "SELECT 'TABLE_OUT_OF_SCOPE' AS error;"

    # Check all backticked table refs are inside allowed project.dataset
    tables = re.findall(r"`([A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+)`", sql)
    violations = [t for t in tables if not t.startswith(f"{data_project}.{dataset_id}.")]
    if tables and violations:
        sql = "SELECT 'TABLE_OUT_OF_SCOPE' AS error;"

    print("\n sql:", sql)
    tool_context.state["sql_query"] = sql
    return sql