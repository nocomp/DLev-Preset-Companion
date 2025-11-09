#!/usr/bin/env python3
import tkinter as tk
from tkinter import filedialog
import subprocess
import os
import time
import wave
import contextlib
import numpy as np

# ==========================================
#  DLev Preset Companion
#  XY voice shaper + preset tools for D-Lev
# By Herve PELLARIN nocomp@gmail.com
# ==========================================

# Path to d-lin (same folder as this script)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DLIN_CMD = os.path.join(SCRIPT_DIR, "d-lin")

# If you need sudo for serial access, set this to True
USE_SUDO = True

# Throttling for knob updates (ms)
UPDATE_INTERVAL_MS = 150

# Global throttle timestamp
_last_update_time = 0.0


# -------------------------------
# Generic D-Lev helpers
# -------------------------------
def run_dlin(args):
    """
    Run a generic d-lin command.
    No throttling (used for dump/pump/view etc.).
    """
    cmd = []
    if USE_SUDO:
        cmd.append("sudo")
    cmd.append(DLIN_CMD)
    cmd += args

    print(">>", " ".join(cmd))
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.stdout:
            print(res.stdout.strip())
        if res.stderr:
            print(res.stderr.strip())
        return res
    except Exception as e:
        print("Error running d-lin:", e)
        return None


def run_dlin_knob(pkv_str):
    """
    Run a 'knob -pkv <page:knob:val>' command with throttling,
    to avoid flooding the D-Lev while dragging the XY pad.
    """
    global _last_update_time
    now = time.time()
    if (now - _last_update_time) * 1000 < UPDATE_INTERVAL_MS:
        return
    _last_update_time = now

    cmd = []
    if USE_SUDO:
        cmd.append("sudo")
    cmd.append(DLIN_CMD)
    cmd += ["knob", "-pkv", pkv_str]

    print(">>", " ".join(cmd))
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.stdout:
            print(res.stdout.strip())
        if res.stderr:
            print(res.stderr.strip())
    except Exception as e:
        print("Error running d-lin knob:", e)


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def hz_to_knob_value(freq_hz, lo_hz=200.0, hi_hz=4000.0,
                     knob_lo=100, knob_hi=3500):
    """
    Simple mapping from Hz → numeric knob value for 0f:2, 1f:2, etc.
    """
    f = clamp(freq_hz, lo_hz, hi_hz)
    t = (f - lo_hz) / (hi_hz - lo_hz)
    v = knob_lo + t * (knob_hi - knob_lo)
    return int(round(v))


# -------------------------------
# Voice Profiles
# -------------------------------
def get_profile_params(profile_name):
    """
    Return formant ranges for given voice type.
    Rough typical ranges for vowels (approx).
    """
    p = profile_name.lower()

    if p == "bass":
        return {
            "F1_min": 300.0, "F1_max": 650.0,
            "F2_min": 700.0, "F2_max": 1200.0,
            "F3_min": 1700.0, "F3_max": 2400.0,
            "F4_min": 2200.0, "F4_max": 3200.0,
        }
    elif p == "baritone":
        return {
            "F1_min": 330.0, "F1_max": 700.0,
            "F2_min": 800.0, "F2_max": 1350.0,
            "F3_min": 1800.0, "F3_max": 2500.0,
            "F4_min": 2300.0, "F4_max": 3400.0,
        }
    elif p == "tenor":
        return {
            "F1_min": 380.0, "F1_max": 750.0,
            "F2_min": 900.0, "F2_max": 1500.0,
            "F3_min": 1900.0, "F3_max": 2600.0,   # slightly tamed
            "F4_min": 2400.0, "F4_max": 3400.0,   # slightly tamed
        }
    elif p == "alto":
        return {
            "F1_min": 400.0, "F1_max": 800.0,
            "F2_min": 1000.0, "F2_max": 1700.0,
            "F3_min": 2100.0, "F3_max": 2900.0,
            "F4_min": 2600.0, "F4_max": 3500.0,
        }
    elif p == "mezzo":
        return {
            "F1_min": 420.0, "F1_max": 850.0,
            "F2_min": 1100.0, "F2_max": 1800.0,
            "F3_min": 2200.0, "F3_max": 3000.0,
            "F4_min": 2700.0, "F4_max": 3600.0,
        }
    elif p == "soprano":
        return {
            "F1_min": 450.0, "F1_max": 900.0,
            "F2_min": 1200.0, "F2_max": 2000.0,
            "F3_min": 2400.0, "F3_max": 3100.0,
            "F4_min": 2800.0, "F4_max": 3700.0,
        }
    else:  # Neutral / default
        return {
            "F1_min": 360.0, "F1_max": 780.0,
            "F2_min": 850.0, "F2_max": 1500.0,
            "F3_min": 1900.0, "F3_max": 2700.0,
            "F4_min": 2400.0, "F4_max": 3400.0,
        }


