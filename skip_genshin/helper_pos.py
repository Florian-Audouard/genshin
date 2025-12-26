import cv2
import numpy as np
import mss
import pyautogui
from pynput import keyboard
import time
import tkinter as tk
from tkinter import ttk, scrolledtext
from PIL import Image, ImageTk
import threading
from datetime import datetime
import io
import win32clipboard

# Default ROI
ROI = {"left": 0, "top": 0, "width": 1000, "height": 1000}


class ROIHelperGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ROI Helper Tool")
        self.root.geometry("600x700")
        self.root.resizable(True, True)

        # ROI values
        self.roi_left = tk.IntVar(value=ROI["left"])
        self.roi_top = tk.IntVar(value=ROI["top"])
        self.roi_width = tk.IntVar(value=ROI["width"])
        self.roi_height = tk.IntVar(value=ROI["height"])

        # Live preview toggle
        self.live_preview = tk.BooleanVar(value=True)
        self.running = True

        self.setup_ui()
        self.setup_keyboard_listener()
        self.start_live_preview()

    def setup_ui(self):
        """Setup the GUI components."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ROI Controls Frame
        roi_frame = ttk.LabelFrame(main_frame, text="ROI Settings", padding="10")
        roi_frame.pack(fill=tk.X, pady=(0, 10))

        # Left
        ttk.Label(roi_frame, text="Left:").grid(row=0, column=0, sticky=tk.W, padx=5)
        left_spin = ttk.Spinbox(
            roi_frame, from_=0, to=3840, textvariable=self.roi_left, width=10
        )
        left_spin.grid(row=0, column=1, padx=5, pady=2)

        # Top
        ttk.Label(roi_frame, text="Top:").grid(row=0, column=2, sticky=tk.W, padx=5)
        top_spin = ttk.Spinbox(
            roi_frame, from_=0, to=2160, textvariable=self.roi_top, width=10
        )
        top_spin.grid(row=0, column=3, padx=5, pady=2)

        # Width
        ttk.Label(roi_frame, text="Width:").grid(row=1, column=0, sticky=tk.W, padx=5)
        width_spin = ttk.Spinbox(
            roi_frame, from_=1, to=1920, textvariable=self.roi_width, width=10
        )
        width_spin.grid(row=1, column=1, padx=5, pady=2)

        # Height
        ttk.Label(roi_frame, text="Height:").grid(row=1, column=2, sticky=tk.W, padx=5)
        height_spin = ttk.Spinbox(
            roi_frame, from_=1, to=1080, textvariable=self.roi_height, width=10
        )
        height_spin.grid(row=1, column=3, padx=5, pady=2)

        # Buttons frame
        btn_frame = ttk.Frame(roi_frame)
        btn_frame.grid(row=2, column=0, columnspan=4, pady=10)

        ttk.Button(
            btn_frame, text="Set from Mouse (F8)", command=self.set_roi_from_mouse
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            btn_frame, text="Capture ROI (F7)", command=self.capture_current_roi
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            btn_frame, text="Copy Image", command=self.copy_image_to_clipboard
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Copy ROI Code", command=self.copy_roi_code).pack(
            side=tk.LEFT, padx=5
        )

        # Live preview checkbox
        ttk.Checkbutton(
            roi_frame, text="Live Preview", variable=self.live_preview
        ).grid(row=3, column=0, columnspan=4)

        # Preview Frame
        preview_frame = ttk.LabelFrame(
            main_frame, text="ROI Live Preview", padding="10"
        )
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Canvas for image preview
        self.canvas = tk.Canvas(preview_frame, bg="gray", width=400, height=300)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Current mouse position display
        pos_frame = ttk.Frame(main_frame)
        pos_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(pos_frame, text="Current Mouse Position:").pack(side=tk.LEFT)
        self.mouse_pos_label = ttk.Label(
            pos_frame, text="(0, 0)", font=("Consolas", 12)
        )
        self.mouse_pos_label.pack(side=tk.LEFT, padx=10)

        # Log Frame
        log_frame = ttk.LabelFrame(
            main_frame, text="Mouse Position Log (F8 to log)", padding="10"
        )
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=8, font=("Consolas", 10)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Clear log button
        ttk.Button(log_frame, text="Clear Log", command=self.clear_log).pack(pady=5)

        # Status bar
        self.status_var = tk.StringVar(
            value="Ready - Press F7 to capture, F8 to log mouse position"
        )
        status_bar = ttk.Label(
            self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W
        )
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def get_current_roi(self):
        """Get the current ROI dictionary."""
        return {
            "left": self.roi_left.get(),
            "top": self.roi_top.get(),
            "width": self.roi_width.get(),
            "height": self.roi_height.get(),
        }

    def capture_screen(self, region=None):
        """Capture the screen or a specific region in color."""
        with mss.mss() as sct:
            if region:
                monitor = region
            else:
                monitor = sct.monitors[1]

            screenshot = sct.grab(monitor)
            img = np.array(screenshot)
            bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            return bgr

    def capture_current_roi(self):
        """Capture the current ROI and save to file."""
        roi = self.get_current_roi()
        img = self.capture_screen(roi)
        filename = "captured_roi.png"
        cv2.imwrite(filename, img)
        self.log_message(f"ROI captured and saved to {filename}")
        self.status_var.set(f"ROI saved to {filename}")

    def copy_image_to_clipboard(self):
        """Capture the current ROI and copy to clipboard."""
        roi = self.get_current_roi()
        img = self.capture_screen(roi)

        # Convert BGR to RGB
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)

        # Convert to BMP format for Windows clipboard
        output = io.BytesIO()
        pil_img.convert("RGB").save(output, "BMP")
        data = output.getvalue()[14:]  # Remove BMP header
        output.close()

        # Copy to clipboard
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()

        self.log_message(
            f"ROI image copied to clipboard ({roi['width']}x{roi['height']})"
        )
        self.status_var.set("Image copied to clipboard!")

    def set_roi_from_mouse(self):
        """Set ROI position from current mouse position."""
        pos = pyautogui.position()
        self.roi_left.set(pos[0])
        self.roi_top.set(pos[1])
        self.log_message(f"ROI position set to ({pos[0]}, {pos[1]})")
        self.status_var.set(f"ROI position updated to ({pos[0]}, {pos[1]})")

    def copy_roi_code(self):
        """Copy the ROI dictionary code to clipboard."""
        roi = self.get_current_roi()
        code = f'{{"left": {roi["left"]}, "top": {roi["top"]}, "width": {roi["width"]}, "height": {roi["height"]}}}'
        self.root.clipboard_clear()
        self.root.clipboard_append(code)
        self.status_var.set("ROI code copied to clipboard!")
        self.log_message(f"Copied: {code}")

    def log_message(self, message):
        """Add a timestamped message to the log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)

    def log_mouse_position(self):
        """Log current mouse position."""
        pos = pyautogui.position()
        self.log_message(f"Mouse Position: ({pos[0]}, {pos[1]})")
        self.status_var.set(f"Logged mouse position: ({pos[0]}, {pos[1]})")

    def clear_log(self):
        """Clear the log text."""
        self.log_text.delete(1.0, tk.END)
        self.status_var.set("Log cleared")

    def update_preview(self):
        """Update the live preview of the ROI."""
        if not self.running:
            return

        try:
            # Update mouse position label
            pos = pyautogui.position()
            self.mouse_pos_label.config(text=f"({pos[0]}, {pos[1]})")

            if self.live_preview.get():
                roi = self.get_current_roi()

                # Capture ROI
                img = self.capture_screen(roi)

                # Convert BGR to RGB for PIL
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

                # Get canvas size
                canvas_width = self.canvas.winfo_width()
                canvas_height = self.canvas.winfo_height()

                if canvas_width > 1 and canvas_height > 1:
                    # Calculate scale to fit canvas while maintaining aspect ratio
                    img_h, img_w = img_rgb.shape[:2]
                    scale = min(
                        canvas_width / img_w, canvas_height / img_h, 5
                    )  # Max 5x zoom

                    new_w = max(1, int(img_w * scale))
                    new_h = max(1, int(img_h * scale))

                    # Resize image
                    img_resized = cv2.resize(
                        img_rgb, (new_w, new_h), interpolation=cv2.INTER_NEAREST
                    )

                    # Convert to PhotoImage
                    pil_img = Image.fromarray(img_resized)
                    self.photo = ImageTk.PhotoImage(pil_img)

                    # Update canvas
                    self.canvas.delete("all")
                    self.canvas.create_image(
                        canvas_width // 2,
                        canvas_height // 2,
                        image=self.photo,
                        anchor=tk.CENTER,
                    )

                    # Draw info text
                    info_text = f"ROI: {roi['width']}x{roi['height']} @ ({roi['left']}, {roi['top']})"
                    self.canvas.create_text(
                        10,
                        10,
                        text=info_text,
                        anchor=tk.NW,
                        fill="white",
                        font=("Consolas", 10),
                    )
        except Exception as e:
            pass  # Ignore errors during preview update

        # Schedule next update
        if self.running:
            self.root.after(33, self.update_preview)  # ~30 FPS

    def start_live_preview(self):
        """Start the live preview update loop."""
        self.update_preview()

    def setup_keyboard_listener(self):
        """Setup global keyboard listener for F7 and F8."""

        def on_press(key):
            try:
                if key == keyboard.Key.f8:
                    # Schedule log_mouse_position on main thread
                    self.root.after(0, self.log_mouse_position)
                elif key == keyboard.Key.f7:
                    # Schedule capture on main thread
                    self.root.after(0, self.capture_current_roi)
            except AttributeError:
                pass

        self.listener = keyboard.Listener(on_press=on_press)
        self.listener.start()

    def on_closing(self):
        """Handle window close."""
        self.running = False
        self.listener.stop()
        self.root.destroy()

    def run(self):
        """Run the GUI application."""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()


def main():
    app = ROIHelperGUI()
    app.run()


if __name__ == "__main__":
    main()
