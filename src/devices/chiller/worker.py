# src/devices/chiller/worker.py
"""
Thin wrapper that runs the existing Julabo worker (julabo.py) with a stable entrypoint.
Avoid relative imports; import via repo root so running as a script works.
"""

from __future__ import annotations

import sys
import json
from pathlib import Path


def _json_error(message: str) -> None:
    try:
        sys.stdout.write(json.dumps({"event": "error", "message": message}) + "\n")
        sys.stdout.flush()
    except Exception:
        pass


def _import_julabo():
    """
    Try to import the real julabo worker in a few common locations.
    - Preferred: src.devices.chiller.julabo
    - Fallbacks: src.julabo  (if you haven’t moved it yet)
    """
    here = Path(__file__).resolve()
    repo_root = here.parents[3]  # <repo>/
    # Ensure <repo>/ is on sys.path so 'import src.*' works
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    # Try preferred location
    try:
        from src.devices.chiller import julabo as _julabo  # type: ignore
        return _julabo
    except Exception as e1:
        # Fallback to old location if still there
        try:
            import src.julabo as _julabo  # type: ignore
            return _julabo
        except Exception as e2:
            _json_error(
                f"Failed to import julabo worker. Tried "
                f"'src.devices.chiller.julabo' ({e1!r}) and 'src.julabo' ({e2!r})."
            )
            raise SystemExit(3)


def main() -> int:
    _julabo = _import_julabo()
    # Delegate; julabo.py should parse argv and do the real work
    try:
        return int(_julabo.main())
    except SystemExit as ex:
        return int(getattr(ex, "code", 0) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
