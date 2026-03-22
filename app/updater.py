from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass


@dataclass
class UpdateInfo:
    latest_version: str
    download_url: str
    notes: list[str]
    mandatory: bool = False
    allowed_labs: list[str] | None = None


def parse_version(v: str) -> tuple[int, ...]:
    """
    Convert version string like '1.0.3' into a tuple for comparison.
    """
    parts = []
    for x in (v or "0").split("."):
        try:
            parts.append(int(x))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def is_newer_version(current: str, latest: str) -> bool:
    """
    Return True if latest version is newer than current version.
    """
    return parse_version(latest) > parse_version(current)


def fetch_update_manifest(url: str) -> UpdateInfo:
    """
    Download and parse the update manifest JSON file.
    """
    with urllib.request.urlopen(url, timeout=10) as response:
        data = json.loads(response.read().decode("utf-8"))

    return UpdateInfo(
        latest_version=data["latest_version"],
        download_url=data["download_url"],
        notes=data.get("notes", []),
        mandatory=bool(data.get("mandatory", False)),
        allowed_labs=data.get("allowed_labs"),
    )


def is_lab_allowed(lab_id: str, allowed_labs: list[str] | None) -> bool:
    """
    Return True if the given lab is allowed to receive this update.
    If allowed_labs is missing or empty, the update is available to all labs.
    """
    if not allowed_labs:
        return True
    return lab_id in allowed_labs