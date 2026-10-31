import pytest
from fastapi import HTTPException

import api


@pytest.fixture(autouse=True)
def reset_state():
    api.hits.clear()
    api.daily.update(day=None, count=0)


def test_per_visitor_limit(monkeypatch):
    monkeypatch.setattr(api, "PER_IP_LIMIT", 2)
    api.check_rate_limit("1.1.1.1")
    api.check_rate_limit("1.1.1.1")
    with pytest.raises(HTTPException) as err:
        api.check_rate_limit("1.1.1.1")
    assert err.value.status_code == 429
    api.check_rate_limit("2.2.2.2")  # a different visitor is unaffected


def test_daily_cap(monkeypatch):
    monkeypatch.setattr(api, "DAILY_CAP", 2)
    monkeypatch.setattr(api, "PER_IP_LIMIT", 100)
    api.check_rate_limit("a")
    api.check_rate_limit("b")
    with pytest.raises(HTTPException) as err:
        api.check_rate_limit("c")
    assert err.value.status_code == 429