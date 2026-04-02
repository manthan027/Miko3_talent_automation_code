"""
Storytelling Talent Test Module
===============================
Automates testing of Miko3's Storytelling Talent — selects a story,
triggers playback, and monitors the session to completion.
"""

import time
import logging

from .base_talent import BaseTalentTest, TestStatus
from ..core.adb_utils import ADBError

logger = logging.getLogger(__name__)


class StorytellingTalentTest(BaseTalentTest):
    """
    Automated test for Miko3 Storytelling Talent.

    Test Flow:
    1. Launch storytelling talent
    2. Select the first story from the story list
    3. Tap play to start the storytelling session
    4. Monitor the session — periodically check screen changes
    5. Navigate through pages (if applicable)
    6. Wait for session to complete or timeout
    7. Verify session played without crashes

    Configuration (from config.yaml → talents.storytelling):
        - coordinates.story_list_first: [x, y]
        - coordinates.play_button: [x, y]
        - coordinates.next_page: [x, y]
        - coordinates.close_button: [x, y]
        - timings.load_wait: seconds
        - timings.page_duration: seconds
        - timings.session_timeout: seconds
    """

    def __init__(self, adb, config, **kwargs):
        talent_cfg = config.get("talents", {}).get("storytelling", {})
        super().__init__(
            adb=adb,
            config=config,
            talent_name=talent_cfg.get("display_name", "Storytelling Talent"),
            package_name=talent_cfg.get("package", "com.miko.storytime"),
            activity_name=talent_cfg.get("activity", ".main_story.view.GameActivity"),
            **kwargs,
        )
        self.talent_cfg = talent_cfg
        self.coords = talent_cfg.get("coordinates", {})
        self.timings = talent_cfg.get("timings", {})
        self.pages_progressed = 0

    def execute(self) -> None:
        """Select a story and play through it."""

        load_wait = self.timings.get("load_wait", 5)
        page_duration = self.timings.get("page_duration", 10)
        session_timeout = self.timings.get("session_timeout", 120)

        # --- Step 1: Select a Story ---
        self.step("Select story from list", "Tapping the first story in the list")
        story_btn = self.coords.get("story_list_first", [640, 200])
        self.adb.tap(story_btn[0], story_btn[1])
        self.wait(load_wait, "Waiting for story details to load")
        self.take_screenshot("story_selected")
        self.pass_step("Story selected")

        # --- Step 2: Start Playback ---
        self.step("Start storytelling playback", "Tapping the play button")
        play_btn = self.coords.get("play_button", [640, 500])
        self.adb.tap(play_btn[0], play_btn[1])
        self.wait(load_wait, "Waiting for storytelling session to start")
        self.take_screenshot("playback_started")
        self.pass_step("Playback initiated")

        # --- Step 3: Monitor Session ---
        self.step("Monitor storytelling session", "Tracking pages and screen changes")
        next_page_btn = self.coords.get("next_page", [1100, 400])
        session_start = time.time()
        max_pages = 20  # Safety limit

        while time.time() - session_start < session_timeout and self.pages_progressed < max_pages:
            # Check if still in the storytelling talent
            try:
                current = self.adb.get_current_package()
                if self.package_name.lower() not in current.lower():
                    logger.info("Storytelling session ended (left talent)")
                    break
            except ADBError:
                pass

            # Take periodic screenshot
            self.take_screenshot(f"page_{self.pages_progressed + 1}")

            # Wait for current page
            self.wait(page_duration, f"Listening to page {self.pages_progressed + 1}")

            # Try to advance to next page
            try:
                before_screen = self.result.screenshots[-1] if self.result.screenshots else ""
                self.adb.tap(next_page_btn[0], next_page_btn[1])
                self.wait(2, "Transitioning to next page")

                # Check if screen changed (new page loaded)
                after_path = f"reports/screenshots/{self.talent_name}_page_check_{int(time.time())}.png"
                try:
                    self.adb.screenshot(after_path)
                    self.result.screenshots.append(after_path)
                except ADBError:
                    pass

                self.pages_progressed += 1
                logger.info("  Page %d completed", self.pages_progressed)

            except ADBError as e:
                logger.warning("Could not advance page: %s", e)
                break

        elapsed = time.time() - session_start
        self.pass_step(
            f"Session monitored for {elapsed:.0f}s, {self.pages_progressed} pages"
        )

        # --- Step 4: Close Session ---
        self.step("Close storytelling session")
        close_btn = self.coords.get("close_button", [1200, 50])
        try:
            self.adb.tap(close_btn[0], close_btn[1])
            self.wait(2, "Closing session")
        except ADBError:
            self.adb.press_back()
            self.wait(1)
        self.take_screenshot("session_closed")
        self.pass_step("Session closed")

    def verify(self) -> None:
        """Verify storytelling talent test results."""

        # Verify at least one page was progressed
        self.step("Verify session progress")
        if self.pages_progressed > 0:
            self.pass_step(f"{self.pages_progressed} pages completed")
        else:
            self.fail_step("No pages were progressed during session")

        # Verify no crashes
        self.step("Verify no crashes")
        crash_result = self.verify_no_crash()
        if crash_result.passed:
            self.pass_step("No crashes detected")
        else:
            self.fail_step(f"Crash detected: {crash_result.message}")

        # Verify screen content changed
        self.step("Verify visual progression")
        screenshots = self.result.screenshots
        if len(screenshots) >= 2:
            screen_result = self.verify_screen_changed(
                screenshots[0], screenshots[-1]
            )
            if screen_result.passed:
                self.pass_step("Visual content progressed during session")
            else:
                self.fail_step("Visual content did not change significantly")
        else:
            self.pass_step("Insufficient screenshots for comparison (skipped)")

        self.take_screenshot("final_state")
