from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path


def main():
    if len(sys.argv) < 4:
        sys.exit(1)

    installer_path = Path(sys.argv[1])
    app_exe_path = Path(sys.argv[2])

    try:
        silent_args = json.loads(sys.argv[3])
        if not isinstance(silent_args, list):
            silent_args = []
    except Exception:
        silent_args = []

    if not installer_path.exists():
        sys.exit(2)

    # Give the main app time to exit fully.
    time.sleep(2)

    try:
        if installer_path.suffix.lower() == ".msi":
            cmd = ["msiexec", "/i", str(installer_path), *silent_args]
        else:
            cmd = [str(installer_path), *silent_args]

        subprocess.run(cmd, check=False)
    except Exception:
        sys.exit(3)

    # Give installer a moment to finalize.
    time.sleep(2)

    try:
        if app_exe_path.exists():
            subprocess.Popen([str(app_exe_path)])
    except Exception:
        pass


if __name__ == "__main__":
    main()