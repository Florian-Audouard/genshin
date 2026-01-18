"""
Genshin Dialogue Skipper - Unified GUI Application
Combines helper_pos.py and my_skip.py into a single application with:
- JSON-based configuration storage
- Modifiable ROIs and thresholds via GUI
- Toggleable skip actions
"""

import threading
import time
import json
import os
import io
import sys
import ctypes
import cv2

# Hide console window on Windows
if sys.platform == "win32":
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
import numpy as np
import mss
import keyboard
import pyautogui
import win32gui
import win32clipboard
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from PIL import Image, ImageTk
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from pynput import keyboard as pynput_keyboard

# ==================== Configuration Manager ====================

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

DEFAULT_CONFIG = {
    "general": {
        "pause_between_spams": 0.05,
        "check_interval": 0.1,
        "default_color_tolerance": 15,
        "skip_dialogue_key": "space",
        "choose_option_key": "e"
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
        # Calculate standard deviation across all channels
        std_dev = np.std(image.astype(np.float32))
        return std_dev < threshold
    
    def calculate_confidence(self, screen: np.ndarray, template: np.ndarray, 
                            mask: np.ndarray = None, color_tolerance: int = 15) -> float:
        """Calculate match confidence between screen and template.
        Includes protection against uniform color images (solid screens).
        """
        if screen.shape[:2] != template.shape[:2]:
            screen = cv2.resize(screen, (template.shape[1], template.shape[0]), 
                              interpolation=cv2.INTER_AREA)
        
        # Protection: reject if screen is uniform/solid color
        if self.is_uniform_color(screen):
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
            
            # Penalty: check if transparent areas have same color as opaque areas
            # This detects false positives from solid color screens
            inv_mask_norm = 1.0 - mask_norm  # Inverted mask (transparent areas)
            if np.sum(inv_mask_norm) > 0:  # Only if there are transparent areas
                inv_mask_3ch = np.stack([inv_mask_norm] * 3, axis=-1)
                
                # Get average color of opaque areas in screen
                opaque_pixels = screen.astype(np.float32) * mask_3ch
                opaque_count = np.sum(mask_3ch) / 3  # Divide by 3 for channels
                if opaque_count > 0:
                    avg_opaque_color = np.sum(opaque_pixels, axis=(0, 1)) / opaque_count
                    
                    # Get average color of transparent areas in screen
                    transparent_pixels = screen.astype(np.float32) * inv_mask_3ch
                    transparent_count = np.sum(inv_mask_3ch) / 3
                    if transparent_count > 0:
                        avg_transparent_color = np.sum(transparent_pixels, axis=(0, 1)) / transparent_count
                        
                        # Calculate color similarity between opaque and transparent areas
                        color_diff = np.abs(avg_opaque_color - avg_transparent_color)
                        color_similarity = 1.0 - (np.mean(color_diff) / 255.0)
                        
                        # If colors are very similar (solid color image), apply penalty
                        if color_similarity > 0.9:  # 90% similar = likely solid color
                            penalty = (color_similarity - 0.9) * 5.0  # Scale penalty
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
            
            confidence = self.calculate_confidence(screen, template, mask, color_tolerance)
            detected = confidence >= threshold
            
            # Track state changes for logging
            prev_state = self._last_detection_states.get(detection_name, None)
            if prev_state is not None and prev_state != detected:
                # Always notify callbacks on state change
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


# ==================== Main GUI Application ====================

class GenshinSkipperGUI:
    """Main GUI application combining helper and skipper functionality."""
    
    # Dark theme colors
    DARK_BG = "#1e1e1e"
    DARK_BG2 = "#252526"
    DARK_BG3 = "#2d2d30"
    DARK_FG = "#d4d4d4"
    DARK_ACCENT = "#007acc"
    DARK_ACCENT2 = "#0e639c"
    DARK_BORDER = "#3c3c3c"
    DARK_SELECT = "#094771"
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Genshin Dialogue Skipper")
        self.root.geometry("1100x900")
        self.root.resizable(True, True)
        
        # Apply dark theme
        self.setup_dark_theme()
        
        # Initialize managers
        self.config = ConfigManager()
        self.detection = DetectionEngine(self.config)
        self.spam = SpamEngine(self.config, self.detection)
        
        # GUI state
        self.running = False
        self.live_preview = tk.BooleanVar(value=True)
        self.selected_detection = tk.StringVar(value="DIALOGUE")
        self.comparison_enabled = tk.BooleanVar(value=True)
        self.current_confidence = tk.StringVar(value="N/A")
        self.detection_status = tk.StringVar(value="---")
        
        # ROI variables
        self.roi_left = tk.IntVar(value=0)
        self.roi_top = tk.IntVar(value=0)
        self.roi_width = tk.IntVar(value=100)
        self.roi_height = tk.IntVar(value=100)
        self.threshold_var = tk.DoubleVar(value=0.95)
        
        # Detection enable/disable checkbuttons
        self.detection_vars: Dict[str, tk.BooleanVar] = {}
        
        # Status variables
        self.spam_status = tk.StringVar(value="PAUSED")
        self.debug_status = tk.StringVar(value="OFF")
        
        # Setup
        self.setup_ui()
        self.setup_callbacks()
        self.setup_keyboard_listener()
        self.load_detection_config()
        self.setup_autosave()
        
        # Start engines
        self.spam.start()
        self.start_live_preview()
    
    def setup_dark_theme(self):
        """Setup dark theme for the application."""
        # Configure root window
        self.root.configure(bg=self.DARK_BG)
        
        # Create and configure ttk style
        style = ttk.Style()
        style.theme_use('clam')  # Use clam as base theme (most customizable)
        
        # Configure general styles
        style.configure(".", 
                       background=self.DARK_BG,
                       foreground=self.DARK_FG,
                       fieldbackground=self.DARK_BG2,
                       troughcolor=self.DARK_BG3,
                       bordercolor=self.DARK_BORDER,
                       lightcolor=self.DARK_BG3,
                       darkcolor=self.DARK_BG,
                       focuscolor=self.DARK_ACCENT)
        
        # Frame styles
        style.configure("TFrame", background=self.DARK_BG)
        style.configure("TLabelframe", background=self.DARK_BG, foreground=self.DARK_FG)
        style.configure("TLabelframe.Label", background=self.DARK_BG, foreground=self.DARK_ACCENT)
        
        # Label styles
        style.configure("TLabel", background=self.DARK_BG, foreground=self.DARK_FG)
        
        # Button styles
        style.configure("TButton",
                       background=self.DARK_BG3,
                       foreground=self.DARK_FG,
                       bordercolor=self.DARK_BORDER,
                       padding=(10, 5))
        style.map("TButton",
                 background=[("active", self.DARK_ACCENT2), ("pressed", self.DARK_ACCENT)],
                 foreground=[("active", "#ffffff")])
        
        # Entry styles
        style.configure("TEntry",
                       fieldbackground=self.DARK_BG2,
                       foreground=self.DARK_FG,
                       insertcolor=self.DARK_FG,
                       bordercolor=self.DARK_BORDER)
        style.map("TEntry",
                 fieldbackground=[("focus", self.DARK_BG3)],
                 bordercolor=[("focus", self.DARK_ACCENT)])
        
        # Spinbox styles
        style.configure("TSpinbox",
                       fieldbackground=self.DARK_BG2,
                       foreground=self.DARK_FG,
                       arrowcolor=self.DARK_FG,
                       bordercolor=self.DARK_BORDER)
        style.map("TSpinbox",
                 fieldbackground=[("focus", self.DARK_BG3)],
                 bordercolor=[("focus", self.DARK_ACCENT)])
        
        # Combobox styles
        style.configure("TCombobox",
                       fieldbackground=self.DARK_BG2,
                       foreground=self.DARK_FG,
                       arrowcolor=self.DARK_FG,
                       bordercolor=self.DARK_BORDER,
                       selectbackground=self.DARK_SELECT,
                       selectforeground=self.DARK_FG)
        style.map("TCombobox",
                 fieldbackground=[("focus", self.DARK_BG3), ("readonly", self.DARK_BG2)],
                 bordercolor=[("focus", self.DARK_ACCENT)],
                 selectbackground=[("focus", self.DARK_SELECT)])
        
        # Checkbutton styles
        style.configure("TCheckbutton",
                       background=self.DARK_BG,
                       foreground=self.DARK_FG,
                       indicatorcolor=self.DARK_BG2)
        style.map("TCheckbutton",
                 background=[("active", self.DARK_BG)],
                 indicatorcolor=[("selected", self.DARK_ACCENT)])
        
        # Notebook (tabs) styles
        style.configure("TNotebook",
                       background=self.DARK_BG,
                       bordercolor=self.DARK_BORDER,
                       tabmargins=[2, 5, 2, 0])
        style.configure("TNotebook.Tab",
                       background=self.DARK_BG3,
                       foreground=self.DARK_FG,
                       padding=[15, 5],
                       bordercolor=self.DARK_BORDER)
        style.map("TNotebook.Tab",
                 background=[("selected", self.DARK_BG), ("active", self.DARK_BG2)],
                 foreground=[("selected", self.DARK_ACCENT)],
                 expand=[("selected", [1, 1, 1, 0])])
        
        # Scrollbar styles
        style.configure("TScrollbar",
                       background=self.DARK_BG3,
                       troughcolor=self.DARK_BG,
                       arrowcolor=self.DARK_FG,
                       bordercolor=self.DARK_BORDER)
        style.map("TScrollbar",
                 background=[("active", self.DARK_ACCENT2)])
        
        # Configure option menu for combobox dropdown
        self.root.option_add("*TCombobox*Listbox.background", self.DARK_BG2)
        self.root.option_add("*TCombobox*Listbox.foreground", self.DARK_FG)
        self.root.option_add("*TCombobox*Listbox.selectBackground", self.DARK_SELECT)
        self.root.option_add("*TCombobox*Listbox.selectForeground", self.DARK_FG)
    
    def setup_ui(self):
        """Setup the complete GUI."""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Main control tab
        self.main_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.main_tab, text="Main Control")
        
        # ROI Helper tab
        self.roi_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.roi_tab, text="ROI Helper")
        
        # Settings tab
        self.settings_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_tab, text="Settings")
        
        self.setup_main_tab()
        self.setup_roi_tab()
        self.setup_settings_tab()
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready - Press F7 to start/pause | F8 for debug")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
    def setup_main_tab(self):
        """Setup the main control tab."""
        main_frame = ttk.Frame(self.main_tab, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Control Panel
        control_frame = ttk.LabelFrame(main_frame, text="Control Panel", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Status indicators
        status_frame = ttk.Frame(control_frame)
        status_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(status_frame, text="Spam Status:", font=("Consolas", 11)).pack(side=tk.LEFT, padx=5)
        self.spam_label = ttk.Label(status_frame, textvariable=self.spam_status, 
                                    font=("Consolas", 14, "bold"), foreground="red")
        self.spam_label.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(status_frame, text="Debug:", font=("Consolas", 11)).pack(side=tk.LEFT, padx=20)
        self.debug_label = ttk.Label(status_frame, textvariable=self.debug_status, 
                                     font=("Consolas", 14, "bold"), foreground="gray")
        self.debug_label.pack(side=tk.LEFT, padx=5)
        
        # Control buttons
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        self.toggle_btn = ttk.Button(btn_frame, text="▶ Start (F7)", command=self.toggle_spam, width=20)
        self.toggle_btn.pack(side=tk.LEFT, padx=5)
        
        self.debug_btn = ttk.Button(btn_frame, text="🔧 Debug (F8)", command=self.toggle_debug, width=20)
        self.debug_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text=" Reload Config", command=self.reload_config, width=15).pack(side=tk.LEFT, padx=5)
        
        # Detection toggles
        det_frame = ttk.LabelFrame(main_frame, text="Detection Toggles", padding="10")
        det_frame.pack(fill=tk.X, pady=(0, 10))
        
        detections = self.config.get("detections", default={})
        row = 0
        col = 0
        for name, det_config in detections.items():
            var = tk.BooleanVar(value=det_config.get("enabled", True))
            self.detection_vars[name] = var
            
            chk = ttk.Checkbutton(det_frame, text=f"{name} ({det_config.get('action', 'spam')})", 
                                  variable=var, command=lambda n=name: self.toggle_detection(n))
            chk.grid(row=row, column=col, sticky=tk.W, padx=10, pady=2)
            
            col += 1
            if col >= 3:
                col = 0
                row += 1
        
        # Speed display (for debug)
        self.speed_frame = ttk.LabelFrame(main_frame, text="Spam Speed (Debug Mode)", padding="10")
        self.speed_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.speed_label = ttk.Label(self.speed_frame, text="0.00 actions/sec", font=("Consolas", 16, "bold"))
        self.speed_label.pack()
        
        # Log area
        log_frame = ttk.LabelFrame(main_frame, text="Activity Log", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=12, font=("Consolas", 9),
                                                   bg=self.DARK_BG2, fg=self.DARK_FG,
                                                   insertbackground=self.DARK_FG,
                                                   selectbackground=self.DARK_SELECT,
                                                   selectforeground=self.DARK_FG,
                                                   relief=tk.FLAT, borderwidth=2)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        ttk.Button(log_frame, text="Clear Log", command=self.clear_log).pack(pady=5)
    
    def setup_roi_tab(self):
        """Setup the ROI helper tab."""
        main_frame = ttk.Frame(self.roi_tab, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # ROI Controls
        roi_frame = ttk.LabelFrame(main_frame, text="ROI Settings", padding="10")
        roi_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Detection selector
        ttk.Label(roi_frame, text="Detection:").grid(row=0, column=0, sticky=tk.W, padx=5)
        det_combo = ttk.Combobox(roi_frame, textvariable=self.selected_detection,
                                 values=list(self.config.get("detections", default={}).keys()),
                                 state="readonly", width=15)
        det_combo.grid(row=0, column=1, padx=5)
        det_combo.bind("<<ComboboxSelected>>", self.on_detection_changed)
        
        # ROI values
        ttk.Label(roi_frame, text="Left:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Spinbox(roi_frame, from_=0, to=3840, textvariable=self.roi_left, width=10).grid(row=1, column=1, padx=5)
        
        ttk.Label(roi_frame, text="Top:").grid(row=1, column=2, sticky=tk.W, padx=5)
        ttk.Spinbox(roi_frame, from_=0, to=2160, textvariable=self.roi_top, width=10).grid(row=1, column=3, padx=5)
        
        ttk.Label(roi_frame, text="Width:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Spinbox(roi_frame, from_=1, to=1920, textvariable=self.roi_width, width=10).grid(row=2, column=1, padx=5)
        
        ttk.Label(roi_frame, text="Height:").grid(row=2, column=2, sticky=tk.W, padx=5)
        ttk.Spinbox(roi_frame, from_=1, to=1080, textvariable=self.roi_height, width=10).grid(row=2, column=3, padx=5)
        
        ttk.Label(roi_frame, text="Threshold:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Spinbox(roi_frame, from_=0.0, to=1.0, increment=0.01, textvariable=self.threshold_var, 
                   width=10, format="%.2f").grid(row=3, column=1, padx=5)
        
        # Buttons
        btn_frame = ttk.Frame(roi_frame)
        btn_frame.grid(row=4, column=0, columnspan=4, pady=10)
        
        ttk.Button(btn_frame, text="Set from Mouse (F9)", command=self.set_roi_from_mouse).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Capture ROI", command=self.capture_roi).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Copy Image", command=self.copy_image_to_clipboard).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Copy ROI Code", command=self.copy_roi_code).pack(side=tk.LEFT, padx=5)
        
        ttk.Checkbutton(roi_frame, text="Live Preview", variable=self.live_preview).grid(row=5, column=0, columnspan=4)
        
        # Comparison info
        compare_frame = ttk.LabelFrame(main_frame, text="Detection Comparison", padding="10")
        compare_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Checkbutton(compare_frame, text="Enable Comparison", variable=self.comparison_enabled).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(compare_frame, text="Threshold:").pack(side=tk.LEFT, padx=10)
        self.threshold_label = ttk.Label(compare_frame, text="0.95", font=("Consolas", 11, "bold"))
        self.threshold_label.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(compare_frame, text="Confidence:").pack(side=tk.LEFT, padx=10)
        self.confidence_label = ttk.Label(compare_frame, textvariable=self.current_confidence, 
                                          font=("Consolas", 11, "bold"), foreground="gray")
        self.confidence_label.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(compare_frame, text="Status:").pack(side=tk.LEFT, padx=10)
        self.status_detection_label = ttk.Label(compare_frame, textvariable=self.detection_status, 
                                                font=("Consolas", 11, "bold"))
        self.status_detection_label.pack(side=tk.LEFT, padx=5)
        
        # Preview canvases
        preview_frame = ttk.LabelFrame(main_frame, text="Preview", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        canvas_container = ttk.Frame(preview_frame)
        canvas_container.pack(fill=tk.BOTH, expand=True)
        
        # Current ROI canvas
        left_frame = ttk.Frame(canvas_container)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        ttk.Label(left_frame, text="Current ROI", font=("Consolas", 9)).pack()
        self.canvas = tk.Canvas(left_frame, bg=self.DARK_BG3, width=200, height=200,
                                highlightbackground=self.DARK_BORDER, highlightthickness=1)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Threshold view canvas
        middle_frame = ttk.Frame(canvas_container)
        middle_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        ttk.Label(middle_frame, text="Threshold View", font=("Consolas", 9)).pack()
        self.threshold_canvas = tk.Canvas(middle_frame, bg=self.DARK_BG3, width=200, height=200,
                                          highlightbackground=self.DARK_BORDER, highlightthickness=1)
        self.threshold_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Template canvas
        right_frame = ttk.Frame(canvas_container)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        ttk.Label(right_frame, text="Template", font=("Consolas", 9)).pack()
        self.template_canvas = tk.Canvas(right_frame, bg=self.DARK_BG3, width=200, height=200,
                                         highlightbackground=self.DARK_BORDER, highlightthickness=1)
        self.template_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Mouse position
        pos_frame = ttk.Frame(main_frame)
        pos_frame.pack(fill=tk.X)
        
        ttk.Label(pos_frame, text="Mouse Position:").pack(side=tk.LEFT)
        self.mouse_pos_label = ttk.Label(pos_frame, text="(0, 0)", font=("Consolas", 12))
        self.mouse_pos_label.pack(side=tk.LEFT, padx=10)
    
    def setup_settings_tab(self):
        """Setup the settings tab."""
        main_frame = ttk.Frame(self.settings_tab, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # General settings
        general_frame = ttk.LabelFrame(main_frame, text="General Settings", padding="10")
        general_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Pause between spams
        ttk.Label(general_frame, text="Pause Between Spams (sec):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.pause_var = tk.DoubleVar(value=self.config.get("general", "pause_between_spams", default=0.05))
        ttk.Spinbox(general_frame, from_=0.01, to=1.0, increment=0.01, textvariable=self.pause_var, 
                   width=10, format="%.2f").grid(row=0, column=1, padx=5)
        
        # Color tolerance
        ttk.Label(general_frame, text="Color Tolerance (0-255):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.tolerance_var = tk.IntVar(value=self.config.get("general", "default_color_tolerance", default=15))
        ttk.Spinbox(general_frame, from_=0, to=255, textvariable=self.tolerance_var, width=10).grid(row=1, column=1, padx=5)
        
        # Key settings
        keys_frame = ttk.LabelFrame(main_frame, text="Action Keys", padding="10")
        keys_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(keys_frame, text="Skip Dialogue Key:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.skip_dialogue_key_var = tk.StringVar(value=self.config.get("general", "skip_dialogue_key", default="e"))
        ttk.Entry(keys_frame, textvariable=self.skip_dialogue_key_var, width=10).grid(row=0, column=1, padx=5)
        
        ttk.Label(keys_frame, text="Choose Option Key:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.choose_option_key_var = tk.StringVar(value=self.config.get("general", "choose_option_key", default="space"))
        ttk.Entry(keys_frame, textvariable=self.choose_option_key_var, width=10).grid(row=0, column=3, padx=5)
        
        # Click position
        click_frame = ttk.LabelFrame(main_frame, text="Click Position (for close actions)", padding="10")
        click_frame.pack(fill=tk.X, pady=(0, 10))
        
        click_pos = self.config.get("click_position", default={"x": 1687, "y": 715})
        ttk.Label(click_frame, text="X:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.click_x_var = tk.IntVar(value=click_pos["x"])
        ttk.Spinbox(click_frame, from_=0, to=3840, textvariable=self.click_x_var, width=10).grid(row=0, column=1, padx=5)
        
        ttk.Label(click_frame, text="Y:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.click_y_var = tk.IntVar(value=click_pos["y"])
        ttk.Spinbox(click_frame, from_=0, to=2160, textvariable=self.click_y_var, width=10).grid(row=0, column=3, padx=5)
        
        ttk.Button(click_frame, text="Set from Mouse", command=self.set_click_from_mouse).grid(row=0, column=4, padx=10)
        
        # Hotkeys
        hotkey_frame = ttk.LabelFrame(main_frame, text="Hotkeys", padding="10")
        hotkey_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(hotkey_frame, text="Toggle Spam:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.hotkey_spam_var = tk.StringVar(value=self.config.get("hotkeys", "toggle_spam", default="F7"))
        ttk.Entry(hotkey_frame, textvariable=self.hotkey_spam_var, width=10).grid(row=0, column=1, padx=5)
        
        ttk.Label(hotkey_frame, text="Toggle Debug:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.hotkey_debug_var = tk.StringVar(value=self.config.get("hotkeys", "toggle_debug", default="F8"))
        ttk.Entry(hotkey_frame, textvariable=self.hotkey_debug_var, width=10).grid(row=0, column=3, padx=5)
        
        # Info
        info_frame = ttk.LabelFrame(main_frame, text="Information", padding="10")
        info_frame.pack(fill=tk.X)
        
        info_text = """
Actions:
  • spam: Press E + Space (for dialogue skipping)
  • close_escape: Press Escape (for closing pages)
  • close_space_click: Press Space + Click (for confirmation dialogs)
  • click_only: Just click at position (for buttons)

Hotkeys:
  • F7: Toggle spam on/off
  • F8: Toggle debug mode
  • F9: Set ROI position from mouse (in ROI Helper tab)
        """
        ttk.Label(info_frame, text=info_text, justify=tk.LEFT, font=("Consolas", 9)).pack(anchor=tk.W)
    
    def setup_autosave(self):
        """Setup auto-save traces on all configurable variables."""
        # ROI variables - save when changed
        self.roi_left.trace_add("write", lambda *args: self.autosave_roi())
        self.roi_top.trace_add("write", lambda *args: self.autosave_roi())
        self.roi_width.trace_add("write", lambda *args: self.autosave_roi())
        self.roi_height.trace_add("write", lambda *args: self.autosave_roi())
        self.threshold_var.trace_add("write", lambda *args: self.autosave_roi())
        
        # Settings variables - save when changed
        self.pause_var.trace_add("write", lambda *args: self.autosave_setting("general", "pause_between_spams", self.pause_var.get()))
        self.tolerance_var.trace_add("write", lambda *args: self.autosave_setting("general", "default_color_tolerance", self.tolerance_var.get()))
        self.skip_dialogue_key_var.trace_add("write", lambda *args: self.autosave_setting("general", "skip_dialogue_key", self.skip_dialogue_key_var.get()))
        self.choose_option_key_var.trace_add("write", lambda *args: self.autosave_setting("general", "choose_option_key", self.choose_option_key_var.get()))
        self.click_x_var.trace_add("write", lambda *args: self.autosave_click_position())
        self.click_y_var.trace_add("write", lambda *args: self.autosave_click_position())
        self.hotkey_spam_var.trace_add("write", lambda *args: self.autosave_setting("hotkeys", "toggle_spam", self.hotkey_spam_var.get()))
        self.hotkey_debug_var.trace_add("write", lambda *args: self.autosave_setting("hotkeys", "toggle_debug", self.hotkey_debug_var.get()))
    
    def autosave_roi(self):
        """Auto-save ROI settings for the selected detection."""
        try:
            name = self.selected_detection.get()
            roi = {
                "left": self.roi_left.get(),
                "top": self.roi_top.get(),
                "width": self.roi_width.get(),
                "height": self.roi_height.get()
            }
            self.config.set(roi, "detections", name, "roi")
            self.config.set(self.threshold_var.get(), "detections", name, "threshold")
            self.detection.clear_template_cache(name)
        except (tk.TclError, ValueError):
            pass  # Ignore errors during typing/invalid values
    
    def autosave_setting(self, *keys_and_value):
        """Auto-save a setting to config."""
        try:
            *keys, value = keys_and_value
            self.config.set(value, *keys)
        except (tk.TclError, ValueError):
            pass  # Ignore errors during typing/invalid values
    
    def autosave_click_position(self):
        """Auto-save click position."""
        try:
            self.config.set({"x": self.click_x_var.get(), "y": self.click_y_var.get()}, "click_position")
        except (tk.TclError, ValueError):
            pass  # Ignore errors during typing/invalid values
    
    def setup_callbacks(self):
        """Setup callbacks from spam engine to GUI."""
        self.spam.add_callback("state_change", self.on_spam_state_change)
        self.spam.add_callback("debug_change", self.on_debug_state_change)
        self.spam.add_callback("spam_speed", self.on_spam_speed)
        # Add detection state change callback
        self.detection.add_state_change_callback(self.on_detection_state_change)
    
    def on_detection_state_change(self, name: str, detected: bool, confidence: float):
        """Handle detection state change - log when detections activate/deactivate."""
        status = "DETECTED" if detected else "CLEARED"
        self.root.after(0, lambda: self.log_message(f"{name}: {status} (conf: {confidence:.3f})"))
    
    def setup_keyboard_listener(self):
        """Setup global keyboard listener."""
        def on_press(key):
            try:
                if key == pynput_keyboard.Key.f7:
                    self.root.after(0, self.toggle_spam)
                elif key == pynput_keyboard.Key.f8:
                    self.root.after(0, self.toggle_debug)
                elif key == pynput_keyboard.Key.f9:
                    self.root.after(0, self.set_roi_from_mouse)
            except AttributeError:
                pass
        
        self.keyboard_listener = pynput_keyboard.Listener(on_press=on_press)
        self.keyboard_listener.start()
    
    def on_spam_state_change(self, running: bool):
        """Handle spam state change."""
        self.root.after(0, lambda: self._update_spam_status(running))
    
    def _update_spam_status(self, running: bool):
        """Update spam status in GUI (must be called from main thread)."""
        if running:
            self.spam_status.set("RUNNING")
            self.spam_label.config(foreground="green")
            self.toggle_btn.config(text="⏸ Pause (F7)")
        else:
            self.spam_status.set("PAUSED")
            self.spam_label.config(foreground="red")
            self.toggle_btn.config(text="▶ Start (F7)")
        self.log_message(f"Spam: {'STARTED' if running else 'PAUSED'}")
    
    def on_debug_state_change(self, debug: bool):
        """Handle debug state change."""
        self.root.after(0, lambda: self._update_debug_status(debug))
    
    def _update_debug_status(self, debug: bool):
        """Update debug status in GUI."""
        if debug:
            self.debug_status.set("ON")
            self.debug_label.config(foreground="green")
        else:
            self.debug_status.set("OFF")
            self.debug_label.config(foreground="gray")
        self.log_message(f"Debug: {'ON' if debug else 'OFF'}")
    
    def on_spam_speed(self, speed: float, count: int, elapsed: float):
        """Handle spam speed update."""
        self.root.after(0, lambda: self.speed_label.config(text=f"{speed:.2f} actions/sec"))
    
    def toggle_spam(self):
        """Toggle spam on/off."""
        self.spam.toggle()
    
    def toggle_debug(self):
        """Toggle debug mode."""
        self.spam.toggle_debug()
    
    def toggle_detection(self, name: str):
        """Toggle a detection on/off."""
        var = self.detection_vars.get(name)
        if var:
            enabled = var.get()
            self.config.set(enabled, "detections", name, "enabled")
            self.log_message(f"{name}: {'ENABLED' if enabled else 'DISABLED'}")
    
    def load_detection_config(self, event=None):
        """Load ROI config for selected detection."""
        name = self.selected_detection.get()
        det_config = self.config.get("detections", name)
        if det_config:
            roi = det_config.get("roi", {})
            self.roi_left.set(roi.get("left", 0))
            self.roi_top.set(roi.get("top", 0))
            self.roi_width.set(roi.get("width", 100))
            self.roi_height.set(roi.get("height", 100))
            self.threshold_var.set(det_config.get("threshold", 0.95))
            self.threshold_label.config(text=f"{det_config.get('threshold', 0.95):.2f}")
    
    def on_detection_changed(self, event):
        """Handle detection selection change."""
        self.load_detection_config()
        self.detection.clear_template_cache(self.selected_detection.get())
    
    def get_current_roi(self) -> dict:
        """Get current ROI from spinboxes."""
        return {
            "left": self.roi_left.get(),
            "top": self.roi_top.get(),
            "width": self.roi_width.get(),
            "height": self.roi_height.get()
        }
    
    def set_roi_from_mouse(self):
        """Set ROI position from current mouse position."""
        pos = pyautogui.position()
        self.roi_left.set(pos[0])
        self.roi_top.set(pos[1])
        self.log_message(f"ROI position set to ({pos[0]}, {pos[1]})")
        self.status_var.set(f"ROI position: ({pos[0]}, {pos[1]})")
    
    def set_click_from_mouse(self):
        """Set click position from current mouse position."""
        pos = pyautogui.position()
        self.click_x_var.set(pos[0])
        self.click_y_var.set(pos[1])
        self.log_message(f"Click position set to ({pos[0]}, {pos[1]})")
    
    def capture_roi(self):
        """Capture current ROI and save to file."""
        roi = self.get_current_roi()
        img = self.detection.capture_screen(roi)
        filename = f"captured_roi_{self.selected_detection.get()}.png"
        cv2.imwrite(filename, img)
        self.log_message(f"ROI captured: {filename}")
        self.status_var.set(f"Saved: {filename}")
    
    def copy_image_to_clipboard(self):
        """Copy current ROI image to clipboard."""
        roi = self.get_current_roi()
        img = self.detection.capture_screen(roi)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)
        
        output = io.BytesIO()
        pil_img.convert("RGB").save(output, "BMP")
        data = output.getvalue()[14:]
        output.close()
        
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()
        
        self.log_message(f"Image copied to clipboard ({roi['width']}x{roi['height']})")
        self.status_var.set("Image copied!")
    
    def copy_roi_code(self):
        """Copy ROI as code to clipboard."""
        roi = self.get_current_roi()
        code = f'{{"left": {roi["left"]}, "top": {roi["top"]}, "width": {roi["width"]}, "height": {roi["height"]}}}'
        self.root.clipboard_clear()
        self.root.clipboard_append(code)
        self.log_message(f"Copied: {code}")
        self.status_var.set("ROI code copied!")
    
    def reload_config(self):
        """Reload configuration from file."""
        self.config.config = self.config.load()
        self.detection.clear_template_cache()
        self.load_detection_config()
        
        # Reload detection toggles
        for name, var in self.detection_vars.items():
            enabled = self.config.get("detections", name, "enabled", default=True)
            var.set(enabled)
        
        self.log_message("Configuration reloaded!")
        self.status_var.set("Configuration reloaded!")
    
    def log_message(self, message: str):
        """Add timestamped message to log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
    
    def clear_log(self):
        """Clear the log."""
        self.log_text.delete(1.0, tk.END)
    
    def start_live_preview(self):
        """Start the live preview update loop."""
        self.update_preview()
    
    def update_preview(self):
        """Update the live preview."""
        try:
            # Update mouse position
            pos = pyautogui.position()
            self.mouse_pos_label.config(text=f"({pos[0]}, {pos[1]})")
            
            if self.live_preview.get() and self.notebook.index(self.notebook.select()) == 1:  # ROI tab
                roi = self.get_current_roi()
                img = self.detection.capture_screen(roi)
                
                # Update main canvas
                self.update_canvas(self.canvas, img, f"ROI: {roi['width']}x{roi['height']}")
                
                # Update comparison if enabled
                if self.comparison_enabled.get():
                    self.update_comparison(img)
        except Exception as e:
            pass
        
        self.root.after(33, self.update_preview)  # ~30 FPS
    
    def update_canvas(self, canvas: tk.Canvas, img: np.ndarray, info_text: str = ""):
        """Update a canvas with an image."""
        try:
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            canvas_width = canvas.winfo_width()
            canvas_height = canvas.winfo_height()
            
            if canvas_width > 1 and canvas_height > 1:
                img_h, img_w = img_rgb.shape[:2]
                scale = min(canvas_width / img_w, canvas_height / img_h, 5)
                new_w = max(1, int(img_w * scale))
                new_h = max(1, int(img_h * scale))
                
                img_resized = cv2.resize(img_rgb, (new_w, new_h), interpolation=cv2.INTER_NEAREST)
                pil_img = Image.fromarray(img_resized)
                
                # Store reference to prevent garbage collection
                photo = ImageTk.PhotoImage(pil_img)
                canvas.image = photo
                
                canvas.delete("all")
                canvas.create_image(canvas_width // 2, canvas_height // 2, image=photo, anchor=tk.CENTER)
                
                if info_text:
                    canvas.create_text(10, 10, text=info_text, anchor=tk.NW, fill="white", font=("Consolas", 10))
        except Exception:
            pass
    
    def update_comparison(self, screen_img: np.ndarray):
        """Update comparison display."""
        name = self.selected_detection.get()
        det_config = self.config.get("detections", name)
        if not det_config:
            return
        
        try:
            template, mask = self.detection.get_cached_template(name)
            threshold = det_config.get("threshold", 0.95)
            color_tolerance = self.config.get("general", "default_color_tolerance", default=15)
            
            confidence = self.detection.calculate_confidence(screen_img, template, mask, color_tolerance)
            
            # Update labels
            self.current_confidence.set(f"{confidence:.4f}")
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
            
            # Update threshold canvas
            self.update_threshold_canvas(screen_img, template, mask, threshold, confidence)
            
        except Exception as e:
            self.current_confidence.set(f"Error")
    
    def update_template_canvas(self, template: np.ndarray, mask: np.ndarray = None):
        """Update template canvas."""
        try:
            template_rgb = cv2.cvtColor(template, cv2.COLOR_BGR2RGB)
            if mask is not None:
                mask_overlay = np.zeros_like(template_rgb)
                mask_overlay[:, :, 0] = mask
                template_rgb = cv2.addWeighted(template_rgb, 0.7, mask_overlay, 0.3, 0)
            
            self.update_canvas(self.template_canvas, cv2.cvtColor(template_rgb, cv2.COLOR_RGB2BGR), 
                             f"Template: {template.shape[1]}x{template.shape[0]}")
        except Exception:
            pass
    
    def update_threshold_canvas(self, screen_img: np.ndarray, template: np.ndarray, 
                                mask: np.ndarray, threshold: float, confidence: float):
        """Update threshold visualization canvas."""
        try:
            if screen_img.shape[:2] != template.shape[:2]:
                screen_resized = cv2.resize(screen_img, (template.shape[1], template.shape[0]), 
                                          interpolation=cv2.INTER_AREA)
            else:
                screen_resized = screen_img.copy()
            
            diff = cv2.absdiff(screen_resized, template)
            diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
            
            if mask is not None:
                mask_norm = (mask > 0).astype(np.uint8) * 255
                diff_gray = cv2.bitwise_and(diff_gray, diff_gray, mask=mask_norm)
            
            vis_img = np.zeros((diff_gray.shape[0], diff_gray.shape[1], 3), dtype=np.uint8)
            diff_threshold = int(255 * (1.0 - threshold))
            
            vis_img[:, :, 1] = np.where(diff_gray <= diff_threshold, 255, 0)
            vis_img[:, :, 2] = np.where(diff_gray > diff_threshold, diff_gray, 0)
            vis_img[:, :, 0] = diff_gray // 2
            
            if mask is not None:
                mask_3ch = np.stack([mask_norm] * 3, axis=-1) / 255.0
                vis_img = (vis_img * mask_3ch).astype(np.uint8)
            
            status = "PASS" if confidence >= threshold else "FAIL"
            self.update_canvas(self.threshold_canvas, vis_img, f"Thresh: {threshold:.2f} | {status}")
        except Exception:
            pass
    
    def on_closing(self):
        """Handle window close."""
        self.keyboard_listener.stop()
        self.root.destroy()
    
    def run(self):
        """Run the GUI application."""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()


# ==================== Admin Check ====================

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def request_admin():
    if not is_admin():
        print("ERROR: This script requires administrator privileges!")
        print("Requesting admin rights...")
        try:
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 1
            )
        except Exception as e:
            print(f"Failed to elevate privileges: {e}")
        sys.exit()


# ==================== Main ====================

def main():
    request_admin()
    app = GenshinSkipperGUI()
    app.run()


if __name__ == "__main__":
    main()
