"""Failure-injection test for AI configuration SAVEPOINT/outer transaction."""

import pytest
from sqlalchemy import select

from models import AIConfigAction, Setting
from services.ai_config_service import apply_config_action
from services.settings_service import SettingsService


@pytest.mark.asyncio
async def test_ai_config_rolls_back_first_setting_when_later_write_fails(
    db_session, monkeypatch
):
    """Rejected multi-setting actions must not persist partial config writes."""
    async with db_session() as db:
        action = AIConfigAction(
            action_type="plugin_config",
            natural_language_input="Update two settings",
            ai_interpretation="Test proposal",
            proposed_changes='{"probe.first": "one", "probe.second": "two"}',
            status="pending",
        )
        db.add(action)
        await db.commit()
        action_id = action.id

    original = SettingsService.set_value
    writes = []

    async def fault_after_first(db, key, value, category="general", actor="system"):
        writes.append(key)
        if key == "probe.second":
            raise RuntimeError("injected failure on second setting")
        return await original(db, key, value, category, actor)

    monkeypatch.setattr(SettingsService, "set_value", staticmethod(fault_after_first))

    async with db_session() as db:
        result = await apply_config_action(action_id, db)
        assert result.status == "rejected"
        await db.commit()

    assert writes == ["probe.first", "probe.second"]
    async with db_session() as db:
        first = await db.scalar(select(Setting).where(Setting.key == "probe.first"))
        second = await db.scalar(select(Setting).where(Setting.key == "probe.second"))
        action = await db.get(AIConfigAction, action_id)
        assert first is None
        assert second is None
        assert action.status == "rejected"
        assert action.error_message.startswith("Failed to apply")
