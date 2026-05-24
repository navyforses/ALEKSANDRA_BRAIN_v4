"""Phase 0.1 environment probe — disk, GPU, RAM."""

import shutil
import subprocess
import sys


def main() -> None:
    total, used, free = shutil.disk_usage("C:\\")
    print(f"Disk_C_Total_GB: {total / 1024**3:.2f}")
    print(f"Disk_C_Free_GB:  {free / 1024**3:.2f}")
    print(f"Disk_C_Used_GB:  {used / 1024**3:.2f}")
    print("---")

    try:
        import psutil

        vm = psutil.virtual_memory()
        print(f"Total_RAM_GB: {vm.total / 1024**3:.2f}")
        print(f"Free_RAM_GB:  {vm.available / 1024**3:.2f}")
    except ImportError:
        print("psutil not installed")
    print("---")

    try:
        out = subprocess.check_output(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name",
            ],
            text=True,
            timeout=30,
        )
        print("GPUs:")
        for line in out.strip().splitlines():
            if line.strip():
                print(f"  - {line.strip()}")
    except Exception as e:
        print(f"GPU detect failed: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
