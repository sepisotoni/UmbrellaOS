"""
api/routers/knowledge.py — Knowledge base CRUD + search + pending review.

All endpoints require require_admin_hmac_or_session (admin key, HMAC, or
session token). The dashboard calls these directly; the bot uses the
search_knowledge() method on UmbrellaCoreClient for the /knowledge_search
slash command.

Endpoints
---------
GET    /api/v1/knowledge                  — search / list entries
POST   /api/v1/knowledge                  — create (staff-submitted, auto-approved)
GET    /api/v1/knowledge/pending          — list all PENDING corrections
GET    /api/v1/knowledge/{entry_id}       — single entry + version history
PATCH  /api/v1/knowledge/{entry_id}       — update content (snapshots prior)
DELETE /api/v1/knowledge/{entry_id}       — hard delete
POST   /api/v1/knowledge/{entry_id}/approve — approve pending correction
POST   /api/v1/knowledge/{entry_id}/reject  — reject pending correction
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User
from models.knowledge import KnowledgeEntry, KnowledgeReviewStatus
from services.knowledge.repository import KnowledgeRepository
from services.knowledge.service import KnowledgeService
from api.middleware.auth import require_admin_hmac_or_session

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class KnowledgeEntrySchema(BaseModel):
    id: str
    channel_name: str
    author_name: str
    content: str
    confidence_score: float
    review_status: str
    created_at: datetime
    updated_at: datetime | None
    corrects_entry_id: str | None
    superseded_by_id: str | None
    model_config = ConfigDict(from_attributes=True)


class KnowledgeVersionSchema(BaseModel):
    version_number: int
    content: str
    edited_by: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class KnowledgeCreateRequest(BaseModel):
    title: str
    content: str
    category: str | None = None


class KnowledgeUpdateRequest(BaseModel):
    content: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _actor_id(auth: User | str) -> str:
    return str(auth.id) if isinstance(auth, User) else "admin"


def _actor_name(auth: User | str) -> str:
    return auth.username if isinstance(auth, User) else "admin"


async def _get_or_404(db: AsyncSession, entry_id: str) -> KnowledgeEntry:
    entry = await db.get(KnowledgeEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    return entry


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=dict)
async def list_knowledge(
    query: str = Query(default="", description="ILIKE keyword search"),
    limit: int = Query(default=20, ge=1, le=50),
    status: str | None = Query(default=None, description="approved | pending | rejected"),
    auth: User | str = Depends(require_admin_hmac_or_session),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    List/search knowledge entries.
    Default: approved + non-superseded (via KnowledgeRepository.search).
    With ?status=: filter by that review_status instead.
    """
    if status is not None:
        try:
            status_enum = KnowledgeReviewStatus(status.lower())
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid status: {status}")

        like = f"%{query}%"
        stmt = (
            select(KnowledgeEntry)
            .where(
                KnowledgeEntry.content.ilike(like),
                KnowledgeEntry.review_status == status_enum,
            )
            .order_by(KnowledgeEntry.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        entries = list(result.scalars().all())
    else:
        # Default: approved + non-superseded only
        entries = await KnowledgeRepository.search(db, query, limit=limit)

    return {
        "entries": [KnowledgeEntrySchema.model_validate(e) for e in entries],
        "total": len(entries),
    }


@router.post("", response_model=KnowledgeEntrySchema, status_code=201)
async def create_knowledge(
    body: KnowledgeCreateRequest,
    auth: User | str = Depends(require_admin_hmac_or_session),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeEntrySchema:
    """
    Create a new knowledge entry directly (staff-submitted, auto-approved).
    Uses synthetic discord field values so index_entry() is satisfied.
    The channel_name field serves as the category in the dashboard.
    """
    category = body.category or "general"
    # Combine title + content so the content field carries both
    full_content = f"{body.title}\n\n{body.content}" if body.title else body.content

    # index_entry() checks is_knowledge_channel() — bypass by inserting directly
    # (dashboard entries aren't from a Discord channel, so the channel check
    # would always return None).
    entry = KnowledgeEntry(
        channel_id="dashboard",
        channel_name=category,
        discord_message_id=f"dashboard-{uuid.uuid4()}",
        author_id=_actor_id(auth),
        author_name=_actor_name(auth),
        content=full_content,
        confidence_score=1.0,
        review_status=KnowledgeReviewStatus.APPROVED,
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return KnowledgeEntrySchema.model_validate(entry)


@router.get("/pending", response_model=dict)
async def list_pending(
    auth: User | str = Depends(require_admin_hmac_or_session),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all PENDING entries (corrections awaiting review)."""
    entries = await KnowledgeService.list_pending(db)
    return {"entries": [KnowledgeEntrySchema.model_validate(e) for e in entries]}


@router.get("/{entry_id}", response_model=dict)
async def get_knowledge_entry(
    entry_id: str,
    auth: User | str = Depends(require_admin_hmac_or_session),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return a single entry by ID plus its full version history."""
    entry = await _get_or_404(db, entry_id)
    versions = await KnowledgeRepository.history(db, entry_id)
    return {
        "entry": KnowledgeEntrySchema.model_validate(entry),
        "versions": [KnowledgeVersionSchema.model_validate(v) for v in versions],
    }


@router.patch("/{entry_id}", response_model=KnowledgeEntrySchema)
async def update_knowledge_entry(
    entry_id: str,
    body: KnowledgeUpdateRequest,
    auth: User | str = Depends(require_admin_hmac_or_session),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeEntrySchema:
    """Update entry content. Snapshots the prior content as a version first."""
    entry = await _get_or_404(db, entry_id)
    if entry.content != body.content:
        await KnowledgeRepository.snapshot_version(db, entry, edited_by=_actor_id(auth))
        entry.content = body.content
        await db.flush()
        await db.refresh(entry)
    return KnowledgeEntrySchema.model_validate(entry)


@router.delete("/{entry_id}", response_model=dict)
async def delete_knowledge_entry(
    entry_id: str,
    auth: User | str = Depends(require_admin_hmac_or_session),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Hard-delete a knowledge entry."""
    entry = await _get_or_404(db, entry_id)
    await db.delete(entry)
    await db.flush()
    return {"deleted": True}


@router.post("/{entry_id}/approve", response_model=KnowledgeEntrySchema)
async def approve_knowledge_entry(
    entry_id: str,
    auth: User | str = Depends(require_admin_hmac_or_session),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeEntrySchema:
    """Approve a pending correction."""
    entry = await KnowledgeService.approve(db, entry_id, reviewed_by=_actor_id(auth))
    if entry is None:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    return KnowledgeEntrySchema.model_validate(entry)


@router.post("/{entry_id}/reject", response_model=KnowledgeEntrySchema)
async def reject_knowledge_entry(
    entry_id: str,
    auth: User | str = Depends(require_admin_hmac_or_session),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeEntrySchema:
    """Reject a pending correction."""
    entry = await KnowledgeService.reject(db, entry_id, reviewed_by=_actor_id(auth))
    if entry is None:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    return KnowledgeEntrySchema.model_validate(entry)
