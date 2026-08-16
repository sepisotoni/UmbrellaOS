"""
capabilities/hosting.py — Phase 2's hosting domain, exposed through the
Capability Registry. Every function here is a thin translation from a
CallContext + validated params into a call against the hosting services
(services/node_service.py, services/server_template_service.py,
services/allocation_service.py, services/server_service.py) — no business
logic lives in this file, matching capabilities/system.py's pattern from
Phase 0.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from registry.context import CallContext
from registry.decorator import capability
from services.allocation_service import AllocationService
from services.backup_service import BackupService
from services.node_service import NodeService
from services.server_service import ServerService
from services.server_template_service import ServerTemplateService

# --------------------------------------------------------------------------
# hosting.node.*
# --------------------------------------------------------------------------


class RegisterNodeParams(BaseModel):
    name: str
    daemon_url: str
    labels: dict[str, str] = Field(default_factory=dict)


class NodeResult(BaseModel):
    id: str
    name: str
    daemon_url: str
    status: str
    labels: dict
    signing_secret: str | None = None  # only populated on registration, and only with plaintext — see register_node

    @classmethod
    def from_model(cls, node) -> "NodeResult":
        return cls(
            id=node.id, name=node.name, daemon_url=node.daemon_url,
            status=node.status, labels=node.labels, signing_secret=None,
        )


@capability(
    name="hosting.node.register",
    summary="Register a new node and generate its daemon signing secret.",
    params_model=RegisterNodeParams,
    result_model=NodeResult,
    required_permission="hosting.node.manage",
    destructive=False,
    audit_category="hosting",
)
async def register_node(ctx: CallContext, params: RegisterNodeParams) -> NodeResult:
    """
    The returned `signing_secret` is shown exactly once, here, at
    registration — it must be copied into the node's
    `UMBRELLA_NODE_SIGNING_SECRET` environment variable immediately.
    `hosting.node.list`/`hosting.node.get` never include it. As of Phase 4,
    only the *encrypted* form is ever persisted (services/secrets_service.py)
    — this plaintext exists only transiently, in this response.
    """
    node, plaintext_secret = await NodeService.register_node(ctx.db, params.name, params.daemon_url, params.labels)
    result = NodeResult.from_model(node)
    result.signing_secret = plaintext_secret
    return result


class ListNodesParams(BaseModel):
    pass


@capability(
    name="hosting.node.list",
    summary="List every registered node.",
    params_model=ListNodesParams,
    result_model=list[NodeResult],
    required_permission="hosting.node.view",
    destructive=False,
    audited=False,
)
async def list_nodes(ctx: CallContext, params: ListNodesParams) -> list[NodeResult]:
    nodes = await NodeService.list_nodes(ctx.db)
    return [NodeResult.from_model(n) for n in nodes]


class GetNodeParams(BaseModel):
    node_id: str


@capability(
    name="hosting.node.get",
    summary="Get one node by ID.",
    params_model=GetNodeParams,
    result_model=NodeResult,
    required_permission="hosting.node.view",
    destructive=False,
    audited=False,
)
async def get_node(ctx: CallContext, params: GetNodeParams) -> NodeResult:
    node = await NodeService.get_node(ctx.db, params.node_id)
    return NodeResult.from_model(node)


# --------------------------------------------------------------------------
# hosting.template.*
# --------------------------------------------------------------------------


class CreateTemplateParams(BaseModel):
    name: str
    image: str
    description: str | None = None
    startup_command: list[str] = Field(default_factory=list)
    default_env: dict[str, str] = Field(default_factory=dict)
    default_memory_bytes: int = 1_073_741_824
    default_cpu_cores: float = 1.0


class TemplateResult(BaseModel):
    id: str
    name: str
    image: str
    version: int
    description: str | None
    startup_command: list[str]
    default_env: dict[str, str]
    default_memory_bytes: int
    default_cpu_cores: float

    @classmethod
    def from_model(cls, template) -> "TemplateResult":
        return cls(
            id=template.id, name=template.name, image=template.image, version=template.version,
            description=template.description, startup_command=template.startup_command,
            default_env=template.default_env, default_memory_bytes=template.default_memory_bytes,
            default_cpu_cores=template.default_cpu_cores,
        )


@capability(
    name="hosting.template.create",
    summary="Create a new server template.",
    params_model=CreateTemplateParams,
    result_model=TemplateResult,
    required_permission="hosting.template.manage",
    destructive=False,
    audit_category="hosting",
)
async def create_template(ctx: CallContext, params: CreateTemplateParams) -> TemplateResult:
    template = await ServerTemplateService.create_template(
        ctx.db, params.name, params.image,
        description=params.description, startup_command=params.startup_command,
        default_env=params.default_env, default_memory_bytes=params.default_memory_bytes,
        default_cpu_cores=params.default_cpu_cores,
    )
    return TemplateResult.from_model(template)


class ListTemplatesParams(BaseModel):
    pass


@capability(
    name="hosting.template.list",
    summary="List every server template.",
    params_model=ListTemplatesParams,
    result_model=list[TemplateResult],
    required_permission="hosting.template.view",
    destructive=False,
    audited=False,
)
async def list_templates(ctx: CallContext, params: ListTemplatesParams) -> list[TemplateResult]:
    templates = await ServerTemplateService.list_templates(ctx.db)
    return [TemplateResult.from_model(t) for t in templates]


# --------------------------------------------------------------------------
# hosting.allocation.*
# --------------------------------------------------------------------------


class CreateAllocationParams(BaseModel):
    node_id: str
    port: int = Field(ge=1, le=65535)
    protocol: str = "tcp"

    def audit_target(self) -> str:
        return self.node_id


class AllocationResult(BaseModel):
    id: str
    node_id: str
    port: int
    protocol: str
    server_id: str | None

    @classmethod
    def from_model(cls, allocation) -> "AllocationResult":
        return cls(
            id=allocation.id, node_id=allocation.node_id, port=allocation.port,
            protocol=allocation.protocol, server_id=allocation.server_id,
        )


@capability(
    name="hosting.allocation.create",
    summary="Reserve a port on a node for future server assignment.",
    params_model=CreateAllocationParams,
    result_model=AllocationResult,
    required_permission="hosting.allocation.manage",
    destructive=False,
    audit_category="hosting",
)
async def create_allocation(ctx: CallContext, params: CreateAllocationParams) -> AllocationResult:
    allocation = await AllocationService.create_allocation(ctx.db, params.node_id, params.port, params.protocol)
    return AllocationResult.from_model(allocation)


class ListFreeAllocationsParams(BaseModel):
    node_id: str


@capability(
    name="hosting.allocation.list_free",
    summary="List unassigned (free) allocations on a node.",
    params_model=ListFreeAllocationsParams,
    result_model=list[AllocationResult],
    required_permission="hosting.allocation.view",
    destructive=False,
    audited=False,
)
async def list_free_allocations(ctx: CallContext, params: ListFreeAllocationsParams) -> list[AllocationResult]:
    allocations = await AllocationService.list_free_allocations(ctx.db, params.node_id)
    return [AllocationResult.from_model(a) for a in allocations]


# --------------------------------------------------------------------------
# hosting.server.*
# --------------------------------------------------------------------------


class CreateServerParams(BaseModel):
    name: str
    node_id: str
    template_id: str
    allocation_ids: list[str] = Field(min_length=1)
    env_overrides: dict[str, str] = Field(default_factory=dict)
    memory_bytes: int | None = None
    cpu_cores: float | None = None

    def audit_target(self) -> str:
        return self.name


class ServerResult(BaseModel):
    id: str
    name: str
    node_id: str
    template_id: str
    template_version: int
    status: str
    memory_bytes: int
    cpu_cores: float

    @classmethod
    def from_model(cls, server) -> "ServerResult":
        return cls(
            id=server.id, name=server.name, node_id=server.node_id, template_id=server.template_id,
            template_version=server.template_version, status=server.status,
            memory_bytes=server.memory_bytes, cpu_cores=server.cpu_cores,
        )


@capability(
    name="hosting.server.create",
    summary="Create a new server from a template, on a node, with one or more allocations.",
    params_model=CreateServerParams,
    result_model=ServerResult,
    required_permission="hosting.server.manage",
    destructive=False,
    reversible=True,
    audit_category="hosting",
)
async def create_server(ctx: CallContext, params: CreateServerParams) -> ServerResult:
    server = await ServerService.create_server(
        ctx.db, params.name, params.node_id, params.template_id, params.allocation_ids,
        env_overrides=params.env_overrides, memory_bytes=params.memory_bytes, cpu_cores=params.cpu_cores,
    )
    return ServerResult.from_model(server)


class ServerIDParams(BaseModel):
    server_id: str

    def audit_target(self) -> str:
        return self.server_id


@capability(
    name="hosting.server.get",
    summary="Get one server's current state.",
    params_model=ServerIDParams,
    result_model=ServerResult,
    required_permission="hosting.server.view",
    destructive=False,
    audited=False,
)
async def get_server(ctx: CallContext, params: ServerIDParams) -> ServerResult:
    server = await ServerService.get_server(ctx.db, params.server_id)
    return ServerResult.from_model(server)


class ListServersParams(BaseModel):
    node_id: str | None = None


@capability(
    name="hosting.server.list",
    summary="List servers, optionally filtered to one node.",
    params_model=ListServersParams,
    result_model=list[ServerResult],
    required_permission="hosting.server.view",
    destructive=False,
    audited=False,
)
async def list_servers(ctx: CallContext, params: ListServersParams) -> list[ServerResult]:
    servers = await ServerService.list_servers(ctx.db, params.node_id)
    return [ServerResult.from_model(s) for s in servers]


@capability(
    name="hosting.server.start",
    summary="Start a server.",
    params_model=ServerIDParams,
    result_model=ServerResult,
    required_permission="hosting.server.control",
    destructive=False,
    reversible=True,
    audit_category="hosting",
)
async def start_server(ctx: CallContext, params: ServerIDParams) -> ServerResult:
    server = await ServerService.start_server(ctx.db, params.server_id)
    return ServerResult.from_model(server)


class StopServerParams(BaseModel):
    server_id: str
    grace_period_seconds: int | None = None

    def audit_target(self) -> str:
        return self.server_id


@capability(
    name="hosting.server.stop",
    summary="Gracefully stop a server.",
    params_model=StopServerParams,
    result_model=ServerResult,
    required_permission="hosting.server.control",
    destructive=False,
    reversible=True,
    audit_category="hosting",
)
async def stop_server(ctx: CallContext, params: StopServerParams) -> ServerResult:
    server = await ServerService.stop_server(ctx.db, params.server_id, params.grace_period_seconds)
    return ServerResult.from_model(server)


@capability(
    name="hosting.server.restart",
    summary="Restart a server.",
    params_model=ServerIDParams,
    result_model=ServerResult,
    required_permission="hosting.server.control",
    destructive=True,
    reversible=False,  # a restart isn't undoable — see registry/decorator.py's own docstring example
    audit_category="hosting",
)
async def restart_server(ctx: CallContext, params: ServerIDParams) -> ServerResult:
    server = await ServerService.restart_server(ctx.db, params.server_id)
    return ServerResult.from_model(server)


@capability(
    name="hosting.server.kill",
    summary="Forcibly kill a server with no grace period.",
    params_model=ServerIDParams,
    result_model=ServerResult,
    required_permission="hosting.server.control",
    destructive=True,
    reversible=False,
    audit_category="hosting",
)
async def kill_server(ctx: CallContext, params: ServerIDParams) -> ServerResult:
    server = await ServerService.kill_server(ctx.db, params.server_id)
    return ServerResult.from_model(server)


class StatsResult(BaseModel):
    timestamp: str
    cpu_percent: float
    memory_used_bytes: int
    memory_limit_bytes: int
    network_rx_bytes: int
    network_tx_bytes: int


@capability(
    name="hosting.server.stats",
    summary="Fetch one live CPU/memory/network snapshot for a server.",
    params_model=ServerIDParams,
    result_model=StatsResult,
    required_permission="hosting.server.view",
    destructive=False,
    audited=False,
)
async def get_server_stats(ctx: CallContext, params: ServerIDParams) -> StatsResult:
    stats = await ServerService.get_stats(ctx.db, params.server_id)
    return StatsResult(
        timestamp=stats.timestamp, cpu_percent=stats.cpu_percent,
        memory_used_bytes=stats.memory_used_bytes, memory_limit_bytes=stats.memory_limit_bytes,
        network_rx_bytes=stats.network_rx_bytes, network_tx_bytes=stats.network_tx_bytes,
    )


class DeleteServerResult(BaseModel):
    deleted: bool


@capability(
    name="hosting.server.delete",
    summary="Remove a server's container and release its allocations permanently.",
    params_model=ServerIDParams,
    result_model=DeleteServerResult,
    required_permission="hosting.server.manage",
    destructive=True,
    reversible=False,
    audit_category="hosting",
)
async def delete_server(ctx: CallContext, params: ServerIDParams) -> DeleteServerResult:
    await ServerService.delete_server(ctx.db, params.server_id)
    return DeleteServerResult(deleted=True)


# --------------------------------------------------------------------------
# hosting.backup.* (Phase 4)
# --------------------------------------------------------------------------


class CreateBackupParams(BaseModel):
    server_id: str

    def audit_target(self) -> str:
        return self.server_id


class BackupResult(BaseModel):
    id: str
    server_id: str
    status: str
    size_bytes: int | None
    error_message: str | None
    created_at: str
    completed_at: str | None

    @classmethod
    def from_model(cls, backup) -> "BackupResult":
        return cls(
            id=backup.id, server_id=backup.server_id, status=backup.status,
            size_bytes=backup.size_bytes, error_message=backup.error_message,
            created_at=backup.created_at.isoformat() if backup.created_at else None,
            completed_at=backup.completed_at.isoformat() if backup.completed_at else None,
        )


@capability(
    name="hosting.backup.create",
    summary="Create a new backup of a server's working directory.",
    params_model=CreateBackupParams,
    result_model=BackupResult,
    required_permission="hosting.backup.manage",
    destructive=False,
    reversible=True,
    audit_category="hosting",
)
async def create_backup(ctx: CallContext, params: CreateBackupParams) -> BackupResult:
    backup = await BackupService.create_backup(ctx.db, params.server_id)
    return BackupResult.from_model(backup)


class ListBackupsParams(BaseModel):
    server_id: str


@capability(
    name="hosting.backup.list",
    summary="List every backup for a server, newest first.",
    params_model=ListBackupsParams,
    result_model=list[BackupResult],
    required_permission="hosting.backup.view",
    destructive=False,
    audited=False,
)
async def list_backups(ctx: CallContext, params: ListBackupsParams) -> list[BackupResult]:
    backups = await BackupService.list_backups(ctx.db, params.server_id)
    return [BackupResult.from_model(b) for b in backups]


class BackupIDParams(BaseModel):
    backup_id: str

    def audit_target(self) -> str:
        return self.backup_id


class RestoreBackupResult(BaseModel):
    restored: bool


@capability(
    name="hosting.backup.restore",
    summary="Restore a server's working directory from a completed backup. Stop the server first.",
    params_model=BackupIDParams,
    result_model=RestoreBackupResult,
    required_permission="hosting.backup.manage",
    destructive=True,
    reversible=False,
    audit_category="hosting",
)
async def restore_backup(ctx: CallContext, params: BackupIDParams) -> RestoreBackupResult:
    await BackupService.restore_backup(ctx.db, params.backup_id)
    return RestoreBackupResult(restored=True)


class DeleteBackupResult(BaseModel):
    deleted: bool


@capability(
    name="hosting.backup.delete",
    summary="Delete a backup archive permanently.",
    params_model=BackupIDParams,
    result_model=DeleteBackupResult,
    required_permission="hosting.backup.manage",
    destructive=True,
    reversible=False,
    audit_category="hosting",
)
async def delete_backup(ctx: CallContext, params: BackupIDParams) -> DeleteBackupResult:
    await BackupService.delete_backup(ctx.db, params.backup_id)
    return DeleteBackupResult(deleted=True)


# --------------------------------------------------------------------------
# hosting.server.reconcile / hosting.fleet.reconcile — self-healing (Phase 4)
# --------------------------------------------------------------------------


class ReconcileServerResult(BaseModel):
    server: ServerResult
    crash_detected: bool


@capability(
    name="hosting.server.reconcile",
    summary="Check a server's actual daemon-reported state and restart it if it has crashed.",
    params_model=ServerIDParams,
    result_model=ReconcileServerResult,
    required_permission="hosting.server.control",
    destructive=False,  # the restart it may trigger is an automated recovery action, not an operator command
    reversible=True,
    audit_category="hosting",
)
async def reconcile_server(ctx: CallContext, params: ServerIDParams) -> ReconcileServerResult:
    server, crash_detected = await ServerService.reconcile_server(ctx.db, params.server_id)
    return ReconcileServerResult(server=ServerResult.from_model(server), crash_detected=crash_detected)


class ReconcileFleetParams(BaseModel):
    pass


class ReconcileFleetResult(BaseModel):
    crashed_server_ids: list[str]


@capability(
    name="hosting.fleet.reconcile",
    summary=(
        "Reconcile every non-suspended server's actual state, restarting any that have crashed. "
        "This is what self-healing composes from — schedule it via automation.schedule.create "
        "(e.g. every minute) rather than relying on a separate always-on watchdog process."
    ),
    params_model=ReconcileFleetParams,
    result_model=ReconcileFleetResult,
    required_permission="hosting.server.control",
    destructive=False,
    reversible=True,
    audit_category="hosting",
)
async def reconcile_fleet(ctx: CallContext, params: ReconcileFleetParams) -> ReconcileFleetResult:
    crashed_ids = await ServerService.reconcile_fleet(ctx.db)
    return ReconcileFleetResult(crashed_server_ids=crashed_ids)
