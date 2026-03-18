"""Hackathon Skeleton — JokeReviewAgent with conditional routing.

Architecture:
  START → [judge] ─┬─ funny ──→ END
                   └─ not funny → [rewriter] → END

The judge uses structured output to decide if a joke is funny.
If not, the rewriter critiques it and produces a better version
(also via structured output).
"""

from typing import Any, AsyncGenerator

import mlflow
from pydantic import BaseModel, Field

from databricks_langchain import ChatDatabricks
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from mlflow.genai.agent_server import invoke, stream
from mlflow.types.responses import ResponsesAgentRequest, ResponsesAgentResponse

mlflow.langchain.autolog()


# ---------------------------------------------------------------------------
# Structured-output schemas
# ---------------------------------------------------------------------------
class JokeVerdict(BaseModel):
    """The judge's verdict on the joke."""

    is_funny: bool = Field(description="Whether the joke is genuinely funny")
    reasoning: str = Field(description="Brief explanation of the verdict")


class JokeRewrite(BaseModel):
    """Critique and rewrite of a bad joke."""

    critique: str = Field(description="What makes the original joke fall flat")
    rewritten_joke: str = Field(description="An improved version of the joke")


# ---------------------------------------------------------------------------
# Extended state — carries the is_funny flag for conditional routing
# ---------------------------------------------------------------------------
class JokeReviewState(MessagesState):
    is_funny: bool


# ---------------------------------------------------------------------------
# LLM instances – swap the endpoint for any Foundation Model or custom
# Model Serving endpoint available in your workspace.
# ---------------------------------------------------------------------------
LLM = ChatDatabricks(endpoint="databricks-claude-sonnet-4")
JUDGE_LLM = LLM.with_structured_output(JokeVerdict)
REWRITER_LLM = LLM.with_structured_output(JokeRewrite)


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------
def judge(state: JokeReviewState) -> dict[str, Any]:
    """Evaluate whether the submitted joke is funny."""
    system = SystemMessage(
        content=(
            "You are a discerning comedy critic. "
            "Judge whether the following joke is genuinely funny."
        )
    )
    verdict: JokeVerdict = JUDGE_LLM.invoke([system] + state["messages"])
    return {
        "is_funny": verdict.is_funny,
        "messages": [
            AIMessage(
                content=(
                    f"{'Funny!' if verdict.is_funny else 'Not funny.'} "
                    f"{verdict.reasoning}"
                )
            )
        ],
    }


def rewriter(state: JokeReviewState) -> dict[str, Any]:
    """Critique the joke and produce a better version."""
    system = SystemMessage(
        content=(
            "You are a comedy writer. The following joke was judged as not "
            "funny. Critique it and write an improved version."
        )
    )
    result: JokeRewrite = REWRITER_LLM.invoke([system] + state["messages"])
    return {
        "messages": [
            AIMessage(
                content=(
                    f"Critique: {result.critique}\n\n"
                    f"Rewritten joke: {result.rewritten_joke}"
                )
            )
        ],
    }


# ---------------------------------------------------------------------------
# Conditional routing
# ---------------------------------------------------------------------------
def route_after_judge(state: JokeReviewState) -> str:
    """If the joke is funny, stop. Otherwise, send it to the rewriter."""
    return END if state.get("is_funny") else "rewriter"


# ---------------------------------------------------------------------------
# Build the LangGraph
# ---------------------------------------------------------------------------
builder = StateGraph(JokeReviewState)
builder.add_node("judge", judge)
builder.add_node("rewriter", rewriter)
builder.add_edge(START, "judge")
builder.add_conditional_edges(
    "judge",
    route_after_judge,
    {END: END, "rewriter": "rewriter"},
)
builder.add_edge("rewriter", END)

graph = builder.compile()


# ---------------------------------------------------------------------------
# MLflow AgentServer handlers  (Responses API <-> LangGraph bridge)
# ---------------------------------------------------------------------------
def _to_langchain_messages(items: list) -> list:
    """Convert Responses API input items to LangChain message objects."""
    cls_map = {
        "user": HumanMessage,
        "assistant": AIMessage,
        "system": SystemMessage,
    }
    messages: list = []
    for item in items:
        if isinstance(item, str):
            messages.append(HumanMessage(content=item))
            continue
        role = getattr(item, "role", "user")
        content = getattr(item, "content", str(item))
        # content may be a list of content blocks
        if isinstance(content, list):
            content = " ".join(getattr(c, "text", str(c)) for c in content)
        messages.append(cls_map.get(role, HumanMessage)(content=content))
    return messages


def _format_output(text: str) -> dict:
    """Build a single Responses API output message."""
    return {
        "type": "message",
        "role": "assistant",
        "content": [{"type": "output_text", "text": text}],
    }


@invoke()
async def handle_invoke(
    request: ResponsesAgentRequest,
) -> ResponsesAgentResponse:
    """Non-streaming handler registered with the AgentServer."""
    lc_messages = _to_langchain_messages(request.input)
    result = graph.invoke({"messages": lc_messages})
    answer = result["messages"][-1].content
    return ResponsesAgentResponse(output=[_format_output(answer)])


@stream()
async def handle_stream(
    request: ResponsesAgentRequest,
) -> AsyncGenerator[ResponsesAgentResponse, None]:
    """Streaming handler — yields one ResponsesAgentResponse per graph node.

    Each LangGraph `.stream()` event is a dict keyed by node name.
    We yield the AI message produced by that node so the client
    receives incremental updates (judge verdict first, then rewrite
    if applicable).
    """
    lc_messages = _to_langchain_messages(request.input)
    for event in graph.stream({"messages": lc_messages}):
        # event looks like {"judge": {"messages": [...], ...}}
        for _node_name, node_output in event.items():
            ai_msgs = [
                m for m in node_output.get("messages", [])
                if isinstance(m, AIMessage)
            ]
            for msg in ai_msgs:
                yield ResponsesAgentResponse(
                    output=[_format_output(msg.content)]
                )
