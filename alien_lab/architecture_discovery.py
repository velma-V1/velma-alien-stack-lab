"""Loader for Experiment 008 architecture discovery.

Implementation is stored in adjacent source parts to keep repository writes robust.
"""
from pathlib import Path

_base = Path(__file__).resolve().parent
_names = (
    "part1", "part2", "part2fix", "part3", "part4a", "part4b", "part5", "part6", "part6fix"
)
_source = "".join((_base / f"architecture_discovery.{name}").read_text(encoding="utf-8") for name in _names)
_guard = '\nif __name__=="__main__": raise SystemExit(main())\n'
if _source.count(_guard) != 1:
    raise RuntimeError("ARCHITECTURE_DISCOVERY_MAIN_GUARD_MISMATCH")
_source = _source.replace(_guard, "\n")
exec(compile(_source, str(_base / "architecture_discovery.full.py"), "exec"), globals(), globals())

if __name__ == "__main__":
    raise SystemExit(main())
