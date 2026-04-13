# Advanced App Launching Guide

## Overview

The framework now supports **3 methods** to launch applications:
1. **`am_start`** (default) - Package-based launching via ADB
2. **`click`** - Click directly on app icon
3. **`search`** - Full user flow: Apps >> Search >> Type >> Click

The **search method** simulates exactly how a real user would find and launch an app.

## Configuration

### Method 1: Default (am_start)

```yaml
storymaker:
  launch_method: "am_start"  # Default - uses package name
  app_icon_coordinates: null
  search_enabled: false
```

### Method 2: Click-Based Launching

Modify your `config/config.yaml`:

```yaml
talents:
  storymaker:
    package: "com.miko.story_maker"
    activity: ".MainActivity"
    display_name: "Storymaker"
    launch_method: "click"                    # Use "click"
    app_icon_coordinates: [640, 400]          # [x, y] of app icon
    search_enabled: false
    # ... rest of config
```

### Method 3: Search-Based Launching (Complete User Flow)

This method simulates the exact flow a user would take to find and launch an app:

```yaml
talents:
  storymaker:
    package: "com.miko.story_maker"
    activity: ".MainActivity"
    display_name: "Storymaker"
    launch_method: "search"                   # Use "search"
    search_enabled: true                      # Enable search-based launching
    search_config:                            # Complete search flow configuration
      apps_button_coordinates: [1150, 750]   # [x, y] - "Apps" button on home
      search_icon_coordinates: [100, 700]    # [x, y] - search icon in apps drawer
      search_text: "Storymaker"               # What to search for
      search_result_coordinates: [640, 400]  # [x, y] - app result to click (optional)
    app_icon_coordinates: null
    # ... rest of config
```

### Parameters

| Parameter | Type | Method | Description |
|-----------|------|--------|-------------|
| `launch_method` | string | all | `"am_start"` (default), `"click"`, or `"search"` |
| `search_config` | object | search | Configuration for search flow |
| — `apps_button_coordinates` | [x, y] or null | search | Coordinates of "Apps" button on home screen |
| — `search_icon_coordinates` | [x, y] or null | search | Coordinates of search icon in apps drawer |
| — `search_text` | string | search | Text to search (e.g., "Storymaker") |
| — `search_result_coordinates` | [x, y] or null | search | Coordinates of search result to click (auto-detect if null) |
| `search_text` | string | search | Text to search (e.g., "Storymaker") |
| `search_result_coordinates` | [x, y] or null | search | Coordinates of search result (auto-detect if null) |

## F1. Apps Button Coordinates (Search Method)

- **Location**: Home screen, usually bottom or corner
- **Step**: Click "Apps" or "Applications" button
- **Measure**: Screenshot → locate → measure (x, y)

Example locations:
- Bottom-right: `[1150, 750]`
- Bottom-center: `[640, 750]`
- Top-right: `[1200, 50]`

### 2. Search Icon Coordinates (Search Method)

- **Location**: Inside apps drawer, usually top
- **Step**: After "Apps" opens, find search icon
- **Measure**: Screenshot → locate → measure (x, y)

Example locations:
- Top-left: `[100, 100]`
- Top-right: `[1200, 100]`
- Bottom-left: `[100, 700]`

### 3. Search Result Coordinates (Search Method - Optional)

- **Location**: Where search results appear
- **Step**: Perform search → results show → find app item
- **Measure**: Screenshot → locate → measure (x, y)

If you don't provide this, the framework will try to auto-detect.

### 4. App Icon Coordinates (Click Method)

- **Location**: Home screen or apps drawer
- **Step**: Find app icon
- **Measure**: Screenshot → locate → measure (x, y)

**Note**: If you don't provide  (Full Flow)
```yaml
vooks:
  package: "com.miko.vooks"
  activity: ".game.view.activity.GameActivity"
  display_name: "Vooks"
  launch_method: "search"
  search_enabled: true
  search_config:
    apps_button_coordinates: [1150, 750]      # "Apps" button on home
    search_icon_coordinates: [100, 700]       # Search icon in apps drawer
    search_text: "Vooks"                       # Search for "Vooks"
    search_result_coordinates: [640, 350]     # Where result appears
  app_icon_coordinates: null
```

**Flow:**
1. ✅ Click Apps at [1207, 644]
2. ✅ Apps drawer opens
3. ✅ Click Search at [1228, 53]
4. ✅ Type "Vooks"
5. ✅ Click result at [640, 350]
6. ✅ Close keyboard
7. ✅ App launches

### Example 3: Mikoji via Search (Auto-Detect Result)
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
    search_result_coordinates: null            # Auto-detect result
  app_icon_coordinates: null
```

### Example 4: Adventure Book via Search
```yaml
adventure_book:
  package: "com.miko.story_maker"
  activity: ".MainActivity"
  display_name: "My Adventure Book"
  launch_method: "search"
  search_enabled: true
  search_config:
    apps_button_coordinates: [1150, 750]
    search_icon_coordinates: [100, 700]
    search_text: "Adventure Book"
    search_result_coordinates: [640, 350]
  app_icon_coordinates: null
