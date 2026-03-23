from __future__ import annotations

import hashlib
import json
import os
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path


@dataclass
class UpdateInfo:
    latest_version: str
    download_url: str
    notes: list[str]
    mandatory: bool = False
    allowed_labs: list[str] | None = None
    installer_type: str = "exe"
    silent_args: list[str] | None = None
    sha256: str = ""


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
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "AlShafaqLabUpdater/1.0"}
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        data = json.loads(response.read().decode("utf-8"))

    return UpdateInfo(
        latest_version=data["latest_version"],
        download_url=data["download_url"],
        notes=data.get("notes", []),
        mandatory=bool(data.get("mandatory", False)),
        allowed_labs=data.get("allowed_labs"),
        installer_type=data.get("installer_type", "exe"),
        silent_args=data.get("silent_args", []),
        sha256=data.get("sha256", ""),
    )


def is_lab_allowed(lab_id: str, allowed_labs: list[str] | None) -> bool:
    """
    Return True if the given lab is allowed to receive this update.
    If allowed_labs is missing or empty, the update is available to all labs.
    """
    if not allowed_labs:
        return True
    return lab_id in allowed_labs


def get_update_dir() -> Path:
    """
    Folder where downloaded update installers are stored.
    """
    appdata = Path(os.getenv("APPDATA", tempfile.gettempdir()))
    update_dir = appdata / "AlShafaqLab" / "updates"
    update_dir.mkdir(parents=True, exist_ok=True)
    return update_dir


def get_download_target(info: UpdateInfo) -> Path:
    """
    Build the local file path for the downloaded installer.
    """
    suffix = ".exe"
    if info.installer_type.lower() == "msi":
        suffix = ".msi"
    elif info.installer_type.lower() == "zip":
        suffix = ".zip"

    return get_update_dir() / f"AL-SHAFAQ-LAB-{info.latest_version}{suffix}"


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().lower()


def verify_download(path: Path, expected_sha256: str) -> bool:
    """
    If manifest has sha256, verify it.
    If manifest sha256 is empty, skip verification.
    """
    expected = (expected_sha256 or "").strip().lower()
    if not expected:
        return True
    return sha256_of_file(path) == expected


def download_file(url: str, dest: Path, progress_cb=None) -> Path:
    """
    Download file to 'dest'.
    progress_cb(downloaded_bytes, total_bytes) will be called during download.
    """
    tmp_dest = dest.with_suffix(dest.suffix + ".part")

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "AlShafaqLabUpdater/1.0"}
    )

    with urllib.request.urlopen(req, timeout=60) as response, tmp_dest.open("wb") as f:
        total = response.headers.get("Content-Length")
        total = int(total) if total else 0
        downloaded = 0

        while True:
            chunk = response.read(1024 * 64)
            if not chunk:
                break

            f.write(chunk)
            downloaded += len(chunk)

            if progress_cb:
                progress_cb(downloaded, total)

    if dest.exists():
        dest.unlink()

    tmp_dest.rename(dest)
    return dest