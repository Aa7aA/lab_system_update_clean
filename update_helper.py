from __future__ import annotations

import ctypes
import json
import subprocess
import sys
import time
from pathlib import Path


SEE_MASK_NOCLOSEPROCESS = 0x00000040
SW_SHOWNORMAL = 1


class SHELLEXECUTEINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("fMask", ctypes.c_ulong),
        ("hwnd", ctypes.c_void_p),
        ("lpVerb", ctypes.c_wchar_p),
        ("lpFile", ctypes.c_wchar_p),
        ("lpParameters", ctypes.c_wchar_p),
        ("lpDirectory", ctypes.c_wchar_p),
        ("nShow", ctypes.c_int),
        ("hInstApp", ctypes.c_void_p),
        ("lpIDList", ctypes.c_void_p),
        ("lpClass", ctypes.c_wchar_p),
        ("hkeyClass", ctypes.c_void_p),
        ("dwHotKey", ctypes.c_ulong),
        ("hIconOrMonitor", ctypes.c_void_p),
        ("hProcess", ctypes.c_void_p),
    ]


def run_elevated_and_wait(exe_path: str, params: str) -> int:
    shell32 = ctypes.windll.shell32
    kernel32 = ctypes.windll.kernel32

    sei = SHELLEXECUTEINFO()
    sei.cbSize = ctypes.sizeof(SHELLEXECUTEINFO)
    sei.fMask = SEE_MASK_NOCLOSEPROCESS
    sei.hwnd = None
    sei.lpVerb = "runas"  # triggers UAC elevation
    sei.lpFile = exe_path
    sei.lpParameters = params
    sei.lpDirectory = str(Path(exe_path).parent)
    sei.nShow = SW_SHOWNORMAL

    success = shell32.ShellExecuteExW(ctypes.byref(sei))
    if not success:
        raise RuntimeError("Failed to start installer with elevation.")

    if not sei.hProcess:
        raise RuntimeError("Installer process handle was not returned.")

    kernel32.WaitForSingleObject(sei.hProcess, 0xFFFFFFFF)

    exit_code = ctypes.c_ulong()
    kernel32.GetExitCodeProcess(sei.hProcess, ctypes.byref(exit_code))
    kernel32.CloseHandle(sei.hProcess)
    return int(exit_code.value)


def quote_arg(value: str) -> str:
    return subprocess.list2cmdline([value])


def main():
    if len(sys.argv) < 4:
        sys.exit(1)

    installer_path = Path(sys.argv[1]).resolve()
    app_exe_path = Path(sys.argv[2]).resolve()

    try:
        silent_args = json.loads(sys.argv[3])
        if not isinstance(silent_args, list):
            silent_args = []
    except Exception:
        silent_args = []

    if not installer_path.exists():
        sys.exit(2)

    time.sleep(2)

    try:
        if installer_path.suffix.lower() == ".msi":
            exe_path = "msiexec"
            params = subprocess.list2cmdline(
                ["/i", str(installer_path), *silent_args]
            )
        else:
            exe_path = str(installer_path)
            params = subprocess.list2cmdline(silent_args)

        exit_code = run_elevated_and_wait(exe_path, params)

        # Common successful installer exit codes
        if exit_code not in (0, 1641, 3010):
            sys.exit(exit_code)

    except Exception:
        sys.exit(3)

    time.sleep(2)

    try:
        if app_exe_path.exists():
            subprocess.Popen([str(app_exe_path)])
    except Exception:
        pass


if __name__ == "__main__":
    main()