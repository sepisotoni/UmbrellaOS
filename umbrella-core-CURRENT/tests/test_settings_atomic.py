"""Atomicity regression tests for settings -> AI model table propagation."""

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from models import AuditLog, Setting
from models.ai import AIModelConfig
from tests.conftest import ADMIN_HEADERS

KEY = "ai.task.atomic_probe.primary_model"


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["patch", "post"])
async def test_model_sync_failure_rolls_back_setting_audit_and_model(
    client, db_session, monkeypatch, method
):
    import api.routers.settings as router

    async with db_session() as db:
        db.add(
            Setting(
                key=KEY,
                value="google/original-model",
                category="ai",
                description="Atomicity regression probe",
                sensitive=False,
                requires_restart=False,
            )
        )
        db.add(
            AIModelConfig(
                id=str(uuid.uuid4()),
                task_type="atomic_probe",
                provider="gemini",
                model_name="original-model",
                priority=10,
                enabled=True,
                is_healthy=True,
                consecutive_failures=0,
            )
        )
        await db.commit()

    real_sync = router.sync_task_model_setting

    async def fail_after_sync(db, key, value):
        await real_sync(db, key, value)
        await db.flush()
        raise HTTPException(status_code=503, detail="injected model-sync failure")

    monkeypatch.setattr(router, "sync_task_model_setting", fail_after_sync)
    response = await getattr(client, method)(
        f"/api/v1/settings/{KEY}",
        json={"value": "openai/next-model"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 503

    async with db_session() as db:
        setting = await db.scalar(select(Setting).where(Setting.key == KEY))
        model = await db.scalar(
            select(AIModelConfig).where(
                AIModelConfig.task_type == "atomic_probe",
                AIModelConfig.priority == 10,
            )
        )
        audit = await db.scalar(
            select(AuditLog).where(
                AuditLog.target == KEY,
                AuditLog.action.in_(["settings.update", "settings.create"]),
            )
        )
        assert setting.value == "google/original-model"
        assert model.provider == "gemini"
        assert model.model_name == "original-model"
        assert audit is None


@pytest.mark.asyncio
async def test_upsert_rolls_back_new_setting_when_model_sync_fails(
    client, db_session, monkeypatch
):
    import api.routers.settings as router

    async def fail_sync(*args, **kwargs):
        raise HTTPException(status_code=503, detail="injected model-sync failure")

    monkeypatch.setattr(router, "sync_task_model_setting", fail_sync)
    response = await client.post(
        f"/api/v1/settings/{KEY}",
        json={"value": "google/proposed-model"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 503

    async with db_session() as db:
        setting = await db.scalar(select(Setting).where(Setting.key == KEY))
        assert setting is None
        audit = await db.scalar(select(AuditLog).where(AuditLog.target == KEY))
        assert audit is None
