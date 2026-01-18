import keyboard
import pyautogui
import time
import threading

KEY = "F10"

stop_event = threading.Event()
spam_thread = None
CLICK = lambda: pyautogui.click()
RIGHT_CLICK = lambda: pyautogui.click(button="right")
WAIT = lambda t: time.sleep(t)

tab_event = [
    CLICK,
    (WAIT, 0.2),
    CLICK,
    (WAIT, 0.2),
    CLICK,
    (WAIT, 0.2),
    CLICK,
    (WAIT, 0.2),
    RIGHT_CLICK,
    (WAIT, 0.2),
]


def spam():
    for action in tab_event:
        if stop_event.is_set():
            break
        if isinstance(action, tuple):
            func, arg = action
            func(arg)
        else:
            action()


def spam_loop():
    while not stop_event.is_set():
        spam()


def on_key_press():
    global spam_thread
    if spam_thread is None or not spam_thread.is_alive():
        stop_event.clear()
        spam_thread = threading.Thread(target=spam_loop, daemon=True)
        spam_thread.start()


def on_key_release():
    stop_event.set()


keyboard.on_press_key(KEY, lambda e: on_key_press())
keyboard.on_release_key(KEY, lambda e: on_key_release())

print(f"Hold '{KEY}' to spam. Release to stop. Ctrl+C to exit.")
keyboard.wait()
