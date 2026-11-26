"""Run all five apps from a single checkout; no external source clones."""
import os
from pathlib import Path
root = Path(__file__).resolve().parents[1]
os.environ.setdefault("COACH_APPS", str(root / "versions"))
os.environ.setdefault("COACH_V4_ROOT", str(root))
from gateway import app
