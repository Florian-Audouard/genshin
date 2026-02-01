"""
Dialogue Skipper - GUI Application
Provides a graphical interface for the dialogue skipper with:
- Multi-profile support (different games/applications)
- JSON-based configuration storage
- Modifiable ROIs and thresholds via GUI
- Toggleable skip actions
- Custom action sequences per detection
- Detection management (create, rename, delete)
"""

import argparse
import io
import sys
import ctypes
import cv2
import os
import shutil
import time

# Parse --debug argument early
parser = argparse.ArgumentParser()
parser.add_argument('--debug', action='store_true', help='Keep terminal open for debugging')
args, _ = parser.parse_known_args()

# Hide console window on Windows (unless --debug)
if sys.platform == "win32" and not args.debug:
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

import numpy as np
import pyautogui
import win32clipboard
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox, simpledialog
from PIL import Image, ImageTk
from datetime import datetime
from typing import Dict
from pynput import keyboard as pynput_keyboard

# Import core logic from separate module
from skipper_core import (
    ConfigManager, DetectionEngine, SpamEngine, GlobalSettingsManager,
    get_available_profiles, create_profile, delete_profile, duplicate_profile,
    get_last_used_profile
)


# ==================== Main GUI Application ====================

class DialogueSkipperGUI:
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
        self.root.title("Dialogue Skipper")
        self.root.geometry("1100x900")
        self.root.resizable(True, True)
        
        # Apply dark theme
        self.setup_dark_theme()
        
        # Profile management
        last_profile = get_last_used_profile()
        self.current_profile = tk.StringVar(value=last_profile)
        self.available_profiles = get_available_profiles()
        
        # Initialize managers with current profile
        self.config = ConfigManager(self.current_profile.get())
        self.global_settings = GlobalSettingsManager()
        self.detection = DetectionEngine(self.config, self.global_settings)
        self.spam = SpamEngine(self.config, self.detection, self.global_settings)
        
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
        self.uniform_color_protection_var = tk.BooleanVar(value=True)
        self.action_sequence_var = tk.StringVar(value="")
        
        # Flag to prevent autosave during detection config loading
        self._loading_detection_config = False
        
        # Detection enable/disable checkbuttons
        self.detection_vars: Dict[str, tk.BooleanVar] = {}
        
        # Status variables
        self.spam_status = tk.StringVar(value="PAUSED")
        self.debug_status = tk.StringVar(value="OFF")
        
        # ROI movement keys setting (separate keys for each direction)
        roi_keys = self.global_settings.get("general", "roi_keys", default={"up": "z", "down": "s", "left": "q", "right": "d"})
        self.roi_key_up_var = tk.StringVar(value=roi_keys.get("up", "z"))
        self.roi_key_down_var = tk.StringVar(value=roi_keys.get("down", "s"))
        self.roi_key_left_var = tk.StringVar(value=roi_keys.get("left", "q"))
        self.roi_key_right_var = tk.StringVar(value=roi_keys.get("right", "d"))
        
        # ROI movement step sizes
        self.roi_step_normal_var = tk.IntVar(value=self.global_settings.get("general", "roi_step_normal", default=10))
        self.roi_step_fine_var = tk.IntVar(value=self.global_settings.get("general", "roi_step_fine", default=1))
        
        # Set initial window title with profile name
        profile_display_name = self.config.get('profile', 'name', default=self.current_profile.get())
        self.root.title(f"Dialogue Skipper - {profile_display_name}")
        
        # Setup
        self.setup_ui()
        self.setup_callbacks()
        self.setup_keyboard_listener()
        self.setup_roi_keyboard_controls()
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
        # Profile selector at top
        profile_frame = ttk.Frame(self.root)
        profile_frame.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        ttk.Label(profile_frame, text="Profile:", font=("Consolas", 10, "bold")).pack(side=tk.LEFT, padx=5)
        self.profile_combo = ttk.Combobox(profile_frame, textvariable=self.current_profile,
                                          values=self.available_profiles, state="readonly", width=20)
        self.profile_combo.pack(side=tk.LEFT, padx=5)
        self.profile_combo.bind("<<ComboboxSelected>>", lambda e: self.switch_profile())
        
        ttk.Button(profile_frame, text="New", command=self.create_new_profile, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(profile_frame, text="Duplicate", command=self.duplicate_current_profile, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(profile_frame, text="Delete", command=self.delete_current_profile, width=8).pack(side=tk.LEFT, padx=2)
        
        # Profile display name
        self.profile_display_var = tk.StringVar(value=self.config.get("profile", "name", default=""))
        ttk.Label(profile_frame, text="  |  ").pack(side=tk.LEFT)
        ttk.Label(profile_frame, textvariable=self.profile_display_var, font=("Consolas", 10)).pack(side=tk.LEFT, padx=5)
        
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
        
        # Container for ROI and Action Sequence side by side
        top_container = ttk.Frame(main_frame)
        top_container.pack(fill=tk.BOTH, expand=False, pady=(0, 10))
        
        # ROI Controls (left side)
        roi_frame = ttk.LabelFrame(top_container, text="ROI Settings", padding="10")
        roi_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Detection selector with management buttons
        det_row = ttk.Frame(roi_frame)
        det_row.grid(row=0, column=0, columnspan=4, sticky=tk.W, pady=(0, 5))
        
        ttk.Label(det_row, text="Detection:").pack(side=tk.LEFT, padx=5)
        self.det_combo = ttk.Combobox(det_row, textvariable=self.selected_detection,
                                 values=list(self.config.get("detections", default={}).keys()),
                                 state="readonly", width=15)
        self.det_combo.pack(side=tk.LEFT, padx=5)
        self.det_combo.bind("<<ComboboxSelected>>", self.on_detection_changed)
        
        ttk.Button(det_row, text="+ New", command=self.create_new_detection, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(det_row, text="Rename", command=self.rename_detection, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(det_row, text="Delete", command=self.delete_detection, width=8).pack(side=tk.LEFT, padx=2)
        
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
        
        ttk.Button(btn_frame, text="Select ROI (F9)", command=self.select_roi_from_screen).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Capture & Save Template", command=self.capture_and_save_template).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Copy Image", command=self.copy_image_to_clipboard).pack(side=tk.LEFT, padx=5)
        
        ttk.Checkbutton(roi_frame, text="Live Preview", variable=self.live_preview).grid(row=5, column=0, columnspan=2)
        ttk.Checkbutton(roi_frame, text="Uniform Color Protection", variable=self.uniform_color_protection_var).grid(row=5, column=2, columnspan=2)
        
        # Action Sequence Editor (right side)
        action_frame = ttk.LabelFrame(top_container, text="Action Sequence (one command per line)", padding="10")
        action_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        action_info = ttk.Label(action_frame, text=r"Commands: click | key | wait:ms | set var val | loop N | if $var>val | endif | endloop",
                       font=("Consolas", 8), foreground="gray")
        action_info.pack(anchor=tk.W)
        
        self.action_text = tk.Text(action_frame, height=8, font=("Consolas", 10),
                                   bg=self.DARK_BG2, fg=self.DARK_FG,
                                   insertbackground=self.DARK_FG,
                                   selectbackground=self.DARK_SELECT,
                                   relief=tk.FLAT, borderwidth=2)
        self.action_text.pack(fill=tk.BOTH, expand=True, pady=5)
        self.action_text.bind("<KeyRelease>", self.on_action_sequence_changed)
        
        ttk.Button(action_frame, text="Save Action Sequence", command=self.save_action_sequence).pack(anchor=tk.W)
        
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
        
        # ROI Keyboard control focus widget
        kb_frame = ttk.Frame(main_frame)
        kb_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(kb_frame, text="Keyboard Control:", font=("Consolas", 9)).pack(side=tk.LEFT)
        self.roi_focus_widget = tk.Label(kb_frame, text="  Click here to enable arrow/ZQSD controls  ",
                                         bg=self.DARK_BG3, fg=self.DARK_FG,
                                         relief=tk.SUNKEN, padx=10, pady=5,
                                         font=("Consolas", 9))
        self.roi_focus_widget.pack(side=tk.LEFT, padx=10)
        self.roi_focus_widget.bind('<Button-1>', self._focus_roi_widget)
        self.roi_focus_widget.bind('<FocusIn>', lambda e: self.roi_focus_widget.config(bg=self.DARK_ACCENT, text="  ACTIVE - Use arrows/keys to move ROI  "))
        self.roi_focus_widget.bind('<FocusOut>', lambda e: self.roi_focus_widget.config(bg=self.DARK_BG3, text="  Click here to enable arrow/ZQSD controls  "))
        # Make it focusable
        self.roi_focus_widget.config(takefocus=True)
        
        step_info = ttk.Label(kb_frame, text="Move: keys | Resize: Ctrl+keys | Fine: Shift+keys",
                              font=("Consolas", 8), foreground="gray")
        step_info.pack(side=tk.LEFT, padx=10)
    
    def setup_settings_tab(self):
        """Setup the settings tab."""
        main_frame = ttk.Frame(self.settings_tab, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Profile settings
        profile_frame = ttk.LabelFrame(main_frame, text="Profile Settings", padding="10")
        profile_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Profile display name
        ttk.Label(profile_frame, text="Profile Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.profile_name_var = tk.StringVar(value=self.config.get("profile", "name", default=""))
        ttk.Entry(profile_frame, textvariable=self.profile_name_var, width=30).grid(row=0, column=1, padx=5, columnspan=2)
        
        # Window title
        ttk.Label(profile_frame, text="Window Title:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.window_title_var = tk.StringVar(value=self.config.get("profile", "window_title", default=""))
        ttk.Entry(profile_frame, textvariable=self.window_title_var, width=30).grid(row=1, column=1, padx=5)
        ttk.Button(profile_frame, text="Browse Windows", command=self.get_active_window_title).grid(row=1, column=2, padx=5)
        
        ttk.Label(profile_frame, text="(Leave empty to always run, regardless of active window)", 
                  font=("Consolas", 8), foreground="gray").grid(row=2, column=0, columnspan=3, sticky=tk.W, padx=5)
        
        # General settings
        general_frame = ttk.LabelFrame(main_frame, text="General Settings", padding="10")
        general_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Pause between spams
        ttk.Label(general_frame, text="Pause Between Spams (sec):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.pause_var = tk.DoubleVar(value=self.global_settings.get("general", "pause_between_spams", default=0.05))
        ttk.Spinbox(general_frame, from_=0.01, to=1.0, increment=0.01, textvariable=self.pause_var, 
                   width=10, format="%.2f").grid(row=0, column=1, padx=5)
        
        # Color tolerance
        ttk.Label(general_frame, text="Color Tolerance (0-255):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.tolerance_var = tk.IntVar(value=self.global_settings.get("general", "default_color_tolerance", default=15))
        ttk.Spinbox(general_frame, from_=0, to=255, textvariable=self.tolerance_var, width=10).grid(row=1, column=1, padx=5)
        
        # Click position
        click_frame = ttk.LabelFrame(main_frame, text="Click Position (for 'click' command)", padding="10")
        click_frame.pack(fill=tk.X, pady=(0, 10))
        
        click_pos = self.global_settings.get("click_position", default={"x": 960, "y": 540})
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
        self.hotkey_spam_var = tk.StringVar(value=self.global_settings.get("hotkeys", "toggle_spam", default="F7"))
        ttk.Entry(hotkey_frame, textvariable=self.hotkey_spam_var, width=10).grid(row=0, column=1, padx=5)
        
        ttk.Label(hotkey_frame, text="Toggle Debug:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.hotkey_debug_var = tk.StringVar(value=self.global_settings.get("hotkeys", "toggle_debug", default="F8"))
        ttk.Entry(hotkey_frame, textvariable=self.hotkey_debug_var, width=10).grid(row=0, column=3, padx=5)
        
        # ROI Movement Keys
        roi_keys_frame = ttk.LabelFrame(main_frame, text="ROI Movement Keys (+ Arrows always work)", padding="10")
        roi_keys_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(roi_keys_frame, text="Up:").grid(row=0, column=0, sticky=tk.W, padx=5)
        ttk.Entry(roi_keys_frame, textvariable=self.roi_key_up_var, width=5).grid(row=0, column=1, padx=5)
        
        ttk.Label(roi_keys_frame, text="Down:").grid(row=0, column=2, sticky=tk.W, padx=5)
        ttk.Entry(roi_keys_frame, textvariable=self.roi_key_down_var, width=5).grid(row=0, column=3, padx=5)
        
        ttk.Label(roi_keys_frame, text="Left:").grid(row=0, column=4, sticky=tk.W, padx=5)
        ttk.Entry(roi_keys_frame, textvariable=self.roi_key_left_var, width=5).grid(row=0, column=5, padx=5)
        
        ttk.Label(roi_keys_frame, text="Right:").grid(row=0, column=6, sticky=tk.W, padx=5)
        ttk.Entry(roi_keys_frame, textvariable=self.roi_key_right_var, width=5).grid(row=0, column=7, padx=5)
        
        ttk.Label(roi_keys_frame, text="Normal Step (px):").grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=5, pady=(10, 0))
        ttk.Spinbox(roi_keys_frame, from_=1, to=100, textvariable=self.roi_step_normal_var, width=5).grid(row=1, column=2, padx=5, pady=(10, 0))
        
        ttk.Label(roi_keys_frame, text="Fine Step (Shift):").grid(row=1, column=3, columnspan=2, sticky=tk.W, padx=5, pady=(10, 0))
        ttk.Spinbox(roi_keys_frame, from_=1, to=50, textvariable=self.roi_step_fine_var, width=5).grid(row=1, column=5, padx=5, pady=(10, 0))
        
        # Info
        info_frame = ttk.LabelFrame(main_frame, text="Information", padding="10")
        info_frame.pack(fill=tk.X)
        
        info_text = """
Action Sequence Commands:
    • click         - Click at configured position
    • Any key       - Press key (e, space, escape, enter, f, etc.)
    • wait:N        - Wait N milliseconds (e.g., wait:100)
    • set var val   - Set variable (e.g., set count 3)
    • loop N        - Loop block N times (or loop $var for variable count)
    • if $var>5     - Conditional block (>, <, >=, <=, ==, !=)
    • endif/endloop - End blocks

Examples:
    • Simple: space, e, wait:100, click
    • Loop 3 times: loop 3, space, wait:50, endloop
    • With variable: set n 5, loop $n, e, endloop
    • Conditional: if $n > 0, click, set n 0, endif

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
        
        # Profile settings - save when changed
        self.profile_name_var.trace_add("write", lambda *args: self.autosave_profile_setting("name", self.profile_name_var.get()))
        self.window_title_var.trace_add("write", lambda *args: self.autosave_profile_setting("window_title", self.window_title_var.get()))
        
        # Settings variables - save when changed
        self.pause_var.trace_add("write", lambda *args: self.autosave_global_setting("general", "pause_between_spams", self.pause_var.get()))
        self.tolerance_var.trace_add("write", lambda *args: self.autosave_global_setting("general", "default_color_tolerance", self.tolerance_var.get()))
        self.click_x_var.trace_add("write", lambda *args: self.autosave_click_position())
        self.click_y_var.trace_add("write", lambda *args: self.autosave_click_position())
        self.hotkey_spam_var.trace_add("write", lambda *args: self.autosave_global_setting("hotkeys", "toggle_spam", self.hotkey_spam_var.get()))
        self.hotkey_debug_var.trace_add("write", lambda *args: self.autosave_global_setting("hotkeys", "toggle_debug", self.hotkey_debug_var.get()))
        self.roi_key_up_var.trace_add("write", lambda *args: self.autosave_roi_keys())
        self.roi_key_down_var.trace_add("write", lambda *args: self.autosave_roi_keys())
        self.roi_key_left_var.trace_add("write", lambda *args: self.autosave_roi_keys())
        self.roi_key_right_var.trace_add("write", lambda *args: self.autosave_roi_keys())
        self.roi_step_normal_var.trace_add("write", lambda *args: self.autosave_global_setting("general", "roi_step_normal", self.roi_step_normal_var.get()))
        self.roi_step_fine_var.trace_add("write", lambda *args: self.autosave_global_setting("general", "roi_step_fine", self.roi_step_fine_var.get()))
        self.uniform_color_protection_var.trace_add("write", lambda *args: self.autosave_uniform_color_protection())
    
    def autosave_profile_setting(self, key: str, value):
        """Auto-save profile setting."""
        try:
            self.config.set(value, "profile", key)
            # Update display name in header
            if key == "name":
                self.profile_display_var.set(value)
        except (tk.TclError, ValueError):
            pass
    
    def autosave_roi_keys(self):
        """Auto-save ROI movement keys."""
        try:
            keys = {
                "up": self.roi_key_up_var.get(),
                "down": self.roi_key_down_var.get(),
                "left": self.roi_key_left_var.get(),
                "right": self.roi_key_right_var.get()
            }
            self.global_settings.set(keys, "general", "roi_keys")
        except (tk.TclError, ValueError):
            pass
    
    def autosave_roi(self):
        """Auto-save ROI settings for the selected detection."""
        # Skip autosave if we're currently loading detection config
        if self._loading_detection_config:
            return
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
            self.config.set(self.uniform_color_protection_var.get(), "detections", name, "uniform_color_protection")
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
    
    def autosave_global_setting(self, *keys_and_value):
        """Auto-save a global setting."""
        try:
            *keys, value = keys_and_value
            self.global_settings.set(value, *keys)
        except (tk.TclError, ValueError):
            pass  # Ignore errors during typing/invalid values
    
    def autosave_click_position(self):
        """Auto-save click position."""
        try:
            self.global_settings.set({"x": self.click_x_var.get(), "y": self.click_y_var.get()}, "click_position")
        except (tk.TclError, ValueError):
            pass  # Ignore errors during typing/invalid values
    
    def autosave_uniform_color_protection(self):
        """Auto-save uniform color protection for the selected detection."""
        if self._loading_detection_config:
            return
        try:
            name = self.selected_detection.get()
            self.config.set(self.uniform_color_protection_var.get(), "detections", name, "uniform_color_protection")
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
                    self.root.after(0, self.select_roi_from_screen)
            except AttributeError:
                pass
        
        self.keyboard_listener = pynput_keyboard.Listener(on_press=on_press)
        self.keyboard_listener.start()
    
    def setup_roi_keyboard_controls(self):
        """Setup keyboard controls for ROI movement and resizing."""
        def is_roi_focus_active():
            """Check if the ROI focus widget has focus."""
            return self.root.focus_get() == self.roi_focus_widget
        
        def get_step(event):
            """Get step size based on Shift key state."""
            if event.state & 0x1:  # Shift pressed
                return self.roi_step_fine_var.get()
            return self.roi_step_normal_var.get()
        
        def handle_roi_move(direction, ctrl_pressed, event=None):
            """Handle ROI movement or resize based on direction and ctrl state."""
            if not is_roi_focus_active():
                return None  # Let default handling occur
            
            step = get_step(event) if event else self.roi_step_normal_var.get()
            
            if ctrl_pressed:
                # Resize mode
                if direction == 'up':
                    self.roi_height.set(max(1, self.roi_height.get() - step))
                elif direction == 'down':
                    self.roi_height.set(self.roi_height.get() + step)
                elif direction == 'left':
                    self.roi_width.set(max(1, self.roi_width.get() - step))
                elif direction == 'right':
                    self.roi_width.set(self.roi_width.get() + step)
            else:
                # Move mode
                if direction == 'up':
                    self.roi_top.set(max(0, self.roi_top.get() - step))
                elif direction == 'down':
                    self.roi_top.set(self.roi_top.get() + step)
                elif direction == 'left':
                    self.roi_left.set(max(0, self.roi_left.get() - step))
                elif direction == 'right':
                    self.roi_left.set(self.roi_left.get() + step)
            
            return "break"  # Prevent default behavior
        
        # Bind arrow keys (always work when focus widget is active)
        self.root.bind('<Up>', lambda e: handle_roi_move('up', False, e))
        self.root.bind('<Down>', lambda e: handle_roi_move('down', False, e))
        self.root.bind('<Left>', lambda e: handle_roi_move('left', False, e))
        self.root.bind('<Right>', lambda e: handle_roi_move('right', False, e))
        self.root.bind('<Control-Up>', lambda e: handle_roi_move('up', True, e))
        self.root.bind('<Control-Down>', lambda e: handle_roi_move('down', True, e))
        self.root.bind('<Control-Left>', lambda e: handle_roi_move('left', True, e))
        self.root.bind('<Control-Right>', lambda e: handle_roi_move('right', True, e))
        
        # Bind all letter keys for custom mapping
        for key in 'abcdefghijklmnopqrstuvwxyz':
            self.root.bind(f'<{key}>', lambda e, k=key: self._handle_letter_key(e, k, False))
            self.root.bind(f'<{key.upper()}>', lambda e, k=key: self._handle_letter_key(e, k, False))
            self.root.bind(f'<Control-{key}>', lambda e, k=key: self._handle_letter_key(e, k, True))
    
    def _focus_roi_widget(self, event=None):
        """Focus the ROI control widget."""
        self.roi_focus_widget.focus_set()
    
    def _handle_letter_key(self, event, key, ctrl_pressed):
        """Handle letter key for ROI movement if configured."""
        # Only work when focus widget is active
        if self.root.focus_get() != self.roi_focus_widget:
            return None
        
        key_lower = key.lower()
        step = self.roi_step_fine_var.get() if (event.state & 0x1) else self.roi_step_normal_var.get()
        
        # Check against configured keys
        direction = None
        if key_lower == self.roi_key_up_var.get().lower():
            direction = 'up'
        elif key_lower == self.roi_key_down_var.get().lower():
            direction = 'down'
        elif key_lower == self.roi_key_left_var.get().lower():
            direction = 'left'
        elif key_lower == self.roi_key_right_var.get().lower():
            direction = 'right'
        
        if direction is None:
            return None
        
        if ctrl_pressed:
            if direction == 'up':
                self.roi_height.set(max(1, self.roi_height.get() - step))
            elif direction == 'down':
                self.roi_height.set(self.roi_height.get() + step)
            elif direction == 'left':
                self.roi_width.set(max(1, self.roi_width.get() - step))
            elif direction == 'right':
                self.roi_width.set(self.roi_width.get() + step)
        else:
            if direction == 'up':
                self.roi_top.set(max(0, self.roi_top.get() - step))
            elif direction == 'down':
                self.roi_top.set(self.roi_top.get() + step)
            elif direction == 'left':
                self.roi_left.set(max(0, self.roi_left.get() - step))
            elif direction == 'right':
                self.roi_left.set(self.roi_left.get() + step)
        
        return "break"

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
            # Set flag to prevent autosave during loading
            self._loading_detection_config = True
            try:
                roi = det_config.get("roi", {})
                self.roi_left.set(roi.get("left", 0))
                self.roi_top.set(roi.get("top", 0))
                self.roi_width.set(roi.get("width", 100))
                self.roi_height.set(roi.get("height", 100))
                self.threshold_var.set(det_config.get("threshold", 0.95))
                self.threshold_label.config(text=f"{det_config.get('threshold', 0.95):.2f}")
                self.uniform_color_protection_var.set(det_config.get("uniform_color_protection", True))
                
                # Load action sequence
                action_sequence = det_config.get("action_sequence", "")
                self.action_text.delete("1.0", tk.END)
                self.action_text.insert("1.0", action_sequence)
            finally:
                # Clear flag after loading is complete
                self._loading_detection_config = False
    
    def clear_detection_ui(self):
        """Clear all detection UI fields and disable controls."""
        self._loading_detection_config = True
        try:
            # Clear ROI values
            self.roi_left.set(0)
            self.roi_top.set(0)
            self.roi_width.set(100)
            self.roi_height.set(100)
            
            # Clear threshold and other settings
            self.threshold_var.set(0.95)
            self.threshold_label.config(text="0.95")
            self.uniform_color_protection_var.set(True)
            
            # Clear action sequence
            self.action_text.delete("1.0", tk.END)
            
            # Clear template display
            if hasattr(self, 'template_label'):
                self.template_label.config(image='', text="No template")
        finally:
            self._loading_detection_config = False
    
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
    
    def select_roi_from_screen(self):
        """Open fullscreen overlay to select ROI by drawing a rectangle."""
        self.root.withdraw()  # Hide main window
        time.sleep(0.1)  # Allow window to hide
        
        # Create fullscreen transparent overlay
        overlay = tk.Toplevel()
        overlay.attributes('-fullscreen', True)
        overlay.attributes('-topmost', True)
        overlay.attributes('-alpha', 0.3)
        overlay.configure(bg='black')
        overlay.config(cursor='cross')
        
        canvas = tk.Canvas(overlay, highlightthickness=0, bg='black')
        canvas.pack(fill=tk.BOTH, expand=True)
        
        # Selection state
        start_pos = [None, None]
        rect_id = [None]
        result = [None]
        
        def on_press(event):
            start_pos[0] = event.x
            start_pos[1] = event.y
            if rect_id[0]:
                canvas.delete(rect_id[0])
            rect_id[0] = canvas.create_rectangle(event.x, event.y, event.x, event.y, 
                                                  outline='red', width=2)
        
        def on_drag(event):
            if start_pos[0] is not None and rect_id[0]:
                canvas.coords(rect_id[0], start_pos[0], start_pos[1], event.x, event.y)
        
        def on_release(event):
            if start_pos[0] is not None:
                x1, y1 = start_pos
                x2, y2 = event.x, event.y
                # Normalize coordinates
                left = min(x1, x2)
                top = min(y1, y2)
                width = abs(x2 - x1)
                height = abs(y2 - y1)
                if width > 5 and height > 5:  # Minimum size check
                    result[0] = (left, top, width, height)
            overlay.destroy()
        
        def on_escape(event):
            overlay.destroy()
        
        canvas.bind('<ButtonPress-1>', on_press)
        canvas.bind('<B1-Motion>', on_drag)
        canvas.bind('<ButtonRelease-1>', on_release)
        overlay.bind('<Escape>', on_escape)
        
        overlay.wait_window()
        self.root.deiconify()  # Show main window again
        
        if result[0]:
            left, top, width, height = result[0]
            self.roi_left.set(left)
            self.roi_top.set(top)
            self.roi_width.set(width)
            self.roi_height.set(height)
            self.log_message(f"ROI set to ({left}, {top}, {width}x{height})")
            self.status_var.set(f"ROI: ({left}, {top}, {width}x{height})")
    
    def set_click_from_mouse(self):
        """Set click position from current mouse position."""
        pos = pyautogui.position()
        self.click_x_var.set(pos[0])
        self.click_y_var.set(pos[1])
        self.log_message(f"Click position set to ({pos[0]}, {pos[1]})")
    
    def capture_and_save_template(self):
        """Capture current ROI and save as template for the selected detection."""
        name = self.selected_detection.get()
        det_config = self.config.get("detections", name)
        if not det_config:
            return
        
        roi = self.get_current_roi()
        img = self.detection.capture_screen(roi)
        
        # Automatically open background removal window
        img = self.remove_background_interactive(img)
        if img is None:
            return  # User cancelled
        
        # Save to template path (relative to profile directory)
        template_path = det_config.get("template", f"img/template_{name.lower()}.png")
        full_path = self.config.get_template_path(template_path)
        
        # Ensure img directory exists
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        cv2.imwrite(full_path, img)
        self.detection.clear_template_cache(name)
        self.log_message(f"Template saved: {template_path}")
        self.status_var.set(f"Template saved: {template_path}")
    
    def remove_background_interactive(self, img: np.ndarray) -> np.ndarray:
        """Interactive background removal - click to select colors to make transparent with live preview."""
        result = [None]
        tolerance = [30]
        selected_colors = []  # List of (color, tolerance) tuples
        preview_image = [img.copy()]  # Current preview with transparency applied
        mode = [False]  # False = Blacklist (remove selected), True = Whitelist (keep selected)
        
        # Create preview window
        preview_window = tk.Toplevel(self.root)
        preview_window.title("Background Remover")
        preview_window.configure(bg=self.DARK_BG)
        preview_window.transient(self.root)
        preview_window.grab_set()
        preview_window.geometry("750x650")
        
        # Instructions label (will be updated based on mode)
        instructions_var = tk.StringVar(value="BLACKLIST MODE: Click on colors to REMOVE (make transparent)")
        instructions_label = ttk.Label(preview_window, textvariable=instructions_var, font=("Consolas", 10))
        instructions_label.pack(pady=5)
        
        # Mode toggle frame
        mode_frame = ttk.Frame(preview_window)
        mode_frame.pack(fill=tk.X, padx=10, pady=5)
        
        mode_var = tk.BooleanVar(value=False)
        
        def on_mode_change():
            mode[0] = mode_var.get()
            if mode[0]:
                instructions_var.set("WHITELIST MODE: Click on colors to KEEP (everything else becomes transparent)")
                colors_frame.config(text="Colors to KEEP (click to remove)")
            else:
                instructions_var.set("BLACKLIST MODE: Click on colors to REMOVE (make transparent)")
                colors_frame.config(text="Colors to REMOVE (click to remove)")
            update_preview()
        
        ttk.Radiobutton(mode_frame, text="Blacklist (remove selected colors)", 
                       variable=mode_var, value=False, command=on_mode_change).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(mode_frame, text="Whitelist (keep only selected colors)", 
                       variable=mode_var, value=True, command=on_mode_change).pack(side=tk.LEFT, padx=10)
        
        # Top controls frame
        controls_frame = ttk.Frame(preview_window)
        controls_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Tolerance slider
        ttk.Label(controls_frame, text="Tolerance:").pack(side=tk.LEFT)
        tol_var = tk.IntVar(value=30)
        tol_slider = ttk.Scale(controls_frame, from_=1, to=100, variable=tol_var, orient=tk.HORIZONTAL, length=150)
        tol_slider.pack(side=tk.LEFT, padx=5)
        tol_label = ttk.Label(controls_frame, text="30", width=4)
        tol_label.pack(side=tk.LEFT)
        
        def on_tolerance_change(*args):
            tolerance[0] = tol_var.get()
            tol_label.config(text=str(tolerance[0]))
        tol_var.trace_add("write", on_tolerance_change)
        
        # Color info label
        ttk.Label(controls_frame, text="   |   ").pack(side=tk.LEFT)
        color_info = ttk.Label(controls_frame, text="Hover to see color", font=("Consolas", 9))
        color_info.pack(side=tk.LEFT, padx=10)
        
        # Preview canvases frame
        canvas_frame = ttk.Frame(preview_window)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Calculate preview dimensions - ensure minimum size for small ROIs
        min_preview_size = 200
        max_preview_size = 350
        
        # Scale up small images to at least min_preview_size
        img_w, img_h = img.shape[1], img.shape[0]
        scale = max(min_preview_size / min(img_w, img_h), 1)  # Scale up if needed
        
        preview_width = int(img_w * scale)
        preview_height = int(img_h * scale)
        
        # Cap at max size while maintaining aspect ratio
        if preview_width > max_preview_size or preview_height > max_preview_size:
            scale_down = max_preview_size / max(preview_width, preview_height)
            preview_width = int(preview_width * scale_down)
            preview_height = int(preview_height * scale_down)
        
        # Ensure minimum dimensions
        preview_width = max(preview_width, min_preview_size)
        preview_height = max(preview_height, min_preview_size)
        
        # Original image canvas (left)
        left_frame = ttk.LabelFrame(canvas_frame, text="Original (Click to select color)")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        orig_canvas = tk.Canvas(left_frame, width=preview_width, height=preview_height, 
                               bg=self.DARK_BG3, cursor="crosshair")
        orig_canvas.pack(padx=5, pady=5)
        
        # Preview canvas (right) - shows checkerboard for transparency
        right_frame = ttk.LabelFrame(canvas_frame, text="Preview (Transparent areas shown)")
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        preview_canvas = tk.Canvas(right_frame, width=preview_width, height=preview_height, 
                                   bg=self.DARK_BG3)
        preview_canvas.pack(padx=5, pady=5)
        
        # Selected colors list
        colors_frame = ttk.LabelFrame(preview_window, text="Colors to REMOVE (click to remove)")
        colors_frame.pack(fill=tk.X, padx=10, pady=5)
        
        colors_inner = ttk.Frame(colors_frame)
        colors_inner.pack(fill=tk.X, padx=5, pady=5)
        
        def create_checkerboard(width, height, square_size=8):
            """Create a checkerboard pattern for transparency preview."""
            checker = np.zeros((height, width, 3), dtype=np.uint8)
            for y in range(0, height, square_size):
                for x in range(0, width, square_size):
                    if (x // square_size + y // square_size) % 2 == 0:
                        checker[y:y+square_size, x:x+square_size] = [60, 60, 60]
                    else:
                        checker[y:y+square_size, x:x+square_size] = [40, 40, 40]
            return checker
        
        def update_preview():
            """Update the preview with current transparency settings."""
            if not selected_colors:
                # No colors selected, show original
                preview_image[0] = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
            else:
                # Apply all selected colors
                img_bgra = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
                combined_mask = np.zeros((img.shape[0], img.shape[1]), dtype=np.uint8)
                
                for color, tol in selected_colors:
                    color_bgr = color[:3]
                    lower = np.maximum(color_bgr.astype(np.int32) - tol, 0).astype(np.uint8)
                    upper = np.minimum(color_bgr.astype(np.int32) + tol, 255).astype(np.uint8)
                    mask = cv2.inRange(img[:, :, :3], lower, upper)
                    combined_mask = cv2.bitwise_or(combined_mask, mask)
                
                if mode[0]:  # Whitelist mode - keep selected colors, remove everything else
                    img_bgra[:, :, 3] = np.where(combined_mask > 0, 255, 0)
                else:  # Blacklist mode - remove selected colors
                    img_bgra[:, :, 3] = np.where(combined_mask > 0, 0, 255)
                preview_image[0] = img_bgra
            
            # Update preview canvas with checkerboard background
            checker = create_checkerboard(preview_width, preview_height)
            
            # Resize and composite
            preview_resized = cv2.resize(preview_image[0], (preview_width, preview_height), 
                                        interpolation=cv2.INTER_NEAREST)
            
            # Composite over checkerboard
            alpha = preview_resized[:, :, 3:4].astype(np.float32) / 255.0
            preview_rgb = preview_resized[:, :, :3]
            preview_rgb = cv2.cvtColor(preview_rgb, cv2.COLOR_BGR2RGB)
            
            composite = (preview_rgb.astype(np.float32) * alpha + 
                        checker.astype(np.float32) * (1 - alpha)).astype(np.uint8)
            
            pil_preview = Image.fromarray(composite)
            photo_preview = ImageTk.PhotoImage(pil_preview)
            preview_canvas.delete("all")
            preview_canvas.create_image(0, 0, image=photo_preview, anchor=tk.NW)
            preview_canvas.image = photo_preview
        
        def update_colors_display():
            """Update the selected colors display."""
            for widget in colors_inner.winfo_children():
                widget.destroy()
            
            if not selected_colors:
                ttk.Label(colors_inner, text="No colors selected yet").pack(side=tk.LEFT)
            else:
                for i, (color, tol) in enumerate(selected_colors):
                    # Create a small colored button
                    color_hex = f"#{color[2]:02x}{color[1]:02x}{color[0]:02x}"  # BGR to RGB hex
                    frame = ttk.Frame(colors_inner)
                    frame.pack(side=tk.LEFT, padx=2)
                    
                    btn = tk.Button(frame, bg=color_hex, width=3, height=1, relief=tk.RAISED,
                                   command=lambda idx=i: remove_color(idx))
                    btn.pack()
                    ttk.Label(frame, text=f"±{tol}", font=("Consolas", 7)).pack()
        
        def remove_color(index):
            """Remove a color from the selection."""
            if 0 <= index < len(selected_colors):
                selected_colors.pop(index)
                update_colors_display()
                update_preview()
        
        def on_canvas_click(event):
            """Handle click on original canvas to pick color."""
            # Scale to original image coordinates using fixed preview dimensions
            scale_x = img.shape[1] / preview_width
            scale_y = img.shape[0] / preview_height
            
            orig_x = int(event.x * scale_x)
            orig_y = int(event.y * scale_y)
            
            if 0 <= orig_x < img.shape[1] and 0 <= orig_y < img.shape[0]:
                picked_color = img[orig_y, orig_x].copy()
                selected_colors.append((picked_color, tolerance[0]))
                update_colors_display()
                update_preview()
        
        def on_canvas_motion(event):
            """Show color under cursor."""
            # Scale to original image coordinates using fixed preview dimensions
            scale_x = img.shape[1] / preview_width
            scale_y = img.shape[0] / preview_height
            
            orig_x = int(event.x * scale_x)
            orig_y = int(event.y * scale_y)
            
            if 0 <= orig_x < img.shape[1] and 0 <= orig_y < img.shape[0]:
                color = img[orig_y, orig_x]
                color_hex = f"#{color[2]:02x}{color[1]:02x}{color[0]:02x}"
                color_info.config(text=f"Color: {color_hex} RGB({color[2]},{color[1]},{color[0]})")
        
        orig_canvas.bind("<Button-1>", on_canvas_click)
        orig_canvas.bind("<Motion>", on_canvas_motion)
        
        # Display original image
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img_resized = cv2.resize(img_rgb, (preview_width, preview_height), interpolation=cv2.INTER_NEAREST)
        pil_img = Image.fromarray(img_resized)
        photo = ImageTk.PhotoImage(pil_img)
        orig_canvas.create_image(0, 0, image=photo, anchor=tk.NW)
        orig_canvas.image = photo
        
        # Initialize preview
        update_preview()
        update_colors_display()
        
        # Bottom buttons
        btn_frame = ttk.Frame(preview_window)
        btn_frame.pack(pady=10)
        
        def on_apply():
            if selected_colors:
                result[0] = preview_image[0].copy()
            else:
                result[0] = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
            preview_window.destroy()
        
        def on_clear():
            selected_colors.clear()
            update_colors_display()
            update_preview()
        
        def on_skip():
            result[0] = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
            preview_window.destroy()
        
        def on_cancel():
            result[0] = None
            preview_window.destroy()
        
        ttk.Button(btn_frame, text="✓ Apply", command=on_apply, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Clear All", command=on_clear, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Skip (No Transparency)", command=on_skip, width=18).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=on_cancel, width=12).pack(side=tk.LEFT, padx=5)
        
        preview_window.wait_window()
        return result[0]
    
    def make_color_transparent(self, img: np.ndarray, color: np.ndarray, tolerance: int = 30) -> np.ndarray:
        """Make a specific color transparent in the image."""
        # Convert to BGRA
        if img.shape[2] == 3:
            img_bgra = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
        else:
            img_bgra = img.copy()
        
        # Create mask for the color (within tolerance)
        color = color[:3]  # Ensure only BGR
        lower = np.maximum(color.astype(np.int32) - tolerance, 0).astype(np.uint8)
        upper = np.minimum(color.astype(np.int32) + tolerance, 255).astype(np.uint8)
        
        mask = cv2.inRange(img_bgra[:, :, :3], lower, upper)
        
        # Set alpha to 0 where mask is white (color matches)
        img_bgra[:, :, 3] = np.where(mask > 0, 0, 255)
        
        return img_bgra
    
    def create_new_detection(self):
        """Create a new detection with a custom name."""
        # Generate automatic name
        existing = self.config.get("detections", default={})
        counter = 1
        name = f"DETECTION_{counter}"
        while name in existing:
            counter += 1
            name = f"DETECTION_{counter}"
        
        # Create new detection config (path relative to profile directory)
        template_path = f"img/template_{name.lower()}.png"
        new_config = {
            "enabled": True,
            "roi": {"left": 0, "top": 0, "width": 100, "height": 100},
            "threshold": 0.95,
            "template": template_path,
            "action_sequence": "click",
            "uniform_color_protection": True
        }
        
        self.config.set(new_config, "detections", name)
        
        # Update combobox
        self.refresh_detection_list()
        self.selected_detection.set(name)
        self.load_detection_config()
        
        # Add to main tab toggles
        self.refresh_detection_toggles()
        
        self.log_message(f"Created new detection: {name}")
        self.status_var.set(f"Created new detection: {name}. Position ROI and click 'Capture & Save Template'")
    
    def rename_detection(self):
        """Rename the selected detection."""
        old_name = self.selected_detection.get()
        if not old_name:
            self.log_message("No detection selected to rename")
            return
        
        # Create custom dialog with uppercase input
        dialog = tk.Toplevel(self.root)
        dialog.title("Rename Detection")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog on parent window
        dialog.geometry("350x120")
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 175
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 60
        dialog.geometry(f"+{x}+{y}")
        
        tk.Label(dialog, text=f"Enter new name for '{old_name}':").pack(pady=5)
        
        var = tk.StringVar(value=old_name.upper())
        entry = tk.Entry(dialog, textvariable=var, width=40)
        entry.pack(pady=5, padx=10)
        entry.select_range(0, tk.END)
        entry.focus()
        
        # Convert to uppercase as user types
        def on_change(*args):
            current = var.get()
            uppercase = current.upper()
            if current != uppercase:
                var.set(uppercase)
        
        var.trace('w', on_change)
        
        result = [None]
        
        def ok():
            result[0] = var.get()
            dialog.destroy()
        
        def cancel():
            dialog.destroy()
        
        frame = tk.Frame(dialog)
        frame.pack(pady=5)
        tk.Button(frame, text="OK", command=ok).pack(side=tk.LEFT, padx=5)
        tk.Button(frame, text="Cancel", command=cancel).pack(side=tk.LEFT, padx=5)
        
        dialog.wait_window()
        
        new_name = result[0]
        if not new_name or new_name == old_name:
            return
        
        # Rename in config (also renames template file)
        if self.config.rename_detection(old_name, new_name):
            self.detection.clear_template_cache(old_name)
            self.refresh_detection_list()
            self.selected_detection.set(new_name)
            self.load_detection_config()
            self.refresh_detection_toggles()
            self.log_message(f"Renamed detection: {old_name} -> {new_name}")
        else:
            self.log_message(f"Failed to rename detection: {old_name}")
    
    def delete_detection(self):
        """Delete the selected detection."""
        name = self.selected_detection.get()
        if not name:
            return
        
        # Confirm deletion
        if not messagebox.askyesno("Confirm Delete", f"Delete detection '{name}'?", parent=self.root):
            return
        
        # Get template path before deletion
        det_config = self.config.get("detections", name)
        template_path = det_config.get("template", "") if det_config else ""
        
        # Delete from config
        if self.config.delete("detections", name):
            # Delete template file
            if template_path:
                full_path = self.config.get_template_path(template_path)
                if os.path.exists(full_path):
                    try:
                        os.remove(full_path)
                    except OSError:
                        pass
            
            self.detection.clear_template_cache(name)
            self.refresh_detection_list()
            
            # Select first available detection
            detections = list(self.config.get("detections", default={}).keys())
            if detections:
                self.selected_detection.set(detections[0])
                self.load_detection_config()
            
            self.refresh_detection_toggles()
            self.log_message(f"Deleted detection: {name}")
    
    def refresh_detection_list(self):
        """Refresh the detection combobox list."""
        detections = list(self.config.get("detections", default={}).keys())
        self.det_combo['values'] = detections
        
        # If no detections, clear UI and disable controls
        if not detections:
            self.selected_detection.set("")
            self.clear_detection_ui()
        else:
            # Select first detection if not already selected
            if not self.selected_detection.get() or self.selected_detection.get() not in detections:
                self.selected_detection.set(detections[0])
                self.load_detection_config()
    
    def refresh_detection_toggles(self):
        """Refresh detection toggles in main tab."""
        # Clear existing toggles
        det_frame = None
        for child in self.main_tab.winfo_children():
            if isinstance(child, ttk.Frame):
                for subchild in child.winfo_children():
                    if isinstance(subchild, ttk.LabelFrame):
                        if "Detection Toggles" in str(subchild.cget("text")):
                            det_frame = subchild
                            break
        
        if det_frame:
            for widget in det_frame.winfo_children():
                widget.destroy()
            
            self.detection_vars.clear()
            detections = self.config.get("detections", default={})
            row = 0
            col = 0
            for name, det_config in detections.items():
                var = tk.BooleanVar(value=det_config.get("enabled", True))
                self.detection_vars[name] = var
                
                action_preview = det_config.get("action_sequence", "")[:20]
                if action_preview:
                    action_preview = action_preview.replace('\n', ',')[:15] + "..."
                else:
                    action_preview = "(empty)"
                
                chk = ttk.Checkbutton(det_frame, text=f"{name} ({action_preview})", 
                                      variable=var, command=lambda n=name: self.toggle_detection(n))
                chk.grid(row=row, column=col, sticky=tk.W, padx=10, pady=2)
                
                col += 1
                if col >= 3:
                    col = 0
                    row += 1
    
    def on_action_sequence_changed(self, event=None):
        """Handle action sequence text changes (for visual feedback only)."""
        pass  # Save is done explicitly via button
    
    def save_action_sequence(self):
        """Save the action sequence for the current detection."""
        if self._loading_detection_config:
            return
        
        name = self.selected_detection.get()
        sequence = self.action_text.get("1.0", tk.END).strip()
        
        self.config.set(sequence, "detections", name, "action_sequence")
        self.refresh_detection_toggles()
        self.log_message(f"Action sequence saved for {name}")
        self.status_var.set(f"Action sequence saved for {name}")
    
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
    
    def reload_config(self):
        """Reload configuration from file."""
        self.config.config = self.config.load()
        self.detection.clear_template_cache()
        self.load_detection_config()
        
        # Reload detection toggles
        for name, var in self.detection_vars.items():
            enabled = self.config.get("detections", name, "enabled", default=True)
            var.set(enabled)
        
        # Update profile settings UI
        self._loading_detection_config = True
        self.profile_name_var.set(self.config.get("profile", "name", default=""))
        self.window_title_var.set(self.config.get("profile", "window_title", default=""))
        self.profile_display_var.set(self.config.get("profile", "name", default=""))
        self._loading_detection_config = False
        
        self.log_message("Configuration reloaded!")
        self.status_var.set("Configuration reloaded!")
    
    # ==================== Profile Management ====================
    
    def switch_profile(self):
        """Switch to a different profile."""
        profile_name = self.current_profile.get()
        
        # Stop spam if running
        if self.spam.running:
            self.spam.toggle()
            self.on_spam_state_change(False)
        
        # Switch config manager to new profile
        self.config.switch_profile(profile_name)
        self.detection.clear_template_cache()
        
        # Reload all UI elements
        self.reload_config()
        self.refresh_detection_list()
        self.refresh_detection_toggles()
        
        # Update window title with profile name
        profile_display_name = self.config.get('profile', 'name', default=profile_name)
        self.root.title(f"Dialogue Skipper - {profile_display_name}")
        
        self.log_message(f"Switched to profile: {profile_name}")
        self.status_var.set(f"Switched to profile: {profile_display_name}")
    
    def create_new_profile(self):
        """Create a new profile."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Create New Profile")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.geometry("400x120")
        
        # Center dialog
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 200
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 60
        dialog.geometry(f"+{x}+{y}")
        
        ttk.Label(dialog, text="Profile Name:").pack(pady=(10, 2))
        name_var = tk.StringVar()
        name_entry = ttk.Entry(dialog, textvariable=name_var, width=40)
        name_entry.pack(pady=2)
        
        def on_create():
            profile_name = name_var.get().strip().lower().replace(" ", "_")
            display_name = name_var.get().strip()
            
            if not profile_name:
                messagebox.showerror("Error", "Profile name is required")
                return
            
            if create_profile(profile_name, display_name, ""):
                self.available_profiles = get_available_profiles()
                self.profile_combo['values'] = self.available_profiles
                self.current_profile.set(profile_name)
                self.switch_profile()
                dialog.destroy()
                self.log_message(f"Created new profile: {profile_name}")
            else:
                messagebox.showerror("Error", f"Profile '{profile_name}' already exists")
        
        name_entry.focus()
        ttk.Button(dialog, text="Create", command=on_create).pack(pady=10)
    
    def duplicate_current_profile(self):
        """Duplicate the current profile."""
        source = self.current_profile.get()
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Duplicate Profile")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.geometry("400x100")
        
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 200
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 50
        dialog.geometry(f"+{x}+{y}")
        
        ttk.Label(dialog, text=f"Duplicating: {source}").pack(pady=(10, 5))
        ttk.Label(dialog, text="New Profile Name:").pack(pady=(5, 2))
        name_var = tk.StringVar(value=f"{source}_copy")
        name_entry = ttk.Entry(dialog, textvariable=name_var, width=40)
        name_entry.pack(pady=2)
        
        def on_duplicate():
            new_id = name_var.get().strip().lower().replace(" ", "_")
            if not new_id:
                messagebox.showerror("Error", "Profile name is required")
                return
            
            display_name = name_var.get().strip()
            
            if duplicate_profile(source, new_id, display_name):
                self.available_profiles = get_available_profiles()
                self.profile_combo['values'] = self.available_profiles
                self.current_profile.set(new_id)
                self.switch_profile()
                dialog.destroy()
                self.log_message(f"Duplicated profile: {source} -> {new_id}")
            else:
                messagebox.showerror("Error", f"Could not duplicate. Profile '{new_id}' may already exist.")
        
        name_entry.focus()
        name_entry.select_range(0, tk.END)
        ttk.Button(dialog, text="Duplicate", command=on_duplicate).pack(pady=10)
    
    def delete_current_profile(self):
        """Delete the current profile."""
        profile = self.current_profile.get()
        
        if len(self.available_profiles) <= 1:
            messagebox.showerror("Error", "Cannot delete the last profile")
            return
        
        if not messagebox.askyesno("Confirm Delete", 
                                   f"Are you sure you want to delete profile '{profile}'?\n\nThis will delete all templates and configuration for this profile."):
            return
        
        # Stop spam if running
        if self.spam.running:
            self.spam.toggle()
            self.on_spam_state_change(False)
        
        if delete_profile(profile):
            self.available_profiles = get_available_profiles()
            self.profile_combo['values'] = self.available_profiles
            self.current_profile.set(self.available_profiles[0])
            self.switch_profile()
            self.log_message(f"Deleted profile: {profile}")
        else:
            messagebox.showerror("Error", f"Could not delete profile '{profile}'")
    
    def get_active_window_title(self):
        """Show a dialog with list of running windows to select from."""
        import win32gui
        import win32process
        
        # Get list of visible windows
        windows = []
        
        def enum_windows(hwnd, lParam):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title and len(title) > 0:  # Only include windows with titles
                    windows.append((title, hwnd))
            return True
        
        win32gui.EnumWindows(enum_windows, None)
        
        if not windows:
            messagebox.showwarning("No Windows", "No visible windows found")
            return
        
        # Sort by title
        windows.sort(key=lambda x: x[0])
        window_titles = [title for title, _ in windows]
        
        # Create selection dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Window")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.geometry("500x400")
        
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 250
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 200
        dialog.geometry(f"+{x}+{y}")
        
        ttk.Label(dialog, text="Select a window:").pack(pady=(10, 5))
        
        # Create listbox with scrollbar
        frame = ttk.Frame(dialog)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set,
                             bg=self.DARK_BG2, fg=self.DARK_FG,
                             selectbackground=self.DARK_SELECT,
                             selectforeground=self.DARK_FG,
                             relief=tk.FLAT, borderwidth=1)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)
        
        # Populate listbox
        for title in window_titles:
            listbox.insert(tk.END, title)
        
        # Select first item by default
        if window_titles:
            listbox.selection_set(0)
            listbox.see(0)
        
        result = [None]
        
        def on_select():
            selection = listbox.curselection()
            if selection:
                result[0] = window_titles[selection[0]]
                dialog.destroy()
        
        def on_enter(event):
            on_select()
        
        listbox.bind('<Return>', on_enter)
        listbox.bind('<Double-Button-1>', lambda e: on_select())
        
        ttk.Button(dialog, text="Select", command=on_select).pack(pady=10)
        
        # Wait for dialog to close
        self.root.wait_window(dialog)
        
        if result[0]:
            self.window_title_var.set(result[0])
            self.log_message(f"Set window title: {result[0]}")
    
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
            color_tolerance = self.global_settings.get("general", "default_color_tolerance", default=15)
            use_uniform = det_config.get("uniform_color_protection", True)
            confidence = self.detection.calculate_confidence(screen_img, template, mask, color_tolerance, use_uniform)
            
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
    try:
        app = DialogueSkipperGUI()
        app.run()
    except Exception as e:
        if args.debug:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
    finally:
        if args.debug:
            input("\nPress Enter to close...")


if __name__ == "__main__":
    main()
