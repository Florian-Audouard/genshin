"""
Module to detect if Genshin Impact is the active/foreground window.
"""

import win32gui
import time
from utils import track_changes


def get_active_window_title() -> str:
    """
    Get the title of the currently active/foreground window.

    Returns:
        str: The title of the active window, or empty string if none.
    """
    try:
        hwnd = win32gui.GetForegroundWindow()
        return win32gui.GetWindowText(hwnd)
    except Exception:
        return ""


@track_changes(
    name="Active Window",
    true_message="Genshin Impact",
    false_message="Other Application",
)
def is_genshin_active() -> bool:
    """
    Check if Genshin Impact is the currently active window.

    Returns:
        bool: True if Genshin Impact is the active window, False otherwise.
    """
    window_title = get_active_window_title()
    # Genshin Impact window title is typically "Genshin Impact"
    return "Genshin Impact" in window_title


def test_active_window_detection():
    """
    Test function to verify active window detection.
    Prints the active window every second for 10 seconds.
    """
    print("Testing active window detection...")
    print("Switch between windows to see the detection in action.")
    print("-" * 50)

    for i in range(10):
        window_title = get_active_window_title()
        is_genshin = is_genshin_active()

        status = "✓ GENSHIN ACTIVE" if is_genshin else "✗ Not Genshin"
        print(f"[{i+1}/10] {status} | Window: '{window_title}'")

        time.sleep(1)

    print("-" * 50)
    print("Test complete!")


if __name__ == "__main__":
    test_active_window_detection()
