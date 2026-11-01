import os
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

import answer_cache
from agent import ask, build_agent
from guard import is_write_request
from seed_db import DB_PATH, build_database

INDEX_HTML = Path(__file__).resolve().parent / "static" / "index.html"
state: dict = {}

# --- Rate limiting (protects the shared free-model quota) ---
# OpenRouter gives an unfunded account about 50 free-model requests per day, and
# one question can use 2 to 3 of them. Keep this low; it also has to cover your own testing.
PER_IP_LIMIT = 8                                  # questions per visitor...
PER_IP_WINDOW = 60                                # ...per this many seconds
DAILY_CAP = int(os.getenv("DAILY_CAP", "12"))     # model-backed questions per UTC day, all visitors
hits: dict[str, deque] = defaultdict(deque)
daily = {"day": None, "count": 0}
_lock = threading.Lock()


def check_rate_limit(ip: str, uses_model: bool = True) -> None:
    now = time.time()
    today = time.strftime("%Y-%m-%d", time.gmtime(now))
    with _lock:
        if daily["day"] != today:
            daily.update(day=today, count=0)
        if uses_model and daily["count"] >= DAILY_CAP:
            raise HTTPException(status_code=429,
                                detail="The daily demo limit was reached. Please try again tomorrow, "
                                       "or run the project locally (see the README).")
        q = hits[ip]
        while q and now - q[0] > PER_IP_WINDOW:
            q.popleft()
        if len(q) >= PER_IP_LIMIT:
            raise HTTPException(status_code=429,
                                detail="Too many questions too quickly. Please wait a minute.")
        q.append(now)
        if uses_model:
            daily["count"] += 1
        if len(hits) > 1000:  # forget visitors with no recent activity
            for key in [k for k, v in hits.items() if not v]:
                del hits[key]


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not DB_PATH.exists():  # the host's disk is wiped on restart, so rebuild
        build_database()
    state["agent"] = build_agent()  # build once, reuse for every request
    yield
    state.clear()


app = FastAPI(title="ERP Copilot", lifespan=lifespan)


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class AskResponse(BaseModel):
    answer: str
    tools_used: list[str]
    sources: list[str] = []
    model: str


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(INDEX_HTML)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask_endpoint(req: AskRequest, request: Request):
    question = req.question.strip()
    ip = request.client.host if request.client else "unknown"

    # Cached answers and refused write requests cost no model quota
    cached = answer_cache.get(question)
    uses_model = cached is None and not is_write_request(question)
    check_rate_limit(ip, uses_model=uses_model)
    if cached is not None:
        return {**cached, "model": f'{cached["model"]} (cached answer)'}

    try:
        result = ask(state["agent"], question)
    except Exception as e:
        # Log the real error here, but show the user only a safe message
        print("ask failed:", type(e).__name__, e)
        text = f"{type(e).__name__} {e}".lower()
        if "per-day" in text or "per day" in text:
            raise HTTPException(
                status_code=503,
                detail="The free AI models have reached their daily limit. Please try again tomorrow.",
            )
        if "rate limit" in text or "ratelimit" in text:
            raise HTTPException(
                status_code=503,
                detail="The free AI models are busy right now. Please try again in a minute.",
            )
        raise HTTPException(
            status_code=502,
            detail="The AI model failed to answer. Please try again.",
        )

    # Remember real model answers (not refusals or the give-up message)
    if (not result["model"].startswith("input-guard")
            and not result["answer"].startswith("Sorry, I could not finish")):
        answer_cache.put(question, result)
    return result