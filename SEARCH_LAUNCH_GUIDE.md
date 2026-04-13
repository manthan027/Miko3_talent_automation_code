# Advanced App Launching Guide

## Overview

The framework supports **3 methods** to launch applications:

1. **`am_start`** (default) - Package-based launching via ADB (fastest)
2. **`click`** - Direct icon click (simulates user tap)
3. **`search`** - Full user flow: **Apps >> Search >> Type >> Click** (most realistic)

---

## Method 1: Default (am_start)

Uses the Android package manager to launch the app directly.

```yaml
storymaker:
  launch_method: "am_start"           # Default method
  search_enabled: false
```

**Pros**: Fast, reliable, no coordinate dependencies  
**Cons**: No user behavior simulation

---

## Method 2: Click-Based Launching

Clicks directly on the app icon to launch it.

```yaml
storymaker:
  launch_method: "click"
  app_icon_coordinates: [640, 400]    # [x, y] of app icon
  search_enabled: false
```

**Pros**: Simulates user click, tests icon visibility  
**Cons**: Requires exact coordinates

---

## Method 3: Search-Based Launching (RECOMMENDED FOR REALISTIC TESTING)

Simulates the complete flow a user would take:

```yaml
storymaker:
  launch_method: "search"
  search_enabled: true
  search_config:
    apps_button_coordinates: [1150, 750]     # "Apps" button on home
    search_icon_coordinates: [100, 700]      # Search icon in apps drawer
    search_text: "Storymaker"                # What to search for
    search_result_coordinates: [640, 350]    # App result to click
```

---

## Search Flow Step-by-Step

```
┌─────────────────────────────────────────────────┐
│                   HOME SCREEN                    │
│                                                  │
│                                                  │
│                           [Apps]← apps_button   │
└─────────────────────────────────────────────────┘
                      ⬇️ Click Apps
┌─────────────────────────────────────────────────┐
│                   APPS DRAWER                    │
│  [🔍]← search_icon  [Search Box]               │
│  ┌────────────────────────────────────────────┐ │
│  │ Storymaker     ← search_result             │ │
│  │ Vooks                                      │ │
│  │ Mikoji                                     │ │
│  └────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
         ⬇️ Click Search ⬇️ Type ⬇️ Click Result
┌─────────────────────────────────────────────────┐
│               TALENT LAUNCHED                    │
│          (com.miko.story_maker)                  │
└─────────────────────────────────────────────────┘
```

**Detailed Steps:**

1. **Click Apps Button** at `apps_button_coordinates` (e.g., `[1150, 750]`)
2. Wait for apps drawer to load (1.5 seconds)
3. **Click Search Icon** at `search_icon_coordinates` (e.g., `[100, 700]`)
4. Wait for search box (0.5 seconds)
5. **Type Search Text** (e.g., "Storymaker")
6. Wait for results (1.5 seconds)
7. **Click Search Result** at `search_result_coordinates` (e.g., `[640, 350]`)
8. **Close Keyboard** (KEYCODE_BACK)
9. Wait for app to launch (2.0 seconds)
10. **Verify** activity appears in foreground ✅

---

## Configuration Examples

### Example 1: Storymaker with Search Launch

```yaml
storymaker:
  package: "com.miko.story_maker"
  activity: ".MainActivity"
  display_name: "Storymaker"
  launch_method: "search"
  search_enabled: true
  search_config:
    apps_button_coordinates: [1150, 750]
    search_icon_coordinates: [100, 700]
    search_text: "Storymaker"
    search_result_coordinates: [640, 350]
  intent_extras:
    APP_ID: "121"
    INTENT: "create_story"
```

### Example 2: Vooks with Click Launch

```yaml
vooks:
  package: "com.miko.vooks"
  activity: ".game.view.activity.GameActivity"
  display_name: "Vooks"
  launch_method: "click"
  app_icon_coordinates: [450, 350]
  search_enabled: false
```

### Example 3: Mikoji with Auto-Detect Search Result

