# Splash Screen Verification Guide

## Overview

This guide shows how to use OpenCV-based visual verification for talent splash screens in your Miko3 Talents Automation framework.

## Features

- **Template Matching**: Detect if reference splash screen appears in a captured image
- **SSIM Comparison**: Structural Similarity Index for robust comparison (tolerates minor variations)
- **Auto-Selection**: Automatically choose the best comparison method
- **Evidence Generation**: Save difference maps for debugging failed comparisons

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `opencv-python>=4.8.0` - Image processing
- `scikit-image>=0.22.0` - SSIM computation
- `numpy>=1.24.0` - Array operations

### 2. Capture Reference Splash Screen Templates

```bash
python scripts/capture_splash_templates.py
```

This script will:
1. Connect to your Android device via ADB
2. Launch each talent (Adventure Book, Mikoji, Storymaker, Vooks)
3. Capture the splash screen immediately after launch
4. Save templates to `templates/splash_screens/`

**Result**: Creates files like:
- `templates/splash_screens/adventure_book_splash.png`
- `templates/splash_screens/mikoji_splash.png`
- `templates/splash_screens/storymaker_splash.png`
- `templates/splash_screens/vooks_splash.png`

### 3. Update Your Talent Test

Add splash screen verification to your talent's test class `execute()` or `verify()` method:

```python
from miko3_automation.talents.base_talent import BaseTalentTest

class AdventureBookTalentTest(BaseTalentTest):
    def execute(self):
        self.step("Launch talent")
        # ... launch code ...
        
        # Capture splash screen immediately after launch
        self.wait(1, "Wait for splash to appear")
        self.take_screenshot("splash")
        
        self.step("Verify splash screen")
        # ... continue with test ...
    
    def verify(self):
        # Verify splash screen matches reference template
        result = self.verify_splash_screen()
        
        if result.passed:
            logger.info(f"✓ Splash screen verified: {result.message}")
        else:
            logger.warning(f"✗ Splash screen mismatch: {result.message}")
        
        # Other verifications...
        self.verify_activity("com.play.adventure_book")
        self.verify_no_crash()
```

## API Reference

### BaseTalentTest Methods

#### `take_screenshot(name: str) -> str`
Capture a screenshot during test execution.

```python
path = self.take_screenshot("splash")
# Saves to: reports/screenshots/TalentName_1_splash_<timestamp>.png
```

#### `verify_splash_screen(talent_name=None, screenshot_path=None) -> VerificationResult`
Verify captured screenshot against reference splash screen template.

```python
# Auto-detect talent name and use last screenshot
result = self.verify_splash_screen()

# Explicit parameters
result = self.verify_splash_screen(
    talent_name="adventure_book",
    screenshot_path="reports/screenshots/splash.png"
)

if result.passed:
    print(f"✓ {result.message}")
else:
    print(f"✗ {result.message}")
```

### Verifier Methods

#### `verify_splash_screen(talent_name, screenshot_path, comparison_method="auto") -> VerificationResult`
Direct verifier method for splash screen verification.

```python
result = self.verifier.verify_splash_screen(
    talent_name="mikoji",
    screenshot_path="path/to/screenshot.png",
    comparison_method="ssim"  # or "template" or "auto"
)
```

## Comparison Methods

### 1. SSIM (Structural Similarity Index) - Default

**Best for**: Tolerating slight variations in lighting, compression, minor UI changes

```python
# Pros:
# - Robust to compression artifacts
# - Handles lighting variations
# - Better for real-world scenarios
# - Returns value 0.0 - 1.0

# Cons:
# - Slower than template matching
# - Requires full image to be similar

verifier = SplashScreenVerifier()
result = verifier.compare_with_ssim(
    capture_path="capture.png",
    template_path="template.png",
    threshold=0.7  # 70% similarity required
)
```

### 2. Template Matching

**Best for**: Exact splash screen matches, detecting objects

```python
# Pros:
# - Fast
# - Good for finding exact logo/element matches

# Cons:
# - Sensitive to scale and rotation
# - Fails if template not exactly found

result = verifier.compare_with_template(
    capture_path="capture.png",
    template_path="template.png",
    threshold=0.8  # 80% confidence required
)
```

## Advanced Usage

### Custom Comparison Configuration

```python
from miko3_automation.verification.splash_screen_verifier import SplashScreenVerifier

verifier = SplashScreenVerifier(reference_dir="templates/splash_screens")
verifier.ssim_threshold = 0.75  # Stricter matching
verifier.template_threshold = 0.85

result = verifier.verify_talent_splash(
    talent_name="adventure_book",
    capture_path="reports/screenshots/splash.png"
)
```

### Debugging Failed Comparisons

When `verify_splash_screen()` returns `passed=False`:

```python
result = self.verify_splash_screen()

if not result.passed:
    print(f"Message: {result.message}")
    print(f"Evidence path: {result.evidence_path}")  # Difference map
    print(f"Similarity score: {result.similarity_score:.1%}")
    
    # Check detailed information
    print(f"Details: {result.details}")
    # Details show: Method used, score, and template path
```

