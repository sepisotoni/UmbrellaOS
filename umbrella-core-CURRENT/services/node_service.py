"""
services/node_service.py — Node registration and lifecycle.

A Node represents one host running umbrella-daemon. Registration issues a
signing secret (see services/node_auth_service.py) the operator configures
into that daemon's environment out-of-band — matching the "exchanged once,
never transmitted per-request" contract documented in umbrella-daemon's
ADR-0002.
"""
import secrets
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.errors import AppException
from models.hosting import Node
from services.secrets_service import decrypt_secret, encrypt_secret


class NodeError(AppException):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message, "NODE_ERROR", status_code)


class NodeService:
    @staticmethod
    async def register_node(
        db: AsyncSession,
        name: str,
        daemon_url: str,
        labels: dict | None = None,
    ) -> tuple[Node, str]:
        """
        Register a new node. Returns (node, plaintext_signing_secret) — the
        plaintext is what the operator copies into that node's daemon
        config; only its encrypted form (`node.signing_secret`) is ever
        persisted or read back from the database. Every other read of
        `node.signing_secret` from storage is ciphertext — decrypt via
        `NodeService.decrypted_signing_secret`, never by reading the
        column directly.
        """
        existing = await db.scalar(select(Node).where(Node.name == name))
        if existing is not None:
            raise NodeError(f"a node named {name!r} is already registered", 409)

        plaintext_secret = secrets.token_urlsafe(48)  # well over the 32-byte minimum both sides enforce
        node = Node(
            name=name,
            daemon_url=daemon_url,
            signing_secret=encrypt_secret(plaintext_secret),
            labels=labels or {},
            status="pending",
        )
        db.add(node)
        await db.flush()
        return node, plaintext_secret

    @staticmethod
    def decrypted_signing_secret(node: Node) -> str:
        """The one sanctioned way to get a node's real signing secret back
        — used only at the point DaemonClient is actually constructed
        (services/server_service.py), never held longer than that call."""
        return decrypt_secret(node.signing_secret)

    @staticmethod
    async def list_nodes(db: AsyncSession) -> list[Node]:
        result = await db.execute(select(Node).order_by(Node.name))
        return list(result.scalars().all())

    @staticmethod
    async def get_node(db: AsyncSession, node_id: str) -> Node:
        node = await db.get(Node, node_id)
        if node is None:
            raise NodeError(f"no node with id {node_id!r}", 404)
        return node

    @staticmethod
    async def mark_online(db: AsyncSession, node_id: str) -> Node:
        node = await NodeService.get_node(db, node_id)
        node.status = "online"
        node.last_seen_at = datetime.now(timezone.utc)
        await db.flush()
        return node

    @staticmethod
    async def mark_offline(db: AsyncSession, node_id: str) -> Node:
        node = await NodeService.get_node(db, node_id)
        node.status = "offline"
        await db.flush()
        return node
