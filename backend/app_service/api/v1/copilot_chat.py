"""ScamGuard Copilot: Corrective-RAG analysis and a streaming chat.

POST /copilot/analyze  -> JSON: strict CRAG verdict + the underlying scan.
POST /copilot/chat     -> text/event-stream (Server-Sent Events):
    event: status   {"stage": "analyzing" | "retrieving" | "answering"}
    event: verdict  CragVerdict (only when the turn contained new evidence)
    event: token    {"text": "..."}   answer text, in order
    event: done     {"kind": "evidence" | "follow_up" | "guidance"}
    event: error    {"message": "...", "retryable": bool}

Both endpoints are public, rate limited and store nothing. All analysis work
finishes before the stream starts, so a database or model failure becomes a
clean `error` event or HTTP error instead of a half-written answer.
"""

import asyncio
import json
import logging
import re
from collections.abc import AsyncIterator
from typing import Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app_service.core.rate_limit import get_client_ip, limiter
from app_service.db.session import get_db
from app_service.rag.crag import CragVerdict, analyze_evidence
from app_service.schemas.message import AnalysisResult

router = APIRouter(prefix="/copilot", tags=["copilot"])
logger = logging.getLogger(__name__)

MAX_MESSAGE = 4000
MAX_HISTORY = 20
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_URL = re.compile(r"(https?://|www\.)\S+|\b[a-z0-9-]+\.(com|in|xyz|top|co|net|org|info|online|site|link|app|live|shop)\b", re.I)
_PHONE_OR_UPI = re.compile(r"(\+?91[\s-]?)?\b[6-9]\d{9}\b|\b[\w.-]+@(ok\w+|ybl|paytm|upi|ibl|axl)\b", re.I)


def _clean(value: str) -> str:
    value = _CONTROL.sub("", value).strip()
    if not value:
        raise ValueError("must contain some text")
    return value


class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=3, max_length=MAX_MESSAGE)

    @field_validator("text")
    @classmethod
    def _text(cls, v: str) -> str:
        v = _clean(v)
        if len(v) < 3:
            raise ValueError("must be at least 3 characters")
        return v


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=MAX_MESSAGE)

    @field_validator("content")
    @classmethod
    def _content(cls, v: str) -> str:
        return _clean(v)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_MESSAGE)
    history: list[ChatTurn] = Field(default_factory=list, max_length=MAX_HISTORY)

    @field_validator("message")
    @classmethod
    def _message(cls, v: str) -> str:
        return _clean(v)


class AnalyzeResponse(BaseModel):
    verdict: CragVerdict
    analysis: AnalysisResult
    answer: str


def looks_like_evidence(text: str) -> bool:
    """True when a chat turn is something to check, not a question about it."""
    from app_service.services.copilot_service import classify_intent

    words = text.split()
    if _URL.search(text) or _PHONE_OR_UPI.search(text):
        return True
    if text.rstrip().endswith("?") and len(words) < 40 and not _FORWARDED.search(text):
        return False  # a question to the Copilot, however long
    if len(words) >= 12:
        return True
    if classify_intent(text) != "unknown":
        return False
    return len(words) >= 6


_FORWARDED = re.compile(r"\b(dear (customer|user|sir|madam)|your (account|kyc|card|parcel|order)|click|otp|congratulations|you have won)\b", re.I)

COPILOT_PERSONA = (
    "You are ScamGuard Copilot, the AI assistant inside ScamGuard, a scam and fraud detection website for India. "
    "Answer any question the user asks helpfully and accurately, like a capable general AI assistant: general knowledge, "
    "explanations, how-tos, writing help and technology questions are all fine. Your speciality is online safety: scams, "
    "phishing, UPI and banking fraud, digital arrest, job and investment fraud, cyber hygiene, privacy and what to do after "
    "a fraud. Reply in the user's language (English, Hindi or Hinglish), clearly and concisely, in plain text without markdown headings or tables; for lists start lines with '- ' or '1. '. "
    "Never ask for or encourage sharing OTPs, PINs, passwords, CVV or card numbers. If money was lost, tell them to call 1930 "
    "immediately and report at cybercrime.gov.in; for scam calls or messages without loss, report on Chakshu "
    "(sancharsaathi.gov.in). If the user wants a message, link or number checked, tell them to paste it in this chat. "
    "Do not invent facts, phone numbers or laws; say when you are unsure. Refuse clearly harmful requests, such as help "
    "writing scam messages or phishing pages."
)


