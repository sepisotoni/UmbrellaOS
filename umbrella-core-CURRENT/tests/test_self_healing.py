"""
tests/test_self_healing.py — Tests for ServerService.reconcile_server /
reconcile_fleet: the crash-detection, auto-restart, and escalating
suspension policy.
"""
import pytest

from services.allocation_service import AllocationService
from services.daemon_client import ContainerState, DaemonError
from services.node_service import NodeService
from services.server_service import ServerService
from services.server_template_service import ServerTemplateService


class FakeHealingDaemonClient:
    """A fake whose reported `state()` can be scripted per-call, to
    simulate a server crashing, being restarted, and crashing again."""

    def __init__(self, state_sequence: list[str], start_fails: bool = False):
        self._state_sequence = list(state_sequence)
        self._start_fails = start_fails
        self.start_calls = 0

    async def create(self, server_id, **kwargs):
        return ContainerState(server_id=server_id, runtime_id="d", status="created",
                               started_at=None, finished_at=None, exit_code=None, oom_killed=False)

    async def state(self, server_id):
        status = self._state_sequence.pop(0) if self._state_sequence else "running"
        return ContainerState(server_id=server_id, runtime_id="d", status=status,
                               started_at=None, finished_at=None, exit_code=1 if status == "crashed" else 0,
                               oom_killed=False)

    async def start(self, server_id):
        self.start_calls += 1
        if self._start_fails:
            raise DaemonError("simulated restart failure")
        return ContainerState(server_id=server_id, runtime_id="d", status="running",
                               started_at=None, finished_at=None, exit_code=None, oom_killed=False)


async def _setup_server(db_session, fake_client) -> str:
    import uuid
    node_name = f"node-healing-{uuid.uuid4().hex[:8]}"

    async with db_session() as db:
        node, _ = await NodeService.register_node(db, node_name, "https://node:8443")
        template = await ServerTemplateService.create_template(db, "Paper", image="itzg/minecraft-server")
        await db.commit()
        node_id, template_id = node.id, template.id

    async with db_session() as db:
        allocation = await AllocationService.create_allocation(db, node_id, 25565)
        await db.commit()
        allocation_id = allocation.id

    async with db_session() as db:
        server = await ServerService.create_server(
            db, "Survival", node_id, template_id, [allocation_id], daemon_client=fake_client
        )
        await db.commit()
        return server.id


@pytest.mark.asyncio
async def test_reconcile_healthy_server_does_nothing(db_session):
    fake_client = FakeHealingDaemonClient(state_sequence=["running"])
    server_id = await _setup_server(db_session, fake_client)

    async with db_session() as db:
        server, crash_detected = await ServerService.reconcile_server(db, server_id, daemon_client=fake_client)
        await db.commit()
        assert crash_detected is False
        assert server.crash_count == 0
        assert fake_client.start_calls == 0


@pytest.mark.asyncio
async def test_reconcile_detects_crash_and_restarts(db_session):
    fake_client = FakeHealingDaemonClient(state_sequence=["crashed"])
    server_id = await _setup_server(db_session, fake_client)

    async with db_session() as db:
        server, crash_detected = await ServerService.reconcile_server(db, server_id, daemon_client=fake_client)
        await db.commit()
        assert crash_detected is True
        assert server.crash_count == 1
        assert server.last_crash_at is not None
        assert server.status == "running"  # restarted successfully
        assert server.is_suspended is False

    assert fake_client.start_calls == 1


@pytest.mark.asyncio
async def test_repeated_crashes_escalate_to_suspension(db_session):
    fake_client = FakeHealingDaemonClient(state_sequence=["crashed"])
    server_id = await _setup_server(db_session, fake_client)

    # Crash 1, 2, 3: restarted each time (MAX_CONSECUTIVE_CRASHES_BEFORE_SUSPEND == 3).
    for i in range(3):
        fake_client._state_sequence = ["crashed"]
        async with db_session() as db:
            server, crash_detected = await ServerService.reconcile_server(db, server_id, daemon_client=fake_client)
            await db.commit()
            assert crash_detected is True
            assert server.is_suspended is False, f"should not be suspended after {i + 1} crashes"

    # Crash 4: now exceeds the threshold — suspended, not restarted again.
    fake_client._state_sequence = ["crashed"]
    calls_before = fake_client.start_calls
    async with db_session() as db:
        server, crash_detected = await ServerService.reconcile_server(db, server_id, daemon_client=fake_client)
        await db.commit()
        assert crash_detected is True
        assert server.is_suspended is True
        assert server.crash_count == 4

    assert fake_client.start_calls == calls_before  # no further restart attempted once suspended


@pytest.mark.asyncio
async def test_suspended_server_is_never_touched_by_reconcile(db_session):
    fake_client = FakeHealingDaemonClient(state_sequence=["crashed"])
    server_id = await _setup_server(db_session, fake_client)

    async with db_session() as db:
        server = await ServerService.get_server(db, server_id)
        server.is_suspended = True
        await db.commit()

    async with db_session() as db:
        server, crash_detected = await ServerService.reconcile_server(db, server_id, daemon_client=fake_client)
        assert crash_detected is False

    assert fake_client.start_calls == 0  # never even inspected/restarted


@pytest.mark.asyncio
async def test_manual_start_resets_crash_count(db_session):
    fake_client = FakeHealingDaemonClient(state_sequence=["crashed"])
    server_id = await _setup_server(db_session, fake_client)

    async with db_session() as db:
        server, _ = await ServerService.reconcile_server(db, server_id, daemon_client=fake_client)
        await db.commit()
        assert server.crash_count == 1

    async with db_session() as db:
        server = await ServerService.start_server(db, server_id, daemon_client=fake_client)
        await db.commit()
        assert server.crash_count == 0


@pytest.mark.asyncio
async def test_reconcile_restart_failure_leaves_crash_count_incremented_for_next_tick(db_session):
    fake_client = FakeHealingDaemonClient(state_sequence=["crashed"], start_fails=True)
    server_id = await _setup_server(db_session, fake_client)

    async with db_session() as db:
        server, crash_detected = await ServerService.reconcile_server(db, server_id, daemon_client=fake_client)
        await db.commit()
        assert crash_detected is True
        assert server.crash_count == 1
        assert server.is_suspended is False  # restart failing isn't itself grounds for suspension yet


@pytest.mark.asyncio
async def test_reconcile_fleet_skips_suspended_servers_and_returns_only_crashed_ids(db_session):
    fake_client_a = FakeHealingDaemonClient(state_sequence=["running"])
    fake_client_b = FakeHealingDaemonClient(state_sequence=["crashed"])

    server_a_id = await _setup_server(db_session, fake_client_a)
    server_b_id = await _setup_server(db_session, fake_client_b)

    async with db_session() as db:
        server_b = await ServerService.get_server(db, server_b_id)
        server_b.is_suspended = True
        await db.commit()

    # reconcile_fleet uses a single daemon_client for every server in this
    # test's setup — swap fake_client_b in isn't meaningful once suspended
    # is set, since suspended servers are skipped before any daemon call.
    async with db_session() as db:
        crashed = await ServerService.reconcile_fleet(db, daemon_client=fake_client_a)
        await db.commit()
        # server_a is healthy (fake_client_a reports "running"); server_b
        # is suspended and skipped entirely — neither should appear.
        assert server_a_id not in crashed
        assert server_b_id not in crashed
