"""
services/roles_service.py — Role and permission management.

Seeds default roles and permissions on first boot.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from models.permissions import Role, Permission
from models import User

# Seed data: (permission_key, description)
DEFAULT_PERMISSIONS = [
    ("players.view",         "View player records"),
    ("players.manage",       "Create and edit player records"),
    ("punishments.view",     "View punishments"),
    ("punishments.create",   "Create punishments"),
    ("punishments.revoke",   "Revoke punishments"),
    ("appeals.view",         "View appeals"),
    ("appeals.manage",       "Review and manage appeals"),
    ("moderation.kick",      "Kick players from the server"),
    ("moderation.warn",      "Warn players"),
    ("moderation.ban",       "Ban and unban players"),
    ("moderation.ipban",     "IP ban and unban addresses"),
    ("settings.view",        "View server settings"),
    ("settings.manage",      "Edit server settings"),
    ("audit.view",           "View the audit log"),
    ("roles.manage",         "Manage roles and permissions"),
    ("server.control",       "Start, stop, restart servers and maintenance mode"),
    # Phase 2 hosting domain — deliberately namespaced under "hosting.*",
    # distinct from the legacy "server.control" above (which belongs to
    # the pre-existing single-server, non-containerized control path in
    # services/server_control_service.py). The two are different
    # mechanisms; see docs/adr/0003-hosting-domain.md.
    ("hosting.node.view",       "View registered hosting nodes"),
    ("hosting.node.manage",     "Register and manage hosting nodes"),
    ("hosting.template.view",   "View server templates"),
    ("hosting.template.manage", "Create and edit server templates"),
    ("hosting.allocation.view",   "View port allocations"),
    ("hosting.allocation.manage", "Reserve and release port allocations"),
    ("hosting.server.view",    "View hosted server state and stats"),
    ("hosting.server.control", "Start, stop, restart, and kill hosted servers"),
    ("hosting.server.manage",  "Create and delete hosted servers"),
    ("hosting.backup.view",   "View server backups"),
    ("hosting.backup.manage", "Create, restore, and delete server backups"),
    ("automation.schedule.view",   "View scheduled automation tasks"),
    ("automation.schedule.manage", "Create, enable/disable, and delete scheduled automation tasks"),
    ("identity.apikey.manage", "Create, list, and revoke API keys"),
    # Discord-side AI moderation intelligence (Phase 5) — deliberately
    # namespaced under "moderation_intelligence.*", distinct from the
    # pre-existing "moderation.*" keys above, which govern the
    # Minecraft-side, player.uuid-keyed Punishment system. These are two
    # unrelated domains (Discord users vs. Minecraft players) that would
    # otherwise collide under the same permission key.
    ("moderation_intelligence.report.view", "View AI moderation reports and analyses"),
    ("moderation_intelligence.report.manage", "Create moderation reports and trigger AI analysis"),
    ("moderation_intelligence.escalation.view", "View staff escalations"),
    ("moderation_intelligence.escalation.manage", "Resolve staff escalations"),
    ("investigation.run", "Run investigation tools and the aggregate investigator"),
    ("investigation.view", "View past investigations"),
    ("knowledge.entry.manage", "Index knowledge entries and propose corrections"),
    ("knowledge.entry.search", "Search the knowledge base"),
    ("knowledge.correction.review", "Approve or reject proposed knowledge corrections"),
    ("archive.search", "Search all archived chat history (Minecraft and Discord, unfiltered by channel)"),
    ("memory.manage", "Read and write server facts, conversation context, and operational memory"),
    ("operational_intelligence.view", "View predictive crash-risk assessments and operational queries"),
    ("player_risk.view", "View unified player risk scores"),
    # Deliberately its own namespace, not reusing "players.view"/"players.manage"
    # (which also gate the full /players CRUD API and are owner/admin-only —
    # see DEFAULT_ROLES below). verification.confirm is a routine,
    # high-frequency machine action (the Discord bot calls it once per
    # player who DMs a code), so it needs a narrowly-scoped permission an
    # API key can be granted on its own, independent of the broader
    # player-record-editing permission.
    ("verification.link.view", "Check a player's Discord verification link status"),
    ("verification.link.manage", "Confirm verification codes, linking Discord accounts to Minecraft players"),
    # Phase 7 item 2 — webhook subscription CRUD. Deliberately its own
    # namespace, not reusing "identity.apikey.manage": a key admin and a
    # webhook admin are not necessarily the same responsibility, and
    # keeping them separate lets a role be scoped to one without the
    # other. view/manage split matches the identity.apikey.manage
    # single-permission-per-domain size for now — this domain is small
    # enough (4 capabilities) that view vs manage covers it without
    # needing finer splitting the way moderation_intelligence.* has.
    ("webhooks.subscription.view", "View registered webhook subscriptions"),
    ("webhooks.subscription.manage", "Create, update, and delete webhook subscriptions"),
    # Phase 7 item 3 — marketplace plugin listings/installs, the final
    # handoff item. Split into two axes (listing vs install), not one
    # "marketplace.manage": publishing new plugin *code* to the catalog
    # and installing already-published code onto *this* running instance
    # are different levels of trust — an admin might want to let someone
    # curate the catalog without also being able to run arbitrary
    # (sandboxed) code on this instance, or vice versa. Same posture as
    # webhooks.* above: an ops/platform concern, not something any
    # narrower moderation-focused role needs by default — see DEFAULT_ROLES.
    ("marketplace.listing.view", "View marketplace plugin listings and published version history"),
    ("marketplace.listing.manage", "Publish new plugin listings and versions to the marketplace"),
    ("marketplace.install.view", "View installed plugins and their registered Discord commands/dashboard UI slots"),
    ("marketplace.install.manage", "Install, update, and uninstall plugins on this instance"),
    # Phase 9 — observability/security hardening. Deliberately its own
    # namespace rather than folding into "audit.view": the audit log is
    # an append-only record of *actions taken through this platform*,
    # while logs/security events are operational telemetry about the
    # platform's own runtime behavior — a different concern an ops-focused
    # role might need without also getting audit-log access, or vice versa.
    ("observability.logs.view", "Search aggregated core log records"),
    ("security.events.view", "View recorded security events and threat-detection alerts"),
    # Phase 8 completion — plugin debugger/profiler/sandbox visualizer.
    # Deliberately its own namespace rather than reusing
    # "marketplace.install.view": that permission gates *discovery* of
    # what's installed (install list, discord commands, dashboard slots),
    # while this gates visibility into a plugin's actual sandboxed
    # execution history/telemetry — a materially more sensitive read (an
    # execution's error detail can include a plugin's own uncaught
    # exception text, which may reflect its internal logic/data in a way
    # "what's installed" doesn't). One permission for the whole read
    # surface (execution_history/execution_detail/profile/limits) since
    # all four are views over the same telemetry, same "view vs manage"
    # granularity every other domain here uses when there's no write side
    # yet — there is no write side to this domain at all, a plugin's
    # execution records are platform-authored, not admin-editable.
    ("plugin.sandbox.view", "View plugin sandbox execution history, telemetry, and resource limits"),
]

ALL_PERMISSION_KEYS = [p[0] for p in DEFAULT_PERMISSIONS]

# Seed data: (role_name, description, [permission_keys])
DEFAULT_ROLES = [
    ("owner", "Full access to everything", ALL_PERMISSION_KEYS),
    ("admin", "Full access except role management",
     [p for p in ALL_PERMISSION_KEYS if p != "roles.manage"]),
    ("moderator", "Moderation access",
     ["players.view", "punishments.view", "punishments.create", "punishments.revoke",
      "moderation.kick", "moderation.warn", "moderation.ban", "moderation.ipban",
      "appeals.view", "appeals.manage",
      "moderation_intelligence.report.view", "moderation_intelligence.report.manage",
      "moderation_intelligence.escalation.view", "moderation_intelligence.escalation.manage",
      "investigation.run", "investigation.view",
      "knowledge.entry.manage", "knowledge.entry.search", "knowledge.correction.review",
      "archive.search", "memory.manage", "operational_intelligence.view", "player_risk.view",
      "verification.link.view", "verification.link.manage"]),
    ("helper", "Basic helper access",
     ["players.view", "punishments.view", "appeals.view", "investigation.run", "investigation.view",
      "knowledge.entry.search", "verification.link.view"]),
    ("member", "Regular member",
     ["appeals.view"]),
]


class RolesService:

    @staticmethod
    async def seed_defaults(db: AsyncSession) -> None:
        """Seed default permissions and roles if they don't exist. Idempotent."""
        perm_map: dict[str, Permission] = {}
        for key, desc in DEFAULT_PERMISSIONS:
            perm = await db.scalar(
                select(Permission).where(Permission.permission_key == key)
            )
            if perm is None:
                perm = Permission(permission_key=key, description=desc)
                db.add(perm)
                await db.flush()
            perm_map[key] = perm

        for role_name, role_desc, perm_keys in DEFAULT_ROLES:
            role = await db.scalar(
                select(Role).where(Role.name == role_name).options(selectinload(Role.permissions))
            )
            if role is None:
                role = Role(name=role_name, description=role_desc)
                role.permissions = [perm_map[k] for k in perm_keys if k in perm_map]
                db.add(role)

        await db.commit()

    @staticmethod
    async def get_all(db: AsyncSession) -> list[dict]:
        counts = dict(
            (await db.execute(
                select(Role.name, func.count(User.id)).join(User, User.role_id == Role.id).group_by(Role.name)
            )).all()
        )
        result = await db.execute(
            select(Role).options(selectinload(Role.permissions)).order_by(Role.name)
        )
        return [
            {**RolesService._to_dict(r), "member_count": counts.get(r.name, 0)}
            for r in result.scalars().all()
        ]

    @staticmethod
    async def get_all_permissions(db: AsyncSession) -> list[dict]:
        result = await db.execute(select(Permission).order_by(Permission.permission_key))
        return [{"id": p.id, "key": p.permission_key, "description": p.description}
                for p in result.scalars().all()]

    @staticmethod
    def _to_dict(role: Role) -> dict:
        return {
            "id": role.id,
            "name": role.name,
            "description": role.description,
            "permissions": [p.permission_key for p in role.permissions],
            "created_at": role.created_at.isoformat() if role.created_at else None,
        }
