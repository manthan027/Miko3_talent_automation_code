"""
Quick Fix: Click 'Create Story' Button
======================================
This script specifically targets the 'Create Story' button in the 
Storymaker talent to verify the exact coordinates and text detection.

Usage:
    python scripts/click_create_story.py
"""

import sys
import os
import yaml
import logging
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from miko3_automation.core.adb_utils import ADBClient, ADBError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Fix")

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
    print(" STORYMAKER BUTTON FIX - DEMO RUN ")
    print("="*60 + "\n")

    try:
        # Step 1: Ensure Talent is open
        print("🚀 Step 1: Ensuring Storymaker is in foreground...")
        adb.shell("am start -n com.miko.story_maker/.MainActivity")
        time.sleep(5)

        # Step 2: Try to find 'Create Story' by text
        print("🔍 Step 2: Searching for 'Create Story' text label...")
        elements = adb.find_elements_by_text("Create Story", exact=False)
        
        if elements:
            el = elements[0]
            print(f"✅ Found label: '{el['text']}' at {el['bounds']}")
            center = adb.get_element_center(el['bounds'])
            if center:
                print(f"🎯 Tapping at center: {center}")
                adb.tap(center[0], center[1])
                print("\n🔥 SUCCESS: Tapped using Text Recognition.")
        else:
            print("⚠️ Label 'Create Story' not found via UI Automator.")
            
            # Step 3: Fallback to manual coordinates
            create_coords = config.get("talents", {}).get("storymaker", {}).get("coordinates", {}).get("create_story", [640, 600])
            print(f"🕹️ Step 3: Falling back to config coordinates: {create_coords}")
            adb.tap(create_coords[0], create_coords[1])
            print("\n🔥 TAP SENT: Using coordinate fallback.")

        # Step 4: Verification Screenshot
        print("\n📸 Step 4: Taking verification screenshot...")
        screenshot_path = "reports/screenshots/fix_create_story_demo.png"
        adb.take_screenshot(screenshot_path)
        print(f"✅ Screenshot saved: {screenshot_path}")

    except ADBError as e:
        print(f"\n❌ ADB error: {e}")

    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    main()
