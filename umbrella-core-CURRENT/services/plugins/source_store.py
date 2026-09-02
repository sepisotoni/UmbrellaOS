"""
services/plugins/source_store.py — local-disk storage for published plugin
zips (Phase 7 item 3 marketplace, per the design decision: local disk under
f"{plugin_storage_root}/{plugin_id}/{version}/", SHA-256 verification
against the marketplace listing before source ever reaches the sandbox,
explicit admin action to update — no auto-update).

This module owns exactly the "where do plugin zips live and how do we get
a sandbox-ready {module_name: source_text} map out of one" problem that
services/plugins/sandbox.py's own docstring explicitly declines to have an
opinion about (`ProcessSandbox.__init__`'s `sources` arg is "kept as a
plain constructor arg... so this module has no filesystem-layout opinion
of its own — that's the marketplace install flow's job, not the sandbox's").
Nothing here executes plugin code — that's still entirely sandbox.py's
job; this module only ever reads/writes bytes and parses JSON.
"""
from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

from config import get_settings

MANIFEST_FILENAME = "plugin.json"

# [PLUGIN] audit addition, 2026-09-01: decompression-bomb guard.
#
# Neither read_manifest_dict() nor extract_sources() previously checked any
# size before calling zf.read(name) — a tiny (KB-scale) crafted zip can
# have a central-directory-declared file_size in the GB range (classic
# "zip bomb"), and zf.read() will happily decompress the entire thing into
# memory in one call, in this process (umbrella-core itself, not an
# isolated sandbox subprocess — this code runs during publish/install,
# before sandbox.py's process isolation ever begins), regardless of the
# actual on-disk zip size. Reachable via marketplace.listing.manage /
# marketplace.install.manage (capabilities/marketplace.py) — a genuine
# permission gate, so this needs a trusted actor to trigger, not an
# anonymous caller — but a mistake, a corrupted upload, or a compromised
# trusted account should still not be able to take the whole service down
# via a multi-KB file.
#
# Two layers, since a zip's own declared file_size in ZipInfo is untrusted
# metadata the format doesn't cryptographically bind to the actual
# decompressed byte stream:
#   1. Reject upfront if ZipInfo.file_size already exceeds the cap (catches
#      the common/naive case cheaply, no decompression needed).
#   2. Stream-decompress in bounded chunks via zf.open(), aborting the
#      moment real output crosses the cap — this is the actual backstop,
#      independent of whatever the zip's central directory claims.
_MAX_DECOMPRESSED_ENTRY_BYTES = 2 * 1024 * 1024  # 2 MiB — plugin.json and a
# single plugin source module are both tiny text files by design (source
# modules also separately face sandbox_guard.py's 64 KiB check once
# extracted); 2 MiB is generous headroom, not a tight fit.


def _safe_read(zf: zipfile.ZipFile, name: str) -> bytes:
    """Decompress a single zip entry with a hard, streaming byte-count
    cap — see _MAX_DECOMPRESSED_ENTRY_BYTES docstring above. Raises
    PluginPackageError instead of allowing unbounded memory growth from a
    crafted or corrupted entry."""
    info = zf.getinfo(name)
    if info.file_size > _MAX_DECOMPRESSED_ENTRY_BYTES:
        raise PluginPackageError(
            f"{name!r} declares a decompressed size of {info.file_size} bytes, "
            f"exceeding the {_MAX_DECOMPRESSED_ENTRY_BYTES}-byte cap"
        )
    chunks: list[bytes] = []
    total = 0
    with zf.open(name) as fh:
        while True:
            chunk = fh.read(65536)
            if not chunk:
                break
            total += len(chunk)
            if total > _MAX_DECOMPRESSED_ENTRY_BYTES:
                raise PluginPackageError(
                    f"{name!r} decompressed past the {_MAX_DECOMPRESSED_ENTRY_BYTES}-byte "
                    f"cap during read — its declared size was inaccurate or misleading"
                )
            chunks.append(chunk)
    return b"".join(chunks)


class PluginPackageError(ValueError):
    """Raised for a structurally-broken zip (not a zip at all, no
    plugin.json, an unsafe entry name) or an integrity mismatch (the
    bytes on disk don't hash to what the marketplace listing declared at
    publish time). Deliberately one exception type for both publish-time
    and install-time failures — both are "this isn't a trustworthy plugin
    package right now," just caught at different points in the lifecycle,
    the same posture services/plugins/manifest.py's
    ManifestValidationError already takes for structural manifest
    problems."""


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _storage_root() -> Path:
    return Path(get_settings().plugin_storage_root)


