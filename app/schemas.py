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


class ConclusionCreate(BaseModel):
    """Fields accepted when creating a Conclusion."""

    title: str = Field(min_length=1)
    question: str = Field(min_length=1)
    conclusion: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    tradeoffs: str = ""
    conditions: str = ""
    category: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list, max_length=20)
    confidence: Confidence

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
    conclusion: str | None = Field(default=None, min_length=1)
    reason: str | None = Field(default=None, min_length=1)
    tradeoffs: str | None = None
    conditions: str | None = None
    category: str | None = Field(default=None, min_length=1)
    tags: list[str] | None = Field(default=None, max_length=20)
    confidence: Confidence | None = None
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
