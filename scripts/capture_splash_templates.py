#!/usr/bin/env python3
"""
Splash Screen Template Generator
=================================
Helper script to capture and save reference splash screens for each talent.

Usage:
    python scripts/capture_splash_templates.py

This will:
1. Connect to the ADB device
2. For each talent, launch it and capture the splash screen
3. Save reference templates to templates/splash_screens/
"""

import os
import sys
import time
import shutil
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from miko3_automation.core.adb_utils import ADBClient, ADBError
from miko3_automation.core.device_manager import DeviceManager
from miko3_automation.talents.adventure_book_talent import AdventureBookTalentTest
from miko3_automation.talents.mikoji_talent import MikojiTalentTest
from miko3_automation.talents.storymaker_new_user_flow import StorymakerNewUserFlowTest
from miko3_automation.talents.vooks_talent import VooksTalentTest


def load_config():
    """Load configuration from config.yaml."""
    import yaml
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def capture_talent_splash(
    adb: ADBClient,
    config: dict,
    talent_class,
    talent_name: str,
    package_name: str,
) -> str:
    """
    Launch a talent and capture its splash screen.

    Args:
        adb: Connected ADB client.
        config: Configuration dict.
        talent_class: Test class for the talent.
        talent_name: Human-readable talent name.
        package_name: Android package name.

    Returns:
        Path to captured splash screen.
    """
    print(f"\n{'='*60}")
    print(f"Capturing splash screen for: {talent_name}")
    print(f"{'='*60}")

    try:
        # Force stop to ensure clean launch
        adb.shell(f"am force-stop {package_name}")
        time.sleep(2)

        # Create temporary test to launch talent
        screenshot_dir = "reports/screenshots"
        os.makedirs(screenshot_dir, exist_ok=True)

        test = talent_class(
            adb=adb,
            config=config,
            talent_name=talent_name,
            package_name=package_name,
            screenshot_dir=screenshot_dir,
            enable_checkpoints=False,
        )

        # Launch the talent via setup (but just the launch part)
        print("Launching talent...")
        adb.wake_screen()
        adb.unlock_screen()
        adb.press_home()
        time.sleep(2)

        # Try to launch via am start
        activity_name = test.activity_name or f"{package_name}.MainActivity"
        cmd = f"am start -n {package_name}/{activity_name}"
        adb.shell(cmd)
        print(f"Launched: {cmd}")

        # Wait for splash screen to appear
        print("Waiting for splash screen to appear...")
        time.sleep(5)

        # Capture screenshot
        splash_path = os.path.join(
            screenshot_dir, f"{talent_name}_splash_original_{int(time.time())}.png"
        )
        adb.screenshot(splash_path)
        print(f"✓ Screenshot captured: {splash_path}")

        # Copy to templates directory
        template_path = (
            Path(__file__).parent.parent
            / "templates"
            / "splash_screens"
            / f"{talent_name.lower()}_splash.png"
        )
        shutil.copy(splash_path, template_path)
        print(f"✓ Template saved: {template_path}")

        # Force stop
        adb.shell(f"am force-stop {package_name}")
        time.sleep(2)

        return str(template_path)

    except Exception as e:
        print(f"✗ Error capturing splash for {talent_name}: {e}")
        return ""


def main():
    """Main function."""
    print("Miko3 Talents - Splash Screen Template Capture")
    print("=" * 60)

    # Load config
    try:
        config = load_config()
        print("✓ Configuration loaded")
    except Exception as e:
        print(f"✗ Failed to load config: {e}")
        return

    # Connect to device
    try:
        device_manager = DeviceManager(config)
        adb = device_manager.connect()
        print(f"✓ Connected to device: {adb.device_id}")
    except Exception as e:
        print(f"✗ Failed to connect to device: {e}")
        return

    # Define talents to capture
    talents = [
        (AdventureBookTalentTest, "adventure_book", "com.play.adventure_book"),
        (MikojiTalentTest, "mikoji", "com.play.mikoji"),
        (StorymakerNewUserFlowTest, "storymaker", "com.play.storymaker"),
        (VooksTalentTest, "vooks", "com.play.vooks"),
    ]

    # Capture splash screens
    captured = []
    for talent_class, name, package in talents:
        try:
            template = capture_talent_splash(adb, config, talent_class, name, package)
            if template:
                captured.append((name, template))
        except Exception as e:
            print(f"✗ Exception capturing {name}: {e}")

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Successfully captured {len(captured)} splash screen templates:")
    for name, path in captured:
        print(f"  ✓ {name}: {path}")

    remaining = [t[1] for t in talents if t[1] not in [c[0] for c in captured]]
    if remaining:
        print(f"\nFailed to capture: {', '.join(remaining)}")
        print("Try running this script again or manually capture screenshots.")

    print("\nTo use splash screen verification:")
    print("  1. Call take_screenshot('splash') when the splash screen appears")
    print("  2. Call verify_splash_screen() in your verify() method")
    print("  3. Reference templates will be compared automatically")


if __name__ == "__main__":
    main()
