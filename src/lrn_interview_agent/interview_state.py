"""Deterministic, in-memory state for one LRN interview session.

This state is intentionally independent from the LLM conversation context.
The LLM remembers natural language; this object owns facts the application
must enforce, such as whether a session is active and how many planned
questions have been asked.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4


class InterviewStatus(StrEnum):
    CREATED = "created"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class TranscriptEntry:
    """One finalized utterance that can later be persisted to PostgreSQL."""

    speaker: str
    content: str
    timestamp: str
    interrupted: bool = False


@dataclass
class InterviewState:
    """Application-owned state for one candidate interview."""

    mode: str = "investment_banking_technical"
    max_questions: int = 6
    session_id: str = field(default_factory=lambda: str(uuid4()))
    status: InterviewStatus = InterviewStatus.CREATED
    stage: str = "introduction"
    question_number: int = 0
    questions: list[str] = field(default_factory=list)
    answers: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    transcript: list[TranscriptEntry] = field(default_factory=list)

    def start(self) -> None:
        """Mark the session active once a browser has connected."""
        if self.status is InterviewStatus.CREATED:
            self.status = InterviewStatus.ACTIVE

    def record_interviewer_turn(
        self, content: str, timestamp: str, interrupted: bool = False
    ) -> None:
        """Keep the actual spoken interviewer turn, not an LLM draft."""
        if content.strip():
            self.transcript.append(
                TranscriptEntry("interviewer", content.strip(), timestamp, interrupted)
            )

    def record_candidate_turn(self, content: str | None, timestamp: str) -> None:
        """Keep a final candidate answer when Pipecat finalizes the turn."""
        if content and content.strip():
            cleaned = content.strip()
            self.answers.append(cleaned)
            self.transcript.append(TranscriptEntry("candidate", cleaned, timestamp))

    def add_question(self, question: str, topic: str) -> int:
        """Register a planned question and return its one-based number.

        The caller, not the LLM, must use this method before asking a scored
        question. It prevents an interview from exceeding ``max_questions``.
        """
        if self.status is not InterviewStatus.ACTIVE:
            raise RuntimeError("Cannot add a question to an inactive interview.")
        if self.question_number >= self.max_questions:
            raise RuntimeError("The interview has reached its question limit.")

        self.question_number += 1
        self.questions.append(question.strip())
        if topic.strip() and topic.strip() not in self.topics:
            self.topics.append(topic.strip())
        self.stage = "questions"
        return self.question_number

    def complete(self) -> None:
        """End the interview without changing its historical transcript."""
        self.status = InterviewStatus.COMPLETED
        self.stage = "complete"

    def cancel(self) -> None:
        """Record an early disconnect separately from a completed interview."""
        if self.status is not InterviewStatus.COMPLETED:
            self.status = InterviewStatus.CANCELLED

    def snapshot(self) -> dict[str, object]:
        """Return safe state for logs, a future frontend, or persistence."""
        return {
            "session_id": self.session_id,
            "mode": self.mode,
            "status": self.status.value,
            "stage": self.stage,
            "question_number": self.question_number,
            "max_questions": self.max_questions,
            "topics": list(self.topics),
        }


def utc_now() -> str:
    """Create a UTC timestamp for locally generated interview events."""
    return datetime.now(UTC).isoformat()
