from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class ADRCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    context: str | None = None
    decision: str | None = None
    consequences: str | None = None
    alternatives_considered: str | None = None
    related_decisions: list[str] = []
    # NORA committee decision register ([FORK] WP3.4)
    committee: str | None = Field(default=None, max_length=200)
    meeting_date: date | None = None
    stage_no: int | None = Field(default=None, ge=0, le=10)


class ADRUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=500)
    context: str | None = None
    decision: str | None = None
    consequences: str | None = None
    alternatives_considered: str | None = None
    related_decisions: list[str] | None = None
    status: str | None = None
    committee: str | None = Field(default=None, max_length=200)
    meeting_date: date | None = None
    stage_no: int | None = Field(default=None, ge=0, le=10)


class ADRSignatureRequest(BaseModel):
    user_ids: list[str] = Field(..., min_length=1)
    message: str | None = None


class ADRRejectRequest(BaseModel):
    comment: str


class ADRCardLink(BaseModel):
    card_id: str


class ADRLinkedCard(BaseModel):
    id: str
    name: str
    type: str

    model_config = {"from_attributes": True}


class ADRResponse(BaseModel):
    id: str
    reference_number: str
    title: str
    status: str
    context: str | None = None
    decision: str | None = None
    consequences: str | None = None
    alternatives_considered: str | None = None
    related_decisions: list[str] = []
    committee: str | None = None
    meeting_date: date | None = None
    stage_no: int | None = None
    created_by: str | None = None
    creator_name: str | None = None
    signatories: list[dict] = []
    signed_at: datetime | None = None
    revision_number: int = 1
    parent_id: str | None = None
    linked_cards: list[ADRLinkedCard] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class FileAttachmentResponse(BaseModel):
    id: str
    card_id: str
    name: str
    mime_type: str
    size: int
    created_by: str | None = None
    creator_name: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
