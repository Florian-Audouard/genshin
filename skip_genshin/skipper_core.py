"""
Genshin Dialogue Skipper - Core Logic Module
Contains the configuration, detection, and spam engines.
"""

import threading
import time
import json
import os
from typing import Dict, Optional, Tuple

import cv2
import numpy as np
import mss
import pyautogui
import win32gui


# ==================== Configuration ====================

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

DEFAULT_CONFIG = {
    "general": {
        "pause_between_spams": 0.05,
        "default_color_tolerance": 15,
        "skip_dialogue_key": "space",
        "choose_option_key": "e",
        "check_interval": 0.1
    },
    "detections": {
        "DIALOGUE": {
            "enabled": True,
            "roi": {"left": 551, "top": 37, "width": 54, "height": 54},
            "threshold": 0.95,
            "template": "img/template_dialogue.png",
            "action": "spam"
        },
        "PAGE_1": {
            "enabled": True,
            "roi": {"left": 201, "top": 42, "width": 46, "height": 50},
            "threshold": 0.95,
            "template": "img/template_page.png",
            "action": "close_escape"
        },
        "PAGE_2": {
            "enabled": True,
            "roi": {"left": 1701, "top": 1354, "width": 38, "height": 38},
            "threshold": 0.95,
            "template": "img/template_page_2.png",
            "action": "close_space_click"
        },
        "PAGE_2_ALT": {
            "enabled": True,
            "roi": {"left": 1701, "top": 1341, "width": 38, "height": 38},
            "threshold": 0.95,
            "template": "img/template_page_2.png",
            "action": "close_space_click"
        },
        "PAGE_4": {
            "enabled": True,
            "roi": {"left": 1701, "top": 1341, "width": 38, "height": 38},
            "threshold": 0.95,
            "template": "img/template_page_4.png",
            "action": "click_only"
        },
        "PAGE_4_ALT": {
            "enabled": True,
            "roi": {"left": 1701, "top": 1373, "width": 38, "height": 38},
            "threshold": 0.95,
            "template": "img/template_page_2.png",
            "action": "click_only"
        }
    },
    "click_position": {
        "x": 1687,
        "y": 715
    },
    "hotkeys": {
        "toggle_spam": "F7",
        "toggle_debug": "F8"
    }
}


# ==================== Configuration Manager ====================

