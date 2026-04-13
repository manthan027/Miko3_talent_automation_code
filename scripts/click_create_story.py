"""
Storymaker Automate Test - Full Sequence
======================================
This script implements the exact 19-step sequence provided in the batch script,
using the coordinates and timings configured in config.yaml.

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
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("MonkeyTest")

def main():
    # Load config
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(root_dir, "config", "config.yaml")
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

    talent_cfg = config.get("talents", {}).get("storymaker", {})
    coords = talent_cfg.get("coordinates", {})

    print("\n" + "="*60)
    print(" STORYMAKER AUTOMATE TEST - 19 STEP SEQUENCE ")
    print("="*60 + "\n")

    try:
        # Step 1: Home
        print("🏠 Step 1: Home keyevent")
        adb.shell("input keyevent 3")
        time.sleep(2)

        # Step 2: Apps Button
        print(f"📱 Step 2: Clicking APPS button at {coords.get('apps_button')}")
        app_btn = coords.get("apps_button", [1207, 644])
        adb.tap(app_btn[0], app_btn[1])
        time.sleep(3)

        # Step 3: Storymaker Talent
        print(f"🚀 Step 3: Launching Storymaker at {coords.get('talent_icon')}")
        talent_icon = coords.get("talent_icon", [933, 212])
        adb.tap(talent_icon[0], talent_icon[1])
        time.sleep(12)

        # Step 4: AI Disclaimer
        print(f"❌ Step 4: Dismissing Disclaimer at {coords.get('disclaimer_cross')}")
        disc_cross = coords.get("disclaimer_cross", [154, 120])
        adb.tap(disc_cross[0], disc_cross[1])
        time.sleep(2)

        # Step 5: Create Story
        print(f"📝 Step 5: Clicking Create Story at {coords.get('create_story')}")
        create_btn = coords.get("create_story", [186, 591])
        adb.tap(create_btn[0], create_btn[1])
        time.sleep(15)

        # Step 6: Exit Ongoing
        print(f"🚪 Step 6: Exiting ongoing at {coords.get('exit_ongoing_story')}")
        exit_btn = coords.get("exit_ongoing_story", [71, 73])
        adb.tap(exit_btn[0], exit_btn[1])
        time.sleep(12)

        # Step 7: My Adventure
        print(f"🗺️ Step 7: My Adventure at {coords.get('my_adventure')}")
        adv_btn = coords.get("my_adventure", [663, 67])
        adb.tap(adv_btn[0], adv_btn[1])
        time.sleep(3)

        # Step 8: Create Your Own
        print(f"✨ Step 8: Create Your Own at {coords.get('create_own')}")
        own_btn = coords.get("create_own", [634, 614])
        adb.tap(own_btn[0], own_btn[1])
        time.sleep(3)

        # Step 9: Inform Parent
        print(f"👨‍👩‍👧 Step 9: Inform Parent at {coords.get('inform_parent')}")
        inf_btn = coords.get("inform_parent", [615, 545])
        adb.tap(inf_btn[0], inf_btn[1])
        time.sleep(3)

        # Step 10: Parent Cross
        print(f"❌ Step 10: Closing Parent Info at {coords.get('parent_cross')}")
        p_cross = coords.get("parent_cross", [216, 125])
        adb.tap(p_cross[0], p_cross[1])
        time.sleep(3)

        # Step 11: Favourite
        print(f"❤️ Step 11: Favourites at {coords.get('favourite')}")
        fav_btn = coords.get("favourite", [812, 62])
        adb.tap(fav_btn[0], fav_btn[1])
        time.sleep(3)

        # Step 12: Story Book
        print(f"📖 Step 12: Story Book at {coords.get('story_book')}")
        book_btn = coords.get("story_book", [476, 77])
        adb.tap(book_btn[0], book_btn[1])
        time.sleep(3)

        # Step 13: Credits
        print(f"📊 Step 13: Story Credits at {coords.get('remaining_count')}")
        rem_btn = coords.get("remaining_count", [1216, 66])
        adb.tap(rem_btn[0], rem_btn[1])
        time.sleep(3)

        # Step 14: Credits Cross
        print(f"❌ Step 14: Closing Credits at {coords.get('count_cross')}")
        c_cross = coords.get("count_cross", [186, 185])
        adb.tap(c_cross[0], c_cross[1])
        time.sleep(3)

        # Step 15: Final Cross
        print(f"🔚 Step 15: Final Cross at {coords.get('final_cross')}")
        f_cross = coords.get("final_cross", [71, 73])
        adb.tap(f_cross[0], f_cross[1])
        time.sleep(2)

        # Step 16: NO Icon
        print(f"👎 Step 16: NO Icon at {coords.get('no_icon')}")
        no_btn = coords.get("no_icon", [892, 620])
        adb.tap(no_btn[0], no_btn[1])
        time.sleep(2)

        # Step 17: After NO Cross
        print(f"❌ Step 17: Cross after NO at {coords.get('after_no_cross')}")
        an_cross = coords.get("after_no_cross", [71, 73])
        adb.tap(an_cross[0], an_cross[1])
        time.sleep(2)

        # Step 18: YES Icon
        print(f"👍 Step 18: YES Icon at {coords.get('yes_icon')}")
        yes_btn = coords.get("yes_icon", [1114, 630])
        adb.tap(yes_btn[0], yes_btn[1])
        time.sleep(2)

        # Step 19: Root Exit
        print(f"🏠 Step 19: Exiting to Root at {coords.get('root_exit')}")
        root_btn = coords.get("root_exit", [55, 77])
        adb.tap(root_btn[0], root_btn[1])
        time.sleep(2)

        print("\n🔥 SUCCESS: Full 19-step sequence completed.")

    except ADBError as e:
        print(f"\n❌ ADB error: {e}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    main()
