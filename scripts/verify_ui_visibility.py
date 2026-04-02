"""
Verification Script for Miko3 UI Visibility
===========================================
This script tests the screen wake, unlock, and brightness control
functionality on a physical Miko3 robot.

Usage:
    python scripts/verify_ui_visibility.py
"""

import sys
import os
import time
import yaml
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from miko3_automation.core.adb_utils import ADBClient, ADBError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("VisibilityVerifier")

def main():
    # Load config
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "config.yaml")
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return

    # Initialize ADB
    device_cfg = config.get("device", {})
    adb = ADBClient(
        device_serial=device_cfg.get("serial", ""),
        adb_path=device_cfg.get("adb_path", "adb")
    )

    print("\n" + "="*60)
    print(" MIKO3 UI VISIBILITY VERIFICATION ")
    print("="*60 + "\n")

    try:
        # Step 1: Check Connection
        print("[1/5] Checking ADB connection...")
        props = adb.get_device_properties()
        print(f"      Device: {props.get('model')} (Android {props.get('android_version')})")
        
        # Step 2: Wake Screen
        print("[2/5] Testing WAKE SCREEN...")
        adb.wake_screen()
        time.sleep(1)
        if adb.is_screen_on():
            print("      SUCCESS: Screen is ON")
        else:
            print("      WARNING: Screen might still be OFF/DOZING")

        # Step 3: Unlock Screen
        print("[3/5] Testing UNLOCK SCREEN...")
        adb.unlock_screen()
        print("      ACTION: Performed unlock swipe")
        time.sleep(1)

        # Step 4: Brightness
        brightness = device_cfg.get("brightness", 255)
        print(f"[4/5] Testing BRIGHTNESS ({brightness})...")
        adb.set_screen_brightness(brightness)
        print(f"      ACTION: Set brightness to {brightness}")

        # Step 5: Stay Awake
        stay_awake = device_cfg.get("stay_awake", True)
        print(f"[5/5] Testing STAY AWAKE ({stay_awake})...")
        adb.set_stay_awake(stay_awake)
        print(f"      ACTION: Set stay awake to {stay_awake}")

        print("\n" + "="*60)
        print(" VERIFICATION COMPLETE ")
        print(" Please verify that your Miko3 screen is now:")
        print(" 1. ON and bright")
        print(" 2. Unlocked (showing home screen or previous app)")
        print("="*60 + "\n")

    except ADBError as e:
        print(f"\nERROR: ADB command failed: {e}")
    except Exception as e:
        print(f"\nUNEXPECTED ERROR: {e}")

if __name__ == "__main__":
    main()