```yaml
mikoji:
  package: "com.miko.mikoji"
  activity: ".MainActivity"
  display_name: "Mikojis Talent"
  launch_method: "search"
  search_enabled: true
  search_config:
    apps_button_coordinates: [1150, 750]
    search_icon_coordinates: [100, 700]
    search_text: "Mikoji"
    search_result_coordinates: null        # Auto-detect instead of fixed coords
```

### Example 4: Mix All Methods

```yaml
talents:
  storymaker:
    launch_method: "search"
    search_enabled: true
    search_config:
      apps_button_coordinates: [1150, 750]
      search_icon_coordinates: [100, 700]
      search_text: "Storymaker"
      search_result_coordinates: [640, 350]

  vooks:
    launch_method: "click"
    app_icon_coordinates: [450, 350]

  mikoji:
    launch_method: "am_start"           # Default

  adventure_book:
    launch_method: "search"
    search_enabled: true
    search_config:
      apps_button_coordinates: [1150, 750]
      search_icon_coordinates: [100, 700]
      search_text: "Adventure Book"
      search_result_coordinates: null
```

---

## Finding Coordinates

### Step 1: Take Screenshots

```bash
adb shell screencap /sdcard/screen.png
adb pull /sdcard/screen.png .
```

### Step 2: Identify Each Coordinate

**Apps Button** (Home Screen):
- Look for "Apps", "Applications", or grid icon
- Typically at: bottom-right, bottom-center, or top-right
- Example: `[1150, 750]` or `[640, 750]`

**Search Icon** (Inside Apps Drawer):
- Look for magnifying glass &#9209; icon
- Typically at: top-left or top-center
- Example: `[100, 700]` or `[640, 100]`

**Search Result** (After Typing):
- Click on your app name in the results list
- Typically at: center of screen, in the results area
- Example: `[640, 350]` or `[800, 300]`

**App Icon** (For Click Method):
- Look for app icon on home screen or apps drawer
- Example: `[640, 400]` or `[320, 500]`

---

## Common Coordinates (Miko3 Device)

### Home Screen Layout
```
1280 × 720 pixels

Bottom Navigation Bar (y ≈ 680-720):
[Apps]         [Search]       [Home]
 ↓               ↓              ↓
[1150, 750]  [640, 750]    [100, 750]
```

### Apps Drawer Layout
```
Search Area (y ≈ 50-100):
[🔍 Search Box]
 ↓
[100, 100] or [100, 700] depending on layout
```

### Common Positions

| Element | X | Y | Coordinate |
|---------|---|---|-----------|
| Apps Button (bottom-right) | 1150 | 750 | [1150, 750] |
| Apps Button (bottom-center) | 640 | 750 | [640, 750] |
| Search Icon (top-left) | 100 | 100 | [100, 100] |
| Search Icon (bottom-left) | 100 | 700 | [100, 700] |
| Search Result (center) | 640 | 350 | [640, 350] |
| Center of Screen | 640 | 360 | [640, 360] |

---

## Troubleshooting

### Issue: "Apps drawer didn't open"

**Possible Causes:**
- Wrong `apps_button_coordinates`
- Button not visible on current screen
- Screen locked or in sleep

**Solution:**
```bash
# Verify device state
adb shell dumpsys power | grep mWakefulness
# Should show: mWakefulness=Awake

# Take screenshot to confirm position
adb shell screencap /sdcard/screen.png
adb pull /sdcard/screen.png .
```

### Issue: "Search icon not found"

