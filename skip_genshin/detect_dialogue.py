import cv2
import numpy as np
import mss
import time
import os
from utils import track_changes

DEBUG_SAVED = False  # Flag to save debug image only once
DEBUG = False

# Path to the template image
TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "img", "template.png")

# Region of interest (ROI) - adjust these values to match where the icon appears
# Format: (left, top, width, height)
# Set to None to scan the full screen, or specify coordinates for better performance
ROI = {
    "left": 270,
    "top": 28,
    "width": 40,
    "height": 40,
}  # Example: {"left": 1800, "top": 100, "width": 100, "height": 100}

# Detection threshold (0.0 to 1.0) - higher = more strict matching
THRESHOLD = 0.95

# Check interval in seconds
CHECK_INTERVAL = 0.1


def load_template():
    """Load the template image with alpha channel for masking transparency, resized to ROI."""
    # Load with alpha channel (IMREAD_UNCHANGED preserves transparency)
    template_bgra = cv2.imread(TEMPLATE_PATH, cv2.IMREAD_UNCHANGED)
    if template_bgra is None:
        raise FileNotFoundError(f"Template not found at: {TEMPLATE_PATH}")

    # Resize template to match ROI size
    target_size = (ROI["width"], ROI["height"])
    template_bgra = cv2.resize(template_bgra, target_size, interpolation=cv2.INTER_AREA)

    # Check if template has alpha channel
    if template_bgra.shape[2] == 4:
        # Extract BGR and alpha channel
        template_bgr = template_bgra[:, :, :3]
        alpha = template_bgra[:, :, 3]
        # Create mask from alpha channel (non-transparent pixels = 255)
        mask = alpha.copy()
        return template_bgr, mask
    else:
        # No alpha channel, no mask needed
        return template_bgra, None


def save_debug_image(img, filename="debug_capture.png"):
    """Save the captured region for debugging purposes."""
    global DEBUG_SAVED
    if not DEBUG_SAVED:
        debug_path = os.path.join(os.path.dirname(__file__), filename)
        cv2.imwrite(debug_path, img)
        print(f"DEBUG: Saved captured region to {debug_path}")
        DEBUG_SAVED = True


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

        # Save debug image once
        if DEBUG:
            save_debug_image(bgr)

        return bgr


# Cached template data for the simple function mode
_cached_template = None
_cached_mask = None


def _get_cached_template():
    """Load and cache the template for reuse."""
    global _cached_template, _cached_mask
    if _cached_template is None:
        _cached_template, _cached_mask = load_template()
    return _cached_template, _cached_mask


@track_changes(name="DIALOGUE", true_message="DETECTED", false_message="CLEARED")
def is_dialogue_detected(threshold=THRESHOLD):
    """
    Check if dialogue icon is currently visible on screen.
    Returns True if detected, False otherwise.

    This is a simple synchronous function that can be called directly
    without needing to set up threads or callbacks.
    """
    try:
        template, mask = _get_cached_template()
        screen = capture_screen(ROI)
        return detect_icon(screen, template, mask, threshold)
    except Exception as e:
        if DEBUG:
            print(f"Detection error: {e}")
        return False


def detect_icon(screen, template, mask=None, threshold=THRESHOLD):
    """
    Detect if the template icon is present in the screen.
    Uses mask to ignore transparent pixels in template.
    Returns True if detected, False otherwise.
    """
    # If template and screen are the same size, use direct comparison
    if screen.shape[:2] == template.shape[:2]:
        if mask is not None:
            # Normalize mask to 0-1 range
            mask_norm = mask.astype(np.float32) / 255.0
            mask_3ch = np.stack([mask_norm] * 3, axis=-1)

            # Calculate masked difference
            diff = np.abs(screen.astype(np.float32) - template.astype(np.float32))
            masked_diff = diff * mask_3ch

            # Calculate similarity (1 - normalized error)
            max_error = np.sum(mask_3ch) * 255.0
            if max_error > 0:
                error = np.sum(masked_diff) / max_error
                max_val = 1.0 - error
            else:
                max_val = 0.0
        else:
            # Simple normalized comparison
            diff = np.abs(screen.astype(np.float32) - template.astype(np.float32))
            max_val = 1.0 - (np.mean(diff) / 255.0)
    else:
        # Template matching with optional mask for transparency
        if mask is not None:
            result = cv2.matchTemplate(screen, template, cv2.TM_CCORR_NORMED, mask=mask)
        else:
            result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)

        # Find the best match
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    # Check if the match exceeds the threshold
    if DEBUG:
        print(f"Detection confidence: {max_val:.3f}")
    return max_val >= threshold


def start_detection_daemon(callback):
    """
    Daemon mode: Continuous detection loop (meant to run in a thread).
    Calls callback(True) when dialogue icon is detected.
    Calls callback(False) when dialogue icon is not detected.

    Use this for daemon/thread mode. For simple synchronous checks,
    use is_dialogue_detected() instead.
    """
    print("Loading template...")
    template, mask = load_template()
    print(f"Template loaded: {template.shape}")
    if mask is not None:
        print("Transparency mask enabled")
    print("Starting dialogue detection daemon...")

    while True:
        try:
            # Capture screen
            screen = capture_screen(ROI)

            # Detect the icon
            detected = detect_icon(screen, template, mask)

            # Call the callback with detection result
            callback(detected)

        except Exception as e:
            print(f"Detection error: {e}")
            callback(False)

        time.sleep(CHECK_INTERVAL)


# Alias for backwards compatibility
on_detect_do_sometthing = start_detection_daemon


if __name__ == "__main__":
    DEBUG = True

    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--daemon":
        # Daemon mode test
        def test_callback(detected):
            if detected:
                print("✓ DIALOGUE DETECTED")
            else:
                print("✗ No dialogue")

        print("Running detection daemon test... Press CTRL+C to stop")
        start_detection_daemon(test_callback)
    else:
        # Simple function mode test
        print("Running simple detection test... Press CTRL+C to stop")
        print("Use --daemon flag to test daemon mode")
        while True:
            detected = is_dialogue_detected()
            if detected:
                print("✓ DIALOGUE DETECTED")
            else:
                print("✗ No dialogue")
            time.sleep(CHECK_INTERVAL)
