import pytest

import answer_cache


@pytest.fixture(autouse=True)
def empty_cache():
    answer_cache.clear()


ANSWER = {"answer": "Sunrise Traders", "tools_used": ["customers_who_owe"],
          "sources": [], "model": "some/model:free"}


def test_stores_and_returns_an_answer():
    answer_cache.put("Who owes us the most?", ANSWER, now=1000)
    assert answer_cache.get("Who owes us the most?", now=1001) == ANSWER


def test_ignores_case_and_extra_spaces():
    answer_cache.put("Who owes us the most?", ANSWER, now=1000)
    assert answer_cache.get("  who  OWES us   the most? ", now=1001) == ANSWER


def test_unknown_question_is_a_miss():
    assert answer_cache.get("never asked", now=1000) is None


def test_entries_expire_after_the_ttl():
    answer_cache.put("q one", ANSWER, now=1000)
    assert answer_cache.get("q one", now=1000 + answer_cache.TTL_SECONDS - 1) == ANSWER
    assert answer_cache.get("q one", now=1000 + answer_cache.TTL_SECONDS + 1) is None


def test_oldest_entries_are_evicted_when_full(monkeypatch):
    monkeypatch.setattr(answer_cache, "MAX_ENTRIES", 2)
    answer_cache.put("first", ANSWER, now=1)
    answer_cache.put("second", ANSWER, now=2)
    answer_cache.put("third", ANSWER, now=3)
    assert answer_cache.get("first", now=4) is None
    assert answer_cache.get("second", now=4) is not None
    assert answer_cache.get("third", now=4) is not None


def test_changing_a_returned_answer_does_not_change_the_cache():
    answer_cache.put("q", ANSWER, now=1)
    got = answer_cache.get("q", now=2)
    got["answer"] = "tampered"
    assert answer_cache.get("q", now=3)["answer"] == "Sunrise Traders"