def map_xy_to_formants(x_norm, y_norm, profile_name,
                       brightness_factor, resonance_factor):
    """
    x_norm, y_norm ∈ [0,1]
      x : dark (0) → bright (1)
      y : chest (0) → head (1)
    brightness_factor, resonance_factor ∈ [0,1]

    Returns dict with F1..F4 (Hz) and L1..L4, R1..R4.
    """
    prof = get_profile_params(profile_name)

    # Low formants F1/F2 (vertical axis)
    F1_min, F1_max = prof["F1_min"], prof["F1_max"]
    F2_min, F2_max = prof["F2_min"], prof["F2_max"]

    F1 = F1_min + (F1_max - F1_min) * y_norm
    F2 = F2_min + (F2_max - F2_min) * y_norm

    # High formants F3/F4 (horizontal axis, scaled by brightness factor)
    F3_min, F3_max = prof["F3_min"], prof["F3_max"]
    F4_min, F4_max = prof["F4_min"], prof["F4_max"]

    # Centered X to allow brightness_factor to shrink movement
    x_centered = (x_norm - 0.5) * brightness_factor + 0.5
    x_centered = clamp(x_centered, 0.0, 1.0)

    F3 = F3_min + (F3_max - F3_min) * x_centered
    F4 = F4_min + (F4_max - F4_min) * x_centered

    # Levels: F1/F2 stable, F3/F4 increase with brightness/X
    L1 = 55
    L2 = 45
    L3 = int(round(25 + 15 * x_centered * brightness_factor))  # 25 → ~40
    L4 = int(round(20 + 10 * x_centered * brightness_factor))  # 20 → ~30

    # Resonances: base + extra scaled by resonance_factor and global "energy"
    base_R = 3
    energy = 0.5 * x_norm + 0.5 * y_norm  # more head/bright = more resonance
    extra_R = int(round(4 * resonance_factor * energy))  # up to +4
    R = clamp(base_R + extra_R, 3, 7)

    R1 = R2 = R3 = R4 = R

    return {
        "F1": F1, "F2": F2, "F3": F3, "F4": F4,
        "L1": L1, "L2": L2, "L3": L3, "L4": L4,
        "R1": R1, "R2": R2, "R3": R3, "R4": R4,
    }


