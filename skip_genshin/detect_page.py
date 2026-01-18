import cv2
import numpy as np
import mss
import time
import os
from typing import Dict, Any, Optional, Tuple
from utils import track_changes

DEBUG_SAVED = {}  # Flag to save debug image only once per image
DEBUG = False
# Check interval in seconds
CHECK_INTERVAL = 0.1

# Default threshold
DEFAULT_THRESHOLD = 0.95

# Color tolerance for HDR/transparent icons (0-255)
# Higher value = more lenient color matching
DEFAULT_COLOR_TOLERANCE = 15

# 1920 x 1080
# ROI_PAGE_1 = {"left": 79, "top": 32, "width": 34, "height": 37}

# 3440 x 1440
ROI_PAGE_1 = {"left": 201, "top": 42, "width": 46, "height": 50}

# 1920 x 1080
# ROI_PAGE_2 = {"left": 946, "top": 1006, "width": 28, "height": 28}

# 3440 x 1440
ROI_PAGE_2 = {"left": 1701, "top": 1354, "width": 38, "height": 38}

# 3440 x 1440
ROI_PAGE_2_ALT = {"left": 1701, "top": 1341, "width": 38, "height": 38}


# 1920 x 1080
ROI_PAGE_4 = {"left": 946, "top": 1006, "width": 28, "height": 28}

# 3440 x 1440
ROI_PAGE_4 = {"left": 1701, "top": 1341, "width": 38, "height": 38}

# 3440 x 1440
ROI_PAGE_4_ALT = {"left": 1701, "top": 1373, "width": 38, "height": 38}

# Page detection configurations
# Each page has: template_path, roi, threshold
PAGE_CONFIGS: Dict[str, Dict[str, Any]] = {
    "PAGE_1": {
        "template": os.path.join(os.path.dirname(__file__), "img", "template_page.png"),
        "roi": ROI_PAGE_1,
        "threshold": DEFAULT_THRESHOLD,
    },
    "PAGE_2": {
        "template": os.path.join(
            os.path.dirname(__file__), "img", "template_page_2.png"
        ),
        "roi": ROI_PAGE_2,
        "threshold": DEFAULT_THRESHOLD,
    },
    "PAGE_2_ALT": {
        "template": os.path.join(
            os.path.dirname(__file__), "img", "template_page_2.png"
        ),
        "roi": ROI_PAGE_2_ALT,
        "threshold": DEFAULT_THRESHOLD,
    },
    "PAGE_4": {
        "template": os.path.join(
            os.path.dirname(__file__), "img", "template_page_4.png"
        ),
        "roi": ROI_PAGE_4,
        "threshold": DEFAULT_THRESHOLD,
    },
    "PAGE_4_ALT": {
        "template": os.path.join(
            os.path.dirname(__file__), "img", "template_page_2.png"
        ),
        "roi": ROI_PAGE_4_ALT,
        "threshold": DEFAULT_THRESHOLD,
    },
}

# Template cache: {page_name: (template, mask)}
_template_cache: Dict[str, Tuple[np.ndarray, Optional[np.ndarray]]] = {}


def load_template_for_page(page_name: str) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """Load template image for a given page configuration."""
    if page_name not in PAGE_CONFIGS:
        raise ValueError(
            f"Unknown page: {page_name}. Available: {list(PAGE_CONFIGS.keys())}"
        )

    config = PAGE_CONFIGS[page_name]
    template_path = config["template"]
    roi = config["roi"]

    template_bgra = cv2.imread(template_path, cv2.IMREAD_UNCHANGED)
    if template_bgra is None:
        raise FileNotFoundError(f"Template not found at: {template_path}")

    target_size = (roi["width"], roi["height"])
    template_bgra = cv2.resize(template_bgra, target_size, interpolation=cv2.INTER_AREA)

    if template_bgra.shape[2] == 4:
        template_bgr = template_bgra[:, :, :3]
        alpha = template_bgra[:, :, 3]
        mask = alpha.copy()
        return template_bgr, mask
    else:
        return template_bgra, None


def get_cached_template(page_name: str) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """Get cached template for a page, loading if necessary."""
    if page_name not in _template_cache:
        _template_cache[page_name] = load_template_for_page(page_name)
    return _template_cache[page_name]


def save_debug_image(img, filename):
    """Save the captured region for debugging purposes (once)."""
    global DEBUG_SAVED
    if filename not in DEBUG_SAVED:
        debug_folder = os.path.join(os.path.dirname(__file__), "debug")
        os.makedirs(debug_folder, exist_ok=True)
        debug_path = os.path.join(debug_folder, filename)
        cv2.imwrite(debug_path, img)
        print(f"DEBUG: Saved captured region to {debug_path}")
        DEBUG_SAVED[filename] = True


def capture_screen(config=None):
    """Capture the screen or a specific region in color."""
    region = config["roi"] if config else None
    with mss.mss() as sct:
        monitor = region if region else sct.monitors[1]
        screenshot = sct.grab(monitor)
        img = np.array(screenshot)
        bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        if DEBUG:
            save_debug_image(bgr, filename=f"debug_capture_{config['page_name']}.png")
        return bgr