**Difference Maps**: For SSIM comparisons, a difference map is generated showing pixel differences:
- `capture.png_diff.png` - Shows areas where images differ (white = different, black = same)

### Batch Testing

```python
from miko3_automation.verification.splash_screen_verifier import SplashScreenVerifier

talents = ["adventure_book", "mikoji", "storymaker", "vooks"]
verifier = SplashScreenVerifier()

results = []
for talent in talents:
    result = verifier.verify_talent_splash(
        talent_name=talent,
        capture_path=f"reports/screenshots/{talent}_splash.png"
    )
    results.append(result)
    print(f"{talent}: {'PASS' if result.passed else 'FAIL'} ({result.similarity_score:.1%})")
```

## Troubleshooting

### "Reference template not found"

**Cause**: Template file doesn't exist at expected location

**Solution**:
1. Run `python scripts/capture_splash_templates.py`
2. Or manually place screenshot at `templates/splash_screens/{talent_name}_splash.png`

### "OpenCV dependencies not installed"

**Cause**: Missing required packages

**Solution**:
```bash
pip install opencv-python scikit-image numpy
```

### Low similarity scores

**Possible causes**:
- Device screen resolution changed
- Splash screen UI updated
- Capture quality too low

**Solutions**:
- Recapture templates with `capture_splash_templates.py`
- Adjust thresholds: `verifier.ssim_threshold = 0.6`
- Check `_diff.png` files to see differences

### Template not detected in capture

**Possible causes**:
- Template appears at center of screen (not at edges)
- Template scaled or rotated differently

**Solution**: 
Use SSIM instead of template matching (it's the default "auto" method)

## Integration with Test Reports

Splash screen verification results are included in the HTML test report:

```python
# In your verify() method
result = self.verify_splash_screen()
# result.passed → indicates PASS/FAIL in report
# result.message → shown in details
# result.evidence_path → screenshot included if available
```

## Best Practices

1. **Capture templates on initial setup**
   ```bash
   python scripts/capture_splash_templates.py
   ```

2. **Verify immediately after launch**
   ```python
   def execute(self):
       self.step("Launch app")
       launch_talent()
       time.sleep(2)
       self.take_screenshot("splash")  # ← Capture early
   ```

3. **Use descriptive screenshot names**
   ```python
   self.take_screenshot("splash_before_interaction")
   self.take_screenshot("after_loading")
   ```

4. **Check evidence when tests fail**
   - Look for `_diff.png` files in `reports/screenshots/`
   - These show pixel-level differences

5. **Version control templates**
   - Commit `templates/splash_screens/*.png` to git
   - Re-capture if UI changes significantly

## Example: Complete Talent Test

```python
from miko3_automation.talents.base_talent import BaseTalentTest
from miko3_automation.talents.base_talent import TestStatus
import time

class StorymakerTalentTest(BaseTalentTest):
    """Test for Storymaker talent with splash screen verification."""

    def execute(self):
        """Execute test steps."""
        self.step("Screen management", "Prepare device")
        self.adb.wake_screen()
        self.adb.unlock_screen()
        time.sleep(2)

        self.step("Launch Storymaker", "Starting talent via package")
        self.adb.shell("am start -n com.play.storymaker/com.play.storymaker.MainActivity")
        
        self.step("Wait for splash screen")
        time.sleep(3)
        self.take_screenshot("splash_screen")

        self.step("Wait for content load")
        self.wait_for_text("Create Story", timeout=20)
        time.sleep(2)
        self.take_screenshot("main_ui")

        self.pass_step("Execution completed successfully")

    def verify(self):
        """Verify test results."""
        # Verify splash screen
        splash_result = self.verify_splash_screen()
        print(f"Splash verification: {splash_result.message}")

        # Verify app is running
        self.verify_activity("com.play.storymaker")
        
        # Verify no crashes
        self.verify_no_crash()
        
        # Verify main UI appeared
        if not self.find_text("Create Story"):
            self.result.verifications.append(
                VerificationResult(
                    check_name="Main UI",
                    passed=False,
                    message="'Create Story' button not found"
                )
            )
```

## File Structure

```
templates/
├── splash_screens/
│   ├── adventure_book_splash.png  ← Reference templates
│   ├── mikoji_splash.png
│   ├── storymaker_splash.png
│   └── vooks_splash.png

reports/
├── screenshots/
│   ├── Storymaker_1_splash_1680123456.png  ← Captured during test
│   ├── Storymaker_1_splash_1680123456_diff.png  ← SSIM difference map
│   └── ...

miko3_automation/
├── verification/
│   ├── verifier.py  ← Main verifier (has verify_splash_screen)
│   └── splash_screen_verifier.py  ← Splash screen logic
└── talents/
    └── base_talent.py  ← Has verify_splash_screen() method
```

## Examples in Your Project

See working examples:
- [base_talent.py](../miko3_automation/talents/base_talent.py) - `verify_splash_screen()` method
- [splash_screen_verifier.py](../miko3_automation/verification/splash_screen_verifier.py) - Full implementation
- [scripts/capture_splash_templates.py](scripts/capture_splash_templates.py) - Template capture script
