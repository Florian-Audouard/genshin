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
import os

# Import detection modules for comparison
from detect_dialogue import (
    ROI_DIALOGUE,
    THRESHOLD as DIALOGUE_THRESHOLD,
    _get_cached_template as get_dialogue_template,
    detect_icon as detect_dialogue_icon,
)
from detect_page import (
    PAGE_CONFIGS,
    get_cached_template as get_page_template,
    detect_icon as detect_page_icon,
    DEFAULT_THRESHOLD as PAGE_DEFAULT_THRESHOLD,
    DEFAULT_COLOR_TOLERANCE,
)

# Default ROI
ROI = {"left": 0, "top": 0, "width": 1000, "height": 1000}

# Detection configurations for comparison
DETECTION_CONFIGS = {
    "DIALOGUE": {
        "roi": ROI_DIALOGUE,
        "threshold": DIALOGUE_THRESHOLD,
        "get_template": get_dialogue_template,
        "detect_func": detect_dialogue_icon,
    },
}

# Add page configs dynamically
for page_name, config in PAGE_CONFIGS.items():
    DETECTION_CONFIGS[page_name] = {
        "roi": config["roi"],
        "threshold": config["threshold"],
        "get_template": lambda pn=page_name: get_page_template(pn),
        "detect_func": lambda pn, s, t, m, th, ct=DEFAULT_COLOR_TOLERANCE: detect_page_icon(
            pn, s, t, m, th, ct
        ),
        "page_name": page_name,
    }


class ROIHelperGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ROI Helper Tool")
        self.root.geometry("900x800")
        self.root.resizable(True, True)

        # ROI values
        self.roi_left = tk.IntVar(value=ROI["left"])
        self.roi_top = tk.IntVar(value=ROI["top"])
        self.roi_width = tk.IntVar(value=ROI["width"])
        self.roi_height = tk.IntVar(value=ROI["height"])

        # Live preview toggle
        self.live_preview = tk.BooleanVar(value=True)
        self.running = True

        # Detection comparison
        self.selected_detection = tk.StringVar(value="DIALOGUE")
        self.comparison_enabled = tk.BooleanVar(value=True)
        self.current_confidence = tk.StringVar(value="N/A")
        self.detection_status = tk.StringVar(value="---")

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

        # Detection Comparison Frame
        compare_frame = ttk.LabelFrame(
            main_frame, text="Detection Comparison", padding="10"
        )
        compare_frame.pack(fill=tk.X, pady=(0, 10))

        # Enable comparison checkbox
        ttk.Checkbutton(
            compare_frame,
            text="Enable Comparison",
            variable=self.comparison_enabled,
            command=self.on_comparison_toggle,
        ).grid(row=0, column=0, sticky=tk.W, padx=5)

        # Detection selector
        ttk.Label(compare_frame, text="Detection:").grid(
            row=0, column=1, sticky=tk.W, padx=5
        )
        detection_combo = ttk.Combobox(
            compare_frame,
            textvariable=self.selected_detection,
            values=list(DETECTION_CONFIGS.keys()),
            state="readonly",
            width=15,
        )
        detection_combo.grid(row=0, column=2, padx=5)
        detection_combo.bind("<<ComboboxSelected>>", self.on_detection_changed)

        # Apply ROI button
        ttk.Button(
            compare_frame, text="Apply Detection ROI", command=self.apply_detection_roi
        ).grid(row=0, column=3, padx=5)

        # Threshold and confidence display
        info_frame = ttk.Frame(compare_frame)
        info_frame.grid(row=1, column=0, columnspan=4, pady=5, sticky=tk.W)

        ttk.Label(info_frame, text="Threshold:").pack(side=tk.LEFT, padx=5)
        self.threshold_label = ttk.Label(
            info_frame, text="0.95", font=("Consolas", 11, "bold")
        )
        self.threshold_label.pack(side=tk.LEFT, padx=5)

        ttk.Label(info_frame, text="Confidence:").pack(side=tk.LEFT, padx=15)
        self.confidence_label = ttk.Label(
            info_frame,
            textvariable=self.current_confidence,
            font=("Consolas", 11, "bold"),
            foreground="gray",
        )
        self.confidence_label.pack(side=tk.LEFT, padx=5)

        ttk.Label(info_frame, text="Status:").pack(side=tk.LEFT, padx=15)
        self.status_detection_label = ttk.Label(
            info_frame,
            textvariable=self.detection_status,
            font=("Consolas", 11, "bold"),
        )
        self.status_detection_label.pack(side=tk.LEFT, padx=5)

        # Preview Frame with comparison
        preview_frame = ttk.LabelFrame(
            main_frame, text="ROI Live Preview", padding="10"
        )
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Create a frame to hold all canvases side by side
        canvas_container = ttk.Frame(preview_frame)
        canvas_container.pack(fill=tk.BOTH, expand=True)

        # Left canvas for ROI preview
        left_frame = ttk.Frame(canvas_container)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        ttk.Label(left_frame, text="Current ROI", font=("Consolas", 9)).pack()
        self.canvas = tk.Canvas(left_frame, bg="gray", width=200, height=250)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Middle canvas for threshold/difference view
        middle_frame = ttk.Frame(canvas_container)
        middle_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        ttk.Label(
            middle_frame, text="Threshold View (Diff)", font=("Consolas", 9)
        ).pack()
        self.threshold_canvas = tk.Canvas(
            middle_frame, bg="gray", width=200, height=250
        )
        self.threshold_canvas.pack(fill=tk.BOTH, expand=True)

        # Right canvas for template comparison
        right_frame = ttk.Frame(canvas_container)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        ttk.Label(right_frame, text="Template", font=("Consolas", 9)).pack()
        self.template_canvas = tk.Canvas(right_frame, bg="gray", width=200, height=250)
        self.template_canvas.pack(fill=tk.BOTH, expand=True)

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

    def on_comparison_toggle(self):
        """Handle comparison toggle."""
        if self.comparison_enabled.get():
            self.on_detection_changed(None)

    def on_detection_changed(self, event):
        """Handle detection selection change."""
        detection_name = self.selected_detection.get()
        if detection_name in DETECTION_CONFIGS:
            config = DETECTION_CONFIGS[detection_name]
            self.threshold_label.config(text=f"{config['threshold']:.2f}")

    def apply_detection_roi(self):
        """Apply the ROI from the selected detection to the current ROI."""
        detection_name = self.selected_detection.get()
        if detection_name in DETECTION_CONFIGS:
            config = DETECTION_CONFIGS[detection_name]
            roi = config["roi"]
            self.roi_left.set(roi["left"])
            self.roi_top.set(roi["top"])
            self.roi_width.set(roi["width"])
            self.roi_height.set(roi["height"])
            self.log_message(f"Applied ROI from {detection_name}: {roi}")
            self.status_var.set(f"Applied ROI from {detection_name}")

    def calculate_confidence(
        self, screen, template, mask=None, color_tolerance=DEFAULT_COLOR_TOLERANCE
    ):
        """Calculate match confidence between screen and template.
        color_tolerance: pixels within this difference (0-255) are considered matching.
        """
        if screen.shape[:2] != template.shape[:2]:
            # Resize screen to match template
            screen = cv2.resize(
                screen,
                (template.shape[1], template.shape[0]),
                interpolation=cv2.INTER_AREA,
            )

        if mask is not None:
            mask_norm = mask.astype(np.float32) / 255.0
            mask_3ch = np.stack([mask_norm] * 3, axis=-1)
            diff = np.abs(screen.astype(np.float32) - template.astype(np.float32))
            # Apply color tolerance: differences below tolerance are zeroed out
            diff = np.maximum(diff - color_tolerance, 0.0)
            masked_diff = diff * mask_3ch
            max_error = np.sum(mask_3ch) * (255.0 - color_tolerance)
            if max_error > 0:
                error = np.sum(masked_diff) / max_error
                confidence = 1.0 - error
            else:
                confidence = 0.0
        else:
            diff = np.abs(screen.astype(np.float32) - template.astype(np.float32))
            # Apply color tolerance: differences below tolerance are zeroed out
            diff = np.maximum(diff - color_tolerance, 0.0)
            confidence = 1.0 - (np.mean(diff) / (255.0 - color_tolerance))

        return confidence

    def update_comparison(self, screen_img):
        """Update the comparison display with template and confidence."""
        detection_name = self.selected_detection.get()
        if detection_name not in DETECTION_CONFIGS:
            return

        config = DETECTION_CONFIGS[detection_name]
        threshold = config["threshold"]

        try:
            # Get template
            template, mask = config["get_template"]()

            # Calculate confidence
            confidence = self.calculate_confidence(screen_img, template, mask)

            # Update confidence label
            self.current_confidence.set(f"{confidence:.4f}")

            # Update color based on threshold
            if confidence >= threshold:
                self.confidence_label.config(foreground="green")
                self.detection_status.set("DETECTED")
                self.status_detection_label.config(foreground="green")
            else:
                self.confidence_label.config(foreground="red")
                self.detection_status.set("NOT DETECTED")
                self.status_detection_label.config(foreground="red")

            # Update template canvas
            self.update_template_canvas(template, mask)

            # Update threshold/difference canvas
            self.update_threshold_canvas(
                screen_img, template, mask, threshold, confidence
            )

        except Exception as e:
            self.current_confidence.set(f"Error: {e}")
            self.confidence_label.config(foreground="gray")

    def update_template_canvas(self, template, mask=None):
        """Update the template canvas with the template image."""
        try:
            # Convert BGR to RGB
            template_rgb = cv2.cvtColor(template, cv2.COLOR_BGR2RGB)

            # Apply mask visualization if available
            if mask is not None:
                # Create an overlay showing masked areas
                mask_overlay = np.zeros_like(template_rgb)
                mask_overlay[:, :, 0] = mask  # Red channel shows mask
                template_rgb = cv2.addWeighted(template_rgb, 0.7, mask_overlay, 0.3, 0)

            # Get canvas size
            canvas_width = self.template_canvas.winfo_width()
            canvas_height = self.template_canvas.winfo_height()

            if canvas_width > 1 and canvas_height > 1:
                # Calculate scale to fit canvas
                img_h, img_w = template_rgb.shape[:2]
                scale = min(
                    canvas_width / img_w, canvas_height / img_h, 10
                )  # Max 10x zoom

                new_w = max(1, int(img_w * scale))
                new_h = max(1, int(img_h * scale))

                # Resize image
                img_resized = cv2.resize(
                    template_rgb, (new_w, new_h), interpolation=cv2.INTER_NEAREST
                )

                # Convert to PhotoImage
                pil_img = Image.fromarray(img_resized)
                self.template_photo = ImageTk.PhotoImage(pil_img)

                # Update canvas
                self.template_canvas.delete("all")
                self.template_canvas.create_image(
                    canvas_width // 2,
                    canvas_height // 2,
                    image=self.template_photo,
                    anchor=tk.CENTER,
                )

                # Draw template info
                info_text = f"Template: {img_w}x{img_h}"
                self.template_canvas.create_text(
                    10,
                    10,
                    text=info_text,
                    anchor=tk.NW,
                    fill="white",
                    font=("Consolas", 10),
                )
        except Exception as e:
            pass

    def update_threshold_canvas(
        self, screen_img, template, mask=None, threshold=0.95, confidence=0.0
    ):
        """Update the threshold canvas showing the difference/thresholded view."""
        try:
            # Resize screen to match template if needed
            if screen_img.shape[:2] != template.shape[:2]:
                screen_resized = cv2.resize(
                    screen_img,
                    (template.shape[1], template.shape[0]),
                    interpolation=cv2.INTER_AREA,
                )
            else:
                screen_resized = screen_img.copy()

            # Calculate absolute difference
            diff = cv2.absdiff(screen_resized, template)

            # Convert to grayscale for better visualization
            diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)

            # Apply mask if available (only show masked regions)
            if mask is not None:
                # Normalize mask
                mask_norm = (mask > 0).astype(np.uint8) * 255
                diff_gray = cv2.bitwise_and(diff_gray, diff_gray, mask=mask_norm)

            # Create a visualization with threshold indicator
            # The whiter the pixel, the more difference there is
            # Apply threshold to show what would be considered "matching"
            # Lower threshold = more forgiving, higher = stricter

            # Calculate per-pixel match (inverted diff normalized)
            match_score = 255 - diff_gray  # Higher = better match

            # Create color-coded visualization
            # Green = good match, Red = poor match
            vis_img = np.zeros(
                (diff_gray.shape[0], diff_gray.shape[1], 3), dtype=np.uint8
            )

            # Threshold for color coding (convert 0-1 threshold to 0-255 range for diff)
            # If confidence threshold is 0.95, then max allowed diff per pixel is ~12 (255 * 0.05)
            diff_threshold = int(255 * (1.0 - threshold))

            # Green channel for matching pixels (low difference)
            vis_img[:, :, 1] = np.where(diff_gray <= diff_threshold, 255, 0)
            # Red channel for non-matching pixels (high difference)
            vis_img[:, :, 2] = np.where(diff_gray > diff_threshold, diff_gray, 0)
            # Blue channel shows the actual difference intensity
            vis_img[:, :, 0] = diff_gray // 2

            # Apply mask visibility
            if mask is not None:
                # Darken non-masked areas
                mask_3ch = np.stack([mask_norm] * 3, axis=-1) / 255.0
                vis_img = (vis_img * mask_3ch).astype(np.uint8)

            # Get canvas size
            canvas_width = self.threshold_canvas.winfo_width()
            canvas_height = self.threshold_canvas.winfo_height()

            if canvas_width > 1 and canvas_height > 1:
                # Calculate scale to fit canvas
                img_h, img_w = vis_img.shape[:2]
                scale = min(
                    canvas_width / img_w, canvas_height / img_h, 10
                )  # Max 10x zoom

                new_w = max(1, int(img_w * scale))
                new_h = max(1, int(img_h * scale))

                # Resize image
                img_resized = cv2.resize(
                    vis_img, (new_w, new_h), interpolation=cv2.INTER_NEAREST
                )

                # Convert BGR to RGB for PIL
                img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)

                # Convert to PhotoImage
                pil_img = Image.fromarray(img_rgb)
                self.threshold_photo = ImageTk.PhotoImage(pil_img)

                # Update canvas
                self.threshold_canvas.delete("all")
                self.threshold_canvas.create_image(
                    canvas_width // 2,
                    canvas_height // 2,
                    image=self.threshold_photo,
                    anchor=tk.CENTER,
                )

                # Draw info text
                status = "PASS" if confidence >= threshold else "FAIL"
                color = "lime" if confidence >= threshold else "red"
                info_text = f"Thresh: {threshold:.2f} | {status}"
                self.threshold_canvas.create_text(
                    10,
                    10,
                    text=info_text,
                    anchor=tk.NW,
                    fill=color,
                    font=("Consolas", 10, "bold"),
                )

                # Add legend
                self.threshold_canvas.create_text(
                    10,
                    canvas_height - 10,
                    text="Green=Match | Red=Diff",
                    anchor=tk.SW,
                    fill="white",
                    font=("Consolas", 8),
                )
        except Exception as e:
            pass

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

                # Update comparison if enabled
                if self.comparison_enabled.get():
                    self.update_comparison(img)

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