def apply_voice_from_xy(profile_name, x_norm, y_norm,
                        brightness_factor, resonance_factor):
    """
    Compute formants from XY + voice profile and send them to D-Lev.
    Assumes the current preset already produces a vocal sound.
    """
    params = map_xy_to_formants(x_norm, y_norm, profile_name,
                                brightness_factor, resonance_factor)

    F1 = params["F1"]
    F2 = params["F2"]
    F3 = params["F3"]
    F4 = params["F4"]

    L1, L2, L3, L4 = params["L1"], params["L2"], params["L3"], params["L4"]
    R1, R2, R3, R4 = params["R1"], params["R2"], params["R3"], params["R4"]

    kF1 = hz_to_knob_value(F1)
    kF2 = hz_to_knob_value(F2)
    kF3 = hz_to_knob_value(F3)
    kF4 = hz_to_knob_value(F4)

    print(f"[Profile {profile_name}] XY → Formants:")
    print(f"  F1 ≈ {F1:.1f} Hz -> 0f:2:{kF1}")
    print(f"  F2 ≈ {F2:.1f} Hz -> 1f:2:{kF2}")
    print(f"  F3 ≈ {F3:.1f} Hz -> 2f:2:{kF3}")
    print(f"  F4 ≈ {F4:.1f} Hz -> 3f:2:{kF4}")
    print(f"  Levels: L1={L1}, L2={L2}, L3={L3}, L4={L4}")
    print(f"  Resonances: R1=R2=R3=R4={R1}")

    # Formants: frequencies
    run_dlin_knob(f"0f:2:{kF1}")
    run_dlin_knob(f"1f:2:{kF2}")
    run_dlin_knob(f"2f:2:{kF3}")
    run_dlin_knob(f"3f:2:{kF4}")

    # Formants: levels
    run_dlin_knob(f"0f:3:{L1}")
    run_dlin_knob(f"1f:3:{L2}")
    run_dlin_knob(f"2f:3:{L3}")
    run_dlin_knob(f"3f:3:{L4}")

    # Formants: resonances
    run_dlin_knob(f"0f:6:{R1}")
    run_dlin_knob(f"1f:6:{R2}")
    run_dlin_knob(f"2f:6:{R3}")
    run_dlin_knob(f"3f:6:{R4}")

    # Global spectral tilt tied to X, scaled by brightness_factor
    bass_base_left, bass_base_right = 8, 5
    treb_base_left, treb_base_right = 4, 8

    bass = int(round(
        bass_base_right + (bass_base_left - bass_base_right) * (1.0 - x_norm) * (0.5 + 0.5 * brightness_factor)
    ))
    treb = int(round(
        treb_base_left + (treb_base_right - treb_base_left) * x_norm * (0.5 + 0.5 * brightness_factor)
    ))

    print(f"  Tilt: bass={bass}, treb={treb}")
    run_dlin_knob(f"0o:1:{treb}")  # 0_OSC:treb
    run_dlin_knob(f"0o:3:{bass}")  # 0_OSC:bass


# -------------------------------
# WAV analysis
# -------------------------------
def analyze_wav_profile(path):
    """
    Analyze a WAV file and return:
      (x_norm, y_norm, centroid_hz, low_ratio)

    x_norm ~ brightness from spectral centroid,
    y_norm ~ chest/head from low vs high energy balance.
    """
    print(f"Analyzing WAV file: {path}")
    with contextlib.closing(wave.open(path, "rb")) as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    if sampwidth == 1:
        dtype = np.uint8
        data = np.frombuffer(raw, dtype=dtype).astype(np.float32)
        data = (data - 128.0) / 128.0
    elif sampwidth == 2:
        dtype = np.int16
        data = np.frombuffer(raw, dtype=dtype).astype(np.float32)
        data = data / 32768.0
    elif sampwidth == 4:
        dtype = np.int32
        data = np.frombuffer(raw, dtype=dtype).astype(np.float32)
        data = data / 2147483648.0
    else:
        raise ValueError(f"Unsupported sample width: {sampwidth * 8} bits")

    if n_channels == 2:
        data = data.reshape(-1, 2).mean(axis=1)

    n = len(data)
    if n == 0:
        raise ValueError("Empty WAV file.")

    window = np.hanning(n)
    x = data * window
    spec = np.fft.rfft(x)
    mag = np.abs(spec)
    freqs = np.fft.rfftfreq(n, d=1.0 / framerate)

    total = np.sum(mag)
    if total <= 0:
        centroid = 0.0
        low_ratio = 0.5
    else:
        centroid = float(np.sum(freqs * mag) / total)
        low_mask = freqs < 1000.0
        low_energy = float(np.sum(mag[low_mask]))
        low_ratio = low_energy / total

    print(f"  Spectral centroid ≈ {centroid:.1f} Hz, low_ratio ≈ {low_ratio:.3f}")

    # Map centroid to x_norm in [0,1] for ~1500..4000 Hz
    x_norm = (centroid - 1500.0) / (4000.0 - 1500.0)
    x_norm = clamp(x_norm, 0.0, 1.0)

    # Map low_ratio (0..1) to y_norm (0..1):
    # more low energy -> more chest (low y), more highs -> more head (high y)
    # we treat low_ratio ~ [0.2, 0.7] as main range
    y_norm = 1.0 - (low_ratio - 0.2) / (0.7 - 0.2)
    y_norm = clamp(y_norm, 0.0, 1.0)

    print(f"  Mapped XY target: x={x_norm:.3f}, y={y_norm:.3f}")
    return x_norm, y_norm, centroid, low_ratio