**Possible Causes:**
- Wrong `search_icon_coordinates`
- Still on home screen (apps drawer didn't open)
- Search icon replaced with different UI

**Solution:**
```bash
# Check if search icon has different position in your apps drawer
# Update search_icon_coordinates to correct position
# Try alternative coordinate suggestions above
```

### Issue: "App not found in search results"

**Possible Causes:**
- Wrong `search_text` value
- Text is case-sensitive
- Search functionality not working on device

**Solution:**
```yaml
# Try different variations:
search_text: "Storymaker"      # Try this
search_text: "storymaker"      # Or this
search_text: "Story Maker"     # Or this
search_text: "story maker"     # Or this
```

### Issue: "Keyboard didn't close"

**Possible Causes:**
- Device uses different key code
- Keyboard stuck or not responding

**Solution:**
- Device typically uses KEYCODE_BACK (4)
- If not working, the framework might need device-specific configuration
- Try enabling verbose logging to see exactly what's happening

### Issue: "Search result click missed"

**Possible Causes:**
- Wrong `search_result_coordinates`
- Result moved after search
- Screen changed during execution

**Solution:**
```bash
# Take screenshot after searching
# Find exact position where app result appears
# Update search_result_coordinates

# Or use null to auto-detect:
search_result_coordinates: null
```

---

## Debugging & Logging

### Enable Verbose Logging

```bash
python runner.py --talent storymaker --verbose
```

### Expected Output for Search Launch

```
[INFO] Using search-based launching: Apps >> Search >> 'Storymaker'
[INFO] Clicking Apps button at (1150, 750)
[INFO] Apps drawer opened
[INFO] Clicking search icon at (100, 700)
[INFO] Search box opened
[INFO] Typing search text: Storymaker
[INFO] Search results loaded
[INFO] Clicking search result at (640, 350)
[INFO] Closing keyboard
[INFO] Successfully launched com.miko.story_maker via search
```

### Common Debug Messages

| Message | Meaning |
|---------|---------|
| "Apps drawer opened" | ✅ Apps button click successful |
| "Search box opened" | ✅ Search icon click successful |
| "Search results loaded" | ✅ Text input and waiting successful |
| "Activity did not appear" | ❌ App didn't launch after all steps |

---

## Performance Comparison

| Metric | am_start | click | search |
|--------|----------|-------|--------|
| Launch Time | ~1-2s | ~3-5s | ~8-10s |
| Reliability | Very High | High | Medium |
| UI Dependency | None | High | High |
| User Simulation | ❌ | ✅ | ✅✅ |

---

## Configuration Template

```yaml
talents:
  your_talent:
    package: "com.your.app"
    activity: ".MainActivity"
    display_name: "Your Talent"
    
    # Choose launch method:
    launch_method: "search"              # "am_start", "click", or "search"
    
    # From "search" method:
    search_enabled: true
    search_config:
      apps_button_coordinates: [1150, 750]      # ← UPDATE THESE
      search_icon_coordinates: [100, 700]       # ← UPDATE THESE
      search_text: "Your App Name"              # ← UPDATE THIS
      search_result_coordinates: [640, 350]     # ← UPDATE THIS (or use null)
    
    # For "click" method:
    app_icon_coordinates: null                  # ← UPDATE IF USING CLICK
    
    intent_extras: {}
    coordinates:
      play_button: [640, 400]
      # ... other coordinates
```

---

## Quick Setup Steps

1. **Take Device Screenshots**
   ```bash
   adb shell screencap /sdcard/home.png /sdcard/apps.png
   adb pull /sdcard/home.png .
   adb pull /sdcard/apps.png .
   ```

2. **Locate Coordinates in Screenshots**
   - Use screenshot editor or online tools
   - Mark: Apps button, Search icon, Search result
   - Note the (x, y) pixel positions

3. **Update config.yaml**
   ```yaml
   storymaker:
     search_enabled: true
     search_config:
       apps_button_coordinates: [YOUR_X, YOUR_Y]
       search_icon_coordinates: [YOUR_X, YOUR_Y]
       search_text: "Storymaker"
       search_result_coordinates: [YOUR_X, YOUR_Y]
   ```

4. **Run Test**
   ```bash
   python runner.py --talent storymaker --verbose
   ```

5. **Verify Output**
   - Check logs for "Successfully launched"
   - If failed, adjust coordinates and retry

---

## Summary

**For All Talents**, the search-based launch applies the same flow:

1. ✅ Click **Apps** button
2. ✅ Click **Search** icon  
3. ✅ Type **talent name**
4. ✅ Close **keyboard**
5. ✅ Click **search result**
6. ✅ **Talent launches** ✓

Just update the coordinates for your device and you're ready to go!
