"""
tests/test_hosting_services.py — Tests for the hosting domain's service
layer: NodeService, ServerTemplateService, AllocationService, and
ServerService's orchestration.

ServerService tests inject a FakeDaemonClient (matching DaemonClient's
public method signatures) rather than talking to a real daemon — the same
dependency-injection pattern used by umbrella-daemon's own DockerClient
interface and the Capability Registry's CallContext.
"""
import pytest

from services.allocation_service import AllocationError, AllocationService
from services.daemon_client import ContainerState, DaemonError, StatsSnapshot
from services.node_service import NodeError, NodeService
from services.server_service import ServerError, ServerService
from services.server_template_service import ServerTemplateError, ServerTemplateService


class FakeDaemonClient:
    """Records calls and returns configurable results — no network, no
    real daemon, matching DaemonClient's public interface exactly."""

    def __init__(self, create_status="created", fail_on: set[str] | None = None):
        self.calls: list[tuple] = []
        self._create_status = create_status
        self._fail_on = fail_on or set()

    def _maybe_fail(self, method: str):
        if method in self._fail_on:
            raise DaemonError(f"simulated failure for {method}")

    async def create(self, server_id, **kwargs):
        self.calls.append(("create", server_id, kwargs))
        self._maybe_fail("create")
        return ContainerState(
            server_id=server_id, runtime_id="docker-fake", status=self._create_status,
            started_at=None, finished_at=None, exit_code=None, oom_killed=False,
        )

    async def start(self, server_id):
        self.calls.append(("start", server_id))
        self._maybe_fail("start")
        return ContainerState(server_id=server_id, runtime_id="docker-fake", status="running",
                               started_at=None, finished_at=None, exit_code=None, oom_killed=False)

    async def stop(self, server_id, grace_period_seconds=None):
        self.calls.append(("stop", server_id, grace_period_seconds))
        self._maybe_fail("stop")
        return ContainerState(server_id=server_id, runtime_id="docker-fake", status="stopped",
                               started_at=None, finished_at=None, exit_code=0, oom_killed=False)

    async def restart(self, server_id):
        self.calls.append(("restart", server_id))
        self._maybe_fail("restart")
        return ContainerState(server_id=server_id, runtime_id="docker-fake", status="running",
                               started_at=None, finished_at=None, exit_code=None, oom_killed=False)

    async def kill(self, server_id):
        self.calls.append(("kill", server_id))
        self._maybe_fail("kill")
        return ContainerState(server_id=server_id, runtime_id="docker-fake", status="stopped",
                               started_at=None, finished_at=None, exit_code=137, oom_killed=False)

    async def stats(self, server_id):
        self.calls.append(("stats", server_id))
        self._maybe_fail("stats")
        return StatsSnapshot(timestamp="2026-07-07T00:00:00Z", cpu_percent=12.5,
                              memory_used_bytes=100, memory_limit_bytes=200,
                              network_rx_bytes=1, network_tx_bytes=2)

    async def remove(self, server_id):
        self.calls.append(("remove", server_id))
        self._maybe_fail("remove")


# --------------------------------------------------------------------------
# NodeService
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_node_creates_node_with_generated_secret(db_session):
    async with db_session() as db:
        node, _ = await NodeService.register_node(db, "node-1", "https://node1:8443")
        await db.commit()
        assert node.status == "pending"
        assert len(node.signing_secret) >= 32


@pytest.mark.asyncio
async def test_register_node_rejects_duplicate_name(db_session):
    async with db_session() as db:
        await NodeService.register_node(db, "node-dup", "https://node1:8443")
        await db.commit()

    async with db_session() as db:
        with pytest.raises(NodeError):
            await NodeService.register_node(db, "node-dup", "https://node2:8443")


@pytest.mark.asyncio
async def test_get_node_raises_for_missing_id(db_session):
    async with db_session() as db:
        with pytest.raises(NodeError):
            await NodeService.get_node(db, "does-not-exist")


@pytest.mark.asyncio
async def test_mark_online_updates_status_and_last_seen(db_session):
    async with db_session() as db:
        node, _ = await NodeService.register_node(db, "node-2", "https://node2:8443")
        await db.commit()
        node_id = node.id

    async with db_session() as db:
        updated = await NodeService.mark_online(db, node_id)
        await db.commit()
        assert updated.status == "online"
        assert updated.last_seen_at is not None


