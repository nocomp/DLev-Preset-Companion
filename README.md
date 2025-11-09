# 🎛️ DLev Preset Companion

**DLev Preset Companion** is an **experimental sound design tool** for the [D-Lev theremin](https://www.d-lev.com/) that allows you to **visualize, sculpt, and compare** vocal-like presets interactively.  
It communicates with the D-Lev through the `d-lin` command-line librarian and provides a real-time interface for exploring **formant structures**, **timbre morphing**, and **preset management**.

> ⚠️ This project is not affiliated with Moog Music or the D-Lev authors.  
> It is an open experimental utility intended for educational and creative exploration only.

---

## 🧩 Concept

The goal of this project is to make **voice synthesis on the D-Lev** more intuitive.

Instead of manually adjusting dozens of formant knobs, you can move a point inside a **2D XY pad**:
- **Horizontal axis (X)**: controls **brightness** (dark ↔ bright).
- **Vertical axis (Y)**: controls **vocal color** between **chest** (low, warm) and **head** (nasal, bright).

The app computes and sends the appropriate formant parameters (`F1..F4`, `L1..L4`, `R1..R4`) to the D-Lev in real time.

It also includes **WAV analysis** to extract a spectral “fingerprint” from a recorded voice and display it on the pad — allowing you to visually compare and approach a real singer’s tone.

---

## ✨ Features

| Category | Description |
|-----------|--------------|
| 🎚️ **XY Voice Pad** | Interactive 2D matrix controlling the D-Lev’s formant and tonal parameters. |
| 🎤 **Voice Profiles** | Preset formant ranges for Bass, Baritone, Tenor, Alto, Mezzo, Soprano, and Neutral voices. |
| ⚙️ **Real-Time Control** | Sends `d-lin knob` commands directly to the connected D-Lev over USB serial. |
| 💡 **Brightness & Resonance Sliders** | Fine-tune the timbre and reduce unwanted distortion or harshness. |
| 🔁 **A/B Processing Toggle** | Instantly switch between your captured base preset and the processed version. |
| 💾 **Preset Management** | Capture base knobs, save current slot to `.dlp`, or copy to another slot. |
| 🎧 **WAV Voice Import (Experimental)** | Analyze a voice recording (mono `.wav`) and plot its spectral centroid on the XY pad. |
| 🔴 **WAV Comparison Marker** | Displays the analyzed voice position as a red marker for visual timbre matching. |
| 🧠 **Auto-Snap to Voice** | Move your current preset point directly to the analyzed voice location. |

---

## 🧱 Requirements

- A **D-Lev theremin** connected over USB and accessible via the `d-lin` librarian tool.
- A working **Python 3.10+** environment (tested on Ubuntu 22.04).
- The user must have permission to access the D-Lev serial port (`dialout` group or use `sudo`).

---

## 🧩 Installation

Clone or download this repository, then install the dependencies:

```bash
cd dlev-preset-companion
pip3 install -r requirements.txt

🚀 Usage

From the directory containing both d-lin and dlev_preset_companion.py:

python3 dlev_preset_companion.py


If you require root access for serial communication, use:

sudo -E python3 dlev_preset_companion.py


Then:

Connect your D-Lev via USB.

Load a vocal preset (e.g. Patsy, Tenor, or your custom voice).

Click “Capture Base From Current Slot” to save your reference.

Choose a voice profile and sculpt the sound using the XY pad.

Use sliders to reduce harshness (Brightness ↓, Resonance ↓).

Optionally load a .wav file to visualize and match a real voice.

Save your preset (Save Current Slot To .dlp) or copy to another slot.

🧪 Experimental Notice

This project is highly experimental and may produce unpredictable or unstable results depending on your D-Lev firmware and preset state.
Always back up your EEPROM and presets before use:

sudo ./d-lin dump -f backup.eeprom


Use at your own risk and have fun exploring — this tool is meant for research, learning, and sonic experimentation.

🧰 Roadmap

 Add gradient visualization for spectral energy (Chest ↔ Head, Dark ↔ Bright).

 Add direct .dlp generation from measured formants.

 Implement formant detection directly from .wav (basic LPC).

 Optional MIDI/OSC control layer for remote morphing.

 Add small spectral display or live input analyzer.
