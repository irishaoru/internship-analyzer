from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    resume: str = Field(min_length=1, max_length=30000)
    job_description: str = Field(min_length=1, max_length=20000)
    cover_letter: str | None = Field(default=None, max_length=15000)

    @field_validator("resume", "job_description", "cover_letter", mode="before")
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("cover_letter")
    @classmethod
    def optional_letter(cls, value):
        return value or None


class RequirementMatch(BaseModel):
    requirement: str
    importance: Literal["required", "preferred"]
    match: Literal["met", "partial", "not_demonstrated"]
    evidence: str
    gap: str


class Improvement(BaseModel):
    location: str
    current_text: str | None
    issue: str
    suggested_change: str
    example_revision: str
    priority: Literal["high", "medium", "low"]


class DocumentFeedback(BaseModel):
    strengths: list[str]
    improvements: list[Improvement]


class AnalysisResult(BaseModel):
    overall_score: Literal["strong", "moderate", "weak"]
    summary: str
    score_reasoning: str
    requirement_matches: list[RequirementMatch]
    resume_feedback: DocumentFeedback
    cover_letter_feedback: DocumentFeedback | None
    next_steps: list[str]
