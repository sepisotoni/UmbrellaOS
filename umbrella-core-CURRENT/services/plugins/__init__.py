"""services/plugins — Phase 7 Plugin SDK.

See docs/design/plugin-sdk-manifest-and-registration.md for the design
this package implements. Not imported by capabilities/__init__.py — unlike
core capability modules, plugin capabilities are registered dynamically
(at install time / from the installed-plugins table at startup), not via a
static import list, since the whole point is that plugins are not known at
code-authoring time.
"""
