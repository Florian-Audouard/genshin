"""
Standalone keyboard and mouse button listener helper.
Displays key names and button clicks in the terminal in real-time.
"""

import keyboard
import mouse
from threading import Thread


def listen_keyboard():
    """Listen for keyboard events and print key names."""
    print("[Keyboard Listener] Started listening for keyboard events...")

    def on_key_event(event):
        if event.event_type == "down":
            print(f"[KEY DOWN] {event.name}")
        elif event.event_type == "up":
            print(f"[KEY UP] {event.name}")

    keyboard.on_press(on_key_event)


def listen_mouse():
    """Listen for mouse button events and print button names."""
    print("[Mouse Listener] Started listening for mouse button clicks...")

    def on_mouse_event(event):
        if isinstance(event, mouse.MouseEvent):
            if event.event_type == "down":
                print(f"[MOUSE DOWN] {event.button}")
            elif event.event_type == "up":
                print(f"[MOUSE UP] {event.button}")

    mouse.on_click(lambda: print("[MOUSE CLICK] left"))


def on_mouse_click(button, x, y, pressed):
    """Callback for mouse button clicks."""
    action = "down" if pressed else "up"
    print(f"[MOUSE {action.upper()}] {button} at ({x}, {y})")


def main():
    """Start listening for keyboard and mouse events."""
    print("=" * 60)
    print("Keyboard & Mouse Button Listener")
    print("=" * 60)
    print("Press ESC to stop the listener")
    print("=" * 60)

    # Start keyboard listener in a separate thread
    keyboard_thread = Thread(target=listen_keyboard, daemon=True)
    keyboard_thread.start()

    # Start mouse listener in a separate thread
    mouse_thread = Thread(target=listen_mouse, daemon=True)
    mouse_thread.start()

    # Wait for ESC key to stop
    try:
        keyboard.wait("esc")
        print("\n[INFO] ESC pressed. Stopping listeners...")
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted. Stopping listeners...")


if __name__ == "__main__":
    main()