```

### Example 5: Mix of Methods
```yaml
talents:
  storymaker:
    launch_method: "search"        # User flow: Apps >> Search >> Type >> Click
    search_enabled: true
    search_config:
      apps_button_coordinates: [1150, 750]
      search_icon_coordinates: [100, 700]
      search_text: "Storymaker"
      search_result_coordinates: [640, 350]
  
  vooks:
    launch_method: "click"         # Direct icon click
    app_icon_coordinates: [450, 350]
  
  mikoji:
    launch_method: "am_start"      # Traditional launch
  
  adventure_book:
    launch_method: "search"        # User flow: Apps >> Search >> Type >> Click
    search_enabled: true
    search_config:
      apps_button_coordinates: [1150, 750]
      search_icon_coordinates: [100, 700]
      search_text: "Adventure Book"
      search_result_coordinates: null  # Auto-detect
    search_result_coordinates: null
  
  vooks:
    launch_method: "click"
    app_icon_coordinates: [450, 350]
  
  mikoji:
    launch_method: "am_start"  # Traditional method
  
  adventure_book:
    launch_method: "search"
    search_enabled: true
    search_icon_coordinates: [100, 700]
    search_text: "Adventure Book"
    search_result_coordinates: null
```

## Search-Based Launch Flow

When using `search` m (Click Method)

1. **Wrong Coordinates**
   - Take a screenshot and verify coordinates
   - Try coordinates near the app icon (±50 pixels)
   - Device resolution: `adb shell wm size`

2. **Screen State**
   - Ensure screen is awake and unlocked
   - Check `stay_awake` is enabled in config

### App Not Found (Search Method)

1. **Wrong Search Icon Coordinates**
   - Verify search icon location on device
   - Take screenshot to confirm position

2. **Wrong Search Text**
   - Use exact text visible on search results
   - Case-sensitive (try different variations)
   - Example: "Storymaker", "storymaker", "Story Maker"

3. **Search Result Not Found**
   - If `search_result_coordinates: null`, auto-detect might fail
   - Manually set the coordinates where result appears
   - Take screenshot of search results

4. **Keyboard Not Closing**
   - Device might use different keycode for back
| Method | Best For | Pros | Cons |
|--------|----------|------|------|
| **am_start** | Automated testing | Most reliable, fastest | No UI simulation |
| **click** | Icon-based launching | Simulates user click | Requires exact coordinates |
| **search** | Realistic user flow | Tests search feature | Requires search UI knowledge |

### Recommendation by Scenario

- **Development/Testing**: Use `am_start` (fastest feedback)
- **User Behavior Simulation**: Use `search` (realistic flow)
- **App Discovery**: Use `click` (tests icon visibility)
- **CI/CD Pipeline**: Use `am_start` (most stable)

## Configuration Template

```yaml
talents:
  your_talent:
    package: "com.your.app"
    activity: ".MainActivity"
    display_name: "Your Talent"
    
    # Launch Method
    launch_method: "am_start"              # Change to "click" or "search"
    
    # For "click" method:
    app_icon_coordinates: null             # [x, y] of icon on home/apps
    
    # For "search" method:
    search_enabled: false                  # Set to true to enable search flow
    search_config:                         # Search flow configuration
      apps_button_coordinates: null        # [x, y] - "Apps" button on home
      search_icon_coordinates: null        # [x, y] - search icon in apps drawer
      search_text: "Your App Name"        # What to search for
      search_result_coordinates: null      # [x, y] - app result (or null for auto)
    
    intent_extras: {}
    coordinates:
      # ... your coordinates
```

---

## Device Information

### Device Resolution
```bash
adb shell wm size
# Output: Physical size: 1280x720
```

### Screen Dimensions (Miko3 Example)
- Width: 1280 pixels
- Height: 720 pixels
- Typical coordinate ranges:
  - X: 0-1280
  - Y: 0-720

### Common Coordinate Regions

```
┌──────────────────────────────┐
│  Top Bar (y: 0-100)          │
│                              │
│  Main Content                │
│  (y: 100-600)                │
│                              │
│  Bottom Navigation           │
│  (y: 600-720)                │
│  [Apps] [Search] [Home]      │
└──────────────────────────────┘
  0          640          1280 (x-axis)
```verify app started

These are hardcoded but can be made configurable if needed.

## Troubleshooting

### App Not Launching

1. **Wrong Coordinates**
   - Take a screenshot and verify coordinates
   - Try coordinates near the app icon (±50 pixels)

2. **Screen State**
   - Ensure the screen is awake and unlocked
   - Check that `stay_awake` is enabled in config

3. **App Not in Foreground**
   - Check if a splash screen or popup appears
   - Verify the activity detection timeout (default 10s)

### Debugging

Enable verbose logging to see click details:
```bash
python runner.py --talent storymaker --verbose
```

Look for messages like:
```
[INFO] Clicking app icon at (640, 400)
[INFO] Successfully launched com.miko.story_maker via click
```

## When to Use Each Method

### Use `am_start`
- Default method that's most reliable
- When you want to pass intent extras
- For automated testing without UI simulation

### Use `click`
- When you want to simulate real user interaction
- For testing app discovery/finder functionality
- When package-based launch is unreliable
- When testing splash screens and launch flows

## Configuration Template

```yaml
talents:
  your_talent:
    package: "com.your.app"
    activity: ".MainActivity"
    display_name: "Your Talent"
    launch_method: "am_start"              # Change to "click" to enable
    app_icon_coordinates: null             # Change to [x, y] for click launch
    intent_extras: {}
    coordinates:
      # ... your coordinates
```

---

**Need Help?**
- Check device screen resolution: `adb shell wm size`
- Take a screenshot: The app icon locations should be visible
- Enable `--verbose` flag to see all click actions
