"""
Listening Mode Diagnostic Script
=================================
Run this while the Miko3 robot is in Storymaker's LISTENING MODE.
It will capture a screenshot + UI hierarchy dump so we can identify
exactly what elements appear during listening mode.

Usage:
    1. Manually open Storymaker on the robot
    2. Click "Create Story" and wait for the intro to finish
    3. When you see the listening waves on screen, run this script:
       python scripts/capture_listening_mode.py
"""

import sys
import os
import time
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from miko3_automation.core.adb_utils import ADBClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-7s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ListeningDiag")


def main():
    print("=" * 60)
    print("LISTENING MODE DIAGNOSTIC")
    print("=" * 60)
    print()
    print("Make sure the robot is currently showing listening waves!")
    print()

    # Connect to device
    adb = ADBClient()

    # Create output directory
    out_dir = "reports/listening_mode_capture"
    os.makedirs(out_dir, exist_ok=True)

    timestamp = int(time.time())

    # 1. Take screenshot
    print("[1/3] Capturing screenshot...")
    screenshot_path = os.path.join(out_dir, f"listening_mode_{timestamp}.png")
    try:
        adb.screenshot(screenshot_path)
        print(f"      Screenshot saved: {screenshot_path}")
    except Exception as e:
        print(f"      Screenshot failed: {e}")

    # 2. Dump UI hierarchy
    print("[2/3] Dumping UI hierarchy...")
    ui_xml_path = os.path.join(out_dir, f"ui_hierarchy_{timestamp}.xml")
    try:
        xml_content = adb.dump_ui_hierarchy()
        if xml_content:
            with open(ui_xml_path, "w", encoding="utf-8") as f:
                f.write(xml_content)
            print(f"      UI hierarchy saved: {ui_xml_path}")

            # Parse and show interesting elements
            print()
            print("[3/3] Analyzing UI elements...")
            print("-" * 60)

            import xml.etree.ElementTree as ET
            try:
                root = ET.fromstring(xml_content)
                interesting = []
                for node in root.iter("node"):
                    text = node.get("text", "").strip()
                    desc = node.get("content-desc", "").strip()
                    res_id = node.get("resource-id", "").strip()
                    cls = node.get("class", "").strip()
                    bounds = node.get("bounds", "")

                    # Show all non-empty elements
                    if text or desc:
                        interesting.append({
                            "text": text,
                            "content-desc": desc,
                            "resource-id": res_id,
                            "class": cls,
                            "bounds": bounds,
                        })

                if interesting:
                    print(f"Found {len(interesting)} elements with text/desc:")
                    print()
                    for i, elem in enumerate(interesting, 1):
                        print(f"  [{i}] text='{elem['text']}'")
                        if elem["content-desc"]:
                            print(f"      desc='{elem['content-desc']}'")
                        if elem["resource-id"]:
                            print(f"      id='{elem['resource-id']}'")
                        print(f"      class={elem['class']}")
                        print(f"      bounds={elem['bounds']}")
                        print()
                else:
                    print("  No elements with text found (listening mode may use")
                    print("  purely visual animations without text labels).")
                    print()
                    print("  We will use SCREENSHOT-BASED detection instead.")
            except ET.ParseError as e:
                print(f"  XML parse error: {e}")
        else:
            print("      UI hierarchy dump returned empty")
    except Exception as e:
        print(f"      UI dump failed: {e}")

    print()
    print("=" * 60)
    print("DONE! Check these files:")
    print(f"  Screenshot: {screenshot_path}")
    print(f"  UI XML:     {ui_xml_path}")
    print()
    print("Share the screenshot or the element list above")
    print("so we can configure listening mode detection.")
    print("=" * 60)


if __name__ == "__main__":
    main()
