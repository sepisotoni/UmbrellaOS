"""
services/alt_detection_service.py — Suspicion scoring and alt detection service.

Implements rule-based suspicion scoring for detecting potential alt accounts.
"""
import json
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from models import (
    Player,
    IPAddress,
    DiscordAccount,
    Punishment,
    SuspicionEvent,
    AuditLog,
)

SUSPICION_RULES = {
    "same_ip": 50,
    "joined_within_5_minutes": 20,
    "no_discord_verification": 30,
    "new_discord_account_under_7_days": 25,
    "previously_punished_ip": 40,
    "similar_username_to_banned_player": 15,
    "vpn_or_proxy_ip": 35,
}


async def calculate_suspicion(
    player_uuid: str,
    ip_address: str,
    username: str,
    db: AsyncSession,
) -> dict:
    """
    Calculate suspicion score for a player based on various rules.
    
    Returns { score, triggers: [list of triggered rules] }
    """
    triggers = []
    total_score = 0
    
    # Ensure player exists
    result = await db.execute(
        select(Player).where(Player.uuid == player_uuid)
    )
    player = result.scalar_one_or_none()
    
    if not player:
        # Create player if it doesn't exist
        player = Player(
            uuid=player_uuid,
            username=username,
        )
        db.add(player)
        await db.flush()
    
    # Add IP address record for this player
    result = await db.execute(
        select(IPAddress).where(
            and_(
                IPAddress.player_uuid == player_uuid,
                IPAddress.ip_address == ip_address,
            )
        )
    )
    ip_record = result.scalar_one_or_none()
    
    if not ip_record:
        ip_record = IPAddress(
            player_uuid=player_uuid,
            ip_address=ip_address,
        )
        db.add(ip_record)
        await db.flush()
    
    # Rule: same_ip - find other players with same IP
    result = await db.execute(
        select(IPAddress).where(
            and_(
                IPAddress.ip_address == ip_address,
                IPAddress.player_uuid != player_uuid,
            )
        )
    )
    same_ip_players = result.scalars().all()
    if same_ip_players:
        triggers.append("same_ip")
        total_score += SUSPICION_RULES["same_ip"]
    
    # Rule: joined_within_5_minutes - check if another player joined from same IP in last 5 minutes
    five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
    result = await db.execute(
        select(Player).where(
            and_(
                Player.uuid != player_uuid,
                Player.first_seen >= five_minutes_ago,
            )
        )
    )
    recent_players = result.scalars().all()
    
    # Check if any recent players share the IP
    for recent_player in recent_players:
        result = await db.execute(
            select(IPAddress).where(
                and_(
                    IPAddress.player_uuid == recent_player.uuid,
                    IPAddress.ip_address == ip_address,
                )
            )
        )
        if result.scalar_one_or_none():
            triggers.append("joined_within_5_minutes")
            total_score += SUSPICION_RULES["joined_within_5_minutes"]
            break
    
    # Rule: no_discord_verification - check DiscordAccount table
    result = await db.execute(
        select(DiscordAccount).where(
            and_(
                DiscordAccount.player_uuid == player_uuid,
                DiscordAccount.verified == True,
            )
        )
    )
    if not result.scalar_one_or_none():
        triggers.append("no_discord_verification")
        total_score += SUSPICION_RULES["no_discord_verification"]
    
    # Rule: previously_punished_ip - check punishments joined with ip_addresses
    result = await db.execute(
        select(Punishment).where(
            Punishment.player_uuid == player_uuid
        )
    )
    player_punishments = result.scalars().all()
    
    # Check if any other players with same IP have been punished
    for same_ip_player in same_ip_players:
        result = await db.execute(
            select(Punishment).where(
                Punishment.player_uuid == same_ip_player.player_uuid
            )
        )
        if result.scalar_one_or_none():
            triggers.append("previously_punished_ip")
            total_score += SUSPICION_RULES["previously_punished_ip"]
            break
    
    # Rule: similar_username_to_banned_player - check Levenshtein distance
    # For simplicity, we'll check for exact substring matches
    result = await db.execute(
        select(Punishment).where(
            Punishment.active == True
        )
    )
    active_punishments = result.scalars().all()
    
    for punishment in active_punishments:
        # Get the punished player's username
        result = await db.execute(
            select(Player).where(Player.uuid == punishment.player_uuid)
        )
        punished_player = result.scalar_one_or_none()
        if punished_player:
            # Simple similarity check: if username contains banned player's username or vice versa
            if (punished_player.username.lower() in username.lower() or
                username.lower() in punished_player.username.lower()):
                triggers.append("similar_username_to_banned_player")
                total_score += SUSPICION_RULES["similar_username_to_banned_player"]
                break
    
    # Save each triggered rule as SuspicionEvent
    for trigger in triggers:
        event = SuspicionEvent(
            player_uuid=player_uuid,
            trigger=trigger,
            points=SUSPICION_RULES[trigger],
            metadata_json=json.dumps({"ip_address": ip_address, "username": username}),
        )
        db.add(event)
    
    # Update player.suspicion_score in players table
    result = await db.execute(
        select(Player).where(Player.uuid == player_uuid)
    )
    player = result.scalar_one_or_none()
    if player:
        player.suspicion_score = total_score
    
    await db.flush()
    
    return {
        "score": total_score,
        "triggers": triggers,
    }


async def flag_player(
    player_uuid: str,
    score: int,
    triggers: list,
    db: AsyncSession,
) -> dict:
    """
    Flag a player based on suspicion score.
    
    Creates audit log entries for high-risk players.
    
    Returns { flagged: bool, risk_level: "low/medium/high/critical" }
    """
    flagged = False
    risk_level = "low"
    
    if score >= 95:
        risk_level = "critical"
        flagged = True
        audit_log = AuditLog(
            actor="system",
            actor_type="system",
            action="alt.high_risk",
            target=player_uuid,
            details_json=json.dumps({"score": score, "triggers": triggers}),
        )
        db.add(audit_log)
    elif score >= 80:
        risk_level = "high"
        flagged = True
        audit_log = AuditLog(
            actor="system",
            actor_type="system",
            action="alt.flagged",
            target=player_uuid,
            details_json=json.dumps({"score": score, "triggers": triggers}),
        )
        db.add(audit_log)
    elif score >= 40:
        risk_level = "medium"
    else:
        risk_level = "low"
    
    await db.flush()
    
    return {
        "flagged": flagged,
        "risk_level": risk_level,
    }