def _version_dir(plugin_id: str, version: str) -> Path:
    return _storage_root() / plugin_id / version


def zip_relative_path(plugin_id: str, version: str) -> str:
    """The path stored on PluginVersion.zip_path — relative to
    plugin_storage_root, so the DB stays portable across a storage-root
    relocation (see models/marketplace.py's module docstring)."""
    return str(Path(plugin_id) / version / "plugin.zip")


def _check_safe_names(names: list[str]) -> None:
    """Rejects zip-slip-style entries (absolute paths, `..` traversal)
    before anything reads their content — defense in depth even though
    this module never writes individual extracted entries back to disk
    itself (only the whole zip, as one opaque blob, in `store_zip`)."""
    for name in names:
        if name.startswith("/") or ".." in Path(name).parts:
            raise PluginPackageError(f"unsafe path in plugin zip: {name!r}")


def read_manifest_dict(zip_bytes: bytes) -> dict:
    """Parses plugin.json out of a zip's bytes without touching disk.
    Raises PluginPackageError for anything that isn't a valid zip
    containing a readable, JSON-parseable plugin.json at its root —
    callers pass the resulting dict straight to
    services.plugins.manifest.parse_manifest for full structural
    validation; this function only gets the raw dict out."""
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            _check_safe_names(zf.namelist())
            try:
                raw = _safe_read(zf, MANIFEST_FILENAME)
            except KeyError:
                raise PluginPackageError(
                    f"plugin zip is missing {MANIFEST_FILENAME} at its root"
                ) from None
    except zipfile.BadZipFile as exc:
        raise PluginPackageError("not a valid zip file") from exc

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PluginPackageError(f"{MANIFEST_FILENAME} is not valid JSON: {exc}") from exc


def extract_sources(zip_bytes: bytes) -> dict[str, str]:
    """Returns {module_name: source_text} for every top-level *.py file in
    the zip (module_name = filename without the .py extension) — the exact
    shape ProcessSandbox's `sources[plugin_id]` constructor arg and
    `set_plugin_sources()` expect. Deliberately flat: only files directly
    at the zip root are read, matching the sandbox's own "module:function"
    entrypoint convention (no package/subpackage support in v1, same
    minimal-surface posture as the manifest's tiny param-type vocabulary —
    see docs/design/plugin-sdk-manifest-and-registration.md)."""
    sources: dict[str, str] = {}
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        _check_safe_names(zf.namelist())
        for name in zf.namelist():
            if name == MANIFEST_FILENAME or "/" in name or not name.endswith(".py"):
                continue
            module_name = name[: -len(".py")]
            sources[module_name] = _safe_read(zf, name).decode("utf-8")
    return sources


def store_zip(plugin_id: str, version: str, zip_bytes: bytes) -> tuple[str, str]:
    """Writes a published version's zip to
    f"{plugin_storage_root}/{plugin_id}/{version}/plugin.zip", creating
    directories as needed. Returns (relative_path, sha256_hex) — the exact
    pair PluginVersion.zip_path/sha256_hash store (see
    models/marketplace.py)."""
    version_dir = _version_dir(plugin_id, version)
    version_dir.mkdir(parents=True, exist_ok=True)
    zip_file = version_dir / "plugin.zip"
    zip_file.write_bytes(zip_bytes)
    return zip_relative_path(plugin_id, version), compute_sha256(zip_bytes)


def load_verified_zip_bytes(relative_path: str, expected_sha256: str) -> bytes:
    """Reads a previously-stored zip back off disk and re-verifies its
    hash against `expected_sha256` (the marketplace listing's declared
    hash) before returning it — the install-time integrity check the
    design decision calls for. Raises PluginPackageError on any mismatch
    or missing file; callers must not proceed to extract/register a
    plugin whose bytes don't match what was published."""
    zip_file = _storage_root() / relative_path
    try:
        data = zip_file.read_bytes()
    except FileNotFoundError as exc:
        raise PluginPackageError(f"stored plugin zip not found at {relative_path!r}") from exc

    actual = compute_sha256(data)
    if actual != expected_sha256:
        raise PluginPackageError(
            f"integrity check failed for {relative_path!r}: expected sha256 "
            f"{expected_sha256}, got {actual}"
        )
    return data
