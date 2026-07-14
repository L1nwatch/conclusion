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
    category: str = Field(min_length=1)
    confidence: Confidence

    @field_validator(
        "title",
        "question",
        "conclusion",
        "reason",
        "tradeoffs",
        "category",
        "confidence",
        mode="before",
    )
    @classmethod
    def strip_outer_whitespace(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


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
