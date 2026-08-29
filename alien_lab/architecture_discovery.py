"""Loader for Experiment 008 architecture discovery.

The original implementation is stored in split source parts for robust repository
writes. Those legacy parts are not guaranteed to end on Python statement/module
boundaries, so they MUST be concatenated contiguously before any hardening
overrides are appended.
"""
from pathlib import Path

_base = Path(__file__).resolve().parent
_legacy_names = ("part1", "part2", "part3", "part4a", "part4b", "part5", "part6")
_override_names = ("part2fix", "part6fix")

_legacy_source = "".join(
    (_base / f"architecture_discovery.{name}").read_text(encoding="utf-8")
    for name in _legacy_names
)
_guard = '\nif __name__=="__main__": raise SystemExit(main())\n'
if _legacy_source.count(_guard) != 1:
    raise RuntimeError("ARCHITECTURE_DISCOVERY_MAIN_GUARD_MISMATCH")
_legacy_source = _legacy_source.replace(_guard, "\n")

_override_source = "".join(
    (_base / f"architecture_discovery.{name}").read_text(encoding="utf-8")
    for name in _override_names
)
_source = _legacy_source + "\n" + _override_source
exec(compile(_source, str(_base / "architecture_discovery.full.py"), "exec"), globals(), globals())

if __name__ == "__main__":
    raise SystemExit(main())
