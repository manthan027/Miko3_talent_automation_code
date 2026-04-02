"""
Base Talent Test Module
=======================
Abstract base class for all Miko3 talent test automation.
Defines the setup → execute → verify → teardown lifecycle.
"""

import os
import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional

from ..core.adb_utils import ADBClient, ADBError
from ..core.talent_discovery import TalentDiscovery
from ..core.checkpoint import CheckpointManager
from ..verification.verifier import Verifier, VerificationResult

logger = logging.getLogger(__name__)


class TestStatus(Enum):
    """Test execution status."""

    NOT_RUN = "NOT_RUN"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


@dataclass
class TestStep:
    """Represents a single step within a talent test."""

    name: str
    description: str = ""
    status: TestStatus = TestStatus.NOT_RUN
    duration: float = 0.0
    screenshot_path: str = ""
    error_message: str = ""
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "duration": round(self.duration, 2),
            "screenshot_path": self.screenshot_path,
            "error_message": self.error_message,
            "timestamp": self.timestamp,
        }


@dataclass
class TestResult:
    """Complete result of a talent test execution."""

    talent_name: str
    package_name: str
    status: TestStatus = TestStatus.NOT_RUN
    start_time: str = ""
    end_time: str = ""
    duration: float = 0.0
    steps: List[TestStep] = field(default_factory=list)
    verifications: List[VerificationResult] = field(default_factory=list)
    screenshots: List[str] = field(default_factory=list)
    logcat_excerpt: str = ""
    error_message: str = ""
    device_info: dict = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status == TestStatus.PASSED

    @property
    def step_summary(self) -> str:
        total = len(self.steps)
        passed = sum(1 for s in self.steps if s.status == TestStatus.PASSED)
        failed = sum(1 for s in self.steps if s.status == TestStatus.FAILED)
        return f"{passed}/{total} passed, {failed} failed"

    def to_dict(self) -> dict:
        return {
            "talent_name": self.talent_name,
            "package_name": self.package_name,
            "status": self.status.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": round(self.duration, 2),
            "steps": [s.to_dict() for s in self.steps],
            "verifications": [v.to_dict() for v in self.verifications],
            "screenshots": self.screenshots,
            "logcat_excerpt": self.logcat_excerpt,
            "error_message": self.error_message,
            "step_summary": self.step_summary,
            "device_info": self.device_info,
        }


