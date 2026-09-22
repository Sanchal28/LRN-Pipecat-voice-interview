"""Small, deterministic question plans for the LRN prototype."""

from dataclasses import dataclass


@dataclass(frozen=True)
class InterviewQuestion:
    topic: str
    prompt: str


IB_TECHNICAL_QUESTIONS = (
    InterviewQuestion("background", "Please introduce yourself and tell me why investment banking interests you."),
    InterviewQuestion("accounting", "Walk me through how the three financial statements link together."),
    InterviewQuestion("valuation", "How would you value a company using a discounted cash flow analysis?"),
    InterviewQuestion("enterprise_value", "What is the difference between enterprise value and equity value?"),
    InterviewQuestion("market_awareness", "Tell me about a recent transaction or market trend you have been following."),
    InterviewQuestion("judgment", "What is one area of finance you would most like to improve, and how would you work on it?"),
)


def build_question_plan(mode: str, max_questions: int) -> tuple[InterviewQuestion, ...]:
    """Return a bounded prototype plan for a supported interview mode."""
    if mode != "investment_banking_technical":
        raise ValueError(f"Unsupported prototype interview mode: {mode}")
    if not 1 <= max_questions <= len(IB_TECHNICAL_QUESTIONS):
        raise ValueError(f"max_questions must be between 1 and {len(IB_TECHNICAL_QUESTIONS)}")
    return IB_TECHNICAL_QUESTIONS[:max_questions]
