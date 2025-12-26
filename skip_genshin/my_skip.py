import threading
import time
import keyboard
import pyautogui
import ctypes
import sys
import os
from detect_dialogue import is_dialogue_detected
from detect_active_window import is_genshin_active
from detect_page import (
    is_page_detected_1,
    is_page_detected_2,
    is_page_detected_3,
    is_page_detected_4,
)
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
    name="DEBUG",
    true_message="ON",
    false_message="OFF",
)
def get_debug_mode():
    global debug_mode
    return debug_mode


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


def close_page_2():
    """Handle page closing action."""
    try:
        pyautogui.press("space")
    except pyautogui.FailSafeException as e:
        pass  # Ignore errors during page closing


def click_page_4():
    """Handle page 4 click action."""
    try:
        pyautogui.click(1687, 715)
    except pyautogui.FailSafeException as e:
        pass  # Ignore errors during click


def debug_speed_tracker():
    """Thread that displays spam speed every second when debug mode is on."""
    global spam_count
    last_spam_time = time.time()
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
        time.sleep(0.1)


def spam_keys():
    while True:
        if running:
            if is_genshin_active():
                if is_dialogue_detected():
                    do_spam()
                elif is_page_detected_2():
                    close_page_2()
                if is_page_detected_1() or is_page_detected_3():
                    close_page()
                if is_page_detected_4():
                    click_page_4()

                time.sleep(PAUSE_BETWEEN_SPAMS)
            else:
                time.sleep(0.1)
        else:
            time.sleep(0.1)


def toggle():
    global running
    running = not running
    get_running()  # Trigger the change tracker


def toggle_debug():
    global debug_mode
    debug_mode = not debug_mode
    get_debug_mode()  # Trigger the change tracker


# Start spam thread
spam_thread = threading.Thread(target=spam_keys, daemon=True)
spam_thread.start()

# Start debug speed tracker thread
debug_thread = threading.Thread(target=debug_speed_tracker, daemon=True)
debug_thread.start()

# Bind hotkeys
keyboard.add_hotkey("F7", toggle)
keyboard.add_hotkey("F8", toggle_debug)

print("=== Genshin Dialogue Skipper ===")
print("Press F7 to start / pause spamming")
print("Press F8 to toggle DEBUG mode (show spam speed)")
print("Press CTRL+C to quit")
print()
print(f"Debug mode: {'ON' if debug_mode else 'OFF'}")

keyboard.wait()
