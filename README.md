<<<<<<< HEAD
# 🤖 Miko3 Talents Automation Framework

> **Full ADB + Python Automation Framework** for testing Miko3 Reboot's talents with built-in verification, HTML reporting, and RICE POT prioritization.

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-green)
![ADB](https://img.shields.io/badge/ADB-Android%20Debug%20Bridge-orange)

---

## 📑 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage Guide](#usage-guide)
- [Talent Automation Details](#talent-automation-details)
- [RICE POT Framework](#rice-pot-framework)
- [ADB Command Reference](#adb-command-reference)
- [Extending the Framework](#extending-the-framework)
- [Troubleshooting](#troubleshooting)

---

## Overview

This framework automates testing of Miko3 Reboot's talents (apps) using ADB. It provides:

| Feature | Description |
|---------|-------------|
| 🎮 **Talent Testing** | Automated tests for Video, Storymaker, Storytelling, and third-party talents |
| ✅ **Verification** | Screenshot diff, crash detection, activity assertions, logcat analysis |
| 📊 **HTML Reports** | Professional dark-themed reports with screenshots, pass/fail badges, and RICE analysis |
| 📈 **RICE POT** | Data-driven prioritization for which talents to automate first |
| 🖥️ **Cross-Platform** | Full support for both Windows and Linux |
| 🔌 **Extensible** | Abstract base class pattern — add new talents in minutes |

---

## Architecture

```
miko3_automation/
├── core/                    # Foundation Layer
│   ├── adb_utils.py         #   40+ ADB commands (tap, swipe, screenshot, etc.)
│   ├── device_manager.py    #   Device connection, health checks, multi-device
│   └── talent_discovery.py  #   Package/activity discovery, intent management
├── talents/                 # Test Layer
│   ├── base_talent.py       #   Abstract base: setup → execute → verify → teardown
│   ├── video_talent.py      #   Video playlist automation
│   ├── storymaker_talent.py #   Story creation flow automation
│   ├── storytelling_talent.py #  Session playback automation
│   └── thirdparty_talent.py #   Generic smoke testing for any app
├── verification/            # Assertion Layer
│   └── verifier.py          #   Screenshot diff, crash detection, log checks
├── reporting/               # Output Layer
│   └── html_report.py       #   Rich HTML report with embedded screenshots
└── rice_pot/                # Analysis Layer
    └── analyzer.py          #   RICE prioritization scoring
```

---

## Prerequisites

### 1. Python 3.8+

```bash
# Windows — Download from https://www.python.org/downloads/
python --version

# Linux
sudo apt install python3 python3-venv python3-pip
python3 --version
```

### 2. ADB (Android Debug Bridge)

```bash
# Windows — Download Platform Tools:
# https://developer.android.com/tools/releases/platform-tools
# Extract and add folder to system PATH
adb version

# Linux
sudo apt install adb              # Ubuntu/Debian
sudo yum install android-tools    # CentOS/RHEL
adb version
```

### 3. Miko3 Reboot — Enable USB Debugging

1. On Miko3, navigate to **Settings → About**
2. Tap **Build Number** 7 times to enable Developer Options
3. Go to **Settings → Developer Options**
4. Enable **USB Debugging**
5. Connect Miko3 to computer via USB cable
6. On Miko3, tap **Allow** when prompted for USB debugging authorization

---

## Quick Start

### Automated Setup

```bash
# Windows
scripts\setup_env.bat

# Linux
chmod +x scripts/setup_env.sh
scripts/setup_env.sh
```

### Manual Setup

```bash
# 1. Create virtual environment
# Windows
python -m venv venv
venv\Scripts\activate.bat

# Linux
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Verify device connection
adb devices
# Expected output:
# List of devices attached
# <serial>    device
```

### Run Tests

```bash
# Run all talent tests
python runner.py --all

# Run specific talent
python runner.py --talent video

# Discover installed talents
python runner.py --discover

# Show RICE POT analysis
python runner.py --rice

# Full verbose run
python runner.py --all --verbose
```

---

## Configuration

Edit `config/config.yaml` to customize the framework:

### Device Settings

```yaml
device:
  serial: ""                    # Auto-detect or set e.g. "192.168.1.100:5555"
  adb_path: "adb"              # Full ADB path if not in PATH
  connection_timeout: 30       # Seconds
  command_timeout: 15          # Per-command timeout
  retry_attempts: 3            # Retry failed commands
```

### Talent Coordinate Mapping

> **IMPORTANT**: You must calibrate these coordinates to match your Miko3's actual screen layout.

```yaml
talents:
  video:
    package: "com.miko.video"         # ← Update with actual package name
    activity: ".MainActivity"          # ← Update with actual activity
    coordinates:
      play_button: [640, 400]          # ← Calibrate to your screen
      next_button: [1100, 750]
```

#### How to Find Coordinates

```bash
# Method 1: Enable "Pointer Location" in Developer Options
# Shows coordinates on screen in real-time

# Method 2: Use ADB to get tap coordinates
adb shell getevent -l  # Then tap the target — look for ABS_MT_POSITION_X/Y

# Method 3: Take a screenshot and measure in an image editor
adb shell screencap -p /sdcard/screen.png
adb pull /sdcard/screen.png
```

#### How to Find Package Names

```bash
# List all packages
adb shell pm list packages                     # All packages
adb shell pm list packages | findstr miko      # Windows: filter for miko
adb shell pm list packages | grep miko         # Linux: filter for miko

# Find foreground app (run while talent is open)
# Windows:
adb shell "dumpsys window windows | grep mFocusedApp"
# Linux:
adb shell dumpsys window windows | grep mFocusedApp

# Find main activity
adb shell dumpsys package com.miko.video | findstr "Activity"     # Windows
adb shell dumpsys package com.miko.video | grep "Activity"        # Linux
```

---

## Usage Guide

### CLI Reference

```
python runner.py [OPTIONS]

Actions:
  --all                      Run all talent tests
  --talent TALENT            Run specific talent: video|storymaker|storytelling|thirdparty
  --discover                 List all installed talents on device
  --rice                     Show RICE POT prioritization analysis

Options:
  --package PACKAGE          Third-party talent package name
  --device SERIAL            Target specific device
  --config PATH              Custom config file (default: config/config.yaml)
  --report-dir DIR           Custom report output directory
  --verbose, -v              Enable debug logging
```

### Examples

```bash
# Test all built-in talents
python runner.py --all

# Test only video talent
python runner.py --talent video

# Test a specific third-party talent
python runner.py --talent thirdparty --package com.example.myapp

# Test multiple specific talents
python runner.py --talent video --talent storytelling

# Target a specific device (for multi-device setups)
python runner.py --all --device 192.168.1.100:5555

# Use custom config
python runner.py --all --config my_config.yaml

# Discover + test
python runner.py --discover --all --verbose
```

### Using Scripts

```bash
# Windows — Run full test suite
scripts\run_all_tests.bat

# Linux — Run full test suite
scripts/run_all_tests.sh

# Pass arguments through scripts
scripts\run_all_tests.bat --talent video --verbose    # Windows
scripts/run_all_tests.sh --talent video --verbose     # Linux
```

---

## Talent Automation Details

### Video Talent

**Test Flow:**
1. Launch video talent via `am start`
2. For each video (configurable count):
   - Tap play button → Wait for video → Tap next
3. Verify: videos played, no crashes, screen changed

```bash
# ADB commands used internally:
adb shell am start -n com.miko.video/.MainActivity       # Launch
adb shell input tap 640 400                                # Play
adb shell input tap 1100 750                               # Next
adb shell screencap -p /sdcard/screenshot.png              # Evidence
adb shell "dumpsys activity activities | grep mResumedActivity"  # Verify
```

### Storymaker Talent

**Test Flow:**
1. Launch storymaker → Tap Start
2. Select: Character → Background → Elements → Next → Finish
3. Verify: UI progression, no crashes

### Storytelling Talent

**Test Flow:**
1. Launch storytelling → Select first story → Play
2. Monitor session: track pages, periodic screenshots
3. Close session after timeout or completion
4. Verify: pages progressed, no crashes

### Third-Party Talents

**Smoke Test Flow:**
1. Auto-discover package and main activity
2. Launch talent → Wait for load
3. Perform generic interactions: center tap, swipes, quadrant exploration
4. Monitor for stability
5. Verify: no crashes, talent remained stable

```bash
# Custom interactions via config or code:
test = ThirdPartyTalentTest(
    adb, config,
    package_name="com.example.app",
    custom_interactions=[
        {"action": "tap", "x": 500, "y": 300, "wait": 2},
        {"action": "swipe", "x1": 800, "y1": 400, "x2": 200, "y2": 400},
        {"action": "text", "value": "hello world"},
        {"action": "screenshot", "name": "after_input"},
    ]
)
```

---

## RICE POT Framework

The framework uses **RICE** scoring to prioritize automation efforts:

| Dimension | Question | Scale |
|-----------|----------|-------|
| **R**each | How many users/scenarios does this talent cover? | 1-10 |
| **I**mpact | What time savings or quality improvement is gained? | 1-10 |
| **C**onfidence | How reliably will the ADB automation work? | 1-10 |
| **E**ffort | How much work to create and maintain? (inverted) | 1-10 |

**Formula**: `Priority Score = (Reach × Impact × Confidence) / Effort`

### Default Scores

| Talent | R | I | C | E | Score | Priority |
|--------|---|---|---|---|-------|----------|
| Video | 9 | 8 | 7 | 5 | 100.8 | 🔴 CRITICAL |
| Storytelling | 8 | 8 | 7 | 6 | 74.7 | 🟠 HIGH |
| Storymaker | 7 | 7 | 6 | 4 | 73.5 | 🟠 HIGH |
| Third-Party | 5 | 6 | 4 | 3 | 40.0 | 🟡 MEDIUM |

```bash
# View analysis
python runner.py --rice
```

---

## ADB Command Reference

Quick reference for common ADB commands used in the framework:

### Connection
```bash
adb devices                              # List connected devices
adb connect 192.168.1.100:5555           # Connect over TCP/IP
adb disconnect                           # Disconnect all
adb reconnect                            # Reconnect
```

### App Management
```bash
adb shell pm list packages               # List all packages
adb shell am start -n PKG/ACTIVITY       # Launch app
adb shell am force-stop PKG              # Force stop
adb shell pm clear PKG                   # Clear data
adb install -r app.apk                   # Install APK
```

### Input Simulation
```bash
adb shell input tap X Y                  # Tap at coordinates
adb shell input swipe X1 Y1 X2 Y2 MS    # Swipe gesture
adb shell input text "hello"             # Type text
adb shell input keyevent 3               # HOME key
adb shell input keyevent 4               # BACK key
adb shell input keyevent 66              # ENTER key
```

### Screen & Logs
```bash
adb shell screencap -p /sdcard/s.png     # Screenshot
adb pull /sdcard/s.png ./screenshot.png  # Pull to local
adb shell screenrecord /sdcard/r.mp4     # Record screen
adb logcat -d -t 100                     # Last 100 logcat lines
adb logcat -c                            # Clear logcat
```

### Device Info
```bash
adb shell getprop ro.product.model       # Device model
adb shell getprop ro.build.version.release # Android version
adb shell wm size                        # Screen resolution
adb shell dumpsys battery | grep level   # Battery level
```

---

## Extending the Framework

### Adding a New Talent Test

1. Create a new file in `miko3_automation/talents/`:

```python
from .base_talent import BaseTalentTest

class MyNewTalentTest(BaseTalentTest):

    def __init__(self, adb, config, **kwargs):
        cfg = config.get("talents", {}).get("mynew", {})
        super().__init__(
            adb=adb,
            config=config,
            talent_name="My New Talent",
            package_name=cfg.get("package", "com.miko.newtalent"),
            **kwargs,
        )

    def execute(self):
        self.step("Do something")
        self.adb.tap(500, 300)
        self.wait(2)
        self.take_screenshot("action_done")
        self.pass_step()

    def verify(self):
        self.step("Check results")
        result = self.verify_no_crash()
        if result.passed:
            self.pass_step()
        else:
            self.fail_step(result.message)
```

2. Add configuration to `config/config.yaml`:

```yaml
talents:
  mynew:
    package: "com.miko.newtalent"
    activity: ".MainActivity"
    display_name: "My New Talent"
```

3. Register in `runner.py`:

```python
from miko3_automation.talents.my_new_talent import MyNewTalentTest

talent_map = {
    "video": VideoTalentTest,
    "mynew": MyNewTalentTest,  # Add this line
    # ...
}
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `adb: command not found` | Add ADB to PATH. Windows: System Properties → Environment Variables. Linux: `export PATH=$PATH:/path/to/platform-tools` |
| `no devices found` | 1. Check USB cable. 2. Enable USB Debugging on Miko3. 3. Windows: install ADB drivers. 4. Try `adb kill-server && adb start-server` |
| `device unauthorized` | Tap "Allow" on the USB debugging popup on Miko3 |
| Wrong coordinates | Enable "Pointer Location" in Miko3 Developer Options and recalibrate |
| Talent not launching | Verify package name: `adb shell pm list packages \| grep <name>`. Find activity: `adb shell dumpsys package <pkg>` |
| Screenshots fail | Check storage permissions: `adb shell ls /sdcard/` |
| Tests are flaky | Increase wait times in `config.yaml`. Add explicit `wait_for_activity()` calls |

### Debug Mode

```bash
# Run with full debug logging
python runner.py --all --verbose

# Check the log file
# Windows:
type reports\automation.log
# Linux:
cat reports/automation.log
```

---

## Project Structure

```
Miko3 Talents Automation/
├── config/config.yaml          # Central configuration
├── miko3_automation/           # Python package
│   ├── core/                   # ADB utils, device mgr, talent discovery
│   ├── talents/                # Talent test implementations
│   ├── verification/           # Assertion engine
│   ├── reporting/              # HTML report generator
│   └── rice_pot/               # RICE POT analyzer
├── scripts/                    # Windows .bat & Linux .sh scripts
├── tests/                      # Unit tests
├── reports/                    # Generated reports (gitignored)
├── runner.py                   # CLI entry point
└── requirements.txt            # Python dependencies
```

---

## License

Internal use — Miko3 QA Automation Team.
=======
# Miko3_talent_automation_code
This repository consists of different talent automation code
>>>>>>> a4d01929d722450c13bafb1ace7fd70296dd0a92
