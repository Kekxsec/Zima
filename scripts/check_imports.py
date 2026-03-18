"""
Enforces the one-directional dependency rule:
core → db → auth → assets → signals → providers → modules
     → correlation → scoring → remediation → automation → api

Any violation exits non-zero and fails the build.
"""

import ast
import sys
from pathlib import Path

FORBIDDEN_UPWARD_IMPORTS: dict[str, list[str]] = {
    "providers": [
        "modules",
        "correlation",
        "scoring",
        "remediation",
        "automation",
        "api",
    ],
    "modules": ["correlation", "scoring", "remediation", "automation", "api"],
    "correlation": ["scoring", "remediation", "automation", "api"],
    "scoring": ["remediation", "automation", "api"],
    "remediation": ["automation", "api"],
    "automation": ["api"],
}

BASE = Path("backend/app")
violations: list[str] = []

for source_layer, forbidden_layers in FORBIDDEN_UPWARD_IMPORTS.items():
    layer_path = BASE / source_layer
    if not layer_path.exists():
        continue
    for py_file in layer_path.rglob("*.py"):
        tree = ast.parse(py_file.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                for forbidden in forbidden_layers:
                    if f"backend.app.{forbidden}" in node.module:
                        violations.append(
                            f"VIOLATION in {py_file}: "
                            f"layer '{source_layer}' must not import from '{forbidden}'"
                        )

if violations:
    print("\n".join(violations))
    sys.exit(1)

print("Import direction check passed.")
sys.exit(0)