# --------------------------------------------------------------------------
# ServerTemplateService
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_template_defaults_to_version_1(db_session):
    async with db_session() as db:
        template = await ServerTemplateService.create_template(
            db, "Paper 1.21", image="itzg/minecraft-server:java21"
        )
        await db.commit()
        assert template.version == 1


@pytest.mark.asyncio
async def test_update_template_bumps_version(db_session):
    async with db_session() as db:
        template = await ServerTemplateService.create_template(db, "Paper", image="itzg/minecraft-server:1")
        await db.commit()
        template_id = template.id

    async with db_session() as db:
        updated = await ServerTemplateService.update_template(db, template_id, image="itzg/minecraft-server:2")
        await db.commit()
        assert updated.version == 2
        assert updated.image == "itzg/minecraft-server:2"


@pytest.mark.asyncio
async def test_update_template_rejects_unknown_field(db_session):
    async with db_session() as db:
        template = await ServerTemplateService.create_template(db, "Paper", image="x")
        await db.commit()
        template_id = template.id

    async with db_session() as db:
        with pytest.raises(ServerTemplateError):
            await ServerTemplateService.update_template(db, template_id, not_a_real_field="x")


# --------------------------------------------------------------------------
# AllocationService
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_allocation_rejects_duplicate_port_on_same_node(db_session):
    async with db_session() as db:
        node, _ = await NodeService.register_node(db, "node-alloc", "https://n:8443")
        await db.commit()
        node_id = node.id

    async with db_session() as db:
        await AllocationService.create_allocation(db, node_id, 25565)
        await db.commit()

    async with db_session() as db:
        with pytest.raises(AllocationError):
            await AllocationService.create_allocation(db, node_id, 25565)


@pytest.mark.asyncio
async def test_bind_and_release_allocation(db_session):
    async with db_session() as db:
        node, _ = await NodeService.register_node(db, "node-alloc2", "https://n:8443")
        await db.commit()
        allocation = await AllocationService.create_allocation(db, node.id, 25566)
        await db.commit()
        allocation_id = allocation.id

    async with db_session() as db:
        bound = await AllocationService.bind_allocation(db, allocation_id, "fake-server-id", 25566)
        await db.commit()
        assert bound.server_id == "fake-server-id"

    async with db_session() as db:
        released = await AllocationService.release_allocation(db, allocation_id)
        await db.commit()
        assert released.server_id is None


# --------------------------------------------------------------------------
# ServerService — the orchestration layer
# --------------------------------------------------------------------------


async def _setup_node_template_allocation(db_session):
    async with db_session() as db:
        node, _ = await NodeService.register_node(db, "node-orch", "https://node-orch:8443")
        template = await ServerTemplateService.create_template(
            db, "Paper", image="itzg/minecraft-server:java21",
            startup_command=["start"], default_env={"EULA": "TRUE"},
        )
        await db.commit()
        node_id, template_id = node.id, template.id

    async with db_session() as db:
        allocation = await AllocationService.create_allocation(db, node_id, 25565)
        await db.commit()
        allocation_id = allocation.id

    return node_id, template_id, allocation_id


@pytest.mark.asyncio
async def test_create_server_happy_path(db_session):
    node_id, template_id, allocation_id = await _setup_node_template_allocation(db_session)
    fake_client = FakeDaemonClient(create_status="created")

    async with db_session() as db:
        server = await ServerService.create_server(
            db, "Survival", node_id, template_id, [allocation_id],
            daemon_client=fake_client,
        )
        await db.commit()

        assert server.status == "created"
        assert server.template_version == 1
        assert server.working_dir == f"/srv/umbrella/servers/{server.id}"

    assert fake_client.calls[0][0] == "create"
    create_kwargs = fake_client.calls[0][2]
    assert create_kwargs["env"] == {"EULA": "TRUE"}
    assert create_kwargs["port_bindings"] == [{"container_port": 25565, "host_port": 25565, "protocol": "tcp"}]


@pytest.mark.asyncio
async def test_create_server_binds_allocation_to_server(db_session):
    node_id, template_id, allocation_id = await _setup_node_template_allocation(db_session)
    fake_client = FakeDaemonClient()

    async with db_session() as db:
        server = await ServerService.create_server(
            db, "Survival", node_id, template_id, [allocation_id], daemon_client=fake_client,
        )
        await db.commit()
        server_id = server.id

    async with db_session() as db:
        allocation = await AllocationService.get_allocation(db, allocation_id)
        assert allocation.server_id == server_id


