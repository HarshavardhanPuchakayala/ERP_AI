import json
from pathlib import Path

import pytest
from langchain_core.messages import ToolMessage

import tools
from agent import _sources
from guard import is_write_request

FIXTURES = Path(__file__).parent / "fixtures" / "knowledge"


@pytest.fixture(autouse=True)
def sample_documents(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_DIR", str(FIXTURES))


def tool_message(name, payload):
    content = payload if isinstance(payload, str) else json.dumps(payload)
    return ToolMessage(content=content, tool_call_id="t1", name=name)


def test_search_documents_is_in_the_allowlist_and_runs():
    assert "search_documents" in tools.TOOL_FUNCTIONS
    out = tools.TOOL_FUNCTIONS["search_documents"]("late fee")
    assert out["results"][0]["source"] == "credit-policy.md"


def test_sources_are_listed_once_each():
    results = {"results": [
        {"source": "credit-policy.md", "section": "Late fees", "text": "x"},
        {"source": "credit-policy.md", "section": "Late fees", "text": "y"},
        {"source": "returns-policy.md", "section": "Return window", "text": "z"},
    ]}
    assert _sources([tool_message("search_documents", results)]) == [
        "credit-policy.md (Late fees)", "returns-policy.md (Return window)"]


def test_sources_ignore_other_tools_and_bad_json():
    msgs = [
        tool_message("customers_who_owe", {"results": [{"source": "x.md", "section": "s"}]}),
        tool_message("search_documents", "Error: something broke"),
    ]
    assert _sources(msgs) == []


def test_guard_lets_policy_questions_through():
    for q in (
        "What does our policy say about overdue invoices?",
        "What is the late fee for overdue invoices?",
        "Can a customer return goods after 14 days?",
        "Sunrise Traders owes us money. What does our policy say about overdue invoices?",
    ):
        assert not is_write_request(q), q