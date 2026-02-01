import ctypes
import sys
import subprocess
import os

HOYOPLAY = r"C:\Program Files\HoYoPlay\launcher.exe"
MIGOTO = r"C:\Users\nairo\Documents\3dmigoto\3DMigoto Loader.exe"


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def start_with_cwd(exe_path):
    exe_dir = os.path.dirname(exe_path)
    subprocess.Popen(exe_path, cwd=exe_dir)


if not is_admin():
    # Relaunch the script with admin rights
    ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        sys.executable,
        f'"{os.path.abspath(__file__)}"',
        None,
        1
    )
    sys.exit(0)

# Already running as admin
start_with_cwd(HOYOPLAY)
start_with_cwd(MIGOTO)
