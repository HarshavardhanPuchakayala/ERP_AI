from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from agent import ask, build_agent

INDEX_HTML = Path(__file__).resolve().parent / "static" / "index.html"
state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
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
def ask_endpoint(req: AskRequest):
    try:
        return ask(state["agent"], req.question.strip())
    except Exception as e:
        # Log the real error here, but show the user only a generic message
        print("ask failed:", type(e).__name__, e)
        raise HTTPException(
            status_code=502,
            detail="The AI model failed to answer. Please try again.",
        )