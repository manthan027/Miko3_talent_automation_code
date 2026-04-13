"""
Mikojis Talent Test Module
========================
Automates testing of Miko3's Mikojis Talent — plays through a series
of videos, verifying playback and navigation.

Includes CLEAR Framework Video Count Validation:
    - Count videos at runtime via UI dump
    - Compare with stored baseline count
    - Detect added, removed, or unchanged videos
    - Validate video titles, thumbnails, and deduplication
"""

import json
import os
import time
import logging

from .base_talent import BaseTalentTest, TestStatus
from ..core.adb_utils import ADBError

logger = logging.getLogger(__name__)


class MikojiTalentTest(BaseTalentTest):
    """
    Automated test for Miko3 Video Talent.

    Test Flow:
    1. Launch video talent
    2. Count videos in Video Talent section (CLEAR Framework)
    3. For each video in the playlist:
       a. Tap play button
       b. Wait for video to load and play
       c. Verify screen is changing (video playing)
       d. Tap next button to advance
    4. Verify no crashes occurred
    5. Verify all videos were played
    6. Validate video count against baseline (CLEAR Framework)

    Configuration (from config.yaml -> talents.video):
        - coordinates.play_button: [x, y]
        - coordinates.next_button: [x, y]
        - timings.video_load_wait: seconds
        - timings.video_play_duration: seconds
        - timings.between_videos: seconds
        - max_videos: int
        - video_count_validation.enabled: bool
        - video_count_validation.baseline_file: path
        - video_count_validation.unexpected_drop_threshold: int
        - video_count_validation.unexpected_spike_threshold: int
        - video_count_validation.video_text_keywords: list
    """

    def __init__(self, adb, config, **kwargs):
        talent_cfg = config.get("talents", {}).get("video", {})
        super().__init__(
            adb=adb,
            config=config,
            talent_name=talent_cfg.get("display_name", "Mikojis Talent"),
            package_name=talent_cfg.get("package", "com.miko.mikoji"),
            activity_name=talent_cfg.get("activity", ".MainActivity"),
            **kwargs,
        )
        self.talent_cfg = talent_cfg
        self.coords = talent_cfg.get("coordinates", {})
        self.timings = talent_cfg.get("timings", {})
        self.max_videos = talent_cfg.get("max_videos", 10)
        self.videos_played = 0

        # CLEAR Framework: Video count validation config
        vc_cfg = talent_cfg.get("video_count_validation", {})
        self.video_count_enabled = vc_cfg.get("enabled", False)
        self.baseline_file = vc_cfg.get(
            "baseline_file", "reports/video_count_baseline.json"
        )
        self.unexpected_drop_threshold = vc_cfg.get("unexpected_drop_threshold", 0)
        self.unexpected_spike_threshold = vc_cfg.get("unexpected_spike_threshold", 50)
        self.video_keywords = vc_cfg.get(
            "video_text_keywords", ["Mikojis", "play", "thumbnail"]
        )

        # Recovery Logic Config
        rec_cfg = talent_cfg.get("recovery", {})
        self.recovery_enabled = rec_cfg.get("enabled", True)
        self.max_retries = rec_cfg.get("max_retries", 2)
        self.popup_keywords = rec_cfg.get(
            "popup_keywords", ["error", "failed", "retry", "ok", "cancel", "close"]
        )
        self.check_interval = rec_cfg.get("check_interval", 2)

        # CLEAR Framework: Video count state
        self.current_video_count = 0
        self.previous_video_count = 0
        self.video_count_difference = 0
        self.video_count_result = ""
        self.video_titles = []
        self.video_ids = []
        self.has_duplicate_videos = False

    def execute(self) -> None:
        """Play through the video playlist."""

        # CLEAR Framework: Count videos before playback
        if self.video_count_enabled:
            self._count_videos()

        # Get coordinate configs
        play_btn = self.coords.get("play_button", [640, 400])
        next_btn = self.coords.get("next_button", [1100, 750])
        load_wait = self.timings.get("video_load_wait", 5)
        play_duration = self.timings.get("video_play_duration", 30)
        between_wait = self.timings.get("between_videos", 3)

        for i in range(1, self.max_videos + 1):
            try:
                # Step: Start video
                self.step(f"Play video {i}/{self.max_videos}")
                self.take_screenshot(f"Mikojis_{i}_before")

                # Tap play button
                logger.info(
                    "  Tapping play button at (%d, %d)", play_btn[0], play_btn[1]
                )
                self.adb.tap(play_btn[0], play_btn[1])
                self.wait(load_wait, "Waiting for video to load")

                # Take screenshot during playback
                self.take_screenshot(f"Mikojis_{i}_playing")

                # Wait for video to play
                logger.info("  Waiting %ds for video playback...", play_duration)
                self.wait(play_duration, f"Video {i} playing")

                # Take screenshot at end of playback
                self.take_screenshot(f"Mikojis_{i}_after")
                self.videos_played += 1
                self.pass_step(f"Mikojis {i} played successfully")

                # Step: Navigate to next video
                if i < self.max_videos:
                    self.step(f"Navigate to next video ({i + 1})")
                    logger.info(
                        "  Tapping next button at (%d, %d)", next_btn[0], next_btn[1]
                    )
                    self.adb.tap(next_btn[0], next_btn[1])
                    self.wait(between_wait, "Waiting for next video to load")

                    # Verify we're still in the video talent
                    current = self.adb.get_current_package()
                    if self.package_name.lower() not in current.lower():
                        logger.warning(
                            "Left video talent! Current: %s. Might be end of playlist.",
                            current,
                        )
                        self.pass_step(f"Playlist may have ended after {i} videos")
                        break
                    self.pass_step("Navigated to next video")

            except ADBError as e:
                self.fail_step(f"Error during video {i}: {e}")
                logger.error("Mikojis %d error: %s", i, e)

                recovered = False
                for retry in range(self.max_retries):
                    if self._attempt_recovery(i, retry):
                        logger.info("  Recovery successful, retrying video %d", i)
                        recovered = True
                        break

                if recovered:
                    continue
                else:
                    logger.error("  All recovery attempts failed for video %d", i)
                    break

        logger.info("Completed %d/%d videos", self.videos_played, self.max_videos)

    def verify(self) -> None:
        """Verify video talent test results."""

        # Verify at least one video was played
        self.step("Verify videos played")
        if self.videos_played > 0:
            self.pass_step(f"{self.videos_played} videos played")
        else:
            self.fail_step("No videos were played")

        # Verify no crashes
        self.step("Verify no crashes")
        crash_result = self.verify_no_crash()
        if crash_result.passed:
            self.pass_step("No crashes detected")
        else:
            self.fail_step(f"Crash detected: {crash_result.message}")

        # Verify screen content changed (video was actually playing)
        self.step("Verify screen changes")
        screenshots = self.result.screenshots
        if len(screenshots) >= 2:
            screen_result = self.verify_screen_changed(screenshots[0], screenshots[-1])
            if screen_result.passed:
                self.pass_step("Screen content changed (video playing confirmed)")
            else:
                self.fail_step("Screen content did not change significantly")
        else:
            self.pass_step("Not enough screenshots for comparison (skipped)")

        # CLEAR Framework: Validate video count against baseline
        if self.video_count_enabled:
            self._validate_video_count()
            self._validate_best_practices()

        # Final evidence
        self.take_screenshot("final_state")

    # -------------------------------------------------------------------------
    # CLEAR Framework: Video Count Validation
    # -------------------------------------------------------------------------

    def _count_videos(self) -> None:
        """
        L - Logic: Count total number of videos in the Video Talent section.

        Uses UI dump to find video elements matching configured keywords.
        Extracts video titles and IDs for best practice validation.
        """
        self.step("Count videos in Video Talent section")
        logger.info("  Counting videos via UI dump...")

        try:
            result = self.adb.count_ui_elements(self.video_keywords)
            self.current_video_count = result["count"]

            # Extract titles and IDs from matched elements
            seen_titles = set()
            seen_ids = set()
            for elem in result["elements"]:
                title = elem.get("text", "").strip()
                vid_id = elem.get("resource-id", "").strip()
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    self.video_titles.append(title)
                if vid_id and vid_id not in seen_ids:
                    seen_ids.add(vid_id)
                    self.video_ids.append(vid_id)

            # Detect duplicate videos
            if len(result["elements"]) > len(seen_titles) + len(seen_ids):
                self.has_duplicate_videos = True

            logger.info(
                "  Current video count: %d (titles: %d, ids: %d)",
                self.current_video_count,
                len(self.video_titles),
                len(self.video_ids),
            )
            self.pass_step(f"Found {self.current_video_count} video elements")

        except ADBError as e:
            logger.warning("  Failed to count videos: %s", e)
            self.fail_step(f"Failed to count videos: {e}")

    def _load_baseline(self) -> int:
        """Load the previous video count from the baseline file."""
        try:
            if os.path.exists(self.baseline_file):
                with open(self.baseline_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("video_count", 0)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning("Could not load baseline file: %s", e)
        return 0

    def _save_baseline(self, count: int) -> None:
        """Save the current video count as the new baseline."""
        try:
            os.makedirs(os.path.dirname(self.baseline_file) or ".", exist_ok=True)
            data = {
                "video_count": count,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "talent": self.talent_name,
            }
            with open(self.baseline_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.info("  Baseline saved: %d videos", count)
        except IOError as e:
            logger.warning("Could not save baseline file: %s", e)

    def _validate_video_count(self) -> None:
        """
        E - Examples / R - Result: Compare current count with baseline.

        Validation Logic:
            Current Count - Previous Count = Difference
            Difference > 0  -> Videos Added
            Difference < 0  -> Videos Removed
            Difference = 0  -> No Change

        Fail conditions:
            Count <= unexpected_drop_threshold (unexpected drop)
            Count >= unexpected_spike_threshold (unexpected spike)
        """
        self.step("Validate video count against baseline")

        self.previous_video_count = self._load_baseline()
        self.video_count_difference = (
            self.current_video_count - self.previous_video_count
        )

        # Determine result
        if self.video_count_difference > 0:
            self.video_count_result = f"Videos Added (+{self.video_count_difference})"
        elif self.video_count_difference < 0:
            self.video_count_result = f"Videos Removed ({self.video_count_difference})"
        else:
            self.video_count_result = "No Change"

        logger.info(
            "  Previous: %d | Current: %d | Difference: %d | Result: %s",
            self.previous_video_count,
            self.current_video_count,
            self.video_count_difference,
            self.video_count_result,
        )

        # Check for unexpected drop (count went to 0 or below threshold)
        if self.current_video_count <= self.unexpected_drop_threshold:
            self.fail_step(
                f"FAIL: Unexpected video count drop! "
                f"Count is {self.current_video_count} (threshold: {self.unexpected_drop_threshold}). "
                f"Previous: {self.previous_video_count}"
            )
            logger.error(
                "  FAIL: Video count %d <= threshold %d",
                self.current_video_count,
                self.unexpected_drop_threshold,
            )
        # Check for unexpected spike (count exceeds threshold)
        elif self.current_video_count >= self.unexpected_spike_threshold:
            self.fail_step(
                f"FAIL: Unexpected video count spike! "
                f"Count is {self.current_video_count} (threshold: {self.unexpected_spike_threshold}). "
                f"Previous: {self.previous_video_count}"
            )
            logger.error(
                "  FAIL: Video count %d >= threshold %d",
                self.current_video_count,
                self.unexpected_spike_threshold,
            )
        else:
            self.pass_step(
                f"Video count validation passed: {self.video_count_result} "
                f"(Previous: {self.previous_video_count}, Current: {self.current_video_count})"
            )

        # Save current count as new baseline
        self._save_baseline(self.current_video_count)

        # Log the validation summary
        self._log_validation_summary()

    def _validate_best_practices(self) -> None:
        """
        Automation Best Practice: Validate beyond just count.

        Validates:
        - Video titles present
        - Video IDs present
        - No duplicate videos
        """
        self.step("Validate video content best practices")

        issues = []

        # Check for video titles
        if not self.video_titles:
            issues.append("No video titles found in UI dump")
            logger.warning("  No video titles detected")
        else:
            logger.info("  Found %d video titles", len(self.video_titles))

        # Check for duplicate videos
        if self.has_duplicate_videos:
            issues.append("Duplicate video elements detected")
            logger.warning("  Duplicate videos detected")
        else:
            logger.info("  No duplicate videos detected")

        if issues:
            self.fail_step(f"Best practice issues: {'; '.join(issues)}")
        else:
            self.pass_step(
                f"Best practice checks passed: "
                f"{len(self.video_titles)} titles, "
                f"{len(self.video_ids)} IDs, "
                f"no duplicates"
            )

    def _log_validation_summary(self) -> None:
        """Log a clear summary of the video count validation results."""
        separator = "=" * 60
        logger.info(separator)
        logger.info("CLEAR FRAMEWORK - VIDEO COUNT VALIDATION SUMMARY")
        logger.info(separator)
        logger.info("  Previous Count:  %d", self.previous_video_count)
        logger.info("  Current Count:   %d", self.current_video_count)
        logger.info("  Difference:      %d", self.video_count_difference)
        logger.info("  Result:          %s", self.video_count_result)
        logger.info("  Titles Found:    %d", len(self.video_titles))
        logger.info("  IDs Found:       %d", len(self.video_ids))
        logger.info(
            "  Duplicates:      %s", "YES" if self.has_duplicate_videos else "NO"
        )
        logger.info(separator)

    # -------------------------------------------------------------------------
    # Recovery Logic
    # -------------------------------------------------------------------------

    def _detect_popup(self) -> bool:
        """
        Detect if an error popup is displayed on screen.

        Checks for common popup keywords in the UI hierarchy.
        Returns True if popup detected, False otherwise.
        """
        if not self.recovery_enabled:
            return False

        for keyword in self.popup_keywords:
            elements = self.adb.find_elements_by_text(keyword, exact=False)
            if elements:
                logger.info("  Popup detected: keyword '%s' found", keyword)
                return True

        return False

    def _recover_level_1(self, video_num: int) -> bool:
        """
        Recovery Level 1: If popup detected, try to dismiss it and retry.

        Steps:
        1. Tap OK or cross button to dismiss popup
        2. Press Back
        3. Relaunch Talent
        4. Retry Video

        Returns True if recovery successful, False otherwise.
        """
        logger.info(
            "  === Recovery Level 1: Attempting to recover video %d ===", video_num
        )

        try:
            self.step("Recovery Level 1", f"Dismiss popup and retry video {video_num}")

            for keyword in ["OK", "ok", "Close", "close", "X"]:
                if self.adb.tap_text(keyword):
                    logger.info("  Tapped '%s' to dismiss popup", keyword)
                    break
            else:
                cross_coords = self.coords.get("cross_button", [1200, 60])
                self.adb.tap(cross_coords[0], cross_coords[1])
                logger.info("  Tapped cross button to dismiss popup")

            self.wait(1, "Waiting for popup to dismiss")
            self.adb.press_back()
            self.wait(1, "Waiting after back press")

            self.step("Relaunch talent", "Restarting talent after popup")
            self.discovery.force_stop(self.package_name)
            self.wait(1)
            self.discovery.launch_talent(self.package_name, self.activity_name)
            self.wait(2, "Waiting for talent to relaunch")

            self.pass_step("Recovery Level 1: Relaunched talent")
            return True

        except ADBError as e:
            logger.warning("  Recovery Level 1 failed: %s", e)
            return False

    def _recover_level_2(self, video_num: int) -> bool:
        """
        Recovery Level 2: Force stop and restart the flow.

        Steps:
        1. Force stop app
        2. Go Home
        3. Restart flow from beginning

        Returns True if recovery successful, False otherwise.
        """
        logger.info("  === Recovery Level 2: Force restart for video %d ===", video_num)

        try:
            self.step("Recovery Level 2", "Force stop and restart flow")

            self.discovery.force_stop(self.package_name)
            logger.info("  Force stopped %s", self.package_name)
            self.wait(1)

            self.adb.press_home()
            logger.info("  Pressed Home button")
            self.wait(1)

            self.step("Restart talent", "Relaunching after force stop")
            self.discovery.launch_talent(self.package_name, self.activity_name)
            self.wait(2, "Waiting for talent to restart")

            self.pass_step("Recovery Level 2: Flow restarted")
            return True

        except ADBError as e:
            logger.warning("  Recovery Level 2 failed: %s", e)
            return False

    def _attempt_recovery(self, video_num: int, retry_count: int) -> bool:
        """
        Attempt to recover from video failure.

        Args:
            video_num: Current video number being played.
            retry_count: Current retry attempt (0-indexed).

        Returns True if recovery successful and can retry, False otherwise.
        """
        if not self.recovery_enabled:
            return False

        if self._detect_popup():
            logger.info("  Popup detected during video %d", video_num)

            if retry_count < 1:
                if self._recover_level_1(video_num):
                    return True
            else:
                if self._recover_level_2(video_num):
                    return True

        logger.warning(
            "  Recovery failed after %d attempts for video %d",
            retry_count + 1,
            video_num,
        )
        return False
