"""Loader for Experiment 008 architecture discovery.

Implementation is stored in adjacent source parts to keep repository writes robust.
"""
from pathlib import Path
_base = Path(__file__).resolve().parent
_names = ("part1", "part2", "part3", "part4a", "part4b", "part5", "part6")
_source = "".join((_base / f"architecture_discovery.{name}").read_text(encoding="utf-8") for name in _names)
exec(compile(_source, str(_base / "architecture_discovery.full.py"), "exec"), globals(), globals())
