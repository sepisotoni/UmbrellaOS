"""
services/daemon_client.py — umbrella-core's HTTP client for a node's
umbrella-daemon, over the API defined in umbrella-daemon's
internal/transport/ws_server.go.

This is the only place in umbrella-core that talks to a daemon directly —
hosting_service.py and friends call through this client rather than
constructing daemon URLs/requests themselves, so the daemon's actual wire
contract (paths, auth header, JSON shapes) is defined in exactly one place
on the core side, mirroring the same "one implementation" principle the
Capability Registry itself is built on.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from services.node_auth_service import issue_node_token


class DaemonError(Exception):
    """Raised for any failure communicating with a node's daemon."""

    def __init__(self, message: str, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(message)


@dataclass(frozen=True)
class ContainerState:
    """Mirrors umbrella-daemon's environment.ContainerState JSON shape."""

    server_id: str
    runtime_id: str
    status: str
    started_at: str | None
    finished_at: str | None
    exit_code: int | None
    oom_killed: bool

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "ContainerState":
        return cls(
            server_id=data.get("ServerID", ""),
            runtime_id=data.get("RuntimeID", ""),
            status=data.get("Status", "unknown"),
            started_at=data.get("StartedAt"),
            finished_at=data.get("FinishedAt"),
            exit_code=data.get("ExitCode"),
            oom_killed=bool(data.get("OOMKilled", False)),
        )


@dataclass(frozen=True)
class StatsSnapshot:
    """Mirrors umbrella-daemon's environment.StatsSnapshot JSON shape."""

    timestamp: str
    cpu_percent: float
    memory_used_bytes: int
    memory_limit_bytes: int
    network_rx_bytes: int
    network_tx_bytes: int

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "StatsSnapshot":
        return cls(
            timestamp=data.get("Timestamp", ""),
            cpu_percent=data.get("CPUPercent", 0.0),
            memory_used_bytes=data.get("MemoryUsedBytes", 0),
            memory_limit_bytes=data.get("MemoryLimitBytes", 0),
            network_rx_bytes=data.get("NetworkRxBytes", 0),
            network_tx_bytes=data.get("NetworkTxBytes", 0),
        )


class DaemonClient:
    """
    A client bound to one node. Short-lived by design — construct one per
    call (or per request) rather than holding a long-lived instance, since
    the node token it issues for itself is time-boxed (see
    services/node_auth_service.py) and there's no benefit to caching a
    client that would need to re-issue a token internally anyway.
    """

    def __init__(
        self,
        daemon_url: str,
        node_id: str,
        signing_secret: str,
        timeout: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ):
        self._base_url = daemon_url.rstrip("/")
        self._node_id = node_id
        self._signing_secret = signing_secret
        self._timeout = timeout
        # Injectable so tests can exercise this class's real request/error
        # handling logic against an httpx.MockTransport instead of a live
        # daemon, rather than monkeypatching private methods. None in
        # production, where httpx.AsyncClient uses its normal network
        # transport.
        self._transport = transport

    def _headers(self) -> dict[str, str]:
        token = issue_node_token(self._node_id, self._signing_secret)
        return {"Authorization": f"Bearer {token}"}

    async def _request(self, method: str, path: str, json: dict | None = None) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
                response = await client.request(method, url, headers=self._headers(), json=json)
        except httpx.RequestError as exc:
            raise DaemonError(f"could not reach daemon at {self._base_url}: {exc}") from exc

        if response.status_code >= 400:
            raise DaemonError(
                f"daemon returned {response.status_code} for {method} {path}: {response.text}",
                status_code=response.status_code,
            )
        if not response.content:
            return {}
        # FIX ([PLUGIN] subsystem audit): response.json() raises a raw
        # json.JSONDecodeError, unguarded, on malformed content — breaking
        # this class's own documented contract ("Raised for any failure
        # communicating with a node's daemon"). A daemon bug, or infra
        # returning an unexpected body on a 2xx status, would previously
        # surface as an unstructured JSONDecodeError instead of the
        # consistent DaemonError every caller of this class is written to
        # expect and catch.
        try:
            return response.json()
        except ValueError as exc:
            # httpx's JSONDecodeError subclasses the stdlib's, which
            # subclasses ValueError — catching the stdlib base keeps this
            # correct even if httpx changes its exact exception class.
            raise DaemonError(
                f"daemon returned malformed JSON for {method} {path}: {exc}",
                status_code=response.status_code,
            ) from exc

    async def create(
        self,
        server_id: str,
        image: str,
        working_dir: str,
        memory_bytes: int,
        cpu_cores: float,
        command: list[str] | None = None,
        env: dict[str, str] | None = None,
        disk_bytes: int = 0,
        port_bindings: list[dict[str, Any]] | None = None,
    ) -> ContainerState:
        """
        Create (but do not start) a server's container. `port_bindings` is
        a list of `{"container_port": int, "host_port": int, "protocol": "tcp"|"udp"}`
        dicts, matching the daemon's `createServerRequest` wire shape
        exactly (see umbrella-daemon's internal/transport/ws_server.go) —
        this method is the one place that shape is constructed on the core
        side.
        """
        body = {
            "image": image,
            "command": command or [],
            "env": env or {},
            "working_dir": working_dir,
            "memory_bytes": memory_bytes,
            "cpu_cores": cpu_cores,
            "disk_bytes": disk_bytes,
            "port_bindings": port_bindings or [],
        }
        data = await self._request("POST", f"/v1/servers/{server_id}", json=body)
        return ContainerState.from_json(data)

    async def remove(self, server_id: str) -> None:
        await self._request("DELETE", f"/v1/servers/{server_id}")

    async def start(self, server_id: str) -> ContainerState:
        data = await self._request("POST", f"/v1/servers/{server_id}/start")
        return ContainerState.from_json(data)

    async def stop(self, server_id: str, grace_period_seconds: int | None = None) -> ContainerState:
        body = {"grace_period_seconds": grace_period_seconds} if grace_period_seconds is not None else None
        data = await self._request("POST", f"/v1/servers/{server_id}/stop", json=body)
        return ContainerState.from_json(data)

    async def kill(self, server_id: str) -> ContainerState:
        data = await self._request("POST", f"/v1/servers/{server_id}/kill")
        return ContainerState.from_json(data)

    async def restart(self, server_id: str) -> ContainerState:
        data = await self._request("POST", f"/v1/servers/{server_id}/restart")
        return ContainerState.from_json(data)

    async def state(self, server_id: str) -> ContainerState:
        data = await self._request("GET", f"/v1/servers/{server_id}/state")
        return ContainerState.from_json(data)

    async def stats(self, server_id: str) -> StatsSnapshot:
        data = await self._request("GET", f"/v1/servers/{server_id}/stats")
        return StatsSnapshot.from_json(data)

    async def create_backup(self, server_id: str, backup_id: str) -> int:
        """Returns the archive's size in bytes."""
        data = await self._request("POST", f"/v1/servers/{server_id}/backups", json={"backup_id": backup_id})
        return data.get("size_bytes", 0)

    async def restore_backup(self, server_id: str, backup_id: str) -> None:
        await self._request("POST", f"/v1/servers/{server_id}/backups/{backup_id}/restore")

    async def delete_backup(self, server_id: str, backup_id: str) -> None:
        await self._request("DELETE", f"/v1/servers/{server_id}/backups/{backup_id}")
