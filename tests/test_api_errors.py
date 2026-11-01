from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import answer_cache
import api


@pytest.fixture(autouse=True)
def reset_state():
    api.hits.clear()
    api.daily.update(day=None, count=0)
    answer_cache.clear()


REQUEST = SimpleNamespace(client=SimpleNamespace(host="9.9.9.9"))


def call_with_error(monkeypatch, error):
    def boom(agent, question):
        raise error

    monkeypatch.setattr(api, "ask", boom)
    monkeypatch.setitem(api.state, "agent", object())
    return api.ask_endpoint(api.AskRequest(question="hello there"), REQUEST)


def test_model_rate_limit_gives_a_friendly_503(monkeypatch):
    err = RuntimeError("Error code: 429 - Rate limit exceeded: free-models-per-min")
    with pytest.raises(HTTPException) as caught:
        call_with_error(monkeypatch, err)
    assert caught.value.status_code == 503
    assert "busy" in caught.value.detail


def test_model_daily_limit_says_try_tomorrow(monkeypatch):
    err = ValueError("{'message': 'Rate limit exceeded: free-models-per-day. Add 10 credits', 'code': 429}")
    with pytest.raises(HTTPException) as caught:
        call_with_error(monkeypatch, err)
    assert caught.value.status_code == 503
    assert "tomorrow" in caught.value.detail


def test_other_errors_give_a_generic_502_without_details(monkeypatch):
    with pytest.raises(HTTPException) as caught:
        call_with_error(monkeypatch, RuntimeError("secret internal detail"))
    assert caught.value.status_code == 502
    assert "secret" not in caught.value.detail


def test_repeated_question_is_served_from_cache_and_not_counted(monkeypatch):
    calls = []

    def fake_ask(agent, question):
        calls.append(question)
        return {"answer": "42", "tools_used": [], "sources": [], "model": "fake/model:free"}

    monkeypatch.setattr(api, "ask", fake_ask)
    monkeypatch.setitem(api.state, "agent", object())
    monkeypatch.setattr(api, "PER_IP_LIMIT", 100)
    body = api.AskRequest(question="Who owes us the most?")

    first = api.ask_endpoint(body, REQUEST)
    second = api.ask_endpoint(body, REQUEST)
    third = api.ask_endpoint(body, REQUEST)

    assert len(calls) == 1               # the model was asked only once
    assert api.daily["count"] == 1       # and only that one counted toward the daily cap
    assert first["model"] == "fake/model:free"
    assert "cached" in second["model"] and "cached" in third["model"]


def test_refused_write_request_uses_no_model_quota(monkeypatch):
    monkeypatch.setitem(api.state, "agent", object())  # would fail if the model were reached
    out = api.ask_endpoint(api.AskRequest(question="Delete invoice SINV-0001."), REQUEST)
    assert out["model"].startswith("input-guard")
    assert api.daily["count"] == 0


def test_daily_cap_blocks_new_model_questions_but_not_cached_ones(monkeypatch):
    def fake_ask(agent, question):
        return {"answer": "ok", "tools_used": [], "sources": [], "model": "fake/model:free"}

    monkeypatch.setattr(api, "ask", fake_ask)
    monkeypatch.setitem(api.state, "agent", object())
    monkeypatch.setattr(api, "PER_IP_LIMIT", 100)
    monkeypatch.setattr(api, "DAILY_CAP", 1)

    api.ask_endpoint(api.AskRequest(question="first question"), REQUEST)
    with pytest.raises(HTTPException) as caught:
        api.ask_endpoint(api.AskRequest(question="a brand new question"), REQUEST)
    assert caught.value.status_code == 429
    # the already-answered question still works when the cap is reached
    assert "cached" in api.ask_endpoint(api.AskRequest(question="first question"), REQUEST)["model"]