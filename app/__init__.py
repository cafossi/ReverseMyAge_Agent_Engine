"""EPC Multi-Agent System - Root orchestrator initialization."""

import os

from . import agent

__all__ = ["agent"]

# ============================================================
# 📁 Ensure Reports Directory Exists
# ============================================================
# Create reports directory at application startup
# This directory is used by the export_agent_report tool
REPORTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)

print(f"✅ EPC System initialized. Reports directory: {REPORTS_DIR}")