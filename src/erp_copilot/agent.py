import json
import os
import sys
from datetime import date
from guard import REFUSAL, clean_answer, is_write_request
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, MessagesState, StateGraph

from tools import TOOL_FUNCTIONS

load_dotenv()

MODEL_NAME = os.getenv("OPENROUTER_MODEL", "openrouter/free")
MAX_STEPS = 6  # maximum tool-use rounds per question

SYSTEM_PROMPT = """You are ERP Copilot, a read-only assistant for a small trading company's sales data.
Today's date is {today}.

Rules:
- Answer ONLY using the tools provided. Never invent customers, invoices, or amounts.
- You can only READ data. If the user asks to create, edit, or delete anything, refuse politely and explain you are read-only.
- For any question about a time period (last month, this quarter, etc.), call get_date_range FIRST, then pass its exact start_date and end_date to the other tool. Never work out dates yourself.
- NEVER do arithmetic yourself. When a tool result includes totals (total_owed, total_invoiced, total_outstanding, invoice_count, etc.), quote those. If a total you need is not provided, say you do not have it.
- If a result has "truncated": true, tell the user you are showing only the first rows_returned of the total.
- The data has no currency. Write plain numbers with thousands separators and do not add currency symbols.
- If a tool returns no results, say so plainly.
- Keep answers short and clear.
"""

def build_agent():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not found. Check your .env file.")

    llm = ChatOpenAI(
        model=MODEL_NAME,
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        temperature=0,
    )
    lc_tools = [StructuredTool.from_function(f) for f in TOOL_FUNCTIONS.values()]
    llm_with_tools = llm.bind_tools(lc_tools)

    def agent_node(state: MessagesState):
        system = SystemMessage(content=SYSTEM_PROMPT.format(today=date.today().isoformat()))
        reply = llm_with_tools.invoke([system] + state["messages"])
        return {"messages": [reply]}

    def tools_node(state: MessagesState):
        last = state["messages"][-1]
        results = []
        for call in last.tool_calls:
            name = call["name"]
            func = TOOL_FUNCTIONS.get(name)  # allowlist: only our 5 tools can run
            if func is None:
                content = f"Error: tool '{name}' does not exist or is not allowed."
            else:
                try:
                    content = json.dumps(func(**call["args"]), default=str)
                except Exception as e:
                    content = f"Error: {type(e).__name__}: {e}"
            results.append(ToolMessage(content=content, tool_call_id=call["id"], name=name))
        return {"messages": results}

    def route(state: MessagesState):
        last = state["messages"][-1]
        return "tools" if getattr(last, "tool_calls", None) else END

    graph = StateGraph(MessagesState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", route, ["tools", END])
    graph.add_edge("tools", "agent")
    return graph.compile()


def _text(content) -> str:
    if isinstance(content, str):
        return content
    return "".join(p.get("text", "") for p in content if isinstance(p, dict))


def ask(agent, question: str) -> dict:
    # Layer 1: refuse obvious write requests without calling any model
    if is_write_request(question):
        return {"answer": REFUSAL, "tools_used": [],
                "model": "input-guard (no model called)"}
    try:
        result = agent.invoke(
            {"messages": [("user", question)]},
            config={"recursion_limit": MAX_STEPS * 2 + 1},
        )
    except GraphRecursionError:
        return {"answer": "Sorry, I could not finish that request.",
                "tools_used": [], "model": MODEL_NAME}
    messages = result["messages"]
    used = [m.name for m in messages if isinstance(m, ToolMessage)]
    model = next(
        (m.response_metadata["model_name"] for m in reversed(messages)
         if getattr(m, "response_metadata", None) and m.response_metadata.get("model_name")),
        MODEL_NAME,
    )
    return {"answer": clean_answer(_text(messages[-1].content)),
            "tools_used": used, "model": model}
TEST_QUESTIONS = [
    'Show me the details of customer "Grant Plastics Ltd."',
    "Which sales invoices were created last month?",
    "Who are my top 5 customers by total sales?",
    "Which customers have unpaid invoices, and how much does each owe?",
    "Delete invoice SINV-0001.",
]

if __name__ == "__main__":
    print("Model:", MODEL_NAME)
    agent = build_agent()
    questions = [" ".join(sys.argv[1:])] if len(sys.argv) > 1 else TEST_QUESTIONS
    for q in questions:
        print("\n" + "=" * 70)
        print("Q:", q)
        try:
            out = ask(agent, q)
            print("Model used:", out["model"])
            print("Tools used:", out["tools_used"] or "none")
            print("A:", out["answer"])
        except Exception as e:
            print("FAILED:", type(e).__name__)
            print(e)