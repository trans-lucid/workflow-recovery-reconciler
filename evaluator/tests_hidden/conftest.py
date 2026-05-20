from __future__ import annotations

import os
import sys
from pathlib import Path


target = os.environ.get("EVAL_TARGET")
if target:
    target_path = Path(target).resolve()
else:
    target_path = Path(__file__).resolve().parents[2] / "solution"

for name in list(sys.modules):
    if name == "src" or name.startswith("src."):
        del sys.modules[name]
sys.path.insert(0, str(target_path))

