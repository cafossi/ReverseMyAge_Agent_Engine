# ⚡ APEX — Agentic Performance Excellence Platform

**Google-Native, Multi-Agent, ADK-Powered Operational Intelligence**

> *"Not a system. Your new AI Operations Lieutenant."*

---

A production-grade, enterprise-class multi-agent architecture built on Google's Agent Development Kit (ADK) to autonomously monitor, analyze, optimize, and report on workforce performance across large-scale operations—including NBOT, scheduling, training compliance, touch points, HR policies, and more.

Deployable natively on **Vertex AI Agent Engine** or **Cloud Run**, APEX unifies:

- **Operational Intelligence** (OPS-INTEL)
- **Training & Skill Reinforcement** (TRAIN-PRO)
- **Agentic Orchestration** (Jordan + ORION Supervisor Model)
- **RAG Search** over HR, Policy, and SOP Documents

---

## 📌 High-Level Highlights

| Capability | Details |
|------------|---------|
| **Root Agent (Jordan)** | Orchestrates all sub-agents, routes tasks, manages responses |
| **ADK-Native Multi-Agent Engine** | Modular agents for NBOT, Scheduling, Training, Touch Points, HR RAG |
| **Full Google-Native Stack** | Vertex AI, BigQuery, GCS, Cloud Run, Secret Manager |
| **Workforce Optimization** | KPI analysis → feedback → training → dashboards → leadership reports |
| **Prompt Hygiene System** | Markdown prompts stored in `prompts/system/` and `prompts/tasks/` |
| **Enterprise Ready** | Pytest, Ruff, Black, CI-ready structure, environment config |
| **RAG Over HR & Policy Docs** | "Amanda" agent runs policy Q&A with citations |
| **Closed-Loop Training** | Performance issue → microlearning assignment → progress tracking |
| **Supervisor Agent (ORION)** | Leadership-facing single pane of glass |

---

## 🧭 Architecture Overview

```
APEX Agent Engine (Root Orchestrator: Jordan)
│
├── agents/
│     ├── nbot/            → Nick – NBOT & analytics
│     ├── scheduling/      → Sammy – OT/DT rules, schedule health
│     ├── training/        → Joe – Course compliance, skill mapping
│     ├── touch_points/    → Engagement and KPI signals
│     ├── research/        → Autonomous research extensions
│     └── rag_hr/          → Amanda – HR Policy RAG
│
├── supervisor/
│     └── orion/           → Leadership-facing unified intelligence
│
├── prompts/
│     ├── system/
│     └── tasks/
│
├── pipelines/             → BQ SQL, ETL patterns, KPI marts
├── utils/                 → GCS, BQ, retry adapters
├── tests/                 → pytest
├── ops/scripts/           → Deployments
└── config/
```

---

## 🔮 APEX Platform Model

APEX is structured into two intelligence organizations, unified via agentic orchestration:

### 1️⃣ OPS-INTEL — Operational Intelligence Organization

**Mission:** Continuous KPI monitoring → feedback → interventions → dashboards.

#### Sub-Agents

**NBOT Agent – "Nick"**

- Weekly NBOT%
- OT/DT risk detection
- Pareto by region/site
- KPI JSON output for downstream agents

**Scheduling Agent – "Sammy"**

- CA OT/DT rule validator
- Shift coverage analysis
- Schedule health optimization
- Cross-week exposure prediction

**Touch Points Agent**

- Site engagement trends
- Driver interaction logs
- Behavioral KPI signals

**Feedback & Interventions Agent**

Generates real-time operational feedback:

| Signal | Action |
|--------|--------|
| 🟢 Green | Recognition |
| 🟡 Yellow | Coaching & microlearning |
| 🔴 Red | Warnings & escalations |

---

### 2️⃣ TRAIN-PRO — Training & Professional Growth Organization

**Mission:** Performance → training → progression → readiness.

#### Sub-Agents

**Training Agent – "Joe"**

- Course compliance & coverage
- Maps operational issues → microlearning
- Tracks skill reinforcement

**Onboarding Agent**

- New hire welcome sequence
- 1-week structured training flow
- Automated policy acknowledgment

**Training-Pill Mapping Engine**

| Issue | Assigned Pill |
|-------|---------------|
| Missed photos | "Delivery Photo Mastery" |
| Late deliveries | "Route Optimization Basics" |
| Ignored notes | "Delivery Checklist Pill" |

---

### 3️⃣ ORION — Leadership Supervisor Agent

**Mission:** Single interface to leadership. Coordinates OPS-INTEL + TRAIN-PRO + RAG + KPIs + reports.

**Produces:**

- 📄 Weekly PDF Brief
- 🧭 Executive Dashboard Sync
- 🟩 Recognition lists
- 🟡 Training Required lists
- 🔴 Repeated-risk escalations
- 📊 KPI summary JSON for BI pipelines

---

## 🔄 Closed-Loop Performance Intelligence Flow

```
Monitor → Analyze → Intervene → Train → Track → Report → Optimize
```

