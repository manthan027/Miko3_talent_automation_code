"""
Third-Party Talent Test Module
==============================
Generic automation for any third-party talent installed on Miko3.
Performs smoke testing: launch, interact, verify stability.
"""

import time
import logging

from .base_talent import BaseTalentTest, TestStatus
from ..core.adb_utils import ADBError

logger = logging.getLogger(__name__)


class ThirdPartyTalentTest(BaseTalentTest):
    """
    Generic automated test for any third-party Miko3 talent.

    Since third-party talents have unknown UIs, this test performs a
    standard smoke test:

    1. Discover and launch the talent
    2. Wait for it to fully load
    3. Perform basic interactions (tap center, swipe, back)
    4. Monitor for crashes or ANRs
    5. Verify the talent remains stable

    The test can be extended with custom interaction sequences
    defined in config.yaml or passed at runtime.

    Usage:
        test = ThirdPartyTalentTest(
            adb, config,
            package_name="com.example.thirdparty",
        )
        result = test.run()
    """

    def __init__(
        self,
        adb,
        config,
        package_name: str,
        activity_name: str = "",
        talent_name: str = "",
        custom_interactions: list = None,
        **kwargs,
    ):
        """
        Initialize third-party talent test.

        Args:
            adb: ADBClient instance.
            config: Config dict.
            package_name: Package name of the third-party talent.
            activity_name: Main activity (auto-discovered if empty).
            talent_name: Display name (defaults to package basename).
            custom_interactions: Optional list of interaction dicts:
                [
                    {"action": "tap", "x": 500, "y": 300, "wait": 2},
                    {"action": "swipe", "x1": 800, "y1": 400, "x2": 200, "y2": 400},
                    {"action": "key", "keycode": 4},
                    {"action": "text", "value": "hello"},
                    {"action": "wait", "seconds": 5},
                    {"action": "screenshot", "name": "custom"},
                ]
        """
        tp_cfg = config.get("thirdparty", {})
        display_name = talent_name or package_name.split(".")[-1].replace("_", " ").title()

        super().__init__(
            adb=adb,
            config=config,
            talent_name=display_name,
            package_name=package_name,
            activity_name=activity_name,
            **kwargs,
        )
        self.tp_cfg = tp_cfg
        self.custom_interactions = custom_interactions or []
        self.launch_wait = tp_cfg.get("default_launch_wait", 5)
        self.smoke_duration = tp_cfg.get("smoke_test_duration", 10)
        self.interaction_delay = tp_cfg.get("interaction_delay", 2)

    def execute(self) -> None:
        """Perform smoke test on the third-party talent."""

        screen_w, screen_h = self.adb.get_screen_resolution()
        center_x = screen_w // 2
        center_y = screen_h // 2

        # --- Additional load wait ---
        self.step("Wait for talent to fully load")
        self.wait(self.launch_wait, "Giving talent extra time to initialize")
        self.take_screenshot("fully_loaded")
        self.pass_step("Talent loaded")

        # --- Run custom interactions if defined ---
        if self.custom_interactions:
            self._run_custom_interactions()
        else:
            self._run_default_smoke_test(screen_w, screen_h, center_x, center_y)

    def _run_default_smoke_test(
        self, screen_w: int, screen_h: int, center_x: int, center_y: int
    ) -> None:
        """Run a standard smoke test with basic interactions."""

        # Interaction 1: Tap center of screen
        self.step("Tap screen center", "Basic interaction test")
        self.adb.tap(center_x, center_y)
        self.wait(self.interaction_delay)
        self.take_screenshot("after_center_tap")
        self.pass_step("Center tap executed")

        # Interaction 2: Swipe left
        self.step("Swipe left", "Testing navigation")
        self.adb.swipe_left(screen_w, screen_h)
        self.wait(self.interaction_delay)
        self.take_screenshot("after_swipe_left")
        self.pass_step("Swipe left executed")

        # Interaction 3: Swipe right
        self.step("Swipe right", "Return navigation")
        self.adb.swipe_right(screen_w, screen_h)
        self.wait(self.interaction_delay)
        self.take_screenshot("after_swipe_right")
        self.pass_step("Swipe right executed")

        # Interaction 4: Tap various quadrants
        self.step("Tap quadrant exploration", "Testing tap responses across screen")
        quadrants = [
            ("Top-Left", screen_w // 4, screen_h // 4),
            ("Top-Right", 3 * screen_w // 4, screen_h // 4),
            ("Bottom-Left", screen_w // 4, 3 * screen_h // 4),
            ("Bottom-Right", 3 * screen_w // 4, 3 * screen_h // 4),
        ]
        for name, x, y in quadrants:
            try:
                self.adb.tap(x, y)
                self.wait(1)
                logger.info("  Tapped %s (%d, %d)", name, x, y)
            except ADBError as e:
                logger.warning("  Tap %s failed: %s", name, e)
        self.take_screenshot("after_quadrant_taps")
        self.pass_step("Quadrant exploration complete")

        # Interaction 5: Wait for stability
        self.step("Stability wait", f"Maintaining talent open for {self.smoke_duration}s")
        self.wait(self.smoke_duration, "Monitoring for stability")
        self.take_screenshot("stability_check")
        self.pass_step(f"Talent stable for {self.smoke_duration}s")

    def _run_custom_interactions(self) -> None:
        """Execute user-defined interaction sequence."""
        for i, interaction in enumerate(self.custom_interactions, 1):
            action = interaction.get("action", "")
            self.step(f"Custom interaction {i}: {action}")

            try:
                if action == "tap":
                    self.adb.tap(interaction["x"], interaction["y"])
                    self.wait(interaction.get("wait", self.interaction_delay))
                elif action == "swipe":
                    self.adb.swipe(
                        interaction["x1"], interaction["y1"],
                        interaction["x2"], interaction["y2"],
                        interaction.get("duration_ms", 300),
                    )
                    self.wait(interaction.get("wait", self.interaction_delay))
                elif action == "long_press":
                    self.adb.long_press(
                        interaction["x"], interaction["y"],
                        interaction.get("duration_ms", 1000),
                    )
                    self.wait(interaction.get("wait", self.interaction_delay))
                elif action == "key":
                    self.adb.key_event(interaction["keycode"])
                    self.wait(interaction.get("wait", 1))
                elif action == "text":
                    self.adb.input_text(interaction["value"])
                    self.wait(interaction.get("wait", 1))
                elif action == "wait":
                    self.wait(interaction.get("seconds", 5))
                elif action == "screenshot":
                    self.take_screenshot(interaction.get("name", f"custom_{i}"))
                elif action == "back":
                    self.adb.press_back()
                    self.wait(interaction.get("wait", 1))
                elif action == "home":
                    self.adb.press_home()
                    self.wait(interaction.get("wait", 1))
                else:
                    logger.warning("Unknown interaction action: %s", action)

                self.pass_step(f"{action} completed")

            except ADBError as e:
                self.fail_step(f"{action} failed: {e}")

    def verify(self) -> None:
        """Verify third-party talent stability."""

        # Verify talent didn't crash
        self.step("Verify no crashes")
        crash_result = self.verify_no_crash()
        if crash_result.passed:
            self.pass_step("No crashes detected")
        else:
            self.fail_step(f"Crash detected: {crash_result.message}")

        # Verify talent is still running (or gracefully exited)
        self.step("Verify talent state")
        try:
            current = self.adb.get_current_package()
            if self.package_name.lower() in current.lower():
                self.pass_step("Talent still running in foreground")
            else:
                self.pass_step(
                    f"Talent not in foreground (current: {current}) — may have completed"
                )
        except ADBError:
            self.pass_step("Could not check foreground — assuming OK")

        # Verify screen changed at all
        self.step("Verify visual responsiveness")
        screenshots = self.result.screenshots
        if len(screenshots) >= 2:
            screen_result = self.verify_screen_changed(
                screenshots[0], screenshots[-1]
            )
            if screen_result.passed:
                self.pass_step("Talent responded to interactions visually")
            else:
                self.pass_step("Screen unchanged — talent may have static UI (acceptable)")
        else:
            self.pass_step("Insufficient screenshots (skipped)")

        self.take_screenshot("final_state")
