import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
os.environ.setdefault("REDACT_MODEL_DIR", str(REPO / "models"))
