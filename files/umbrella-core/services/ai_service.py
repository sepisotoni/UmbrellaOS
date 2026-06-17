"""
services/ai_service.py — AI moderation review service.

Uses Anthropic Claude API to review flagged players, appeals, and chat messages.
"""
import json
from datetime import datetime, timedelta
from typing import Optional
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import (
    AITask, Player, SuspicionEvent, Punishment, Appeal,
    AltGroup, AltGroupMember, DiscordAccount, ChatMessage,
)
from services.settings_service import SettingsService


class AIServiceError(Exception):
    """Raised when AI service encounters an error."""
    pass


ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL_NAME = "claude-haiku-4-5-20251001"


async def _get_anthropic_api_key(db: AsyncSession) -> str:
    """Get Anthropic API key from settings. Raises AIServiceError if not set."""
    api_key = await SettingsService.get_value(db, "ai.anthropic_api_key")
    if not api_key:
        raise AIServiceError("Anthropic API key not configured. Set ai.anthropic_api_key in settings.")
    return api_key


async def _call_claude(
    db: AsyncSession,
    prompt: str,
) -> dict:
    """
    Call Claude API with the given prompt.
    Returns parsed response with summary, recommendation, and confidence.
    """
    api_key = await _get_anthropic_api_key(db)
    
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    
    payload = {
        "model": MODEL_NAME,
        "max_tokens": 1024,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(ANTHROPIC_API_URL, json=payload, headers=headers)
        if response.status_code != 200:
            raise AIServiceError(f"Anthropic API error: {response.status_code} {response.text}")
        
        data = response.json()
        content = data.get("content", [{}])[0].get("text", "")
        
        # Parse the response to extract structured data
        # Expected format: JSON with summary, recommendation, confidence
        try:
            # Try to parse as JSON first
            parsed = json.loads(content)
            return {
                "summary": parsed.get("summary", content[:500]),
                "recommendation": parsed.get("recommendation", "review"),
                "confidence": float(parsed.get("confidence", 0.5)),
            }
        except json.JSONDecodeError:
            # Fallback: extract from text
            return {
                "summary": content[:500],
                "recommendation": "review",
                "confidence": 0.5,
            }


async def review_flagged_player(
    player_uuid: str,
    db: AsyncSession,
) -> AITask:
    """
    AI review of a flagged player.
    Fetches player record, suspicion events, punishment history,
    alt group membership, verification status.
    Calls Claude API and creates AITask with task_type=moderation_review.
    """
    # Fetch player data
    player = await db.scalar(select(Player).where(Player.uuid == player_uuid))
    if not player:
        raise AIServiceError(f"Player not found: {player_uuid}")
    
    # Fetch suspicion events
    suspicion_result = await db.execute(
        select(SuspicionEvent).where(SuspicionEvent.player_uuid == player_uuid)
        .order_by(SuspicionEvent.created_at.desc()).limit(10)
    )
    suspicion_events = suspicion_result.scalars().all()
    
    # Fetch punishment history
    punishment_result = await db.execute(
        select(Punishment).where(Punishment.player_uuid == player_uuid)
        .order_by(Punishment.created_at.desc()).limit(10)
    )
    punishments = punishment_result.scalars().all()
    
    # Fetch alt group membership
    alt_group_result = await db.execute(
        select(AltGroupMember).where(AltGroupMember.player_uuid == player_uuid)
    )
    alt_memberships = alt_group_result.scalars().all()
    
    # Fetch verification status
    discord_account = await db.scalar(
        select(DiscordAccount).where(DiscordAccount.player_uuid == player_uuid)
    )
    
    # Build context prompt
    context = {
        "player": {
            "uuid": player.uuid,
            "username": player.username,
            "first_seen": player.first_seen.isoformat() if player.first_seen else None,
            "last_seen": player.last_seen.isoformat() if player.last_seen else None,
            "playtime": player.playtime,
            "risk_score": player.risk_score,
            "suspicion_score": player.suspicion_score,
            "discord_linked": discord_account is not None,
            "discord_verified": discord_account.verified if discord_account else False,
        },
        "suspicion_events": [
            {
                "trigger": e.trigger,
                "points": e.points,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "reviewed": e.reviewed,
            }
            for e in suspicion_events
        ],
        "punishments": [
            {
                "type": p.type,
                "reason": p.reason,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "active": p.active,
            }
            for p in punishments
        ],
        "alt_groups": [
            {"group_id": m.group_id, "added_at": m.added_at.isoformat() if m.added_at else None}
            for m in alt_memberships
        ],
    }
    
    prompt = f"""You are a Minecraft server moderator AI assistant. Review the following flagged player data and provide a moderation recommendation.

Player Context:
{json.dumps(context, indent=2)}

Respond with a JSON object containing:
- summary: A brief summary of the situation (1-2 sentences)
- recommendation: One of: "ban", "tempban", "mute", "warn", "monitor", "no_action"
- confidence: A float between 0.0 and 1.0 indicating your confidence in this recommendation

Example response:
{{"summary": "Player has high suspicion score from multiple triggers and previous bans", "recommendation": "ban", "confidence": 0.85}}"""
    
    # Call Claude API
    ai_response = await _call_claude(db, prompt)
    
    # Create AITask
    task = AITask(
        task_type="moderation_review",
        status="pending",
        player_uuid=player_uuid,
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(hours=48),
        ai_summary=ai_response["summary"],
        ai_recommendation=ai_response["recommendation"],
        ai_confidence=ai_response["confidence"],
        evidence=json.dumps(context),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    return task


async def review_appeal(
    appeal_id: str,
    db: AsyncSession,
) -> AITask:
    """
    AI review of an appeal.
    Fetches appeal, original punishment, player history, suspicion score.
    Calls Claude API for recommendation (approve/deny/escalate).
    Creates AITask with task_type=appeal_review.
    """
    # Fetch appeal
    appeal = await db.scalar(select(Appeal).where(Appeal.id == appeal_id))
    if not appeal:
        raise AIServiceError(f"Appeal not found: {appeal_id}")
    
    # Fetch original punishment
    punishment = await db.scalar(select(Punishment).where(Punishment.id == appeal.punishment_id))
    
    # Fetch player data
    player = await db.scalar(select(Player).where(Player.uuid == appeal.player_uuid))
    
    # Fetch player history
    punishment_result = await db.execute(
        select(Punishment).where(Punishment.player_uuid == appeal.player_uuid)
        .order_by(Punishment.created_at.desc()).limit(5)
    )
    punishments = punishment_result.scalars().all()
    
    # Build context prompt
    context = {
        "appeal": {
            "id": appeal.id,
            "message": appeal.message,
            "status": appeal.status,
            "created_at": appeal.created_at.isoformat() if appeal.created_at else None,
        },
        "punishment": {
            "type": punishment.type if punishment else None,
            "reason": punishment.reason if punishment else None,
            "created_at": punishment.created_at.isoformat() if punishment and punishment.created_at else None,
        } if punishment else None,
        "player": {
            "uuid": player.uuid if player else None,
            "username": player.username if player else None,
            "suspicion_score": player.suspicion_score if player else None,
        } if player else None,
        "history": [
            {
                "type": p.type,
                "reason": p.reason,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in punishments
        ],
    }
    
    prompt = f"""You are a Minecraft server moderator AI assistant. Review the following punishment appeal and provide a recommendation.

Appeal Context:
{json.dumps(context, indent=2)}

Respond with a JSON object containing:
- summary: A brief summary of the appeal situation (1-2 sentences)
- recommendation: One of: "approve", "deny", "escalate"
- confidence: A float between 0.0 and 1.0 indicating your confidence in this recommendation

Example response:
{{"summary": "Player claims innocence but has multiple prior bans for similar offense", "recommendation": "deny", "confidence": 0.75}}"""
    
    # Call Claude API
    ai_response = await _call_claude(db, prompt)
    
    # Create AITask
    task = AITask(
        task_type="appeal_review",
        status="pending",
        player_uuid=appeal.player_uuid,
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(hours=48),
        ai_summary=ai_response["summary"],
        ai_recommendation=ai_response["recommendation"],
        ai_confidence=ai_response["confidence"],
        evidence=json.dumps(context),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    return task


async def review_chat_message(
    message_id: int,
    db: AsyncSession,
) -> AITask:
    """
    AI review of a chat message.
    Fetches ChatMessage, player history.
    Calls Claude API to assess if message violates rules.
    Creates AITask with task_type=chat_review.
    """
    # Fetch chat message
    message = await db.scalar(select(ChatMessage).where(ChatMessage.id == message_id))
    if not message:
        raise AIServiceError(f"Chat message not found: {message_id}")
    
    # Fetch player data
    player = None
    if message.player_uuid:
        player = await db.scalar(select(Player).where(Player.uuid == message.player_uuid))
    
    # Fetch player punishment history
    punishments = []
    if player:
        punishment_result = await db.execute(
            select(Punishment).where(Punishment.player_uuid == player.uuid)
            .order_by(Punishment.created_at.desc()).limit(5)
        )
        punishments = punishment_result.scalars().all()
    
    # Build context prompt
    context = {
        "message": {
            "id": message.id,
            "source": message.source,
            "message": message.message,
            "timestamp": message.timestamp.isoformat() if message.timestamp else None,
            "filtered": message.filtered,
        },
        "player": {
            "uuid": player.uuid if player else None,
            "username": player.username if player else None,
            "suspicion_score": player.suspicion_score if player else None,
        } if player else None,
        "history": [
            {
                "type": p.type,
                "reason": p.reason,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in punishments
        ],
    }
    
    prompt = f"""You are a Minecraft server moderator AI assistant. Review the following chat message and assess if it violates server rules.

Message Context:
{json.dumps(context, indent=2)}

Respond with a JSON object containing:
- summary: A brief summary of the message and any rule violations (1-2 sentences)
- recommendation: One of: "mute", "warn", "delete", "no_action"
- confidence: A float between 0.0 and 1.0 indicating your confidence in this recommendation

Example response:
{{"summary": "Message contains hate speech directed at another player", "recommendation": "mute", "confidence": 0.95}}"""
    
    # Call Claude API
    ai_response = await _call_claude(db, prompt)
    
    # Create AITask
    task = AITask(
        task_type="chat_review",
        status="pending",
        player_uuid=message.player_uuid,
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(hours=48),
        ai_summary=ai_response["summary"],
        ai_recommendation=ai_response["recommendation"],
        ai_confidence=ai_response["confidence"],
        evidence=json.dumps(context),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    return task