# -------------------------------
# Tkinter UI
# -------------------------------
class DLevPresetCompanionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DLev Preset Companion")

        # XY state
        self.x_norm = 0.5
        self.y_norm = 0.5
        self.point_radius = 8

        # WAV target state
        self.wav_target = None   # (x_norm, y_norm)
        self.wav_marker = None

        # Base knobs
        self.base_knob_file = None
        self.base_captured = False

        self.size = 400
        self.margin = 30

        # ------------- Top controls (profile + enable toggle) -------------
        top_frame = tk.Frame(root)
        top_frame.pack(pady=5)

        # Voice profile menu
        self.profile_var = tk.StringVar(value="Tenor")
        profiles = ["Bass", "Baritone", "Tenor", "Alto", "Mezzo", "Soprano", "Neutral"]

        tk.Label(top_frame, text="Voice profile:").pack(side=tk.LEFT, padx=5)
        self.profile_menu = tk.OptionMenu(top_frame, self.profile_var, *profiles,
                                          command=self.on_profile_change)
        self.profile_menu.pack(side=tk.LEFT)

        # Processing enable/disable
        self.processing_enabled = tk.BooleanVar(value=True)
        self.enable_check = tk.Checkbutton(
            top_frame,
            text="Enable processing",
            variable=self.processing_enabled,
            command=self.on_enable_toggle
        )
        self.enable_check.pack(side=tk.LEFT, padx=10)

        # ------------- Sliders (brightness / resonance) -------------
        slider_frame = tk.Frame(root)
        slider_frame.pack(pady=5, fill=tk.X)

        tk.Label(slider_frame, text="Brightness intensity:").grid(row=0, column=0, sticky="e", padx=4)
        self.brightness_var = tk.DoubleVar(value=70.0)  # 0..100
        self.brightness_scale = tk.Scale(
            slider_frame,
            from_=0, to=100,
            orient=tk.HORIZONTAL,
            variable=self.brightness_var,
            command=self.on_slider_change,
            length=200
        )
        self.brightness_scale.grid(row=0, column=1, padx=4)

        tk.Label(slider_frame, text="Resonance intensity:").grid(row=0, column=2, sticky="e", padx=4)
        self.resonance_var = tk.DoubleVar(value=50.0)  # 0..100
        self.resonance_scale = tk.Scale(
            slider_frame,
            from_=0, to=100,
            orient=tk.HORIZONTAL,
            variable=self.resonance_var,
            command=self.on_slider_change,
            length=200
        )
        self.resonance_scale.grid(row=0, column=3, padx=4)

        # ------------- XY canvas -------------
        self.canvas = tk.Canvas(
            root,
            width=self.size + 2 * self.margin,
            height=self.size + 2 * self.margin,
            bg="white"
        )
        self.canvas.pack(pady=5)

        x0, y0 = self.margin, self.margin
        x1, y1 = self.margin + self.size, self.margin + self.size
        self.canvas.create_rectangle(x0, y0, x1, y1, outline="black")

        # Axis labels
        self.canvas.create_text(self.margin + self.size / 2,
                                self.margin - 10,
                                text="Dark   ←   Timbre   →   Bright")
        self.canvas.create_text(self.margin - 20,
                                self.margin + self.size / 2,
                                text="Chest\n↓\nHead",
                                angle=90)

        # Blue point = current XY
        self.point = self.canvas.create_oval(0, 0, 0, 0, fill="blue")
        self.update_point_position()

        self.dragging = False

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        # ------------- Bottom controls (slots & save) -------------
        bottom_frame = tk.Frame(root)
        bottom_frame.pack(pady=5, fill=tk.X)

        # Current slot
        tk.Label(bottom_frame, text="Current slot:").grid(row=0, column=0, padx=4, pady=2, sticky="e")
        self.slot_var = tk.StringVar(value="200")
        tk.Entry(bottom_frame, textvariable=self.slot_var, width=5).grid(row=0, column=1, padx=4, pady=2, sticky="w")

        # Target slot
        tk.Label(bottom_frame, text="Target slot:").grid(row=0, column=2, padx=4, pady=2, sticky="e")
        self.target_slot_var = tk.StringVar(value="201")
        tk.Entry(bottom_frame, textvariable=self.target_slot_var, width=5).grid(row=0, column=3, padx=4, pady=2, sticky="w")

        # Save name
        tk.Label(bottom_frame, text="Save as .dlp:").grid(row=1, column=0, padx=4, pady=2, sticky="e")
        self.save_name_var = tk.StringVar(value="dpc_preset")
        tk.Entry(bottom_frame, textvariable=self.save_name_var, width=20).grid(row=1, column=1, columnspan=3, padx=4, pady=2, sticky="w")

        # ------------- Action buttons -------------
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=5)

        self.btn_capture_base = tk.Button(
            btn_frame,
            text="Capture Base From Current Slot",
            command=self.capture_base_from_slot
        )
        self.btn_capture_base.pack(side=tk.LEFT, padx=5)

        self.btn_save_dlp = tk.Button(
            btn_frame,
            text="Save Current Slot To .dlp",
            command=self.save_current_to_dlp
        )
        self.btn_save_dlp.pack(side=tk.LEFT, padx=5)

        self.btn_copy_slot = tk.Button(
            btn_frame,
            text="Copy Current Slot To Target Slot",
            command=self.copy_current_to_target_slot
        )
        self.btn_copy_slot.pack(side=tk.LEFT, padx=5)

        self.btn_load_wav = tk.Button(
            btn_frame,
            text="Load WAV & Analyze",
            command=self.load_wav_profile
        )
        self.btn_load_wav.pack(side=tk.LEFT, padx=5)

        self.btn_snap_wav = tk.Button(
            btn_frame,
            text="Snap XY To WAV Profile",
            command=self.snap_to_wav_profile
        )
        self.btn_snap_wav.pack(side=tk.LEFT, padx=5)

        # Initial apply
        self.apply_current()

    # ------------- XY helpers -------------
    def coord_from_norm(self, x_norm, y_norm):
        x0, y0 = self.margin, self.margin
        x1, y1 = self.margin + self.size, self.margin + self.size
        x = x0 + x_norm * (x1 - x0)
        y = y0 + y_norm * (y1 - y0)
        return x, y

    def norm_from_coord(self, x, y):
        x0, y0 = self.margin, self.margin
        x1, y1 = self.margin + self.size, self.margin + self.size
        x_norm = clamp((x - x0) / (x1 - x0), 0.0, 1.0)
        y_norm = clamp((y - y0) / (y1 - y0), 0.0, 1.0)
        return x_norm, y_norm

    def update_point_position(self):
        x, y = self.coord_from_norm(self.x_norm, self.y_norm)
        r = self.point_radius
        self.canvas.coords(self.point, x - r, y - r, x + r, y + r)

    def update_wav_marker(self):
        if self.wav_target is None:
            # Remove marker if present
            if self.wav_marker is not None:
                self.canvas.delete(self.wav_marker)
                self.wav_marker = None
            return

        x_norm, y_norm = self.wav_target
        x, y = self.coord_from_norm(x_norm, y_norm)
        r = 6

        if self.wav_marker is None:
            self.wav_marker = self.canvas.create_oval(
                x - r, y - r, x + r, y + r, outline="red", width=2
            )
        else:
            self.canvas.coords(self.wav_marker, x - r, y - r, x + r, y + r)

    # ------------- Mouse handlers -------------
    def on_press(self, event):
        self.dragging = True
        self.move_point(event.x, event.y)

    def on_drag(self, event):
        if self.dragging:
            self.move_point(event.x, event.y)

    def on_release(self, event):
        self.dragging = False
        self.apply_current()

    def move_point(self, x, y):
        x0, y0 = self.margin, self.margin
        x1, y1 = self.margin + self.size, self.margin + self.size
        x = clamp(x, x0, x1)
        y = clamp(y, y0, y1)

        self.x_norm, self.y_norm = self.norm_from_coord(x, y)
        self.update_point_position()
        self.apply_current()

    # ------------- Apply / profile / enable / sliders -------------
    def get_brightness_resonance(self):
        b = clamp(self.brightness_var.get() / 100.0, 0.0, 1.0)
        r = clamp(self.resonance_var.get() / 100.0, 0.0, 1.0)
        return b, r

    def apply_current(self):
        if not self.processing_enabled.get():
            print("Processing disabled: not sending changes.")
            return
        profile = self.profile_var.get()
        b, r = self.get_brightness_resonance()
        apply_voice_from_xy(profile, self.x_norm, self.y_norm, b, r)

    def on_profile_change(self, value):
        print(f"Profile changed to: {value}")
        self.apply_current()

    def on_enable_toggle(self):
        enabled = self.processing_enabled.get()
        print(f"Processing enabled: {enabled}")
        if not enabled:
            # Disable: restore base knobs if we have them
            if self.base_captured and self.base_knob_file:
                print(f"Restoring base knobs from file: {self.base_knob_file}")
                run_dlin(["pump", "-k", "-f", self.base_knob_file])
            else:
                print("No base knobs captured yet; nothing to restore.")
        else:
            # Re-enable: apply current XY settings to the (restored) preset
            self.apply_current()

    def on_slider_change(self, value):
        # Sliders changed → re-apply if processing enabled
        self.apply_current()

    # ------------- Preset management -------------
    def capture_base_from_slot(self):
        """
        Capture current slot's knobs as 'base' so we can restore
        them when processing is disabled.
        """
        slot_str = self.slot_var.get().strip()
        if not slot_str.isdigit():
            print("Invalid current slot number.")
            return
        slot = int(slot_str)
        self.base_knob_file = f"dpc_base_knobs_slot{slot}"
        print(f"Capturing base knobs from slot {slot} into file '{self.base_knob_file}'...")
        run_dlin(["dump", "-k", "-f", self.base_knob_file])
        self.base_captured = True
        print("Base knobs captured. You can now tweak and toggle processing to compare.")

    def save_current_to_dlp(self):
        """
        Dump the current slot preset to a .dlp file.
        """
        slot_str = self.slot_var.get().strip()
        if not slot_str.isdigit():
            print("Invalid current slot number.")
            return
        slot = int(slot_str)

        name = self.save_name_var.get().strip() or "dpc_preset"
        print(f"Saving slot {slot} to file '{name}.dlp'...")
        run_dlin(["dump", "-s", str(slot), "-f", name])
        print("Save completed (check .dlp file in this directory).")

    def copy_current_to_target_slot(self):
        """
        Copy the current slot preset to another slot via a temp .dlp.
        """
        src_str = self.slot_var.get().strip()
        dst_str = self.target_slot_var.get().strip()

        if not src_str.isdigit() or not dst_str.isdigit():
            print("Invalid slot number(s).")
            return

        src = int(src_str)
        dst = int(dst_str)

        temp_name = "_dpc_temp_copy"
        print(f"Copying slot {src} → slot {dst} via temp file '{temp_name}.dlp'...")

        # Dump from src
        run_dlin(["dump", "-s", str(src), "-f", temp_name])
        # Pump to dst
        run_dlin(["pump", "-f", temp_name, "-s", str(dst)])

        print("Copy completed. You can select the target slot on the D-Lev and test.")

    # ------------- WAV profile -------------
    def load_wav_profile(self):
        """
        Open a WAV file, analyze it and display its XY profile
        as a red marker on the pad.
        """
        path = filedialog.askopenfilename(
            title="Select WAV file",
            filetypes=[("WAV files", "*.wav"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            x_w, y_w, centroid, low_ratio = analyze_wav_profile(path)
            self.wav_target = (x_w, y_w)
            self.update_wav_marker()
            print("WAV profile loaded. Red marker shows its XY target.")
        except Exception as e:
            print(f"Error analyzing WAV file: {e}")

    def snap_to_wav_profile(self):
        """
        Move the blue XY point to the WAV profile target, if any,
        and apply processing.
        """
        if self.wav_target is None:
            print("No WAV profile loaded yet.")
            return
        self.x_norm, self.y_norm = self.wav_target
        self.update_point_position()
        self.apply_current()

# -------------------------------
# main
# -------------------------------
def main():
    root = tk.Tk()
    app = DLevPresetCompanionApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
