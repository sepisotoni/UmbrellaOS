"""
services/ai_config_service.py — AI-powered configuration service.

Uses OpenRouter API to generate configuration suggestions from natural language.
"""
import httpx
import json
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import AIConfigAction
from services.settings_service import SettingsService


SYSTEM_PROMPTS = {
    "dashboard_layout": """You are configuring a Minecraft server management dashboard. Convert natural language requests into JSON layout actions. Available actions:
- create_menu: { action, name, position, icon }
- hide_menu: { action, menu_name, from_roles: [] }
- reorder_menu: { action, menu_name, new_position }
- add_stat_card: { action, title, metric, position }
Return ONLY valid JSON, no explanation.""",
    
    "discord_config": """You are configuring a Discord server for a Minecraft network. Convert natural language to Discord API actions. Available actions:
- create_channel: { action, name, type, category? }
- set_bot_status: { action, status_type, text }
- create_role: { action, name, color?, permissions?: [] }
Return ONLY valid JSON array of actions, no explanation.""",
    
    "plugin_config": """You are configuring a Minecraft server plugin. Convert natural language to config changes. Available settings:
- bridge_mode: off/partial/full
- verify_on_join: true/false
- welcome_message: string
- death_message_format: string
- verification_timeout_seconds: number
Return ONLY valid JSON of setting key/value pairs.""",
}


OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = "openai/gpt-oss-20b:free"


class AIConfigServiceError(Exception):
    """Raised when AI config service encounters an error."""
    pass


async def process_ai_config_request(
    action_type: str,
    natural_language: str,
    db: AsyncSession,
) -> AIConfigAction:
    """
    Process an AI configuration request.
    
    Args:
        action_type: Type of config to generate (dashboard_layout, discord_config, plugin_config)
        natural_language: User's natural language input
        db: Database session
    
    Returns:
        Created AIConfigAction with status=pending
    
    Raises:
        AIConfigServiceError: If API key is not configured or API call fails
    """
    # Get OpenRouter API key from settings
    api_key = await SettingsService.get_value(db, "ai.openrouter_api_key")
    if not api_key:
        raise AIConfigServiceError("OpenRouter API key required. Configure in Settings → AI")
    
    # Get system prompt for the action type
    system_prompt = SYSTEM_PROMPTS.get(action_type)
    if not system_prompt:
        raise AIConfigServiceError(f"Unknown action type: {action_type}")
    
    try:
        # Call OpenRouter API
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                OPENROUTER_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://umbrellaos.app",
                    "X-Title": "UmbrellaOS",
                },
                json={
                    "model": MODEL_NAME,
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt,
                        },
                        {
                            "role": "user",
                            "content": natural_language,
                        },
                    ],
                    "max_tokens": 500,
                    "temperature": 0.1,
                },
            )
            
            if response.status_code != 200:
                raise AIConfigServiceError(f"OpenRouter API error: {response.status_code}")
            
            result = response.json()
            if "choices" not in result or not result["choices"]:
                raise AIConfigServiceError("No response from AI model")
            
            ai_content = result["choices"][0]["message"]["content"].strip()
            
            # Try to parse as JSON
            try:
                proposed_changes = json.dumps(json.loads(ai_content))
                ai_interpretation = ai_content
            except json.JSONDecodeError:
                # If not valid JSON, wrap it as a string
                proposed_changes = json.dumps({"raw_response": ai_content})
                ai_interpretation = f"Raw response: {ai_content}"
            
            # Save AIConfigAction
            config_action = AIConfigAction(
                action_type=action_type,
                natural_language_input=natural_language,
                ai_interpretation=ai_interpretation,
                proposed_changes=proposed_changes,
                status="pending",
                created_at=datetime.utcnow(),
            )
            db.add(config_action)
            await db.commit()
            await db.refresh(config_action)
            
            return config_action
            
    except httpx.TimeoutException:
        raise AIConfigServiceError("OpenRouter API timeout")
    except httpx.RequestError as e:
        raise AIConfigServiceError(f"OpenRouter API request failed: {e}")
    except Exception as e:
        raise AIConfigServiceError(f"AI config error: {e}")


async def apply_config_action(
    action_id: int,
    db: AsyncSession,
) -> AIConfigAction:
    """
    Apply an AI-generated configuration action.
    
    Args:
        action_id: ID of the AIConfigAction to apply
        db: Database session
    
    Returns:
        Updated AIConfigAction with status=applied
    
    Raises:
        ValueError: If action not found or status is not pending
    """
    # Load the action
    result = await db.execute(
        select(AIConfigAction).where(AIConfigAction.id == action_id)
    )
    action = result.scalar_one_or_none()
    
    if not action:
        raise ValueError(f"AI config action {action_id} not found")
    
    if action.status != "pending":
        raise ValueError(f"Action is {action.status}, cannot apply")
    
    # Parse proposed changes
    try:
        changes = json.loads(action.proposed_changes)
    except json.JSONDecodeError as e:
        action.status = "rejected"
        action.error_message = f"Invalid JSON: {e}"
        action.reviewed_at = datetime.utcnow()
        await db.commit()
        await db.refresh(action)
        return action
    
    # Apply changes based on action type
    from api.middleware.audit import create_audit_log, AuditAction
    import models
    
    try:
        if action.action_type == "plugin_config":
            # Apply plugin settings via settings_service
            for key, value in changes.items():
                if isinstance(value, bool):
                    await SettingsService.set_value(db, key, "true" if value else "false", "plugin")
                elif isinstance(value, (str, int, float)):
                    await SettingsService.set_value(db, key, str(value), "plugin")
        
        elif action.action_type == "dashboard_layout":
            # Save dashboard layout settings (new keys)
            for i, layout_item in enumerate(changes if isinstance(changes, list) else [changes]):
                base_key = f"dashboard.layout.{i}"
                await SettingsService.set_value(db, base_key, json.dumps(layout_item), "dashboard")
        
        elif action.action_type == "discord_config":
            # Save Discord config settings (new keys)
            for i, discord_item in enumerate(changes if isinstance(changes, list) else [changes]):
                base_key = f"discord.config.{i}"
                await SettingsService.set_value(db, base_key, json.dumps(discord_item), "discord")
        
        # Mark as applied
        action.status = "applied"
        action.applied_at = datetime.utcnow()
        action.reviewed_at = datetime.utcnow()
        
        # Create audit log
        await create_audit_log(
            db=db,
            action=AuditAction("ai_config.applied"),
            actor="system",
            target_uuid=str(action.id),
            details={
                "action_type": action.action_type,
                "natural_language": action.natural_language_input,
            },
        )
        
        await db.commit()
        await db.refresh(action)
        
        return action
        
    except Exception as e:
        # Mark as rejected with error
        action.status = "rejected"
        action.error_message = f"Failed to apply: {e}"
        action.reviewed_at = datetime.utcnow()
        await db.commit()
        await db.refresh(action)
        return action