1. **KPI Agent** ingests Amazon/MetroOne reports
2. **Performance classified** (🟢/🟡/🔴)
3. **Feedback delivered** (WhatsApp/Email/JSON)
4. **Training triggered** automatically
5. **Training completions** logged
6. **Dashboard updated** (Power BI / custom HTML)
7. **ORION generates** leadership brief
8. **APEX updates** risk predictions

> **Closed-loop intelligence = continuous optimization.**

---

## ⚙️ Agent Definitions

### ⭐ Jordan — Root Orchestrator

- Intent router
- Multi-agent composition layer
- Response synthesizer
- Leadership-facing summary generator

### ⭐ Nick — NBOT Agent

- NBOT%
- OT/DT analytics
- Multi-week trend analysis
- Site-level Pareto

### ⭐ Sammy — Scheduling Agent

- CA OT/DT rule simulation
- Shift coverage validator
- Schedule health card generator

### ⭐ Joe — Training Agent

- LMS ingestion
- Course mapping
- Completion scoring
- Skill reinforcement triggers

### ⭐ Amanda — HR Policy RAG Agent

- RAG over HR corpus on GCS
- Citation-required answers
- Policy, SOP, and compliance logic

---

## 🗂️ Data Access via BigQuery

Adapters only (not raw BQ clients in agents):

- Typed parameterized queries
- Tenacity retry wrapper
- PII-safe logging

**Main Tables:**

| Table | Purpose |
|-------|---------|
| `APEX_NWS` | Schedule/hours + OT/DT logic |
| `APEX_Counters` | Operational counters, derived KPIs |
| Data marts | Agent consumption |

---

## 🔒 Security Model

- ❌ No secrets in code
- ✅ Use `.env` only for local; **Secret Manager** in production
- ✅ IAM least privilege
- ✅ Redact identifiers in logs
- ✅ Prompts contain zero proprietary secrets
- ✅ GCS RAG bucket uses uniform access control

---

## 🧪 Development Workflow

### Branching Strategy

```
feat/<desc>     → New features
fix/<desc>      → Bug fixes
chore/<desc>    → Maintenance tasks
docs/<desc>     → Documentation updates
```

### Quality Gates

```bash
pytest -q
ruff check .
black --check .
```

### PR Standards

- Small, atomic changes
- Tests included
- Context + impact documented
- Green CI required

---

## 🚀 Quick Start (Local)

### Clone & Setup

```bash
git clone https://github.com/cafossi/apex-agent-engine.git APEX
cd APEX
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configure Environment

```bash
cp config/env.example .env
```

Edit `.env`:

```env
# BigQuery Configuration
BQ_DATA_PROJECT_ID=...
BQ_COMPUTE_PROJECT_ID=...
BQ_DATASET_ID=apex_dataset

# GCS RAG Configuration
GCS_RAG_BUCKET=m1-apex-rag-docs
GCS_RAG_PREFIX=hr_policies/

# Vertex AI Configuration
VERTEX_REGION=us-central1
MODEL_NAME=gemini-1.5-pro
ADK_APP_NAME=apex_engine

# Logging
LOG_LEVEL=INFO
```

### Run

```bash
adk run apex_engine
# or
python -m app.main
```

---

## ☁️ Deployment Guide

### Cloud Run Deployment

```bash
# Build and submit
gcloud builds submit \
  --tag gcr.io/$PROJECT/apex-agent-engine:$(git rev-parse --short HEAD)

# Deploy
gcloud run deploy apex-agent-engine \
  --image gcr.io/$PROJECT/apex-agent-engine:$(git rev-parse --short HEAD) \
  --region $REGION \
  --allow-unauthenticated=false
```

> **Note:** Environment variables via Secret Manager.

### Vertex AI Agent Engine Deployment

1. Register ADK tools
2. Configure RAG corpus bucket
3. Bind IAM
4. Run deployment script:

```bash
ops/scripts/deploy_vertex.sh --dry-run
```

---

## 🔮 Optional: Gemini Fullstack Research Agent Integration

This repo can embed Google's fullstack ADK sample:

- React frontend + FastAPI/ADK backend
- HITL planning
- Autonomous research loop
- Deployed to Cloud Run or Vertex AI

> Should live in its own module (e.g., `/services/fullstack_research/`).

---

## 📑 Runbooks

Store under `docs/runbooks/`:

| Runbook | Description |
|---------|-------------|
| NBOT Weekly Brief | Weekly NBOT percentage analysis |
| Schedule Health Card | Shift coverage and OT/DT compliance |
| Training Compliance Summary | Course completion and skill gaps |
| HR Policy Q&A | Amanda RAG agent usage guide |
| Touch Points Snapshot | Engagement and behavioral metrics |

---

## 🤝 Contributing

```bash
# Create feature branch
git checkout -b feat/<desc>

# Run quality checks
ruff check .
pytest
black --check .

# Submit PR
```

**Workflow:** PR → Review → Merge → Delete Branch

---

## 🛡️ License & IP Notice

**Apache 2.0** — © Carlos A. Guzman

**Creator of:** APEX, AIAL, ACE, SENTRA

> This repository and derivative architectures are proprietary intellectual property of Carlos A. Guzman.

---

<div align="center">

**✔️ PRODUCTION READY**

*Built for Metro One LPSG / Specialized*

</div>
