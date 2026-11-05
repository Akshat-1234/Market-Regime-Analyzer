from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import types

import pytest

ROOT = Path(__file__).resolve().parents[2]
SOURCE_COMMIT = "c46541e9ab8611330489a920c46cdb00342931d5"
PREFIX = "market-regime-platform/src/regime_backtester"
PACKAGE = "_task2_immutable_1c"


class Historical1C:
    def __init__(self):
        self.inventory = {}
        inventory_path = ROOT / "provenance/inventory/1c-c46541e-tracked-blobs.jsonl"
        with inventory_path.open() as handle:
            for line in handle:
                record = json.loads(line)
                self.inventory[record["path"]] = record["sha256"]
        self.cache = {}
        self.modules = {}
        package = types.ModuleType(PACKAGE)
        package.__path__ = []
        package.__package__ = PACKAGE
        sys.modules.setdefault(PACKAGE, package)

    def source(self, path: str) -> bytes:
        if path not in self.cache:
            result = subprocess.run(["git", "show", f"{SOURCE_COMMIT}:{path}"], cwd=ROOT,
                                    capture_output=True, check=False)
            if result.returncode:
                pytest.fail(f"immutable 1c object unavailable for {path}; fetch {SOURCE_COMMIT} "
                            "without changing source refs: " + result.stderr.decode(errors="replace"))
            payload = result.stdout
            expected = self.inventory.get(path)
            assert expected is not None, f"{path} is absent from the Task 1 immutable inventory"
            actual = hashlib.sha256(payload).hexdigest()
            assert actual == expected, f"1c source hash mismatch for {path}: {actual} != {expected}"
            self.cache[path] = payload
        return self.cache[path]

    def module(self, name: str):
        if name in self.modules:
            return self.modules[name]
        dependencies = {"predictive": ("significance",), "discovery": ("emhmm",),
                        "allocation": ("execution", "features", "strategies")}.get(name, ())
        for dependency in dependencies:
            self.module(dependency)
        path = f"{PREFIX}/{name}.py"
        fullname = f"{PACKAGE}.{name}"
        module = types.ModuleType(fullname)
        module.__file__ = f"{SOURCE_COMMIT}:{path}"
        module.__package__ = PACKAGE
        sys.modules[fullname] = module
        exec(compile(self.source(path), module.__file__, "exec"), module.__dict__)
        self.modules[name] = module
        return module


@pytest.fixture(scope="session")
def historical_1c():
    return Historical1C()
