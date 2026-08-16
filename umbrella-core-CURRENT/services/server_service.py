"""
services/server_service.py — Server lifecycle orchestration: the one place
that ties a Node, a ServerTemplate, and one or more Allocations together and
actually calls the node's daemon to create/start/stop/restart/kill/remove
the resulting container.

Every method accepts an optional `daemon_client` parameter, defaulting to a
real `DaemonClient` constructed from the server's Node — production code
never passes it explicitly; tests inject a fake/mocked client so this
service's own orchestration logic (which node, which template, which
allocations, what happens to Server.status) is verifiable without a running
daemon, the same dependency-injection pattern used throughout this project
(umbrella-daemon's DockerClient interface, the Capability Registry's
CallContext).
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.errors import AppException
from models.hosting import Allocation, Server
from services.allocation_service import AllocationService
from services.daemon_client import DaemonClient, DaemonError
from services.node_service import NodeService
from services.server_template_service import ServerTemplateService


class ServerError(AppException):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message, "SERVER_ERROR", status_code)


def _working_dir_for(server_id: str) -> str:
    # A single, predictable convention for where a server's persistent data
    # lives on its node — the daemon bind-mounts this path into the
    # container (see umbrella-daemon's toHostConfig). Kept here, not
    # duplicated at each call site.
    return f"/srv/umbrella/servers/{server_id}"


class ServerService:
    @staticmethod
    async def create_server(
        db: AsyncSession,
        name: str,
        node_id: str,
        template_id: str,
        allocation_ids: list[str],
        env_overrides: dict[str, str] | None = None,
        memory_bytes: int | None = None,
        cpu_cores: float | None = None,
        daemon_client: DaemonClient | None = None,
    ) -> Server:
        node = await NodeService.get_node(db, node_id)
        template = await ServerTemplateService.get_template(db, template_id)

        if not allocation_ids:
            raise ServerError("at least one allocation is required to create a server")

        allocations: list[Allocation] = []
        for allocation_id in allocation_ids:
            allocation = await AllocationService.get_allocation(db, allocation_id)
            if allocation.node_id != node_id:
                raise ServerError(
                    f"allocation {allocation_id!r} belongs to a different node than {node_id!r}"
                )
            if allocation.server_id is not None:
                raise ServerError(f"allocation {allocation_id!r} is already in use")
            allocations.append(allocation)

        server_id = str(uuid.uuid4())
        server = Server(
            id=server_id,
            name=name,
            node_id=node_id,
            template_id=template_id,
            template_version=template.version,
            status="unknown",
            working_dir=_working_dir_for(server_id),
            env_overrides=env_overrides or {},
            memory_bytes=memory_bytes or template.default_memory_bytes,
            cpu_cores=cpu_cores or template.default_cpu_cores,
        )
        db.add(server)
        await db.flush()

        for allocation in allocations:
            allocation.server_id = server_id
            # The first allocation's port doubles as the primary game port
            # inside the container (25565 for Minecraft's default) unless a
            # template specifies otherwise — Phase 2 keeps this convention
            # simple; per-allocation container-port mapping beyond "same
            # port number inside and out" is a real gap, noted in
            # docs/adr/0003-hosting-domain.md rather than silently assumed
            # to be handled.
            allocation.container_port = allocation.port
        await db.flush()

        client = daemon_client or DaemonClient(node.daemon_url, node.id, NodeService.decrypted_signing_secret(node))
        merged_env = {**template.default_env, **(env_overrides or {})}
        port_bindings = [
            {"container_port": a.container_port, "host_port": a.port, "protocol": a.protocol}
            for a in allocations
        ]

        try:
            state = await client.create(
                server_id,
                image=template.image,
                working_dir=server.working_dir,
                memory_bytes=server.memory_bytes,
                cpu_cores=server.cpu_cores,
                command=template.startup_command,
                env=merged_env,
                port_bindings=port_bindings,
            )
        except DaemonError as exc:
            # The Server row and its allocation bindings are part of the
            # same transaction as everything above (see conftest-style
            # per-request session usage) — the caller's transaction
            # rollback on this exception undoes the reservation too, so a
            # failed daemon call doesn't leave a half-created Server behind.
            raise ServerError(f"failed to create container on node {node.name!r}: {exc}", 502) from exc

        server.status = state.status
        await db.flush()
        return server

    @staticmethod
    async def get_server(db: AsyncSession, server_id: str) -> Server:
        server = await db.get(Server, server_id)
        if server is None:
            raise ServerError(f"no server with id {server_id!r}", 404)
        return server

    @staticmethod
    async def list_servers(db: AsyncSession, node_id: str | None = None) -> list[Server]:
        query = select(Server).order_by(Server.name)
        if node_id:
            query = query.where(Server.node_id == node_id)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def client_for(db: AsyncSession, server: Server, daemon_client: DaemonClient | None) -> DaemonClient:
        """
        Public (not module-private) because services/backup_service.py
        needs the exact same "use the injected client if given, otherwise
        build a real one from the server's node" logic — promoted here
        rather than duplicated, once a second real caller needed it.
        """
        if daemon_client is not None:
            return daemon_client
        node = await NodeService.get_node(db, server.node_id)
        return DaemonClient(node.daemon_url, node.id, NodeService.decrypted_signing_secret(node))

    @staticmethod
    async def start_server(db: AsyncSession, server_id: str, daemon_client: DaemonClient | None = None) -> Server:
        server = await ServerService.get_server(db, server_id)
        client = await ServerService.client_for(db, server, daemon_client)
        try:
            state = await client.start(server_id)
        except DaemonError as exc:
            raise ServerError(f"failed to start server: {exc}", 502) from exc
        server.status = state.status
        server.last_started_at = datetime.now(timezone.utc)
        # An operator explicitly starting the server resets the
        # consecutive-crash counter — see reconcile_server's docstring on
        # why crash_count tracks *consecutive, unattended* crashes rather
        # than a lifetime tally.
        server.crash_count = 0
        await db.flush()
        return server

    @staticmethod
    async def stop_server(
        db: AsyncSession,
        server_id: str,
        grace_period_seconds: int | None = None,
        daemon_client: DaemonClient | None = None,
    ) -> Server:
        server = await ServerService.get_server(db, server_id)
        client = await ServerService.client_for(db, server, daemon_client)
        try:
            state = await client.stop(server_id, grace_period_seconds=grace_period_seconds)
        except DaemonError as exc:
            raise ServerError(f"failed to stop server: {exc}", 502) from exc
        server.status = state.status
        await db.flush()
        return server

    @staticmethod
    async def restart_server(db: AsyncSession, server_id: str, daemon_client: DaemonClient | None = None) -> Server:
        server = await ServerService.get_server(db, server_id)
        client = await ServerService.client_for(db, server, daemon_client)
        try:
            state = await client.restart(server_id)
        except DaemonError as exc:
            raise ServerError(f"failed to restart server: {exc}", 502) from exc
        server.status = state.status
        server.last_started_at = datetime.now(timezone.utc)
        server.crash_count = 0
        await db.flush()
        return server

    @staticmethod
    async def kill_server(db: AsyncSession, server_id: str, daemon_client: DaemonClient | None = None) -> Server:
        server = await ServerService.get_server(db, server_id)
        client = await ServerService.client_for(db, server, daemon_client)
        try:
            state = await client.kill(server_id)
        except DaemonError as exc:
            raise ServerError(f"failed to kill server: {exc}", 502) from exc
        server.status = state.status
        await db.flush()
        return server

    @staticmethod
    async def get_stats(db: AsyncSession, server_id: str, daemon_client: DaemonClient | None = None):
        server = await ServerService.get_server(db, server_id)
        client = await ServerService.client_for(db, server, daemon_client)
        try:
            return await client.stats(server_id)
        except DaemonError as exc:
            raise ServerError(f"failed to fetch stats: {exc}", 502) from exc

    @staticmethod
    async def delete_server(db: AsyncSession, server_id: str, daemon_client: DaemonClient | None = None) -> None:
        server = await ServerService.get_server(db, server_id)
        client = await ServerService.client_for(db, server, daemon_client)
        try:
            await client.remove(server_id)
        except DaemonError as exc:
            raise ServerError(f"failed to remove container: {exc}", 502) from exc

        result = await db.execute(select(Allocation).where(Allocation.server_id == server_id))
        for allocation in result.scalars().all():
            allocation.server_id = None
            allocation.container_port = None

        await db.delete(server)
        await db.flush()

    # --------------------------------------------------------------------
    # Self-healing (Phase 4)
    # --------------------------------------------------------------------

    # After this many consecutive, unattended crashes, a server is
    # suspended rather than restarted again — an unbounded restart loop
    # (a genuinely broken plugin, corrupted world, or misconfiguration)
    # would otherwise burn resources forever and page nobody, since each
    # individual restart "succeeds" from the daemon's point of view even
    # though the server immediately crashes again. Suspension forces a
    # human to look at it.
    MAX_CONSECUTIVE_CRASHES_BEFORE_SUSPEND = 3

    @staticmethod
    async def reconcile_server(
        db: AsyncSession, server_id: str, daemon_client: DaemonClient | None = None
    ) -> tuple[Server, bool]:
        """
        Compare a server's actual daemon-reported state against what
        UmbrellaOS last recorded, and restart it if it has crashed —
        exactly the composition-over-bespoke-system pattern the ecosystem
        roadmap called for: this is a normal capability
        (`hosting.server.reconcile`), schedulable like any other via
        `automation.schedule.create`, not a separate always-on watchdog
        process with its own code path.

        Suspended servers are never touched here — suspension means "a
        human needs to look at this," and reconciliation silently
        restarting a suspended server would defeat that entirely.

        Returns (server, crash_detected_this_call) — the bool is an
        explicit signal for *this specific call*, not something callers
        have to infer from persisted fields like crash_count/last_crash_at,
        which reflect history across every past reconcile tick, not just
        this one.
        """
        server = await ServerService.get_server(db, server_id)
        if server.is_suspended:
            return server, False

        client = await ServerService.client_for(db, server, daemon_client)
        try:
            state = await client.state(server_id)
        except DaemonError:
            # Can't reach the daemon right now — nothing to reconcile
            # against; leave the server's recorded state as-is rather than
            # guessing. The next reconcile tick tries again.
            return server, False

        if state.status != "crashed":
            server.status = state.status
            await db.flush()
            return server, False

        server.crash_count += 1
        server.last_crash_at = datetime.now(timezone.utc)
        server.status = state.status

        if server.crash_count > ServerService.MAX_CONSECUTIVE_CRASHES_BEFORE_SUSPEND:
            server.is_suspended = True
            await db.flush()
            return server, True

        try:
            restarted_state = await client.start(server_id)
            server.status = restarted_state.status
            server.last_started_at = datetime.now(timezone.utc)
        except DaemonError:
            # The restart attempt itself failed — crash_count is already
            # incremented, so the next reconcile tick will try again (or
            # eventually suspend, if this keeps happening).
            pass

        await db.flush()
        return server, True

    @staticmethod
    async def reconcile_fleet(db: AsyncSession, daemon_client: DaemonClient | None = None) -> list[str]:
        """Reconcile every non-suspended server. Returns the IDs of
        servers found freshly crashed *in this call* (whether or not the
        restart attempt succeeded) — one server's daemon being
        unreachable does not stop the rest of the fleet from being
        reconciled."""
        servers = await ServerService.list_servers(db)
        crashed: list[str] = []
        for server in servers:
            if server.is_suspended:
                continue
            _, crash_detected = await ServerService.reconcile_server(db, server.id, daemon_client=daemon_client)
            if crash_detected:
                crashed.append(server.id)
        return crashed