def ai_stream(message: str, history: list[ChatTurn], scan_context: str | None = None, visitor: str = "anonymous"):
    """An iterator over the configured LLM's answer as it is written, or None
    when no LLM is configured (the caller then uses the built-in answers).
    Nothing is sent until the iterator is first advanced."""
    from app_service.services.copilot_llm_provider import CopilotLlmUnavailableError, get_configured_provider

    try:
        provider = get_configured_provider()
    except CopilotLlmUnavailableError:
        return None
    from app_service.core.config import get_settings
    from app_service.services import llm_budget

    if not llm_budget.allow(visitor, get_settings().COPILOT_LLM_DAILY_LIMIT):
        logger.info("Copilot LLM cap reached; using built-in answers")
        return None
    convo = "\n".join(f"{'User' if t.role == 'user' else 'Copilot'}: {t.content[:1500]}" for t in history[-8:])
    parts = []
    if scan_context:
        parts.append(f"ScamGuard's analysis of the message the user shared earlier:\n{scan_context[:2500]}")
    if convo:
        parts.append(f"Conversation so far:\n{convo}")
    parts.append(f"User: {message}\nCopilot:")
    user = "\n\n".join(parts)
    stream = getattr(provider, "stream", None)
    if stream is not None:
        return iter(stream(COPILOT_PERSONA, user, 900))

    def once():
        yield provider.complete(COPILOT_PERSONA, user, 900)

    return once()


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _chunks(text: str) -> list[str]:
    return re.findall(r"\S+\s*", text)


GUIDANCE = (
    "Paste the message, link, email or call transcript you want me to check, and I'll tell you whether it is a scam, "
    "which tricks it uses and which known scam it matches. You can then ask follow-up questions such as "
    "\"what should I do?\" or \"I already paid\"."
)


@router.post("/analyze", response_model=AnalyzeResponse)
@limiter.limit("20/minute")
def analyze(request: Request, payload: AnalyzeRequest, db: Session = Depends(get_db)) -> AnalyzeResponse:
    # The quick check answers from the detection engine alone (no LLM round
    # trip), so the homepage verdict is fast and is the research pipeline's.
    outcome = analyze_evidence(db, payload.text, llm_review=False)
    return AnalyzeResponse(verdict=outcome.verdict, analysis=outcome.analysis, answer=outcome.answer)


@router.post("/chat")
@limiter.limit("20/minute")
def chat(request: Request, payload: ChatRequest, db: Session = Depends(get_db)) -> StreamingResponse:
    from app_service.services.copilot_service import get_answer

    events: list[str] = []
    kind = "guidance"
    llm = None  # live LLM answer; `answer` is the built-in fallback
    try:
        if looks_like_evidence(payload.message):
            kind = "evidence"
            outcome = analyze_evidence(db, payload.message)
            events.append(_sse("verdict", outcome.verdict.model_dump()))
            answer = outcome.answer
        else:
            previous = next((t.content for t in reversed(payload.history) if t.role == "user" and looks_like_evidence(t.content)), None)
            if previous is None:
                answer = GUIDANCE
                llm = ai_stream(payload.message, payload.history, visitor=get_client_ip(request))
            else:
                kind = "follow_up"
                outcome = analyze_evidence(db, previous, llm_review=False)  # context only
                answer = get_answer(payload.message, outcome.analysis).answer
                llm = ai_stream(payload.message, payload.history, outcome.answer, visitor=get_client_ip(request))
    except Exception:
        logger.exception("Copilot chat failed")
        failure = _sse("error", {"message": "The analysis failed on the server. Please try again in a moment.", "retryable": True})
        return StreamingResponse(iter([failure]), media_type="text/event-stream", headers=_STREAM_HEADERS)

    async def stream() -> AsyncIterator[str]:
        # Everything that can fail ran above; this loop only writes. If writing
        # still fails, the client gets an explicit error event (it never waits
        # on a half-open stream), and the full answer is included so nothing
        # that was already computed is lost.
        try:
            yield ": stream-open\n\n"
            yield _sse("status", {"stage": "answering"})
            for e in events:
                yield e
            if llm is not None:
                started = False
                try:
                    while True:
                        piece = await asyncio.to_thread(next, llm, None)
                        if piece is None:
                            break
                        if not started and not piece.strip():
                            continue
                        started = True
                        yield _sse("token", {"text": piece})
                        if await request.is_disconnected():
                            return
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("Copilot LLM stream failed")
                    if started:
                        yield _sse("error", {"message": "The answer was interrupted. Please retry.", "retryable": True})
                        return
                if started:
                    yield _sse("done", {"kind": kind})
                    return
            for i, piece in enumerate(_chunks(answer)):
                if i % 16 == 0 and await request.is_disconnected():
                    return
                yield _sse("token", {"text": piece})
                await asyncio.sleep(0.012)
            yield _sse("done", {"kind": kind})
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Copilot stream failed while writing")
            yield _sse("error", {"message": "The answer was interrupted. Please retry.", "retryable": True, "fallback_answer": answer})

    return StreamingResponse(stream(), media_type="text/event-stream", headers=_STREAM_HEADERS)


_STREAM_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}
