"""API schemas for Conclusion."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


Confidence = Literal["High", "Medium", "Low"]


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
        "title",
        "question",
        "conclusion",
        "reason",
        "tradeoffs",
        "conditions",
        "category",
        "confidence",
        mode="before",
    )
    @classmethod
    def strip_outer_whitespace(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("tags", mode="before")
    @classmethod
    def strip_tag_whitespace(cls, value: object) -> object:
        if not isinstance(value, list):
            return value
        return [tag.strip() if isinstance(tag, str) else tag for tag in value]

    @field_validator("tags")
    @classmethod
    def validate_and_deduplicate_tags(cls, tags: list[str]) -> list[str]:
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
