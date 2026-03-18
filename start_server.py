"""MLflow AgentServer entry point for the Databricks App.

This file imports agent.py (which registers the @invoke and @stream
handlers) and starts the AgentServer on the configured port.

Usage:
  python start_server.py              # default port 8000
  python start_server.py --reload     # auto-reload on code changes
  python start_server.py --port 9000  # custom port
"""

import agent  # noqa: F401 — triggers @invoke / @stream registration

from mlflow.genai.agent_server import (
    AgentServer,
    setup_mlflow_git_based_version_tracking,
)

# "ResponsesAgent" enables automatic Responses API schema validation
# and streaming trace aggregation.  A custom name like "HackathonAgent"
# would skip both.
agent_server = AgentServer("ResponsesAgent")
app = agent_server.app  # FastAPI app, also used by Gunicorn/Uvicorn

# Optional: tie traces to git commits for reproducibility
setup_mlflow_git_based_version_tracking()


def main() -> None:
    # app_import_string lets the server use multiple workers
    agent_server.run(app_import_string="start_server:app")


if __name__ == "__main__":
    main()
