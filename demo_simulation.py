import sys
import os
import time
import logging
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from miko3_automation.core.adb_utils import ADBClient
from miko3_automation.core.device_manager import DeviceManager
from miko3_automation.talents.storymaker_talent import StorymakerTalentTest

# Setup logging to console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)

def run_demo():
    print("\n" + "="*60)
    print("🎬 MIKO3 AUTOMATION - UI VISIBILITY DEMO (SIMULATION)")
    print("="*60 + "\n")

    config = {
        "device": {"serial": "MIKO3-SIM-123"},
        "talents": {
            "storymaker": {
                "package": "com.miko.storymaker",
                "activity": ".MainActivity",
                "display_name": "Storymaker Talent",
                "coordinates": {"start_button": [640, 500]},
                "timings": {"load_wait": 0.1, "animation_wait": 0.1}
            }
        },
        "verification": {"screenshot_dir": "reports/screenshots"}
    }

    # Mock subprocess.run to show what ADB commands are being sent
    with patch("miko3_automation.core.adb_utils.subprocess.run") as mock_run, \
         patch("miko3_automation.core.adb_utils.shutil.which", return_value="/usr/bin/adb"), \
         patch("miko3_automation.core.adb_utils.ADBClient.get_connected_devices", return_value=[{"serial": "MIKO3-SIM-123", "status": "device"}]), \
         patch("miko3_automation.core.adb_utils.ADBClient.shell", side_effect=lambda x: f"Mock Shell Output: {x}"):

        print("🚀 [Step 1] Initializing Device Manager...")
        dm = DeviceManager(config)
        
        print("\n🛠️ [Step 2] Ensuring Device is Ready (The New Logic)...")
        print("   (This will now wake the screen, set brightness, and stay awake)")
        dm.ensure_ready()

        print("\n📦 [Step 3] Initializing Storymaker Talent Test...")
        adb = dm.get_device()
        test = StorymakerTalentTest(adb, config)

        print("\n🛫 [Step 4] Launching Talent (With Improved Flags)...")
        # Mocking methods to avoid file IO or complex logic in simulation
        test.take_screenshot = MagicMock()
        test.discovery.launch_talent = MagicMock(return_value=True)
        test.setup()

    print("\n" + "="*60)
    print("✅ DEMO COMPLETE")
    print("The logs above show the exact sequence of improvements:")
    print("1. Waking screen via KEYCODE_WAKEUP (224)")
    print("2. Setting brightness to 255")
    print("3. Setting power mode to Stay Awake (usb)")
    print("4. Launching with wait flags and foreground priority")
    print("="*60 + "\n")

if __name__ == "__main__":
    run_demo()
