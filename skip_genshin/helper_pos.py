import pyautogui
from pynput import keyboard


def on_press(key):
    try:
        if key == keyboard.Key.f8:
            print(pyautogui.position())
    except AttributeError:
        pass


listener = keyboard.Listener(on_press=on_press)
listener.start()

while True:
    pass
