import threading
import time
import keyboard
import pyautogui
import ctypes
import sys
import os
from detect_dialogue import is_dialogue_detected
from detect_active_window import is_genshin_active
from detect_page import is_page_detected
from utils import track_changes

pyautogui.PAUSE = 0  # Small pause between actions
PAUSE_BETWEEN_SPAMS = 0.05  # Pause between spam actions


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def request_admin():
    if not is_admin():
        print("ERROR: This script requires administrator privileges!")
        print("Requesting admin rights...")
        try:
            # Fixed: Use shell32 instead of shell
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 1
            )
        except Exception as e:
            print(f"Failed to elevate privileges: {e}")
        sys.exit()


request_admin()

running = False  # play / pause state
# I tested both and they have similar performance so normal is more secure, the pyautogui pause is what limits speed
daemon_mode = (
    False  # True = daemon mode (separate thread), False = normal mode (same thread)
)

genshin_active = False  # Shared variable updated by daemon thread
dialogue_active = False  # Shared variable updated by daemon thread
page_active = False  # Shared variable updated by daemon thread
debug_mode = False  # Debug mode to display spam speed
spam_count = 0  # Counter for spam speed calculation


@track_changes(
    name="SPAMMING",
    true_message="RUNNING",
    false_message="PAUSED",
)
def get_running():
    global running
    return running


@track_changes(
    name="MODE",
    true_message="DAEMON (separate thread)",
    false_message="NORMAL (same thread)",
)
def get_daemon_mode():
    global daemon_mode
    return daemon_mode


@track_changes(
    name="DEBUG",
    true_message="ON",
    false_message="OFF",
)
def get_debug_mode():
    global debug_mode
    return debug_mode


def condition_checker_daemon():
    """Daemon thread that continuously checks conditions and updates the shared variable."""
    global genshin_active, dialogue_active, page_active, daemon_mode
    while True:
        if daemon_mode:
            genshin_active = is_genshin_active()
            dialogue_active = is_dialogue_detected()
            page_active = is_page_detected()
        time.sleep(0.05)  # Check conditions frequently


def do_spam():
    """Execute the spam action and track for debug."""
    global spam_count
    try:
        pyautogui.press("e")
        pyautogui.press("space")
        spam_count += 1
    except pyautogui.FailSafeException as e:
        pass  # Ignore errors during spamming


def close_page():
    """Handle page closing action."""
    try:
        pyautogui.press("escape")
    except pyautogui.FailSafeException as e:
        pass  # Ignore errors during page closing


def debug_speed_tracker():
    """Thread that displays spam speed every second when debug mode is on."""
    global spam_count, daemon_mode
    last_spam_time = time.time()
    saved_daemon_mode = daemon_mode
    while True:
        if debug_mode:
            current_time = time.time()
            elapsed = current_time - last_spam_time
            if elapsed >= 1.0:
                speed = spam_count / elapsed
                print(
                    f"DEBUG: Spam speed: {speed:.2f} actions/sec ({spam_count} in {elapsed:.2f}s)"
                )
                spam_count = 0
                last_spam_time = current_time
        else:
            # Reset counters when debug is off
            spam_count = 0
            last_spam_time = time.time()
        if daemon_mode != saved_daemon_mode:
            # If mode changed, reset counters
            spam_count = 0
            last_spam_time = time.time()
            saved_daemon_mode = daemon_mode
        time.sleep(0.1)


def spam_keys():
    while True:
        if running:
            if daemon_mode:
                # Daemon mode: read the pre-computed condition from the daemon thread
                if genshin_active:
                    if dialogue_active:
                        do_spam()
                    if page_active:
                        close_page()
                    time.sleep(PAUSE_BETWEEN_SPAMS)
                else:
                    time.sleep(0.1)
            else:
                # Normal mode: check conditions in this thread
                if is_genshin_active():
                    if is_dialogue_detected():
                        do_spam()
                    if is_page_detected():
                        close_page()
                    time.sleep(PAUSE_BETWEEN_SPAMS)
                else:
                    time.sleep(0.1)
        else:
            time.sleep(0.1)


def toggle():
    global running
    running = not running
    get_running()  # Trigger the change tracker


def toggle_mode():
    global daemon_mode
    daemon_mode = not daemon_mode
    get_daemon_mode()  # Trigger the change tracker


def toggle_debug():
    global debug_mode
    debug_mode = not debug_mode
    get_debug_mode()  # Trigger the change tracker


# Start condition checker daemon thread
condition_thread = threading.Thread(target=condition_checker_daemon, daemon=True)
condition_thread.start()

# Start spam thread
spam_thread = threading.Thread(target=spam_keys, daemon=True)
spam_thread.start()

# Start debug speed tracker thread
debug_thread = threading.Thread(target=debug_speed_tracker, daemon=True)
debug_thread.start()

# Bind hotkeys
keyboard.add_hotkey("F7", toggle)
keyboard.add_hotkey("F8", toggle_mode)
keyboard.add_hotkey("F9", toggle_debug)

print("=== Genshin Dialogue Skipper ===")
print("Press F7 to start / pause spamming")
print("Press F8 to toggle between DAEMON and NORMAL mode")
print("  - DAEMON: Condition checks in separate thread (async)")
print("  - NORMAL: Condition checks in spam loop (sync)")
print("Press F9 to toggle DEBUG mode (show spam speed)")
print("Press CTRL+C to quit")
print()
print(
    f"Current mode: {'DAEMON (separate thread)' if daemon_mode else 'NORMAL (same thread)'}"
)
print(f"Debug mode: {'ON' if debug_mode else 'OFF'}")

keyboard.wait()
