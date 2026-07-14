"""API schemas for Conclusion."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


Confidence = Literal["High", "Medium", "Low"]
TEXT_FIELDS = (
    "title",
    "question",
    "conclusion",
    "reason",
    "tradeoffs",
    "conditions",
    "category",
    "confidence",
)


def _strip_outer_whitespace(value: object) -> object:
    return value.strip() if isinstance(value, str) else value


def _strip_tag_whitespace(value: object) -> object:
    if not isinstance(value, list):
        return value
    return [tag.strip() if isinstance(tag, str) else tag for tag in value]


def _validate_and_deduplicate_tags(tags: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        if not tag:
            raise ValueError("tags must not contain blank values")
        if len(tag) > 50:
            raise ValueError("tags must not exceed 50 characters")
        normalized = tag.casefold()
        if normalized not in seen:
            seen.add(normalized)
            unique.append(tag)
    return unique


class DecisionAnswers(BaseModel):
    """Shared normalization for free-text decision model answers."""

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("*", mode="before")
    @classmethod
    def strip_answers(cls, value: object) -> object:
        return _strip_outer_whitespace(value)


class TimeHorizonAnswers(DecisionAnswers):
    ten_hours: str = Field(default="", alias="tenHours", max_length=4_000)
    ten_days: str = Field(default="", alias="tenDays", max_length=4_000)
    ten_months: str = Field(default="", alias="tenMonths", max_length=4_000)
    ten_years: str = Field(default="", alias="tenYears", max_length=4_000)


class ScenarioAnswers(DecisionAnswers):
    best_case: str = Field(default="", alias="bestCase", max_length=4_000)
    likely_case: str = Field(default="", alias="likelyCase", max_length=4_000)
    worst_case: str = Field(default="", alias="worstCase", max_length=4_000)
    safeguards: str = Field(default="", max_length=4_000)


class MungerChecklistAnswers(DecisionAnswers):
    incentives: str = Field(default="", max_length=4_000)
    opportunity_cost: str = Field(default="", alias="opportunityCost", max_length=4_000)
    inversion: str = Field(default="", max_length=4_000)
    second_order_effects: str = Field(
        default="",
        alias="secondOrderEffects",
        max_length=4_000,
    )
    circle_of_competence: str = Field(
        default="",
        alias="circleOfCompetence",
        max_length=4_000,
    )
    disconfirming_evidence: str = Field(
        default="",
        alias="disconfirmingEvidence",
        max_length=4_000,
    )


class TimeHorizonModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    model_id: Literal["time-horizons"] = Field(alias="modelId")
    answers: TimeHorizonAnswers

    @model_validator(mode="after")
    def require_answer(self) -> "TimeHorizonModel":
        if not any(self.answers.model_dump().values()):
            raise ValueError("a decision model must contain at least one answer")
        return self


class ScenarioModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    model_id: Literal["scenario-range"] = Field(alias="modelId")
    answers: ScenarioAnswers

    @model_validator(mode="after")
    def require_answer(self) -> "ScenarioModel":
        if not any(self.answers.model_dump().values()):
            raise ValueError("a decision model must contain at least one answer")
        return self


class MungerChecklistModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    model_id: Literal["munger-checklist"] = Field(alias="modelId")
    answers: MungerChecklistAnswers

    @model_validator(mode="after")
    def require_answer(self) -> "MungerChecklistModel":
        if not any(self.answers.model_dump().values()):
            raise ValueError("a decision model must contain at least one answer")
        return self


DecisionModel = TimeHorizonModel | ScenarioModel | MungerChecklistModel


class DecisionAnalysis(BaseModel):
    """Versioned, structured reasoning completed before the final conclusion."""

    version: Literal[1] = 1
    models: list[DecisionModel] = Field(default_factory=list, max_length=3)

    @field_validator("models")
    @classmethod
    def require_unique_models(cls, models: list[DecisionModel]) -> list[DecisionModel]:
        model_ids = [model.model_id for model in models]
        if len(model_ids) != len(set(model_ids)):
            raise ValueError("decision models must be unique")
        return models


class ConclusionCreate(BaseModel):
    """Fields accepted when creating a Conclusion."""

    title: str = Field(min_length=1)
    question: str = Field(min_length=1)
    conclusion: str = Field(min_length=1, max_length=280)
    reason: str = Field(min_length=1)
    tradeoffs: str = ""
    conditions: str = ""
    category: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list, max_length=20)
    confidence: Confidence
    decision_analysis: DecisionAnalysis = Field(
        default_factory=DecisionAnalysis,
        alias="decisionAnalysis",
    )

    model_config = ConfigDict(populate_by_name=True)

    @field_validator(
        *TEXT_FIELDS,
        mode="before",
    )
    @classmethod
    def strip_outer_whitespace(cls, value: object) -> object:
        return _strip_outer_whitespace(value)

    @field_validator("tags", mode="before")
    @classmethod
    def strip_tag_whitespace(cls, value: object) -> object:
        return _strip_tag_whitespace(value)

    @field_validator("tags")
    @classmethod
    def validate_and_deduplicate_tags(cls, tags: list[str]) -> list[str]:
        return _validate_and_deduplicate_tags(tags)


class ConclusionUpdate(BaseModel):
    """Partial fields accepted when updating a Conclusion."""

    model_config = ConfigDict(populate_by_name=True)

    title: str | None = Field(default=None, min_length=1)
    question: str | None = Field(default=None, min_length=1)
    conclusion: str | None = Field(default=None, min_length=1, max_length=280)
    reason: str | None = Field(default=None, min_length=1)
    tradeoffs: str | None = None
    conditions: str | None = None
    category: str | None = Field(default=None, min_length=1)
    tags: list[str] | None = Field(default=None, max_length=20)
    confidence: Confidence | None = None
    decision_analysis: DecisionAnalysis | None = Field(
        default=None,
        alias="decisionAnalysis",
    )
    expected_updated_at: str = Field(alias="expectedUpdatedAt", min_length=1)

    @field_validator(*TEXT_FIELDS, mode="before")
    @classmethod
    def strip_outer_whitespace(cls, value: object) -> object:
        return _strip_outer_whitespace(value)

    @field_validator("tags", mode="before")
    @classmethod
    def strip_tag_whitespace(cls, value: object) -> object:
        return _strip_tag_whitespace(value)

    @field_validator("tags")
    @classmethod
    def validate_and_deduplicate_tags(cls, tags: list[str] | None) -> list[str] | None:
        return _validate_and_deduplicate_tags(tags) if tags is not None else None

    @field_validator("expected_updated_at")
    @classmethod
    def validate_expected_updated_at(cls, value: str) -> str:
        value = value.strip()
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError("expectedUpdatedAt must be an ISO 8601 timestamp") from error
        if parsed.tzinfo is None:
            raise ValueError("expectedUpdatedAt must include a timezone")
        return value

    @model_validator(mode="after")
    def require_non_null_update(self) -> "ConclusionUpdate":
        supplied = self.model_fields_set - {"expected_updated_at"}
        if not supplied:
            raise ValueError("at least one field must be updated")
        if any(getattr(self, field) is None for field in supplied):
            raise ValueError("updated fields must not be null")
        return self


class ConclusionRecord(ConclusionCreate):
    """Stored Conclusion returned by the API."""

    model_config = ConfigDict(populate_by_name=True)

    id: int
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class ConclusionList(BaseModel):
    """Bounded list response with total result metadata."""

    count: int
    returned: int
    items: list[ConclusionRecord]
