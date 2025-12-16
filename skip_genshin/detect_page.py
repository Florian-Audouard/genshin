import cv2
import numpy as np
import mss
import time
import os
from utils import track_changes

DEBUG_SAVED = False  # Flag to save debug image only once
DEBUG = False

# Path to the template image for the page indicator/icon
PAGE_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "img", "template_page.png")

# Region of interest (ROI) where the page indicator lives
# Format: (left, top, width, height)
ROI_PAGE = {
    "left": 79,
    "top": 32,
    "width": 34,
    "height": 37,
}

# Detection threshold (0.0 to 1.0) - higher = more strict matching
THRESHOLD = 0.95

# Check interval in seconds
CHECK_INTERVAL = 0.1


def load_template():
    """Load the template image with alpha channel for masking transparency, resized to ROI."""
    template_bgra = cv2.imread(PAGE_TEMPLATE_PATH, cv2.IMREAD_UNCHANGED)
    if template_bgra is None:
        raise FileNotFoundError(f"Template not found at: {PAGE_TEMPLATE_PATH}")

    target_size = (ROI_PAGE["width"], ROI_PAGE["height"])
    template_bgra = cv2.resize(template_bgra, target_size, interpolation=cv2.INTER_AREA)

    if template_bgra.shape[2] == 4:
        template_bgr = template_bgra[:, :, :3]
        alpha = template_bgra[:, :, 3]
        mask = alpha.copy()
        return template_bgr, mask
    else:
        return template_bgra, None


def save_debug_image(img, filename="debug_capture_page.png"):
    """Save the captured region for debugging purposes (once)."""
    global DEBUG_SAVED
    if not DEBUG_SAVED:
        debug_path = os.path.join(os.path.dirname(__file__), filename)
        cv2.imwrite(debug_path, img)
        print(f"DEBUG: Saved captured region to {debug_path}")
        DEBUG_SAVED = True


def capture_screen(region=None):
    """Capture the screen or a specific region in color."""
    with mss.mss() as sct:
        monitor = region if region else sct.monitors[1]
        screenshot = sct.grab(monitor)
        img = np.array(screenshot)
        bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
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


@track_changes(name="PAGE", true_message="DETECTED", false_message="CLEARED")
def is_page_detected(threshold: float = THRESHOLD) -> bool:
    try:
        template, mask = _get_cached_template()
        screen = capture_screen(ROI_PAGE)
        return detect_icon(screen, template, mask, threshold)
    except Exception as e:
        if DEBUG:
            print(f"Detection error: {e}")
        return False


def detect_icon(screen, template, mask=None, threshold: float = THRESHOLD) -> bool:
    """
    Detect if the template icon is present in the screen.
    Uses mask to ignore transparent pixels in template.
    Returns True if detected, False otherwise.
    """
    if screen.shape[:2] == template.shape[:2]:
        if mask is not None:
            mask_norm = mask.astype(np.float32) / 255.0
            mask_3ch = np.stack([mask_norm] * 3, axis=-1)
            diff = np.abs(screen.astype(np.float32) - template.astype(np.float32))
            masked_diff = diff * mask_3ch
            max_error = np.sum(mask_3ch) * 255.0
            if max_error > 0:
                error = np.sum(masked_diff) / max_error
                max_val = 1.0 - error
            else:
                max_val = 0.0
        else:
            diff = np.abs(screen.astype(np.float32) - template.astype(np.float32))
            max_val = 1.0 - (np.mean(diff) / 255.0)
    else:
        if mask is not None:
            result = cv2.matchTemplate(screen, template, cv2.TM_CCORR_NORMED, mask=mask)
        else:
            result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)

    if DEBUG:
        print(f"Page detection confidence: {max_val:.3f}")
    return max_val >= threshold


def start_detection_daemon(callback):
    """
    Daemon mode: Continuous detection loop (meant to run in a thread).
    Calls callback(True) when page icon is detected.
    Calls callback(False) when page icon is not detected.

    Use this for daemon/thread mode. For simple synchronous checks,
    use is_page_detected() instead.
    """
    print("Loading page template...")
    template, mask = load_template()
    print(f"Template loaded: {template.shape}")
    if mask is not None:
        print("Transparency mask enabled")
    print("Starting page detection daemon...")

    while True:
        try:
            screen = capture_screen(ROI_PAGE)
            detected = detect_icon(screen, template, mask)
            callback(detected)
        except Exception as e:
            print(f"Detection error: {e}")
            callback(False)
        time.sleep(CHECK_INTERVAL)


# Alias for backwards compatibility/convenience
on_detect_do_sometthing = start_detection_daemon


def test_page_detection():
    """Simple looped test printing detection status every CHECK_INTERVAL seconds."""
    print("Running simple page detection test... Press CTRL+C to stop")
    while True:
        detected = is_page_detected()
        print("\u2713 PAGE DETECTED" if detected else "\u2717 No page")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    DEBUG = True

    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--daemon":

        def test_callback(detected):
            print("\u2713 PAGE DETECTED" if detected else "\u2717 No page")

        print("Running page detection daemon test... Press CTRL+C to stop")
        start_detection_daemon(test_callback)
    else:
        test_page_detection()
