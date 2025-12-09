"""
Atlas AnalyticsAgent — configuration module
(Formerly NBOT Agent)
"""

from datetime import date

# ------------------------------------------------------------------
# 🔐 Identity & Naming
# ------------------------------------------------------------------
AGENT_ID: str = "atlas"

DISPLAY_NAME: str = "Atlas – AnalyticsAgent"
ALIAS_NAME: str = "Atlas"

MODEL_ENV_VAR: str = "ATLAS_AGENT_MODEL"

# ------------------------------------------------------------------
# 🗃 Data Environment
# ------------------------------------------------------------------
DEFAULT_DATABASE: str = "BigQuery"
SCHEMA_PRIMARY_KEY: str = "bq_ddl_schema"
SCHEMA_FALLBACK_KEY: str = "bq_schema_and_samples"
INCLUDE_SCHEMA_IN_PROMPT: bool = True

# ------------------------------------------------------------------
# 🧠 Behavior Toggles
# ------------------------------------------------------------------
ENABLE_STANDARD_REPORTS: bool = True
ENABLE_EXPORT_TOOL: bool = True

# ------------------------------------------------------------------
# 📅 Runtime Metadata
# ------------------------------------------------------------------
DATE_TODAY = date.today()
