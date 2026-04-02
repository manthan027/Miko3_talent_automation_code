import yaml
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from miko3_automation.core.device_manager import DeviceManager
from miko3_automation.talents.vooks_talent import VooksTalentTest

with open('config/config.yaml') as f: config = yaml.safe_load(f)
dm = DeviceManager(config)
dm.ensure_ready()
adb = dm.get_device()

# Go Home first to ensure clean state
adb.shell("input keyevent 3")
import time; time.sleep(2)

test = VooksTalentTest(adb, config)
if test.find_text("Apps"):
    test.tap_text("Apps")
else:
    print("Could not find Apps text!")

print("Waiting for Apps drawer to open...")
time.sleep(5)
adb.screenshot("reports/screenshots/apps_drawer.png")
print("Saved apps_drawer.png!")
