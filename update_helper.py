from __future__ import annotations

import ctypes
import sys
import time
from pathlib import Path


SEE_MASK_NOCLOSEPROCESS = 0x00000040
SW_SHOWNORMAL = 1
INFINITE = 0xFFFFFFFF
SYNCHRONIZE = 0x00100000


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


def wait_for_pid_to_exit(pid: int, timeout_seconds: int = 30) -> None:
    kernel32 = ctypes.windll.kernel32

    process_handle = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
    if not process_handle:
        # Process may already be gone
        return

    try:
        kernel32.WaitForSingleObject(process_handle, timeout_seconds * 1000)
    finally:
        kernel32.CloseHandle(process_handle)


def run_elevated_and_wait(exe_path: str, params: str = "") -> int:
    shell32 = ctypes.windll.shell32
    kernel32 = ctypes.windll.kernel32

    sei = SHELLEXECUTEINFO()
    sei.cbSize = ctypes.sizeof(SHELLEXECUTEINFO)
    sei.fMask = SEE_MASK_NOCLOSEPROCESS
    sei.hwnd = None
    sei.lpVerb = "runas"
    sei.lpFile = exe_path
    sei.lpParameters = params
    sei.lpDirectory = str(Path(exe_path).parent)
    sei.nShow = SW_SHOWNORMAL

    success = shell32.ShellExecuteExW(ctypes.byref(sei))
    if not success:
        raise RuntimeError("Failed to start installer with elevation.")

    if not sei.hProcess:
        raise RuntimeError("Installer process handle was not returned.")

    kernel32.WaitForSingleObject(sei.hProcess, INFINITE)

    exit_code = ctypes.c_ulong()
    kernel32.GetExitCodeProcess(sei.hProcess, ctypes.byref(exit_code))
    kernel32.CloseHandle(sei.hProcess)
    return int(exit_code.value)

def force_kill_process(pid: int):
    try:
        import subprocess
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def main():
    if len(sys.argv) < 3:
        sys.exit(1)

    installer_path = Path(sys.argv[1]).resolve()
    parent_pid = int(sys.argv[2])

    if not installer_path.exists():
        sys.exit(2)

    # Wait for app to exit
    wait_for_pid_to_exit(parent_pid, timeout_seconds=10)

    # Force kill if still running (very important)
    force_kill_process(parent_pid)

    # Give Windows time to release file locks
    time.sleep(3)

    try:
        exit_code = run_elevated_and_wait(
            str(installer_path),
            '/SILENT'
        )
        if exit_code not in (0, 1641, 3010):
            sys.exit(exit_code)
    except Exception:
        sys.exit(3)






if __name__ == "__main__":
    main()