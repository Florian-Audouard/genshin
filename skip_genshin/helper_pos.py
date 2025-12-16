import cv2
import numpy as np
import mss
import pyautogui
from pynput import keyboard

# Define your ROI here (same format as detect_dialogue.py)
ROI = {
    "left": 79,
    "top": 32,
    "width": 34,
    "height": 37,
}


def capture_screen(region=None):
    """Capture the screen or a specific region in color."""
    with mss.mss() as sct:
        if region:
            monitor = region
        else:
            monitor = sct.monitors[1]  # Primary monitor

        screenshot = sct.grab(monitor)
        # Convert to numpy array (BGRA) then to BGR
        img = np.array(screenshot)
        bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        return bgr


def capture_roi(roi):
    """Capture a screenshot of the specified ROI and display it."""
    img = capture_screen(roi)
    # save img to file
    filename = "captured_roi.png"
    cv2.imwrite(filename, img)
    print(f"Captured ROI saved to {filename}")


def on_press(key):
    try:
        if key == keyboard.Key.f8:
            print(pyautogui.position())
        elif key == keyboard.Key.f7:
            print(f"Capturing ROI: {ROI}")
            capture_roi(ROI)
    except AttributeError:
        pass


listener = keyboard.Listener(on_press=on_press)
listener.start()

print("Press F7 to capture ROI, F8 to get mouse position, Ctrl+C to exit")
while True:
    pass