class BaseTalentTest(ABC):
    """
    Abstract base class for Miko3 talent test automation.

    Implements the Template Method pattern with a fixed lifecycle:
        setup() → execute() → verify() → teardown()

    Subclasses must implement:
        - execute(): The actual test steps
        - verify(): Verification assertions

    Optionally override:
        - setup(): Additional pre-test preparation
        - teardown(): Additional cleanup

    Usage:
        class MyTalentTest(BaseTalentTest):
            def execute(self):
                self.step("Launch app")
                self.adb.tap(500, 300)

            def verify(self):
                self.verify_activity("com.miko.myapp")

        test = MyTalentTest(adb, config, "MyTalent", "com.miko.myapp")
        result = test.run()
    """

    def __init__(
        self,
        adb: ADBClient,
        config: dict,
        talent_name: str,
        package_name: str,
        activity_name: str = "",
        screenshot_dir: str = "reports/screenshots",
        checkpoint_name: Optional[str] = None,
        enable_checkpoints: bool = True,
    ):
        """
        Initialize base talent test.

        Args:
            adb: Connected ADBClient.
            config: Full config dict (from config.yaml).
            talent_name: Human-readable name of the talent.
            package_name: Android package name.
            activity_name: Main activity name (auto-discovered if empty).
            screenshot_dir: Directory to save screenshots.
            checkpoint_name: Name for checkpoint file (defaults to talent_name).
            enable_checkpoints: Whether to enable checkpoint saving.
        """
        self.adb = adb
        self.config = config
        self.talent_name = talent_name
        self.package_name = package_name
        self.activity_name = activity_name
        self.screenshot_dir = screenshot_dir
        self.discovery = TalentDiscovery(adb)
        self.verifier = Verifier(adb, config)

        # Checkpoint support
        self._checkpoint_enabled = enable_checkpoints
        self._checkpoint_name = checkpoint_name or talent_name
        self._checkpoint_mgr = CheckpointManager() if enable_checkpoints else None

        # Test state
        self.result = TestResult(
            talent_name=talent_name,
            package_name=package_name,
        )
        self._current_step: Optional[TestStep] = None
        self._step_count = 0

    def run(self) -> TestResult:
        """
        Execute the full test lifecycle.

        Returns:
            TestResult with all collected data.
        """
        self.result.start_time = datetime.now().isoformat()
        self.result.status = TestStatus.RUNNING
        start = time.time()

        try:
            # Collect device info
            self.result.device_info = self.adb.get_device_properties()

            # Clear logcat for clean capture
            self.adb.clear_logcat()

            logger.info("=" * 60)
            logger.info("STARTING TEST: %s (%s)", self.talent_name, self.package_name)
            logger.info("=" * 60)

            # Phase 1: Setup
            self._run_phase("Setup", self.setup)

            # Phase 2: Execute
            self._run_phase("Execute", self.execute)

            # Phase 3: Verify
            self._run_phase("Verify", self.verify)

            # Determine overall result
            failed_steps = [
                s for s in self.result.steps if s.status == TestStatus.FAILED
            ]
            failed_verifications = [
                v for v in self.result.verifications if not v.passed
            ]

            if failed_steps or failed_verifications:
                self.result.status = TestStatus.FAILED
                failures = [s.name for s in failed_steps] + [
                    v.check_name for v in failed_verifications
                ]
                self.result.error_message = f"Failed checks: {', '.join(failures)}"
            else:
                self.result.status = TestStatus.PASSED

        except Exception as e:
            self.result.status = TestStatus.ERROR
            self.result.error_message = str(e)
            logger.error("TEST ERROR: %s - %s", self.talent_name, e)
            self._capture_error_evidence()

        finally:
            # Phase 4: Teardown (always runs)
            try:
                self.teardown()
            except Exception as e:
                logger.warning("Teardown error: %s", e)

            # Capture final logcat
            try:
                self.result.logcat_excerpt = self.adb.get_logcat(
                    lines=self.config.get("verification", {}).get(
                        "logcat_buffer_size", 200
                    )
                )
            except ADBError:
                pass

            self.result.end_time = datetime.now().isoformat()
            self.result.duration = time.time() - start

            logger.info("=" * 60)
            logger.info(
                "TEST %s: %s (%.1fs) — %s",
                self.result.status.value,
                self.talent_name,
                self.result.duration,
                self.result.step_summary,
            )
            logger.info("=" * 60)

        return self.result

    def _run_phase(self, phase_name: str, method):
        """Run a test phase with error capture."""
        logger.info("--- %s Phase ---", phase_name)
        try:
            method()
        except Exception as e:
            if self._current_step:
                self._current_step.status = TestStatus.FAILED
                self._current_step.error_message = str(e)
            raise

    # -------------------------------------------------------------------------
    # Step Management
    # -------------------------------------------------------------------------

    def step(self, name: str, description: str = "") -> TestStep:
        """
        Start a new test step. Automatically closes the previous step.

        Args:
            name: Step name.
            description: Step description.

        Returns:
            The new TestStep.
        """
        # Close previous step
        if self._current_step and self._current_step.status == TestStatus.RUNNING:
            self._current_step.status = TestStatus.PASSED
            self._current_step.duration = time.time() - self._step_start

        self._step_count += 1
        self._current_step = TestStep(
            name=f"Step {self._step_count}: {name}",
            description=description,
            status=TestStatus.RUNNING,
            timestamp=datetime.now().isoformat(),
        )
        self._step_start = time.time()
        self.result.steps.append(self._current_step)
        logger.info("  [Step %d] %s", self._step_count, name)
        return self._current_step

    def pass_step(self, message: str = "") -> None:
        """Mark the current step as passed and save checkpoint."""
        if self._current_step:
            self._current_step.status = TestStatus.PASSED
            self._current_step.duration = time.time() - self._step_start
            if message:
                self._current_step.description += f" — {message}"

        # Save checkpoint after each successful step
        self.save_checkpoint()

    def fail_step(self, message: str) -> None:
        """Mark the current step as failed."""
        if self._current_step:
            self._current_step.status = TestStatus.FAILED
            self._current_step.error_message = message
            self._current_step.duration = time.time() - self._step_start
            logger.warning("  [FAIL] %s: %s", self._current_step.name, message)

    def take_screenshot(self, name: str = "") -> str:
        """
        Capture a screenshot during the test.

        Args:
            name: Screenshot label.

        Returns:
            Path to saved screenshot.
        """
        os.makedirs(self.screenshot_dir, exist_ok=True)
        filename = f"{self.talent_name}_{self._step_count}_{name or 'screen'}_{int(time.time())}.png"
        filepath = os.path.join(self.screenshot_dir, filename)
        try:
            self.adb.screenshot(filepath)
            self.result.screenshots.append(filepath)
            if self._current_step:
                self._current_step.screenshot_path = filepath
            return filepath
        except ADBError as e:
            logger.warning("Screenshot failed: %s", e)
            return ""

    def wait(self, seconds: float, reason: str = "") -> None:
        """Wait with logging."""
        if reason:
            logger.debug("  Waiting %.1fs: %s", seconds, reason)
        time.sleep(seconds)

    # -------------------------------------------------------------------------
    # UI Interaction Helpers
    # -------------------------------------------------------------------------

    def tap_text(self, text: str, exact: bool = False) -> bool:
        """
        Find an element by text and tap it.

        Args:
            text: Text label to tap.
            exact: Whether to match exactly.
        """
        logger.info("  Tapping UI element with text: '%s'", text)
        return self.adb.tap_text(text, exact)

    def wait_for_text(
        self, text: str, timeout: int = 20, poll_interval: float = 2.0
    ) -> bool:
        """
        Wait for specific text to appear on the screen.
        """
        logger.info("  Waiting for UI text: '%s'...", text)
        start = time.time()
        while time.time() - start < timeout:
            elements = self.adb.find_elements_by_text(text)
            if elements:
                logger.info("  Text found: '%s'", elements[0]["text"])
                return True
            time.sleep(poll_interval)
        logger.warning("  Timed out waiting for text: '%s'", text)
        return False

    def find_text(self, text: str) -> List[dict]:
        """Find elements by text."""
        return self.adb.find_elements_by_text(text)

    # -------------------------------------------------------------------------
    # Convenience Verification Helpers
    # -------------------------------------------------------------------------

    def verify_activity(self, expected_package: str) -> VerificationResult:
        """Verify the expected package is in the foreground."""
        result = self.verifier.assert_activity(expected_package)
        self.result.verifications.append(result)
        return result

    def verify_no_crash(self) -> VerificationResult:
        """Verify no crashes in logcat."""
        result = self.verifier.assert_no_crash(self.package_name)
        self.result.verifications.append(result)
        return result

    def verify_screen_changed(
        self, before_path: str, after_path: str
    ) -> VerificationResult:
        """Verify the screen content changed between two screenshots."""
        result = self.verifier.assert_screen_changed(before_path, after_path)
        self.result.verifications.append(result)
        return result

    # -------------------------------------------------------------------------
    # Lifecycle Methods
    # -------------------------------------------------------------------------

    def setup(self) -> None:
        """
        Pre-test setup. Performs screen management and talent launch.

        Hybrid approach:
        1. Navigate to Apps drawer (text-based)
        2. Navigate to appropriate category tab (text-based)
        3. Launch talent directly via package name (am start)
        """
        # --- Screen Management ---
        self.step("Screen management", "Ensuring device is awake and ready")
        try:
            # Wake screen
            self.adb.wake_screen()

            # Unlock screen
            self.adb.unlock_screen()

            # Set brightness
            brightness = self.config.get("device", {}).get("brightness", 255)
            self.adb.set_screen_brightness(brightness)

            # Set stay awake
            stay_awake = self.config.get("device", {}).get("stay_awake", True)
            self.adb.set_stay_awake(stay_awake)

            self.pass_step("Device screen is awake and ready")
        except ADBError as e:
            logger.warning("Screen management failed: %s", e)
            self.fail_step(f"Screen management failed: {e}")
            # Continue anyway as some devices might not support all commands

        # --- Navigate to Home and Apps ---
        self.step("Navigate to Home", "Going to home screen")
        self.adb.shell("input keyevent 3")
        self.wait(2, "Waiting for Home screen")
        self.pass_step()

        # Step 1: Open Apps drawer - try multiple text variations
        self.step("Open Apps Drawer", "Tapping Apps button")

        # Debug: dump UI to see what's available
        logger.info("Dumping UI hierarchy to find Apps button...")
        ui_elements = self.find_text("App")
        if ui_elements:
            logger.info(f"Found elements with 'App': {len(ui_elements)}")
            for elem in ui_elements[:3]:
                logger.info(f"  - {elem}")

        # Try multiple variations of Apps button text
        apps_tap_success = False
        for apps_text in ["Apps", "App", "applications"]:
            if self.tap_text(apps_text):
                logger.info(f"Found and tapped '{apps_text}' button")
                apps_tap_success = True
                break

        if not apps_tap_success:
            # Last resort: try swiping up to open apps drawer
            logger.warning("Could not find Apps button, trying swipe gesture")
            self.adb.swipe(640, 700, 640, 200, 500)
            self.wait(2, "Waiting for Apps drawer")

            # Check again if Apps drawer is open
            if self.find_text("Search") or self.find_text("Apps"):
                apps_tap_success = True

        if not apps_tap_success:
            self.fail_step("Cannot find Apps button")
            return

        self.wait(3, "Waiting for Apps drawer")
        self.pass_step()

        # Step 2: Determine which tab based on talent category
        self.step("Navigate to talent category", "Determining appropriate tab")

        # Map talent to category tab based on package name
        talent_category = self._get_talent_category(self.package_name)

        # Try multiple variations for category tabs
        category_tap_success = False
        category_options = {
            "Video": ["Video", "Videos"],
            "Stories": ["Stories", "Story", "Kids"],
            "Games": ["Games", "Game", "Play"],
        }

        options = category_options.get(talent_category, [talent_category])

        for category_text in options:
            if self.tap_text(category_text):
                logger.info(f"Found and tapped '{category_text}' tab")
                category_tap_success = True
                break

        if not category_tap_success:
            logger.warning(
                f"Could not find {talent_category} tab, proceeding with direct launch"
            )

        self.wait(2, "Waiting for category tab to load")
        self.pass_step()

        # --- Launch Talent via Package Name ---
        self.step("Force stop talent", "Clean state before test")
        self.discovery.force_stop(self.package_name)
        self.wait(1, "Waiting after force stop")
        self.pass_step()

        self.step("Launch talent", f"Starting {self.package_name} via am start")
        success = self.discovery.launch_talent(self.package_name, self.activity_name)
        if not success:
            self.fail_step(f"Failed to launch {self.package_name}")
            raise ADBError(f"Could not launch talent: {self.package_name}")
        self.wait(2, "Waiting for talent to fully load")
        self.take_screenshot("after_launch")

        # Verify correct app launched
        self.step("Verify launch", f"Confirming {self.package_name} is in foreground")
        verified = self._verify_activity(self.package_name)
        if not verified:
            logger.warning(f"Warning: {self.package_name} may not be in foreground")
        self.pass_step("Talent launched successfully")

    def _get_talent_category(self, package_name: str) -> str:
        """Determine which category tab to navigate to based on package name."""
        package_lower = package_name.lower()

        # Map packages to their category tabs
        if (
            "video" in package_lower
            or "vooks" in package_lower
            or "mikoji" in package_lower
        ):
            return "Video"
        elif "story" in package_lower:
            return "Stories"
        elif "adventure" in package_lower:
            return "Stories"
        elif "game" in package_lower:
            return "Games"
        else:
            # Default to Video tab for unknown packages
            return "Video"

    def _verify_activity(self, expected_package: str, max_wait: int = 10) -> bool:
        """Verify the expected package is in foreground."""
        for _ in range(max_wait):
            current = self.adb.get_current_activity()
            if expected_package.lower() in current.lower():
                return True
            time.sleep(1)
        return False

    @abstractmethod
    def execute(self) -> None:
        """
        Execute the test steps. Must be implemented by subclasses.

        Use self.step() to define steps, self.adb for device interaction,
        and self.take_screenshot() for evidence capture.
        """
        pass

    @abstractmethod
    def verify(self) -> None:
        """
        Run verification assertions. Must be implemented by subclasses.

        Use self.verify_activity(), self.verify_no_crash(), etc.
        """
        pass

    def teardown(self) -> None:
        """
        Post-test cleanup. Override to add custom teardown steps.

        Default: Force-stop the talent and go home.
        """
        # Close previous step if still running
        if self._current_step and self._current_step.status == TestStatus.RUNNING:
            self._current_step.status = TestStatus.PASSED
            self._current_step.duration = time.time() - self._step_start

        try:
            self.discovery.force_stop(self.package_name)
        except ADBError:
            pass

        try:
            self.adb.press_home()
        except ADBError:
            pass

        # Optionally disable stay awake (commented out to keep it on for now)
        # try:
        #     self.adb.set_stay_awake(False)
        # except ADBError:
        #     pass

        logger.info("Teardown complete for %s", self.talent_name)

    # -------------------------------------------------------------------------
    # Checkpoint / Resume Support
    # -------------------------------------------------------------------------

    def save_checkpoint(self, additional_state: Optional[dict] = None) -> None:
        """
        Save current test progress to checkpoint.

        Args:
            additional_state: Additional state data to save.
        """
        if not self._checkpoint_enabled or not self._checkpoint_mgr:
            return

        state = {
            "current_step": self._step_count,
            "step_name": self._current_step.name if self._current_step else "unknown",
            "package_name": self.package_name,
            "activity_name": self.activity_name,
        }

        if additional_state:
            state.update(additional_state)

        try:
            self._checkpoint_mgr.save_checkpoint(self._checkpoint_name, state)
            logger.debug("Checkpoint saved at step %d", self._step_count)
        except Exception as e:
            logger.warning("Failed to save checkpoint: %s", e)

    def load_checkpoint(self) -> Optional[dict]:
        """
        Load saved checkpoint if exists.

        Returns:
            Checkpoint data dict, or None if no checkpoint exists.
        """
        if not self._checkpoint_enabled or not self._checkpoint_mgr:
            return None
        return self._checkpoint_mgr.load_checkpoint(self._checkpoint_name)

    def has_checkpoint(self) -> bool:
        """Check if checkpoint exists for this test."""
        if not self._checkpoint_enabled or not self._checkpoint_mgr:
            return False
        return self._checkpoint_mgr.has_checkpoint(self._checkpoint_name)

    def clear_checkpoint(self) -> None:
        """Clear checkpoint after successful completion."""
        if self._checkpoint_enabled and self._checkpoint_mgr:
            self._checkpoint_mgr.clear_checkpoint(self._checkpoint_name)

    def resume_from_checkpoint(self, checkpoint_data: dict) -> int:
        """
        Resume test from checkpoint.

        Args:
            checkpoint_data: Loaded checkpoint data.

        Returns:
            Step number to resume from.
        """
        state = checkpoint_data.get("state", {})
        resume_step = state.get("current_step", 0)

        logger.info("Resuming %s from step %d", self._checkpoint_name, resume_step)

        # Update activity name if saved
        if state.get("activity_name"):
            self.activity_name = state.get("activity_name")

        return resume_step

    def _capture_error_evidence(self) -> None:
        """Capture screenshots and logs when an error occurs."""
        try:
            self.take_screenshot("error")
        except Exception:
            pass
