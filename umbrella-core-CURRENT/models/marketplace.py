"""
models/marketplace.py — Marketplace plugin listings/versions and per-instance
installs (Phase 7 item 3, final item).

Three tables, deliberately kept separate rather than folded together,
because they answer three different questions:

- PluginListing: "what plugins exist in the marketplace catalog" — one row
  per plugin_id, updated as new versions publish.
- PluginVersion: "what versions of a plugin have ever been published, and
  what's the source-of-truth manifest/hash for each" — append-only, never
  mutated after publish. A fix ships as a new version, not an edit to an
  old row; this is what makes sha256_hash a durable integrity anchor
  rather than something that could drift out from under an already-issued
  hash.
- PluginInstall: "what's actually active on this instance right now" — at
  most one row per plugin_id (single-install-per-plugin model; installing
  a different version overwrites this row rather than adding a second
  one, matching the "explicit admin action to update, no side-by-side
  versions" decision). Carries a denormalized snapshot of the manifest it
  was installed from (so capabilities/marketplace.py's discord-command/
  dashboard-slot discovery capabilities can read it directly, without
  re-touching PluginVersion or re-extracting the zip on every request)
  plus the exact list of capability names `register_plugin_capabilities`
  returned, so uninstall/update can unregister precisely what was
  registered — see services/plugins/marketplace_service.py.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.engine import Base
from models.user import User  # noqa: F401 - resolves the "User" forward reference below


class PluginListing(Base):
    __tablename__ = "plugin_listings"

    plugin_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    author: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")

    # Denormalized convenience pointer to the newest published version —
    # PluginVersion remains the source of truth for the full history;
    # this just saves every listing-browse query a join.
    latest_version: Mapped[str] = mapped_column(String(64), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    versions: Mapped[list["PluginVersion"]] = relationship(
        "PluginVersion", back_populates="listing", order_by="PluginVersion.published_at"
    )

    def __repr__(self) -> str:
        return f"<PluginListing plugin_id={self.plugin_id!r} latest_version={self.latest_version!r}>"


class PluginVersion(Base):
    __tablename__ = "plugin_versions"
    __table_args__ = (
        UniqueConstraint("plugin_id", "version", name="uq_plugin_versions_plugin_id_version"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plugin_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("plugin_listings.plugin_id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[str] = mapped_column(String(64), nullable=False)

    # The exact plugin.json body this version was published with, as
    # validated JSON text — re-parsed via services.plugins.manifest
    # .parse_manifest() wherever it's needed again (install, discovery),
    # rather than kept as a second, hand-maintained shape.
    manifest_json: Mapped[str] = mapped_column(Text, nullable=False)

    # SHA-256 of the published zip's raw bytes, hex-encoded. Computed at
    # publish time and re-verified against the stored zip at every install
    # (services/plugins/source_store.py) — the marketplace listing is the
    # thing an install is trusted against, so this hash has to be captured
    # at the moment of publish, not re-derived later from a file that
    # could itself have been tampered with.
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Path to the stored zip, relative to settings.plugin_storage_root —
    # e.g. "queue-tools/1.0.0/plugin.zip". Never an absolute path: keeps
    # the DB portable across a storage-root relocation.
    zip_path: Mapped[str] = mapped_column(String(512), nullable=False)

    published_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    listing: Mapped["PluginListing"] = relationship("PluginListing", back_populates="versions")
    publisher: Mapped["User | None"] = relationship("User")

    def __repr__(self) -> str:
        return f"<PluginVersion plugin_id={self.plugin_id!r} version={self.version!r}>"


class PluginInstall(Base):
    __tablename__ = "plugin_installs"

    plugin_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("plugin_listings.plugin_id", ondelete="CASCADE"), primary_key=True
    )
    installed_version: Mapped[str] = mapped_column(String(64), nullable=False)

    # Snapshot of the manifest this exact install/update ran with — see
    # module docstring for why this is denormalized rather than joined.
    manifest_json: Mapped[str] = mapped_column(Text, nullable=False)

    # Snapshot of the exact PluginVersion this install/update pointed at —
    # zip_path/sha256_hash, denormalized here for the same reason
    # manifest_json is: startup re-registration
    # (services/plugins/runtime.py::reload_installed_plugins) needs to
    # reload precisely what was installed without depending on a join to
    # a PluginVersion row that a future, unrelated change could otherwise
    # affect. PluginVersion itself remains append-only/immutable — these
    # are a copy of its values at install time, not a live reference.
    zip_path: Mapped[str] = mapped_column(String(512), nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Fully-qualified capability names (e.g. "plugin.queue-tools.queue_status")
    # that register_plugin_capabilities returned for this install. Read
    # back on uninstall/update to unregister exactly this set — see
    # services/plugins/marketplace_service.py.
    registered_capability_names: Mapped[list] = mapped_column(JSON, nullable=False, default=list, server_default="[]")

    installed_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    installed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    installer: Mapped["User | None"] = relationship("User")

    def __repr__(self) -> str:
        return f"<PluginInstall plugin_id={self.plugin_id!r} installed_version={self.installed_version!r}>"
