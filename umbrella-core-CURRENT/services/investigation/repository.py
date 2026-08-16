"""
services/investigation/repository.py — Ported from Moo-assistant's
InvestigationRepository (in bot/repositories/moderation_intel_repository.py).

Adapted to umbrella-core's dependency-injected AsyncSession convention
(see services/moderation_intelligence/repository.py's module docstring for
the same rationale). `linked_account` is dropped entirely - queries go
against models.discord.DiscordAccount instead, umbrella-core's pre-existing
account-linking table (see models/knowledge.py's module docstring).
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.discord import DiscordAccount
from models.investigation import Investigation, InvestigationFinding
from models.knowledge import KnownIssue, WhitelistEntry


class InvestigationRepository:
    @staticmethod
    async def create_investigation(
        db: AsyncSession,
        *,
        requested_by: str,
        target_user_id: str | None,
        question: str,
        summary: str,
        confidence: float,
    ) -> Investigation:
        investigation = Investigation(
            requested_by=requested_by,
            target_user_id=target_user_id,
            question=question,
            summary=summary,
            confidence=confidence,
        )
        db.add(investigation)
        await db.flush()
        return investigation

    @staticmethod
    async def add_finding(
        db: AsyncSession, *, investigation_id: str, tool_key: str, finding_text: str, confidence: float
    ) -> InvestigationFinding:
        finding = InvestigationFinding(
            investigation_id=investigation_id,
            tool_key=tool_key,
            finding_text=finding_text,
            confidence=confidence,
        )
        db.add(finding)
        await db.flush()
        return finding

    @staticmethod
    async def recent(db: AsyncSession, limit: int = 10) -> list[Investigation]:
        stmt = select(Investigation).order_by(Investigation.created_at.desc()).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def known_issues(db: AsyncSession, *, only_open: bool = True) -> list[KnownIssue]:
        stmt = select(KnownIssue)
        if only_open:
            stmt = stmt.where(KnownIssue.is_resolved.is_(False))
        stmt = stmt.order_by(KnownIssue.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def linked_account(db: AsyncSession, discord_user_id: str) -> DiscordAccount | None:
        """Queries umbrella-core's pre-existing DiscordAccount table, not a
        separate LinkedAccount - see models/knowledge.py's module
        docstring. Only returns verified links, matching what an
        investigation tool should trust as "actually linked" rather than
        a claimed-but-unverified one."""
        stmt = select(DiscordAccount).where(
            DiscordAccount.discord_id == discord_user_id, DiscordAccount.verified.is_(True)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def whitelist_entry(
        db: AsyncSession, *, ingame_username: str | None = None, discord_user_id: str | None = None
    ) -> WhitelistEntry | None:
        if ingame_username is not None:
            stmt = select(WhitelistEntry).where(WhitelistEntry.ingame_username == ingame_username)
        elif discord_user_id is not None:
            stmt = select(WhitelistEntry).where(WhitelistEntry.discord_user_id == discord_user_id)
        else:
            return None
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
