from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .db import APP_DATA_DIR, get_conn
from .lab_identity import get_lab_identity
from .version import APP_VERSION, APP_CHANNEL


def build_support_snapshot() -> dict:
    """
    Build a safe technical snapshot of the lab structure.
    Includes only app/lab/module/test metadata.
    Does not include patient data or report results.
    """
    identity = get_lab_identity()

    with get_conn() as conn:
        modules = conn.execute("""
            SELECT id, name
            FROM modules
            ORDER BY name
        """).fetchall()

        result_modules = []
        for mod in modules:
            tests = conn.execute("""
                SELECT name
                FROM tests
                WHERE module_id = ?
                ORDER BY name
            """, (mod["id"],)).fetchall()

            result_modules.append({
                "module_name": mod["name"],
                "tests": [t["name"] for t in tests]
            })

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "app_version": APP_VERSION,
        "channel": APP_CHANNEL,
        "lab_id": identity["lab_id"],
        "lab_name": identity["lab_name"],
        "modules": result_modules,
    }


def export_support_snapshot() -> Path:
    """
    Export the support snapshot JSON file into the app data folder.
    """
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

    out_path = APP_DATA_DIR / "support_snapshot.json"
    data = build_support_snapshot()

    out_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return out_path