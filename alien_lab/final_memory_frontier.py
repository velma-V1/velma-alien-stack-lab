"""Loader for the audited Experiment 007 final runner.

The implementation is stored in three adjacent source parts only to keep
repository writes lossless through size-limited connectors. They are executed
as one source unit in this module's namespace.
"""
from pathlib import Path
_base = Path(__file__).resolve().parent
_source = "".join((_base / f"final_memory_frontier.part{i}").read_text(encoding="utf-8") for i in (1, 2, 3))
exec(compile(_source, str(_base / "final_memory_frontier.full.py"), "exec"), globals(), globals())
