"""
models/hosting.py — Phase 2's hosting domain: Node, ServerTemplate,
Allocation, Server.

This is UmbrellaOS's first Docker-orchestrated, multi-server, multi-node
domain, distinct from the pre-existing `server_control_service.py` (a
single-server, non-containerized, shell-command-based control path built
for the original single-server UmbrellaMC deployment model). The two are
not in conflict — `server_control_service.py` is untouched and still valid
for anyone not on the Docker/daemon model — but they are genuinely
different mechanisms, not two implementations of the same thing; see
docs/adr/0003-hosting-domain.md for the explicit reasoning on why this
phase doesn't attempt to unify or migrate the legacy path now.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.engine import Base


class Node(Base):
    """A host running umbrella-daemon, capable of running one or more Servers."""

    __tablename__ = "nodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    daemon_url: Mapped[str] = mapped_column(
        String(256), nullable=False, doc="Base URL of this node's umbrella-daemon, e.g. https://node1.example.com:8443"
    )

    # The shared secret this node was registered with — used to verify the
    # node tokens it presents on every daemon request (see
    # services/node_auth_service.py). Stored as-is in Phase 2; encryption
    # at rest for secrets generally is Phase 4's explicit scope (see the
    # master roadmap), not something this phase fakes a partial version of.
    signing_secret: Mapped[str] = mapped_column(String(256), nullable=False)

    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", server_default="pending"
    )  # pending | online | offline | draining
    labels: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    allocations: Mapped[list["Allocation"]] = relationship(
        "Allocation", back_populates="node", cascade="all, delete-orphan"
    )
    servers: Mapped[list["Server"]] = relationship("Server", back_populates="node")

    def __repr__(self) -> str:
        return f"<Node id={self.id!r} name={self.name!r} status={self.status!r}>"


class ServerTemplate(Base):
    """
    A versioned server template ("egg" in Pterodactyl's terminology) — the
    image, default startup command, and default environment a Server is
    created from.

    Versioned explicitly (`version` on the template, `template_version`
    captured on each Server at creation time) so editing a template later
    never silently changes what an already-running Server does — matching
    the master roadmap's requirement that a template update doesn't break
    existing servers.
    """

    __tablename__ = "server_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")

    image: Mapped[str] = mapped_column(String(256), nullable=False)
    startup_command: Mapped[list] = mapped_column(JSON, nullable=False, default=list, server_default="[]")
    default_env: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")

    default_memory_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=1_073_741_824)
    default_cpu_cores: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    servers: Mapped[list["Server"]] = relationship("Server", back_populates="template")

    def __repr__(self) -> str:
        return f"<ServerTemplate id={self.id!r} name={self.name!r} version={self.version}>"


class Allocation(Base):
    """One port on one node — either free, or bound to a Server."""

    __tablename__ = "allocations"
    __table_args__ = (UniqueConstraint("node_id", "port", "protocol", name="uq_allocation_node_port_protocol"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    node_id: Mapped[str] = mapped_column(String(36), ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    protocol: Mapped[str] = mapped_column(String(8), nullable=False, default="tcp", server_default="tcp")

    server_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("servers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    container_port: Mapped[int | None] = mapped_column(
        Integer, nullable=True, doc="The port inside the container this host port maps to, once bound to a Server."
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    node: Mapped["Node"] = relationship("Node", back_populates="allocations")
    server: Mapped["Server | None"] = relationship("Server", back_populates="allocations")

    def __repr__(self) -> str:
        return f"<Allocation node_id={self.node_id!r} port={self.port} protocol={self.protocol!r}>"


class Server(Base):
    """One Minecraft server instance — one container on one node."""

    __tablename__ = "servers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(128), nullable=False)

    node_id: Mapped[str] = mapped_column(String(36), ForeignKey("nodes.id", ondelete="RESTRICT"), nullable=False, index=True)
    template_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("server_templates.id", ondelete="RESTRICT"), nullable=False
    )
    template_version: Mapped[int] = mapped_column(
        Integer, nullable=False, doc="ServerTemplate.version at the time this Server was created — pinned, not live."
    )

    # Runtime-agnostic status, mirrors environment.ContainerStatus's string
    # values on the daemon side (created/starting/running/stopping/stopped/
    # crashed/removed/unknown) — kept as a plain string here (not a shared
    # enum type across the Go/Python boundary) since the two are separate
    # processes; the *string values* are the contract, documented in
    # docs/adr/0003-hosting-domain.md, not a shared code artifact.
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="unknown", server_default="unknown")

    working_dir: Mapped[str] = mapped_column(String(512), nullable=False)
    env_overrides: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    memory_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    cpu_cores: Mapped[float] = mapped_column(Float, nullable=False)

    is_suspended: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    # Self-healing (Phase 4). crash_count resets to 0 on any
    # operator-initiated start/restart — it only tracks *consecutive*
    # unattended crashes, which is what should drive escalating backoff,
    # not a lifetime crash tally that would eventually suspend a
    # perfectly healthy server that happened to crash once months ago.
    crash_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_crash_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    node: Mapped["Node"] = relationship("Node", back_populates="servers")
    template: Mapped["ServerTemplate"] = relationship("ServerTemplate", back_populates="servers")
    allocations: Mapped[list["Allocation"]] = relationship("Allocation", back_populates="server")

    def __repr__(self) -> str:
        return f"<Server id={self.id!r} name={self.name!r} status={self.status!r}>"


class Backup(Base):
    """
    One backup archive of a Server's working directory, Phase 4.

    Metadata lives here in umbrella-core (which backup exists, its status,
    when it was taken); the archive bytes themselves live on the server's
    node, created/restored by umbrella-daemon's internal/backup package —
    matching the same "core owns metadata/scheduling, daemon executes"
    split established for hosting generally since Phase 2.
    """

    __tablename__ = "backups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    server_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("servers.id", ondelete="CASCADE"), nullable=False, index=True
    )

    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", server_default="pending")
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Python-side default (not server_default=func.now()) deliberately:
    # SQLite's CURRENT_TIMESTAMP is second-resolution, which made two
    # backups created in the same second genuinely unorderable by
    # timestamp alone — a real bug caught by a test, not by inspection
    # (see BackupService.list_backups). Python's datetime.now() carries
    # microsecond resolution and is computed at object-construction time,
    # not DB-insert time, which is precise enough that two backups from
    # separate service calls essentially never collide — a fix that works
    # identically on SQLite and Postgres rather than relying on either
    # engine's specific timestamp precision.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    server: Mapped["Server"] = relationship("Server")

    def __repr__(self) -> str:
        return f"<Backup id={self.id!r} server_id={self.server_id!r} status={self.status!r}>"
