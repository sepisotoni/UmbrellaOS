"""
services/ai_config_service.py — AI-powered configuration service.

Routes through the ModelRouter/ProviderFactory/Orchestrator stack so provider
selection, key loading at request time, health tracking, and failover all work
correctly — rather than making a direct OpenRouter call with a hardcoded free
model string ("openai/gpt-oss-20b:free").

Bug fixed: old code bypassed all provider routing, ignored enabled flags,
and used a hardcoded free model that may not exist on OpenRouter any more.
"""
import json
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import AIConfigAction
from services.settings_service import SettingsService
from services.ai.orchestrator import Orchestrator
from services.ai.model_router import NoAvailableModelError


SYSTEM_PROMPTS = {
    "dashboard_layout": (
        "You are configuring a Minecraft server management dashboard. "
        "Convert natural language requests into JSON layout actions. Available actions:\n"
        "- create_menu: { action, name, position, icon }\n"
        "- hide_menu: { action, menu_name, from_roles: [] }\n"
        "- reorder_menu: { action, menu_name, new_position }\n"
        "- add_stat_card: { action, title, metric, position }\n"
        "Return ONLY valid JSON, no explanation."
    ),
    "discord_config": (
        "You are configuring a Discord server for a Minecraft network. "
        "Convert natural language to Discord API actions. Available actions:\n"
        "- create_channel: { action, name, type, category? }\n"
        "- set_bot_status: { action, status_type, text }\n"
        "- create_role: { action, name, color?, permissions?: [] }\n"
        "Return ONLY valid JSON array of actions, no explanation."
    ),
    "plugin_config": (
        "You are configuring UmbrellaOS. Convert natural language to setting key/value pairs.\n"
        "Use exact keys: anticheat.enabled, anticheat.auto_tempban, anticheat.tempban_hours, "
        "bridge.mode, moderation.require_discord_link, server.name, server.max_players.\n"
        'Values must be strings. Booleans: "true"/"false". Return ONLY valid JSON object.'
    ),
}

# Uses "copilot" task_type so it shares the general-purpose model config rows.
# Operators can add a dedicated "ai_config" task_type to ai_model_configs to
# route config requests to a different provider/model if desired.
_CONFIG_TASK_TYPE = "copilot"


class AIConfigServiceError(Exception):
    """Raised when AI config service encounters an error."""
    pass


async def process_ai_config_request(
    action_type: str,
    natural_language: str,
    db: AsyncSession,
) -> AIConfigAction:
    """
    Process an AI configuration request through the ModelRouter stack.

    Raises AIConfigServiceError if no provider is available or the call fails.
    Never falls back to a hardcoded provider — if nothing is configured, the
    error message tells the operator exactly what to fix.
    """
    system_prompt = SYSTEM_PROMPTS.get(action_type)
    if not system_prompt:
        raise AIConfigServiceError(f"Unknown action type: {action_type!r}")

    task_prompt = f"{system_prompt}\n\nUser request: {natural_language}"

    try:
        result = await Orchestrator.run(
            db=db,
            task_type=_CONFIG_TASK_TYPE,
            task_prompt=task_prompt,
            requested_by="ai_config_service",
            require_dual_review=False,
        )
        ai_content = result.text.strip()
    except NoAvailableModelError as exc:
        raise AIConfigServiceError(
            f"No AI provider available for config requests: {exc}. "
            "Add a provider row for task_type='copilot' in Settings → AI → Models."
        ) from exc
    except Exception as exc:
        raise AIConfigServiceError(f"AI config generation error: {exc}") from exc

    # Strip markdown fences if the model wraps its JSON
    if ai_content.startswith("```"):
        ai_content = ai_content.split("```", 2)[1]
        if ai_content.startswith("json"):
            ai_content = ai_content[4:]
        ai_content = ai_content.rsplit("```", 1)[0].strip()

    try:
        proposed_changes = json.dumps(json.loads(ai_content))
        ai_interpretation = ai_content
    except json.JSONDecodeError:
        proposed_changes = json.dumps({"raw_response": ai_content})
        ai_interpretation = f"Raw response: {ai_content}"

    config_action = AIConfigAction(
        action_type=action_type,
        natural_language_input=natural_language,
        ai_interpretation=ai_interpretation,
        proposed_changes=proposed_changes,
        status="pending",
        created_at=datetime.now(timezone.utc),
    )
    db.add(config_action)
    await db.commit()
    await db.refresh(config_action)

    return config_action


async def apply_config_action(
    action_id: int,
    db: AsyncSession,
) -> AIConfigAction:
    """
    Apply an AI-generated configuration action (unchanged from original).
    """
    result = await db.execute(
        select(AIConfigAction).where(AIConfigAction.id == action_id)
    )
    action = result.scalar_one_or_none()

    if not action:
        raise ValueError(f"AI config action {action_id} not found")

    if action.status != "pending":
        raise ValueError(f"Action is {action.status}, cannot apply")

    try:
        changes = json.loads(action.proposed_changes)
    except json.JSONDecodeError as e:
        action.status = "rejected"
        action.error_message = f"Invalid JSON in proposed_changes: {e}"
        action.reviewed_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(action)
        return action

    try:
        if action.action_type == "plugin_config":
            items = changes.items() if isinstance(changes, dict) else []
            for key, value in items:
                cat = key.split(".")[0] if "." in key else "general"
                if isinstance(value, bool):
                    await SettingsService.set_value(db, str(key), "true" if value else "false", cat)
                elif isinstance(value, (str, int, float)):
                    await SettingsService.set_value(db, str(key), str(value), cat)

        elif action.action_type == "dashboard_layout":
            for i, layout_item in enumerate(changes if isinstance(changes, list) else [changes]):
                base_key = f"dashboard.layout.{i}"
                await SettingsService.set_value(db, base_key, json.dumps(layout_item), "dashboard")

        elif action.action_type == "discord_config":
            for i, discord_item in enumerate(changes if isinstance(changes, list) else [changes]):
                base_key = f"discord.config.{i}"
                await SettingsService.set_value(db, base_key, json.dumps(discord_item), "discord")

        action.status = "applied"
        action.applied_at = datetime.now(timezone.utc)
        action.reviewed_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(action)
        return action

    except Exception as e:
        action.status = "rejected"
        action.error_message = f"Failed to apply: {e}"
        action.reviewed_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(action)
        return action
