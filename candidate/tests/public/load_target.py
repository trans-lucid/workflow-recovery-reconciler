from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from types import ModuleType


_PREPARED_TARGET: str | None = None


def load(module_name: str) -> ModuleType:
    global _PREPARED_TARGET
    target = os.environ.get("EVAL_TARGET")
    if target and target != _PREPARED_TARGET:
        for name in list(sys.modules):
            if name == "src" or name.startswith("src."):
                del sys.modules[name]
        sys.path.insert(0, str(Path(target).resolve()))
        _PREPARED_TARGET = target
    return importlib.import_module(module_name)