@pytest.mark.asyncio
async def test_create_server_rejects_allocation_from_different_node(db_session):
    node_id, template_id, allocation_id = await _setup_node_template_allocation(db_session)

    async with db_session() as db:
        other_node, _ = await NodeService.register_node(db, "node-other", "https://other:8443")
        await db.commit()
        other_node_id = other_node.id

    async with db_session() as db:
        with pytest.raises(ServerError):
            await ServerService.create_server(
                db, "Survival", other_node_id, template_id, [allocation_id],
                daemon_client=FakeDaemonClient(),
            )


@pytest.mark.asyncio
async def test_create_server_rejects_already_used_allocation(db_session):
    node_id, template_id, allocation_id = await _setup_node_template_allocation(db_session)

    async with db_session() as db:
        await ServerService.create_server(
            db, "Survival1", node_id, template_id, [allocation_id], daemon_client=FakeDaemonClient()
        )
        await db.commit()

    async with db_session() as db:
        with pytest.raises(ServerError):
            await ServerService.create_server(
                db, "Survival2", node_id, template_id, [allocation_id], daemon_client=FakeDaemonClient()
            )


@pytest.mark.asyncio
async def test_create_server_raises_server_error_when_daemon_call_fails(db_session):
    node_id, template_id, allocation_id = await _setup_node_template_allocation(db_session)
    fake_client = FakeDaemonClient(fail_on={"create"})

    async with db_session() as db:
        with pytest.raises(ServerError):
            await ServerService.create_server(
                db, "Survival", node_id, template_id, [allocation_id], daemon_client=fake_client,
            )


@pytest.mark.asyncio
async def test_start_stop_restart_kill_update_status_and_call_daemon(db_session):
    node_id, template_id, allocation_id = await _setup_node_template_allocation(db_session)
    fake_client = FakeDaemonClient()

    async with db_session() as db:
        server = await ServerService.create_server(
            db, "Survival", node_id, template_id, [allocation_id], daemon_client=fake_client
        )
        await db.commit()
        server_id = server.id

    async with db_session() as db:
        started = await ServerService.start_server(db, server_id, daemon_client=fake_client)
        await db.commit()
        assert started.status == "running"
        assert started.last_started_at is not None

    async with db_session() as db:
        stopped = await ServerService.stop_server(db, server_id, grace_period_seconds=20, daemon_client=fake_client)
        await db.commit()
        assert stopped.status == "stopped"

    async with db_session() as db:
        restarted = await ServerService.restart_server(db, server_id, daemon_client=fake_client)
        await db.commit()
        assert restarted.status == "running"

    async with db_session() as db:
        killed = await ServerService.kill_server(db, server_id, daemon_client=fake_client)
        await db.commit()
        assert killed.status == "stopped"

    call_names = [c[0] for c in fake_client.calls]
    assert call_names == ["create", "start", "stop", "restart", "kill"]
    stop_call = next(c for c in fake_client.calls if c[0] == "stop")
    assert stop_call[2] == 20


@pytest.mark.asyncio
async def test_get_stats_delegates_to_daemon_client(db_session):
    node_id, template_id, allocation_id = await _setup_node_template_allocation(db_session)
    fake_client = FakeDaemonClient()

    async with db_session() as db:
        server = await ServerService.create_server(
            db, "Survival", node_id, template_id, [allocation_id], daemon_client=fake_client
        )
        await db.commit()
        server_id = server.id

    async with db_session() as db:
        stats = await ServerService.get_stats(db, server_id, daemon_client=fake_client)
        assert stats.cpu_percent == 12.5


@pytest.mark.asyncio
async def test_delete_server_removes_container_and_releases_allocations(db_session):
    node_id, template_id, allocation_id = await _setup_node_template_allocation(db_session)
    fake_client = FakeDaemonClient()

    async with db_session() as db:
        server = await ServerService.create_server(
            db, "Survival", node_id, template_id, [allocation_id], daemon_client=fake_client
        )
        await db.commit()
        server_id = server.id

    async with db_session() as db:
        await ServerService.delete_server(db, server_id, daemon_client=fake_client)
        await db.commit()

    async with db_session() as db:
        with pytest.raises(ServerError):
            await ServerService.get_server(db, server_id)
        allocation = await AllocationService.get_allocation(db, allocation_id)
        assert allocation.server_id is None

    assert ("remove", server_id) in fake_client.calls
