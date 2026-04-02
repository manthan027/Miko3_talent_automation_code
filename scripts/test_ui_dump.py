"""
UI Hierarchy Diagnostic Script
==============================
This script dumps the current UI hierarchy and lists all elements
that contain text. Use this to verify if the automation can "see"
the buttons on the robot's screen.

Usage:
    python scripts/test_ui_dump.py
"""

import sys
import os
import yaml
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from miko3_automation.core.adb_utils import ADBClient, ADBError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("UIDump")

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
    print(" MIKO3 UI HIERARCHY DUMP ")
    print("="*60 + "\n")

    try:
        print("📥 Dumping UI hierarchy (this may take 5-10 seconds)...")
        xml = adb.dump_ui_hierarchy()
        
        if not xml:
            print("❌ Failed to retrieve UI hierarchy.")
            return

        print(f"✅ Received XML ({len(xml)} bytes)")
        
        print("\n🔍 ELEMENTS WITH TEXT/DESCRIPTION:\n")
        print(f"{'TEXT':<25} | {'BOUNDS':<25} | {'CLASS'}")
        print("-" * 80)
        
        import xml.etree.ElementTree as ET
        try:
            root = ET.fromstring(xml)
            count = 0
            for node in root.iter("node"):
                text = node.get("text", "")
                desc = node.get("content-desc", "")
                label = text or desc
                
                if label:
                    bounds = node.get("bounds", "")
                    cls = node.get("class", "").split(".")[-1]
                    print(f"{label[:25]:<25} | {bounds:<25} | {cls}")
                    count += 1
            
            print("-" * 80)
            print(f"\nFound {count} elements with labels.")
            
        except Exception as e:
            print(f"❌ Error parsing XML: {e}")
            print("\nRAW XML SNIPPET:")
            print(xml[:500] + "...")

    except ADBError as e:
        print(f"\n❌ ADB error: {e}")

    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    main()