class ConfigManager:
    """Manages loading and saving configuration to JSON file."""
    
    def __init__(self, config_path: str = CONFIG_FILE):
        self.config_path = config_path
        self.config = self.load()
    
    def load(self) -> dict:
        """Load configuration from JSON file, or create default if not exists."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                # Merge with defaults to ensure all keys exist
                return self._merge_with_defaults(config)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading config: {e}. Using defaults.")
                return DEFAULT_CONFIG.copy()
        else:
            self.save(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()
    
    def _merge_with_defaults(self, config: dict) -> dict:
        """Merge loaded config with defaults to ensure all keys exist."""
        result = DEFAULT_CONFIG.copy()
        for key, value in config.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key].update(value)
            else:
                result[key] = value
        return result
    
    def save(self, config: dict = None):
        """Save configuration to JSON file."""
        if config is None:
            config = self.config
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=4)
        except IOError as e:
            print(f"Error saving config: {e}")
    
    def get(self, *keys, default=None):
        """Get a nested configuration value."""
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def set(self, value, *keys):
        """Set a nested configuration value."""
        config = self.config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value
        self.save()


# ==================== Detection Engine ====================

class DetectionEngine:
    """Handles template matching and detection logic."""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.template_cache: Dict[str, Tuple[np.ndarray, Optional[np.ndarray]]] = {}
        self.debug = False
        self._last_detection_states: Dict[str, bool] = {}
        self._state_change_callbacks: list = []
    
    def add_state_change_callback(self, callback):
        """Add a callback for detection state changes. callback(name, detected, confidence)"""
        self._state_change_callbacks.append(callback)
    
    def _notify_state_change(self, name: str, detected: bool, confidence: float):
        """Notify all callbacks of a state change."""
        for callback in self._state_change_callbacks:
            try:
                callback(name, detected, confidence)
            except Exception:
                pass
    
    def load_template(self, detection_name: str) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """Load template image for a detection, resized to ROI size."""
        det_config = self.config.get("detections", detection_name)
        if not det_config:
            raise ValueError(f"Unknown detection: {detection_name}")
        
        template_path = os.path.join(os.path.dirname(__file__), det_config["template"])
        roi = det_config["roi"]
        
        template_bgra = cv2.imread(template_path, cv2.IMREAD_UNCHANGED)
        if template_bgra is None:
            raise FileNotFoundError(f"Template not found: {template_path}")
        
        target_size = (roi["width"], roi["height"])
        template_bgra = cv2.resize(template_bgra, target_size, interpolation=cv2.INTER_AREA)
        
        if template_bgra.shape[2] == 4:
            template_bgr = template_bgra[:, :, :3]
            alpha = template_bgra[:, :, 3]
            mask = alpha.copy()
            return template_bgr, mask
        else:
            return template_bgra, None
    
    def get_cached_template(self, detection_name: str) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """Get cached template, loading if necessary."""
        if detection_name not in self.template_cache:
            self.template_cache[detection_name] = self.load_template(detection_name)
        return self.template_cache[detection_name]
    
    def clear_template_cache(self, detection_name: str = None):
        """Clear template cache for a specific detection or all."""
        if detection_name:
            self.template_cache.pop(detection_name, None)
        else:
            self.template_cache.clear()
    
    def capture_screen(self, roi: dict) -> np.ndarray:
        """Capture a region of the screen."""
        with mss.mss() as sct:
            screenshot = sct.grab(roi)
            img = np.array(screenshot)
            return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    
    def is_uniform_color(self, image: np.ndarray, threshold: float = 5.0) -> bool:
        """Check if image is mostly a uniform/solid color.
        Returns True if the standard deviation of colors is below threshold.
        """
        std_dev = np.std(image.astype(np.float32))
        return std_dev < threshold
    
    def calculate_confidence(self, screen: np.ndarray, template: np.ndarray, 
                            mask: np.ndarray = None, color_tolerance: int = 15,
                            use_uniform_protection: bool = True) -> float:
        """Calculate match confidence between screen and template.
        Includes optional protection against uniform color images (solid screens).
        """
        if screen.shape[:2] != template.shape[:2]:
            screen = cv2.resize(screen, (template.shape[1], template.shape[0]), 
                              interpolation=cv2.INTER_AREA)
        
        # Protection: reject if screen is uniform/solid color (if enabled)
        if use_uniform_protection and self.is_uniform_color(screen):
            return 0.0
        
        if mask is not None:
            mask_norm = mask.astype(np.float32) / 255.0
            mask_3ch = np.stack([mask_norm] * 3, axis=-1)
            
            # Calculate main confidence from masked (opaque) areas
            diff = np.abs(screen.astype(np.float32) - template.astype(np.float32))
            diff = np.maximum(diff - color_tolerance, 0.0)
            masked_diff = diff * mask_3ch
            max_error = np.sum(mask_3ch) * (255.0 - color_tolerance)
            if max_error > 0:
                error = np.sum(masked_diff) / max_error
                confidence = 1.0 - error
            else:
                confidence = 0.0
            
            # Penalty: check if transparent areas have same color as opaque areas (if enabled)
            if use_uniform_protection:
                inv_mask_norm = 1.0 - mask_norm
                if np.sum(inv_mask_norm) > 0:
                    inv_mask_3ch = np.stack([inv_mask_norm] * 3, axis=-1)
                    
                    opaque_pixels = screen.astype(np.float32) * mask_3ch
                    opaque_count = np.sum(mask_3ch) / 3
                    if opaque_count > 0:
                        avg_opaque_color = np.sum(opaque_pixels, axis=(0, 1)) / opaque_count
                        
                        transparent_pixels = screen.astype(np.float32) * inv_mask_3ch
                        transparent_count = np.sum(inv_mask_3ch) / 3
                        if transparent_count > 0:
                            avg_transparent_color = np.sum(transparent_pixels, axis=(0, 1)) / transparent_count
                            
                            color_diff = np.abs(avg_opaque_color - avg_transparent_color)
                            color_similarity = 1.0 - (np.mean(color_diff) / 255.0)
                            
                            if color_similarity > 0.9:
                                penalty = (color_similarity - 0.9) * 5.0
                                confidence = max(0.0, confidence - penalty)
        else:
            diff = np.abs(screen.astype(np.float32) - template.astype(np.float32))
            diff = np.maximum(diff - color_tolerance, 0.0)
            confidence = 1.0 - (np.mean(diff) / (255.0 - color_tolerance))
        
        return confidence
    
    def is_detected(self, detection_name: str) -> Tuple[bool, float]:
        """Check if a detection is triggered. Returns (detected, confidence)."""
        det_config = self.config.get("detections", detection_name)
        if not det_config or not det_config.get("enabled", True):
            return False, 0.0
        
        try:
            template, mask = self.get_cached_template(detection_name)
            screen = self.capture_screen(det_config["roi"])
            threshold = det_config.get("threshold", 0.95)
            color_tolerance = self.config.get("general", "default_color_tolerance", default=15)
            use_uniform_protection = det_config.get("uniform_color_protection", True)
            
            confidence = self.calculate_confidence(screen, template, mask, color_tolerance, use_uniform_protection)
            detected = confidence >= threshold
            
            # Track state changes for logging
            prev_state = self._last_detection_states.get(detection_name, None)
            if prev_state is not None and prev_state != detected:
                self._notify_state_change(detection_name, detected, confidence)
                if self.debug:
                    status = "DETECTED" if detected else "CLEARED"
                    print(f"{detection_name}: {status} (conf: {confidence:.3f})")
            self._last_detection_states[detection_name] = detected
            
            return detected, confidence
        except Exception as e:
            if self.debug:
                print(f"Detection error ({detection_name}): {e}")
            return False, 0.0


# ==================== Spam Engine ====================

class SpamEngine:
    """Handles the spamming/automation logic."""
    
    def __init__(self, config_manager: ConfigManager, detection_engine: DetectionEngine):
        self.config = config_manager
        self.detection = detection_engine
        self.running = False
        self.debug_mode = False
        self.spam_count = 0
        self._thread: Optional[threading.Thread] = None
        self._debug_thread: Optional[threading.Thread] = None
        self._callbacks: Dict[str, list] = {
            "state_change": [],
            "debug_change": [],
            "spam_speed": []
        }
        
        pyautogui.PAUSE = 0
    
    def add_callback(self, event: str, callback):
        """Add a callback for an event."""
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    def _notify(self, event: str, *args):
        """Notify all callbacks for an event."""
        for callback in self._callbacks.get(event, []):
            try:
                callback(*args)
            except Exception as e:
                print(f"Callback error: {e}")
    
    def is_genshin_active(self) -> bool:
        """Check if Genshin Impact is the active window."""
        try:
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)
            return title == "Genshin Impact"
        except Exception:
            return False
    
    def do_spam(self):
        """Execute spam action (configurable keys)."""
        try:
            skip_key = self.config.get("general", "skip_dialogue_key", default="space")
            option_key = self.config.get("general", "choose_option_key", default="e")
            pyautogui.press(skip_key)
            pyautogui.press(option_key)
            self.spam_count += 1
        except pyautogui.FailSafeException:
            pass
    
    def do_close_escape(self):
        """Close page with Escape."""
        try:
            pyautogui.press("escape")
        except pyautogui.FailSafeException:
            pass
    
    def do_close_space_click(self):
        """Close page with Space + Click."""
        try:
            click_pos = self.config.get("click_position")
            option_key = self.config.get("general", "choose_option_key", default="e")
            pyautogui.press(option_key)
            pyautogui.click(click_pos["x"], click_pos["y"])
        except pyautogui.FailSafeException:
            pass
    
    def do_click_only(self):
        """Just click at the configured position."""
        try:
            click_pos = self.config.get("click_position")
            pyautogui.click(click_pos["x"], click_pos["y"])
        except pyautogui.FailSafeException:
            pass
    
    def execute_action(self, action: str):
        """Execute an action based on type."""
        actions = {
            "spam": self.do_spam,
            "close_escape": self.do_close_escape,
            "close_space_click": self.do_close_space_click,
            "click_only": self.do_click_only
        }
        if action in actions:
            actions[action]()
    
    def _spam_loop(self):
        """Main spam loop running in background thread."""
        while True:
            if self.running and self.is_genshin_active():
                detections = self.config.get("detections", default={})
                pause = self.config.get("general", "pause_between_spams", default=0.05)
                
                for name, det_config in detections.items():
                    if det_config.get("enabled", True):
                        detected, _ = self.detection.is_detected(name)
                        if detected:
                            self.execute_action(det_config.get("action", "spam"))
                
                time.sleep(pause)
            else:
                time.sleep(0.1)
    
    def _debug_speed_loop(self):
        """Thread that tracks spam speed."""
        last_time = time.time()
        while True:
            if self.debug_mode:
                current_time = time.time()
                elapsed = current_time - last_time
                if elapsed >= 1.0:
                    speed = self.spam_count / elapsed
                    self._notify("spam_speed", speed, self.spam_count, elapsed)
                    self.spam_count = 0
                    last_time = current_time
            else:
                self.spam_count = 0
                last_time = time.time()
            time.sleep(0.1)
    
    def start(self):
        """Start the spam engine threads."""
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._spam_loop, daemon=True)
            self._thread.start()
        
        if self._debug_thread is None or not self._debug_thread.is_alive():
            self._debug_thread = threading.Thread(target=self._debug_speed_loop, daemon=True)
            self._debug_thread.start()
    
    def toggle(self):
        """Toggle running state."""
        self.running = not self.running
        self._notify("state_change", self.running)
        return self.running
    
    def toggle_debug(self):
        """Toggle debug mode."""
        self.debug_mode = not self.debug_mode
        self.detection.debug = self.debug_mode
        self._notify("debug_change", self.debug_mode)
        return self.debug_mode
