import time, os
os.system("adb shell input tap 750 80") # Try 750, 80 for the video icon
time.sleep(3)
os.system("adb shell screencap -p /sdcard/video_tab.png")
os.system("adb pull /sdcard/video_tab.png reports/screenshots/video_tab.png")
print("Saved video_tab.png")
