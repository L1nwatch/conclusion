"""API schemas for Conclusion."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel


Confidence = Literal["High", "Medium", "Low"]


DecisionStatus = Literal["Draft", "Thinking", "Decided"]
DecisionNodeType = Literal["Topic", "Condition", "Action", "Outcome", "Note"]
DecisionNodeId = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")]
DecisionTitle = Annotated[str, Field(min_length=1, max_length=200)]
DecisionText = Annotated[str, Field(min_length=1, max_length=4000)]
DecisionDescription = Annotated[str, Field(max_length=10000)]
DecisionCoordinate = Annotated[float, Field(allow_inf_nan=False, ge=-1e9, le=1e9)]
DecisionVersion = Annotated[int, Field(ge=1)]


class DecisionPayload(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, extra="forbid", str_strip_whitespace=True
    )


class DecisionNodeInput(DecisionPayload):
    id: DecisionNodeId
    parent_id: DecisionNodeId | None = None
    text: DecisionText
    description: DecisionDescription | None = None
    type: DecisionNodeType | None = None
    order: int = Field(default=0, ge=0)
    position_x: DecisionCoordinate | None = None
    position_y: DecisionCoordinate | None = None
    collapsed: bool = False

    @model_validator(mode="after")
    def validate_position(self) -> DecisionNodeInput:
        if (self.position_x is None) != (self.position_y is None):
            raise ValueError("positionX and positionY must both be set or both be null")
        return self


class DecisionCreate(DecisionPayload):
    title: DecisionTitle
    description: DecisionDescription | None = None
    status: DecisionStatus = "Draft"
    nodes: list[DecisionNodeInput] | None = Field(default=None, min_length=1)


class DecisionSummary(DecisionPayload):
    id: int
    title: DecisionTitle
    description: DecisionDescription | None
    status: DecisionStatus
    version: DecisionVersion
    created_at: datetime
    updated_at: datetime


class DecisionNodeRecord(DecisionNodeInput):
    decision_id: int
    created_at: datetime
    updated_at: datetime


class DecisionRecord(DecisionSummary):
    root_id: DecisionNodeId
    nodes: list[DecisionNodeRecord]


class DecisionList(DecisionPayload):
    count: int
    offset: int
    items: list[DecisionSummary]


class DecisionChanges(DecisionPayload):
    title: DecisionTitle | None = None
    description: DecisionDescription | None = None
    status: DecisionStatus | None = None

    @field_validator("title", "status")
    @classmethod
    def require_value(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("must not be null")
        return value


class DecisionUpdate(DecisionChanges):
    expected_version: DecisionVersion


class DecisionNodeChanges(DecisionPayload):
    text: DecisionText | None = None
    description: DecisionDescription | None = None
    type: DecisionNodeType | None = None
    position_x: DecisionCoordinate | None = None
    position_y: DecisionCoordinate | None = None
    collapsed: bool | None = None

    @model_validator(mode="after")
    def validate_changes(self) -> DecisionNodeChanges:
        fields = self.model_fields_set
        if not fields:
            raise ValueError("At least one node field is required")
        if ("text" in fields and self.text is None) or ("collapsed" in fields and self.collapsed is None):
            raise ValueError("text and collapsed must not be null")
        if bool(fields & {"position_x", "position_y"}) and (
            not {"position_x", "position_y"} <= fields
            or (self.position_x is None) != (self.position_y is None)
        ):
            raise ValueError("Set both coordinates together, or clear both with null")
        return self


class AddDecisionNode(DecisionPayload):
    op: Literal["add"]
    id: DecisionNodeId
    parent_id: DecisionNodeId
    text: DecisionText
    description: DecisionDescription | None = None
    type: DecisionNodeType | None = None
    order: int | None = Field(default=None, ge=0)


class EditDecisionNode(DecisionPayload):
    op: Literal["update"]
    id: DecisionNodeId
    changes: DecisionNodeChanges


class MoveDecisionNode(DecisionPayload):
    op: Literal["move"]
    id: DecisionNodeId
    parent_id: DecisionNodeId
    order: int | None = Field(default=None, ge=0)


class DeleteDecisionNode(DecisionPayload):
    op: Literal["delete"]
    id: DecisionNodeId


DecisionNodeOperation = Annotated[
    AddDecisionNode | EditDecisionNode | MoveDecisionNode | DeleteDecisionNode,
    Field(discriminator="op"),
]


class DecisionTreeUpdate(DecisionPayload):
    expected_version: DecisionVersion
    nodes: list[DecisionNodeInput] | None = Field(default=None, min_length=1)
    operations: list[DecisionNodeOperation] | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def require_one_update(self) -> DecisionTreeUpdate:
        if (self.nodes is None) == (self.operations is None):
            raise ValueError("Provide either nodes or operations")
        return self

    def db_values(self) -> dict[str, Any]:
        return {
            "expected_version": self.expected_version,
            "nodes": [node.model_dump() for node in self.nodes] if self.nodes else None,
            "operations": [op.model_dump(exclude_unset=True) for op in self.operations]
            if self.operations else None,
        }


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


MODEL_ID_PATTERN = r"^[a-z0-9][a-z0-9-]{1,63}$"


class DecisionModelCreate(BaseModel):
    """The two business fields in a reusable decision model plus its technical ID."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(min_length=2, max_length=64, pattern=MODEL_ID_PATTERN)
    name: str = Field(min_length=1, max_length=120)
    explanation: str = Field(min_length=1, max_length=800)

    @field_validator("id", "name", "explanation", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return _strip_outer_whitespace(value)


class DecisionModelRecord(DecisionModelCreate):
    """Stored decision model returned by the API."""

    model_config = ConfigDict(populate_by_name=True)

    is_builtin: bool = Field(alias="isBuiltin")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class DecisionModelList(BaseModel):
    count: int
    items: list[DecisionModelRecord]


class DecisionModelUpdate(BaseModel):
    """Fields used to edit a model definition in place."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(min_length=1, max_length=120)
    explanation: str = Field(min_length=1, max_length=800)
    expected_updated_at: str = Field(alias="expectedUpdatedAt", min_length=1)

    @field_validator("name", "explanation", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return _strip_outer_whitespace(value)

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


class DecisionModelRun(BaseModel):
    """Answers produced with a registered model."""

    model_config = ConfigDict(populate_by_name=True)

    model_id: str = Field(alias="modelId", min_length=2, max_length=64, pattern=MODEL_ID_PATTERN)
    answers: dict[str, str] = Field(min_length=1, max_length=20)

    @field_validator("answers", mode="before")
    @classmethod
    def normalize_answers(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        return {
            key.strip() if isinstance(key, str) else key: answer.strip()
            if isinstance(answer, str)
            else answer
            for key, answer in value.items()
        }

    @field_validator("answers")
    @classmethod
    def validate_answers(cls, answers: dict[str, str]) -> dict[str, str]:
        for key, answer in answers.items():
            if not key or len(key) > 64 or not key[0].islower() or not key.isalnum():
                raise ValueError("decision answer keys must be lower camel case alphanumeric")
            if not answer:
                raise ValueError("decision answers must not be blank")
            if len(answer) > 4_000:
                raise ValueError("decision answers must not exceed 4000 characters")
        return answers


class DecisionAnalysis(BaseModel):
    """Structured reasoning completed before the final conclusion."""

    version: Literal[1] = 1
    models: list[DecisionModelRun] = Field(default_factory=list, max_length=20)

    @field_validator("models")
    @classmethod
    def require_unique_models(cls, models: list[DecisionModelRun]) -> list[DecisionModelRun]:
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