def _is_page_detected_generic(
    page_name: str, threshold: Optional[float] = None
) -> bool:
    """Generic page detection for any configured page."""
    if page_name not in PAGE_CONFIGS:
        raise ValueError(
            f"Unknown page: {page_name}. Available: {list(PAGE_CONFIGS.keys())}"
        )

    config = PAGE_CONFIGS[page_name]
    config["page_name"] = page_name
    if threshold is None:
        threshold = config["threshold"]

    try:
        template, mask = get_cached_template(page_name)
        screen = capture_screen(config)
        return detect_icon(page_name, screen, template, mask, threshold)
    except Exception as e:
        if DEBUG:
            print(f"Detection error ({page_name}): {e}")
        return False


# Create decorated detection functions for each page
@track_changes(name="PAGE_1", true_message="DETECTED", false_message="CLEARED")
def is_page_detected_1(threshold: Optional[float] = None) -> bool:
    """Detect PAGE_1 template."""
    return _is_page_detected_generic("PAGE_1", threshold)


@track_changes(name="PAGE_2", true_message="DETECTED", false_message="CLEARED")
def is_page_detected_2(threshold: Optional[float] = None) -> bool:
    """Detect PAGE_2 template."""
    return _is_page_detected_generic("PAGE_2", threshold) or _is_page_detected_generic(
        "PAGE_2_ALT", threshold
    )


@track_changes(name="PAGE_3", true_message="DETECTED", false_message="CLEARED")
def is_page_detected_3(threshold: Optional[float] = None) -> bool:
    """Detect PAGE_3 template."""
    return _is_page_detected_generic("PAGE_3", threshold)


@track_changes(name="PAGE_4", true_message="DETECTED", false_message="CLEARED")
def is_page_detected_4(threshold: Optional[float] = None) -> bool:
    """Detect PAGE_4 template."""
    return _is_page_detected_generic("PAGE_4", threshold) or _is_page_detected_generic(
        "PAGE_4_ALT", threshold
    )


def detect_icon(
    page_name,
    screen,
    template,
    mask=None,
    threshold: float = DEFAULT_THRESHOLD,
    color_tolerance: int = DEFAULT_COLOR_TOLERANCE,
) -> bool:
    """
    Detect if the template icon is present in the screen.
    Uses mask to ignore transparent pixels in template.
    color_tolerance: pixels within this difference (0-255) are considered matching.
                     Higher values are more lenient for HDR/transparent icons.
    Returns True if detected, False otherwise.
    """
    if screen.shape[:2] == template.shape[:2]:
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
                max_val = 1.0 - error
            else:
                max_val = 0.0
        else:
            diff = np.abs(screen.astype(np.float32) - template.astype(np.float32))
            # Apply color tolerance: differences below tolerance are zeroed out
            diff = np.maximum(diff - color_tolerance, 0.0)
            max_val = 1.0 - (np.mean(diff) / (255.0 - color_tolerance))
    else:
        if mask is not None:
            result = cv2.matchTemplate(screen, template, cv2.TM_CCORR_NORMED, mask=mask)
        else:
            result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)

    if DEBUG:
        print(f"{page_name} detection confidence: {max_val:.3f} ({threshold})")
    return max_val >= threshold


def test_page_detection_for_page(page_name: str):
    """Generic looped test for any configured page."""
    if page_name not in PAGE_CONFIGS:
        raise ValueError(
            f"Unknown page: {page_name}. Available: {list(PAGE_CONFIGS.keys())}"
        )

    detection_funcs = {
        "PAGE": is_page_detected_1,
        "PAGE_2": is_page_detected_2,
        "PAGE_3": is_page_detected_3,
    }
    detect_func = detection_funcs[page_name]

    print(f"Running simple page detection ({page_name}) test... Press CTRL+C to stop")
    while True:
        detected = detect_func()
        print(
            f"\u2713 {page_name} DETECTED"
            if detected
            else f"\u2717 No page ({page_name})"
        )
        time.sleep(CHECK_INTERVAL)


def test_page_detection():
    """Simple looped test printing detection status every CHECK_INTERVAL seconds."""
    test_page_detection_for_page("PAGE")


def test_page_detection_2():
    """Simple looped test for PAGE_2."""
    test_page_detection_for_page("PAGE_2")


def test_page_detection_3():
    """Simple looped test for PAGE_3."""
    test_page_detection_for_page("PAGE_3")


def test_page_detection_4():
    """Simple looped test for PAGE_4."""
    test_page_detection_for_page("PAGE_4")


def toggle_debug_page():
    global DEBUG
    DEBUG = not DEBUG


if __name__ == "__main__":
    DEBUG = True

    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--test2":
        test_page_detection_2()
    elif len(sys.argv) > 1 and sys.argv[1] == "--test3":
        test_page_detection_3()
    else:
        test_page_detection()
