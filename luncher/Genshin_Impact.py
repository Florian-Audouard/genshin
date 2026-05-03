import ctypes
import sys
import subprocess
import os
import shutil
from pathlib import Path

HOYOPLAY = r"C:\Users\nairo\Documents\safe_space\unlockfps_nc.exe"
MIGOTO = r"C:\Users\nairo\Documents\3dmigoto\3DMigoto Loader.exe"


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def cleanup_mei_folders():
    """Remove all _MEI* folders from temp directory"""
    temp_dir = Path(os.getenv('TEMP'))
    try:
        for mei_folder in temp_dir.glob('_MEI*'):
            if mei_folder.is_dir():
                try:
                    shutil.rmtree(mei_folder)
                    print(f"Cleaned up: {mei_folder}")
                except Exception as e:
                    print(f"Failed to clean {mei_folder}: {e}")
    except Exception as e:
        print(f"Error during cleanup: {e}")


def start_with_cwd(exe_path):
    exe_dir = os.path.dirname(exe_path)
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    subprocess.Popen(
        exe_path,
        cwd=exe_dir,
        startupinfo=startupinfo,
        creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


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
cleanup_mei_folders()
start_with_cwd(HOYOPLAY)
start_with_cwd(MIGOTO)
