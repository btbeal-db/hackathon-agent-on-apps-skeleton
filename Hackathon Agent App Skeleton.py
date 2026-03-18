# Databricks notebook source
# DBTITLE 1,Project Overview
# Hackathon Agent App — Skeleton

**Author:** brennan.beal@databricks.com  
**Date:** 2026-03-15  
**Purpose:** Bare-minimum template for a Databricks App that serves a LangGraph agent through the MLflow AgentServer. Demonstrates **conditional routing** and **structured output**.

## Project Layout

| File | Role |
|---|---|
| `agent.py` | JokeReviewAgent graph (judge → rewriter) with `ChatDatabricks`, `with_structured_output`, and `@invoke` handler |
| `start_server.py` | MLflow `AgentServer` entry point (FastAPI under the hood) |
| `app.yaml` | Databricks App runtime config — tells the platform to run `start_server.py` |
| `requirements.txt` | Python dependencies |

## How It Fits Together

```
User submits a joke
        │
        ▼
 MLflow AgentServer  (start_server.py)
        │  @invoke handler
        ▼
 LangGraph  (agent.py)
   ┌─────────────┐
   │    judge    │  ← LLM.with_structured_output(JokeVerdict)
   └──────┬──────┘
          │
     is_funny?
      ╱       ╲
   True       False
    │           │
    ▼           ▼
   END    ┌──────────┐
          │ rewriter │  ← LLM.with_structured_output(JokeRewrite)
          └────┬─────┘
               │
               ▼
              END
```

# COMMAND ----------

# DBTITLE 1,Smoke Test Instructions
# MAGIC %md
# MAGIC ## Quick Smoke Test
# MAGIC Run the cells below to invoke the **JokeReviewAgent** directly (no server needed).  
# MAGIC This validates that the graph compiles, structured output works, and conditional routing fires correctly.

# COMMAND ----------

# DBTITLE 1,Install dependencies
# MAGIC %pip install -U -qqq databricks-langchain langgraph mlflow[genai] --quiet
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# DBTITLE 1,Test the LangGraph agent locally
import sys, os

# Make sure the app-skeleton directory is importable
app_dir = "/Workspace/Users/brennan.beal@databricks.com/app-skeleton"
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

from agent import graph
from langchain_core.messages import HumanMessage

# --- Test 1: A bad joke (should route to rewriter) ---
bad_joke = "Why did the chicken cross the road? To get to the other side."
result = graph.invoke({"messages": [HumanMessage(content=bad_joke)]})

print("=" * 60)
print(f"INPUT:  {bad_joke}")
print(f"ROUTE:  judge → {'END' if result.get('is_funny') else 'rewriter → END'}")
print("=" * 60)
for msg in result["messages"]:
    if hasattr(msg, 'content') and msg.type == 'ai':
        print(f"\n[{msg.type.upper()}]\n{msg.content}")

# COMMAND ----------

# DBTITLE 1,Test with a good joke (expect early exit)
# --- Test 2: A good joke (should stop at judge) ---
good_joke = (
    "A SQL query walks into a bar, sees two tables, and asks... "
    "'Can I join you?'"
)
result = graph.invoke({"messages": [HumanMessage(content=good_joke)]})

print("=" * 60)
print(f"INPUT:  {good_joke}")
print(f"ROUTE:  judge → {'END' if result.get('is_funny') else 'rewriter → END'}")
print("=" * 60)
for msg in result["messages"]:
    if hasattr(msg, 'content') and msg.type == 'ai':
        print(f"\n[{msg.type.upper()}]\n{msg.content}")

# COMMAND ----------

# DBTITLE 1,Deployment Instructions
# MAGIC %md
# MAGIC ## Deploy to Databricks Apps
# MAGIC
# MAGIC ### Option A — Databricks CLI (recommended)
# MAGIC ```bash
# MAGIC # 1. Create the app (first time only)
# MAGIC databricks apps create hackathon-agent
# MAGIC
# MAGIC # 2. Sync files to workspace
# MAGIC DATABRICKS_USERNAME=$(databricks current-user me | jq -r .userName)
# MAGIC databricks sync ./app-skeleton "/Users/$DATABRICKS_USERNAME/app-skeleton"
# MAGIC
# MAGIC # 3. Deploy
# MAGIC databricks apps deploy hackathon-agent \
# MAGIC   --source-code-path /Workspace/Users/$DATABRICKS_USERNAME/app-skeleton
# MAGIC ```
# MAGIC
# MAGIC ### Option B — Workspace UI
# MAGIC 1. Go to **Compute → Apps → Create App**
# MAGIC 2. Point the source to this `app-skeleton/` folder
# MAGIC 3. Click **Deploy**
# MAGIC
# MAGIC ### Test the running app
# MAGIC ```bash
# MAGIC curl -X POST https://<app-url>/invocations \
# MAGIC   -H "Content-Type: application/json" \
# MAGIC   -d '{"input": [{"role": "user", "content": "Why did the chicken cross the road? To get to the other side."}]}'
# MAGIC ```