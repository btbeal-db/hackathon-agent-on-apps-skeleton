# Hackathon Agent App Skeleton

A minimal template for deploying a [LangGraph](https://langchain-ai.github.io/langgraph/) agent on [Databricks Apps](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/) using the MLflow AgentServer.

The agent is a **Joke Review Critic** that demonstrates two key LangGraph concepts:
- **Conditional routing** — a judge node decides if a joke is funny; if not, it routes to a rewriter
- **Structured output** — both nodes use Pydantic models via `with_structured_output`

```
User submits a joke
        │
  ┌─────┴──────┐
  │    judge    │  → LLM.with_structured_output(JokeVerdict)
  └─────┬──────┘
        │
   is_funny?
    ╱       ╲
 True       False
  │           │
  ▼           ▼
 END    ┌──────────┐
        │ rewriter │  → LLM.with_structured_output(JokeRewrite)
        └────┬─────┘
             ▼
            END
```

## Project layout

| File | Role |
|---|---|
| `agent.py` | LangGraph graph with `@invoke` / `@stream` handlers |
| `start_server.py` | MLflow AgentServer entry point (FastAPI) |
| `app.yaml` | Databricks App runtime config |
| `databricks.yml` | Databricks Asset Bundle definition |
| `requirements.txt` | Python dependencies |
| `ui/` | Simple browser UI (vanilla HTML/CSS/JS) |

## Prerequisites

1. **Databricks CLI** — install and configure a connection profile:
   - [Install the CLI](https://docs.databricks.com/aws/en/dev-tools/cli/install.html)
   - [Set up authentication](https://docs.databricks.com/aws/en/dev-tools/cli/authentication.html)

2. Verify your setup:
   ```bash
   databricks current-user me
   ```

## Deploy

Follow the [Databricks Apps deployment guide](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/deploy?language=Databricks+CLI) or use the quick steps below:

```bash
# 1. Clone this repo
git clone https://github.com/btbeal-db/hackathon-agent-on-apps-skeleton.git
cd hackathon-agent-on-apps-skeleton

# 2. Update databricks.yml:
#    - Set the workspace host to match your workspace
#    - Change the app_name default to something unique (e.g. joke-agent-yourname)
#      so it doesn't collide with other participants

# 3. Deploy the bundle (syncs files + deploys the app)
databricks bundle deploy

# 4. Check your app status (use the app name you chose above)
databricks apps get <your-app-name>
```

Once deployed, open the app URL in your browser to see the UI.

## Test with curl

```bash
curl -X POST https://<app-url>/invocations \
  -H "Content-Type: application/json" \
  -d '{"input": [{"role": "user", "content": "Why did the chicken cross the road? To get to the other side."}]}'
```
