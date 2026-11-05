"""Export the CancerLens OpenAPI 3.1 contract to ``backend/openapi.json`` without starting a server (HO-2).

Usage (either works):
    python -m backend.scripts.export_openapi        # from the repository root
    python scripts/export_openapi.py                # from backend/
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


def export(output_path: Path = BACKEND_DIR / "openapi.json") -> Path:
    # Defaults only: no .env secrets are read into the contract and no lifespan (DB / network) runs.
    app = create_app(Settings(_env_file=None))
    schema = app.openapi()
    output_path.write_text(json.dumps(schema, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return output_path


def main() -> int:
    path = export()
    schema = json.loads(path.read_text(encoding="utf-8"))
    print(
        f"Wrote {path} (OpenAPI {schema['openapi']}, {len(schema['paths'])} paths, "
        f"{len(schema.get('components', {}).get('schemas', {}))} schemas)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
