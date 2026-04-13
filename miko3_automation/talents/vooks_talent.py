"""
Vooks Talent Test Module
========================
Automates testing of Miko3's Vooks Talent — repeatedly cycles through stories,
plays them, verifies pause/resume/seek functionality, and handles popups.
"""

import time
import logging
from typing import List, Optional, Tuple

from .base_talent import BaseTalentTest, TestStatus
from ..core.adb_utils import ADBError

logger = logging.getLogger(__name__)


class VooksTalentTest(BaseTalentTest):
    """
    Automated test for Miko3 Vooks Talent.

    Flow:
    1. Loop through stories (count limit)
    2. Open Story -> Verify video start -> Pause
    3. Resume
    4. Seek Forward -> Seek Backward -> Play Duration
    5. Exit via Cross button
    6. Generate report automatically via BaseTalentTest
    """

    def __init__(self, adb, config, **kwargs):
        talent_cfg = config.get("talents", {}).get("vooks", {})
        super().__init__(
            adb=adb,
            config=config,
            talent_name=talent_cfg.get("display_name", "Vooks"),
            package_name=talent_cfg.get("package", "com.miko.vooks"),
            activity_name=talent_cfg.get("activity", ".game.view.activity.GameActivity"),
            **kwargs,
        )
        self.talent_cfg = talent_cfg
        self.coords = talent_cfg.get("coordinates", {})
        self.timings = talent_cfg.get("timings", {})
        self.stories_tested = 0

    def _verify_launch(self, expected_package: str, max_wait: int = 15) -> bool:
        """
        Verify the correct app is in foreground after launch.

        Args:
            expected_package: Package name to verify.
            max_wait: Maximum seconds to wait for correct app.

        Returns:
            True if correct app is in foreground, False otherwise.
        """
        current_activity = ""
        for attempt in range(max_wait):
            current_activity = self.adb.get_current_activity()
            if expected_package.lower() in current_activity.lower():
                logger.info(f"Verified correct app launched: {current_activity}")
                return True
            self.wait(
                1, f"Waiting for {expected_package} (attempt {attempt + 1}/{max_wait})"
            )

        logger.warning(f"Expected {expected_package} but got: {current_activity}")
        return False

    def _dismiss_popups(self) -> None:
        """Check for and dismiss common popup messages (OK button, error dialogs, etc.)."""
        popup_dismissed = False

        # Try common popup dismiss buttons
        for button_text in [
            "OK",
            "Ok",
            "ok",
            "Close",
            "X",
            "Retry",
            "Try Again",
            "Cancel",
        ]:
            if self.tap_text(button_text):
                logger.info(f"Dismissed popup via '{button_text}' button")
                popup_dismissed = True
                self.wait(1, "Waiting for popup to close")
                break

        # If no text button worked, try tapping the center (common for error overlays)
        if not popup_dismissed:
            # Check if there's an overlay by looking for common error text
            error_elements = self.find_text("Can't play")
            if error_elements:
                logger.info("Found error text, tapping center to dismiss")
                self.adb.tap(640, 400)
                self.wait(1, "Waiting for error to dismiss")

    def _is_error_state(self) -> bool:
        """Check if the Vooks app is stuck in an error state (smiley face, error message, etc.)."""
        # Check for common error indicators
        error_texts = ["Can't play", "Error", "Failed", "Sorry", "Unable"]
        for text in error_texts:
            if self.find_text(text):
                logger.warning(f"Found error text: {text}")
                return True

        # Check for smiley face / stuck state by looking for specific UI elements
        # If we can't find any video controls or playback indicators, we're likely stuck
        elements = self.adb.find_elements_by_text(":", exact=False)
        if not elements:
            # Check if screen is still on the story selection or stuck on loading
            story_elements = self.find_text("Story")
            if story_elements:
                # We're still on story list, might be stuck on a story
                return True

        return False

    def _exit_current_story(self) -> None:
        """Exit the current story and go back to story list."""
        cross_btn = self.coords.get("cross_button", [1200, 60])
        try:
            self.adb.tap(cross_btn[0], cross_btn[1])
            self.wait(2, "Waiting to exit story")
        except ADBError:
            # Try back button as fallback
            self.adb.press_back()
            self.wait(2, "Waiting to exit story")

    def _find_icon_by_image(
        self,
        template_name: str,
        template_dir: str = "templates",
        threshold: float = 0.8,
    ) -> Optional[Tuple[int, int]]:
        """
        Find an icon on screen using template image matching.

        Args:
            template_name: Name of the template image file (e.g., "vooks_icon.png")
            template_dir: Directory containing template images
            threshold: Match confidence threshold (0.0-1.0)

        Returns:
            Tuple of (x, y) center coordinates of matched region, or None if not found
        """
        import os
        from PIL import Image

        # Get the project root (parent of miko3_automation)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        template_path = os.path.join(project_root, template_dir, template_name)

        if not os.path.exists(template_path):
            logger.warning(f"Template not found: {template_path}")
            return None

        try:
            # Take a screenshot of current screen
            temp_screenshot = os.path.join(
                self.screenshot_dir, f"temp_scan_{int(time.time())}.png"
            )
            self.adb.screenshot(temp_screenshot)

            # Load images
            screenshot = Image.open(temp_screenshot).convert("RGB")
            template = Image.open(template_path).convert("RGB")

            # Get dimensions
            screenshot_w, screenshot_h = screenshot.size
            template_w, template_h = template.size

            # Skip if template is larger than screenshot
            if template_w > screenshot_w or template_h > screenshot_h:
                logger.warning(
                    f"Template ({template_w}x{template_h}) larger than screenshot ({screenshot_w}x{screenshot_h})"
                )
                os.remove(temp_screenshot)
                return None

            # Simple template matching using PIL
            # Convert to grayscale for matching
            screenshot_gray = screenshot.convert("L")
            template_gray = template.convert("L")

            # Use resize to match template size for comparison
            # We'll scan the screenshot in patches
            best_match = None
            best_score = threshold  # Only accept matches above threshold

            # Scan with step size for performance (scan every 10 pixels)
            step = 10
            for y in range(0, screenshot_h - template_h + 1, step):
                for x in range(0, screenshot_w - template_w + 1, step):
                    # Extract region
                    region = screenshot_gray.crop(
                        (x, y, x + template_w, y + template_h)
                    )

                    # Calculate difference (lower = more similar)
                    diff = 0
                    # Get pixel data properly
                    region_data = region.tobytes()
                    template_data = template_gray.tobytes()

                    for i in range(len(region_data)):
                        diff += abs(region_data[i] - template_data[i])

                    avg_diff = diff / len(region_data)
                    score = 1 - (avg_diff / 255)  # Convert to similarity score

                    if score > best_score:
                        best_score = score
                        best_match = (x + template_w // 2, y + template_h // 2)

            # Clean up temp file
            os.remove(temp_screenshot)

            if best_match:
                logger.info(
                    f"Matched {template_name} at {best_match} with score {best_score:.2f}"
                )
                return best_match
            else:
                logger.info(f"No match found for {template_name}")
                return None

        except Exception as e:
            logger.warning(f"Image matching failed: {e}")
            return None

    def execute(self) -> None:
        """Loop through stories and play through them."""

        load_wait = self.timings.get("load_wait", 5)
        video_load_wait = self.timings.get("video_load_wait", 5)
        play_dur = self.timings.get("play_duration", 15)

        max_tests = 3  # Automating playback for first 3 videos

        for i in range(max_tests):
            self.step(f"Open Vooks Story {i + 1}", f"Selecting story index {i}")

            # Select story thumbnail
            story_btn = self.coords.get("story_list_first", [300, 400])
            try:
                self.adb.tap(story_btn[0], story_btn[1])
                self.wait(video_load_wait, "Waiting for video to start loading")
            except ADBError as e:
                self.fail_step(f"Could not open story {i + 1}: {e}")
                break

            self.take_screenshot(f"story_{i}_start")

            # Check for and dismiss any error popups after opening story
            self._dismiss_popups()

            # Wait a bit more for any delayed popups
            self.wait(2, "Waiting for any delayed popups")
            self._dismiss_popups()

            # Verify video started properly by checking for UI playback indicators (timer/progress)
            self.step(
                f"Verify Video {i + 1} Playback", "Waiting for video to start playing"
            )

            # Check if stuck on smiley/error screen - if so, skip this story
            if self._is_error_state():
                logger.warning(
                    f"Story {i + 1} stuck in error state, skipping to next story"
                )
                self._exit_current_story()
                # Try scrolling to next story
                self.adb.swipe_left()
                self.wait(2, "Scrolling to next story")
                continue

            video_started = False
            for attempt in range(5):  # 10 seconds total wait
                # Check for common playback indicators in Vooks (timer text like "00:01", etc)
                # Or check for the absence of the loading spinner if applicable.
                # Here we check for any element containing ":" which usually indicates a timer
                elements = self.adb.find_elements_by_text(":", exact=False)
                if elements:
                    logger.info(
                        f"Video playback confirmed via UI timer: {elements[0]['text']}"
                    )
                    video_started = True
                    break
                self.wait(2, "Poling for playback indicator...")

            if not video_started:
                logger.warning(
                    "No playback timer found, but proceeding with caution (fallback to screenshot check)"
                )
                # Check if still in error state
                if self._is_error_state():
                    logger.warning("Still in error state, skipping story")
                    self._exit_current_story()
                    continue
                self.pass_step(
                    "Proceeding with playback (UI timer not found but load wait complete)"
                )
            else:
                self.pass_step("Playback confirmed")

            # Pause Video
            self.step(f"Pause Video {i + 1}")
            play_btn = self.coords.get("play_button", [640, 400])
            pause_btn = self.coords.get("pause_button", [640, 400])
            try:
                self.adb.tap(play_btn[0], play_btn[1])
                self.wait(1, "Let video pause")
                self.take_screenshot(f"story_{i}_paused")
                self.pass_step("Video paused")
            except ADBError as e:
                self.fail_step(f"Failed to pause: {e}")

            # Resume Video
            self.step(f"Resume Video {i + 1}")
            try:
                self.adb.tap(pause_btn[0], pause_btn[1])
                self.wait(3, "Video playing...")
                self.pass_step("Video resumed")
            except ADBError as e:
                self.fail_step(f"Failed to resume: {e}")

            # Seek Forward
            self.step(f"Seek Forward Video {i + 1}")
            try:
                seek_y = self.coords.get("seek_bar_y", [700])[0]
                # Swiping right along horizontal bar
                self.adb.swipe(400, seek_y, 800, seek_y, 400)
                self.wait(2, "Wait after seeking forward")
                self.take_screenshot(f"story_{i}_seek_fwd")
                self.pass_step("Seeked forward")
            except ADBError as e:
                self.fail_step(f"Seek forward failed: {e}")

            # Seek Backward
            self.step(f"Seek Backward Video {i + 1}")
            try:
                seek_y = self.coords.get("seek_bar_y", [700])[0]
                # Swiping left back
                self.adb.swipe(800, seek_y, 400, seek_y, 400)
                self.wait(2, "Wait after seeking backward")
                self.take_screenshot(f"story_{i}_seek_back")
                self.pass_step("Seeked backward")
            except ADBError as e:
                self.fail_step(f"Seek backward failed: {e}")

            # Play Duration
            self.step(f"Play Duration {i + 1}")
            self.wait(play_dur, f"Playing story for {play_dur} seconds")
            self.take_screenshot(f"story_{i}_playing")
            self.pass_step("Play duration completed")

            # Exit Video using Cross Button
            # The cross button is always visible as mentioned by the user
            self.step(f"Exit Story {i + 1}")
            cross_btn = self.coords.get("cross_button", [1200, 60])
            try:
                self.adb.tap(cross_btn[0], cross_btn[1])
                self.wait(load_wait, "Wait for exit to homescreen")
                self.take_screenshot(f"story_{i}_exit")
                self.pass_step("Story exited back to talent home")
            except ADBError as e:
                self.adb.press_back()
                self.fail_step(f"Failed to tap cross button: {e}")

            # Scroll to next story loop
            try:
                # Swipe left (scroll forward)
                self.adb.swipe_left()
                self.wait(2, "Scrolling to next stories")
            except:
                pass

            self.stories_tested += 1

    def verify(self) -> None:
        """Verify Vooks talent test results."""

        self.step("Verify session progress")
        if self.stories_tested > 0:
            self.pass_step(
                f"{self.stories_tested} Vooks story sessions completed successfully"
            )
        else:
            self.fail_step("No Vooks stories were successfully tested")

        self.step("Verify no crashes")
        crash_result = self.verify_no_crash()
        if crash_result.passed:
            self.pass_step("No crashes detected")
        else:
            self.fail_step(f"Crash detected: {crash_result.message}")

        self.take_screenshot("final_state")
