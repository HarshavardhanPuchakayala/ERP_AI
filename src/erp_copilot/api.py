import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from agent import ask, build_agent
from seed_db import DB_PATH, build_database

INDEX_HTML = Path(__file__).resolve().parent / "static" / "index.html"
state: dict = {}

# --- Rate limiting (protects the shared free-model quota) ---
PER_IP_LIMIT = 8      # questions per visitor...
PER_IP_WINDOW = 60    # ...per this many seconds
DAILY_CAP = 300       # all visitors combined, per UTC day
hits: dict[str, deque] = defaultdict(deque)
daily = {"day": None, "count": 0}
_lock = threading.Lock()


def check_rate_limit(ip: str) -> None:
    now = time.time()
    today = time.strftime("%Y-%m-%d", time.gmtime(now))
    with _lock:
        if daily["day"] != today:
            daily.update(day=today, count=0)
        if daily["count"] >= DAILY_CAP:
            raise HTTPException(status_code=429,
                                detail="The daily demo limit was reached. Please try again tomorrow.")
        q = hits[ip]
        while q and now - q[0] > PER_IP_WINDOW:
            q.popleft()
        if len(q) >= PER_IP_LIMIT:
            raise HTTPException(status_code=429,
                                detail="Too many questions too quickly. Please wait a minute.")
        q.append(now)
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
    model: str


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(INDEX_HTML)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask_endpoint(req: AskRequest, request: Request):
    check_rate_limit(request.client.host if request.client else "unknown")
    try:
        return ask(state["agent"], req.question.strip())
    except Exception as e:
        # Log the real error here, but show the user only a generic message
        print("ask failed:", type(e).__name__, e)
        raise HTTPException(
            status_code=502,
            detail="The AI model failed to answer. Please try again.",
        )