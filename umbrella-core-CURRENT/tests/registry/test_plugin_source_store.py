"""tests/registry/test_plugin_source_store.py — local-disk zip storage,
SHA-256 integrity verification, and {module_name: source_text} extraction
for the marketplace install flow.
"""
import io
import json
import zipfile

import pytest

from config import get_settings
from services.plugins.source_store import (
    PluginPackageError,
    compute_sha256,
    extract_sources,
    load_verified_zip_bytes,
    read_manifest_dict,
    store_zip,
    zip_relative_path,
)


def _make_zip(manifest: dict, modules: dict[str, str] | None = None, extra_entries: dict[str, bytes] | None = None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("plugin.json", json.dumps(manifest))
        for module_name, source in (modules or {}).items():
            zf.writestr(f"{module_name}.py", source)
        for name, content in (extra_entries or {}).items():
            zf.writestr(name, content)
    return buf.getvalue()


@pytest.fixture(autouse=True)
def _plugin_storage_root(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "plugin_storage_root", str(tmp_path / "plugins"))
    yield


def test_read_manifest_dict_parses_plugin_json():
    zip_bytes = _make_zip({"plugin_id": "demo", "version": "1.0.0"})
    manifest = read_manifest_dict(zip_bytes)
    assert manifest == {"plugin_id": "demo", "version": "1.0.0"}


def test_read_manifest_dict_rejects_non_zip():
    with pytest.raises(PluginPackageError, match="not a valid zip"):
        read_manifest_dict(b"this is not a zip file")


def test_read_manifest_dict_rejects_missing_manifest():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("handlers.py", "def run(params):\n    return {}\n")
    with pytest.raises(PluginPackageError, match="missing plugin.json"):
        read_manifest_dict(buf.getvalue())


def test_read_manifest_dict_rejects_invalid_json():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("plugin.json", "{not valid json")
    with pytest.raises(PluginPackageError, match="not valid JSON"):
        read_manifest_dict(buf.getvalue())


def test_read_manifest_dict_rejects_path_traversal_entry():
    zip_bytes = _make_zip(
        {"plugin_id": "demo"}, extra_entries={"../../etc/passwd": b"evil"}
    )
    with pytest.raises(PluginPackageError, match="unsafe path"):
        read_manifest_dict(zip_bytes)


def test_extract_sources_reads_top_level_py_files_only():
    zip_bytes = _make_zip(
        {"plugin_id": "demo"},
        modules={"handlers": "def run(params):\n    return {'ok': True}\n"},
        extra_entries={"nested/other.py": b"should not be read"},
    )
    sources = extract_sources(zip_bytes)
    assert sources == {"handlers": "def run(params):\n    return {'ok': True}\n"}


def test_extract_sources_excludes_manifest_itself():
    zip_bytes = _make_zip({"plugin_id": "demo"}, modules={"handlers": "x = 1\n"})
    sources = extract_sources(zip_bytes)
    assert "plugin" not in sources
    assert set(sources.keys()) == {"handlers"}


def test_store_zip_writes_file_and_returns_relative_path_and_hash():
    zip_bytes = _make_zip({"plugin_id": "demo"})
    relative_path, sha = store_zip("demo", "1.0.0", zip_bytes)

    assert relative_path == zip_relative_path("demo", "1.0.0")
    assert sha == compute_sha256(zip_bytes)

    stored = load_verified_zip_bytes(relative_path, sha)
    assert stored == zip_bytes


def test_load_verified_zip_bytes_rejects_hash_mismatch():
    zip_bytes = _make_zip({"plugin_id": "demo"})
    relative_path, _real_hash = store_zip("demo", "1.0.0", zip_bytes)

    with pytest.raises(PluginPackageError, match="integrity check failed"):
        load_verified_zip_bytes(relative_path, "0" * 64)


def test_load_verified_zip_bytes_rejects_missing_file():
    with pytest.raises(PluginPackageError, match="not found"):
        load_verified_zip_bytes("never/published/plugin.zip", "0" * 64)


def test_store_zip_separates_versions_of_same_plugin():
    zip_v1 = _make_zip({"plugin_id": "demo", "version": "1.0.0"})
    zip_v2 = _make_zip({"plugin_id": "demo", "version": "2.0.0"})
    path_v1, hash_v1 = store_zip("demo", "1.0.0", zip_v1)
    path_v2, hash_v2 = store_zip("demo", "2.0.0", zip_v2)

    assert path_v1 != path_v2
    assert hash_v1 != hash_v2
    assert load_verified_zip_bytes(path_v1, hash_v1) == zip_v1
    assert load_verified_zip_bytes(path_v2, hash_v2) == zip_v2


# --- [PLUGIN] audit addition, 2026-09-01: decompression-bomb guard ---
#
# Empirically confirmed before this fix: read_manifest_dict()/extract_sources()
# called zf.read(name) with no size check at all — a multi-KB crafted zip
# with a highly-compressible payload (e.g. all zero bytes) decompresses to
# tens of megabytes in a single call, in umbrella-core's own process, not
# an isolated sandbox subprocess (this code runs during publish/install,
# before sandbox.py's process isolation ever begins).


def test_read_manifest_dict_rejects_oversized_declared_manifest():
    """A zip whose plugin.json entry declares (and actually contains) a
    decompressed size over the cap must be rejected before the full
    content is ever materialized in memory."""
    bomb = b"\x00" * (5 * 1024 * 1024)  # 5 MiB, well over the 2 MiB cap
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zf.writestr("plugin.json", bomb)
    zip_bytes = buf.getvalue()
    assert len(zip_bytes) < 100_000, "sanity check: the zip itself must stay small — it's the ratio that matters"

    with pytest.raises(PluginPackageError, match="exceeding the .* cap"):
        read_manifest_dict(zip_bytes)


def test_extract_sources_rejects_oversized_declared_module():
    """Same guard, but for a .py module entry rather than plugin.json —
    confirms the fix applies to extract_sources() independently, not just
    read_manifest_dict()."""
    bomb = b"\x00" * (5 * 1024 * 1024)
    zip_bytes = _make_zip(
        {"plugin_id": "bomb-test", "version": "1.0.0"},
        extra_entries={"handlers.py": bomb},
    )
    with pytest.raises(PluginPackageError, match="exceeding the .* cap"):
        extract_sources(zip_bytes)


def test_ordinary_small_manifest_and_module_still_extract_fine():
    """The fix must not false-positive on realistically-sized plugin
    packages — plugin.json and a handful of small source modules are the
    overwhelmingly common case and must pass through unaffected."""
    zip_bytes = _make_zip(
        {"plugin_id": "normal-plugin", "version": "1.0.0"},
        modules={"handlers": "def run(params):\n    return {'ok': True}\n"},
    )
    manifest = read_manifest_dict(zip_bytes)
    assert manifest["plugin_id"] == "normal-plugin"
    sources = extract_sources(zip_bytes)
    assert "handlers" in sources
    assert "def run(params):" in sources["handlers"]


def test_safe_read_streaming_loop_handles_multichunk_reads_correctly():
    """_safe_read() reads in 64 KiB chunks rather than one shot, as
    defense-in-depth against relying solely on the size-hint pre-check
    (see the module docstring above _MAX_DECOMPRESSED_ENTRY_BYTES).
    Investigated empirically while writing this test: Python's own
    zipfile.ZipExtFile.read() treats an entry's declared file_size as a
    hard ceiling on decompressed output — it will never emit more bytes
    than file_size regardless of how the compressed stream is
    constructed, verifying CRC once that ceiling is reached — so a zip
    cannot be crafted, via the standard zipfile writer, to declare a
    small file_size while a .read() call still emits more than that. The
    size-hint pre-check is therefore fully authoritative for zips
    produced by the standard library's own writer. This test instead
    confirms the chunked-read loop itself is correct for a file just
    under the cap (2 MiB / 64 KiB chunks = 32 loop iterations), rather
    than asserting an unconstructible "lied about its own size" scenario."""
    from services.plugins.source_store import _safe_read, _MAX_DECOMPRESSED_ENTRY_BYTES

    payload = b"A" * (_MAX_DECOMPRESSED_ENTRY_BYTES - 1024)  # just under the cap
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zf.writestr("payload.bin", payload)
    buf.seek(0)
    with zipfile.ZipFile(buf) as zf:
        result = _safe_read(zf, "payload.bin")
    assert result == payload
