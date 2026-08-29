"""Loader for Experiment 008 architecture discovery.

Implementation is stored in adjacent source parts to keep repository writes robust.
"""
from pathlib import Path
_base = Path(__file__).resolve().parent
_source = "".join((_base / f"architecture_discovery.part{i}").read_text(encoding="utf-8") for i in range(1, 7))
exec(compile(_source, str(_base / "architecture_discovery.full.py"), "exec"), globals(), globals())
