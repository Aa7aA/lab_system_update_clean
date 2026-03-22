from __future__ import annotations

import json
from pathlib import Path

from .db import APP_DATA_DIR
from .branding import LAB_BRANDING
from .version import APP_CHANNEL


LAB_INFO_PATH = APP_DATA_DIR / "lab_info.json"


def ensure_lab_identity() -> dict:
    """
    Ensure a local lab identity file exists.
    Creates a default one on first run.
    """
    if LAB_INFO_PATH.exists():
        return json.loads(LAB_INFO_PATH.read_text(encoding="utf-8"))

    data = {
        "lab_id": "LAB-LOCAL-001",
        "lab_name": LAB_BRANDING["lab_name_en"],
        "channel": APP_CHANNEL,
    }

    LAB_INFO_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return data


def get_lab_identity() -> dict:
    """
    Read and return the current lab identity.
    """
    return ensure_lab_identity()