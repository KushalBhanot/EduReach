"""Request/response bodies. JSON uses camelCase to match the app's TypeScript types."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from .models import Tier

Subject = Literal["Math", "Science", "English"]
Language = Literal["English", "Hindi", "Spanish", "Swahili", "French", "Bengali"]


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Turn(CamelModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=8000)


class AskRequest(CamelModel):
    subject: Subject
    grade: int = Field(ge=1, le=10)
    language: Language
    tier: Tier
    history: list[Turn] = Field(default_factory=list, max_length=200)
    question: str = Field(min_length=1, max_length=2000)
    deep_thinking: bool = False
    # The offline queue's item id: a retried flush returns the cached answer
    # instead of paying for the same question twice.
    client_request_id: str | None = Field(default=None, max_length=100)


class Source(CamelModel):
    book: str
    section_id: str
    title: str
    url: str


class AskResponse(CamelModel):
    answer: str
    thinking: str | None
    actual_model: str
    used_fallback: bool
    sources: list[Source] = Field(default_factory=list)
    # cited: answer cites textbook passages. uncited: passages were given but
    # none was cited. insufficient: the model said the passages don't cover it.
    # out_of_scope: no book covers this subject/grade, or nothing matched.
    # unavailable: retrieval failed; answered without sources.
    # none: retrieval is not configured.
    grounding: Literal["cited", "uncited", "insufficient", "out_of_scope", "unavailable", "none"] = "none"
    request_id: str


class QuizRequest(CamelModel):
    subject: Subject
    grade: int = Field(ge=1, le=10)
    language: Language
    explanation: str = Field(min_length=1, max_length=8000)


class QuizQuestion(CamelModel):
    question: str
    options: list[str] = Field(min_length=4, max_length=4)
    correct_index: int = Field(ge=0, le=3)
    explanation: str


class QuizResponse(CamelModel):
    questions: list[QuizQuestion]
    request_id: str


class LLMQuizItem(BaseModel):
    """Schema handed to Gemini as response_schema (snake_case, no aliases)."""

    question: str
    options: list[str]
    correct_index: int
    explanation: str
