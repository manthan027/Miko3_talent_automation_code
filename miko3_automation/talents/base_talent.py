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
from ..core.audio_utils import AudioUtils
from ..core.tts_utils import TextToSpeech
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

        # Audio and TTS support
        self.audio = AudioUtils(adb)
        self.tts = TextToSpeech(output_dir="audio")

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

    def verify_splash_screen(
        self, talent_name: Optional[str] = None, screenshot_path: Optional[str] = None
    ) -> VerificationResult:
        """
        Verify a talent's splash screen against reference template.

        Uses OpenCV for visual comparison.

        Args:
            talent_name: Name of the talent (defaults to self.talent_name).
            screenshot_path: Path to screenshot (defaults to last captured screenshot).

        Returns:
            VerificationResult indicating if splash screen matches reference.

        Usage:
            self.take_screenshot("splash")
            result = self.verify_splash_screen()
        """
        effective_talent = talent_name or self.talent_name
        if not screenshot_path:
            # Use the last captured screenshot
            if self.result.screenshots:
                screenshot_path = self.result.screenshots[-1]
            else:
                result = VerificationResult(
                    check_name=f"Splash Screen: {effective_talent}",
                    passed=False,
                    message="No screenshot captured for splash screen verification",
                )
                self.result.verifications.append(result)
                return result

        result = self.verifier.verify_splash_screen(effective_talent, screenshot_path)
        self.result.verifications.append(result)
        return result

    # -------------------------------------------------------------------------
    # Audio and Text-to-Speech Helpers
    # -------------------------------------------------------------------------

    def generate_speech(
        self,
        text: str,
        filename: str = "speech.wav",
        provider: str = "edge",
        **kwargs
    ) -> Optional[str]:
        """
        Generate speech audio from text using TTS.

        Args:
            text: Text to convert to speech.
            filename: Output filename.
            provider: "edge" (recommended) or "google".
            **kwargs: Provider-specific options (voice, language, rate).

        Returns:
            Local path to generated audio file.

        Usage:
            # Generate with Edge TTS (default, better quality)
            audio = self.generate_speech("Welcome to the adventure")
            
            # Generate with specific voice
            audio = self.generate_speech(
                "Let's create a story",
                voice="en-US-GuyNeural"  # Male voice
            )
            
            # Generate with Google TTS
            audio = self.generate_speech(
                "Hello world",
                provider="google"
            )
        """
        logger.info(f"Generating speech: '{text[:50]}...'")
        return self.tts.convert(text, filename, provider, **kwargs)

    def play_speech(
        self,
        text: Optional[str] = None,
        audio_file: Optional[str] = None,
        wait_seconds: float = 5.0,
        provider: str = "edge",
    ) -> bool:
        """
        Generate speech and play it on device (or play existing audio).

        Args:
            text: Text to generate speech from (if audio_file not provided).
            audio_file: Path to existing audio file (skip TTS).
            wait_seconds: How long to wait for audio playback.
            provider: TTS provider ("edge" or "google").

        Returns:
            True if audio was played successfully.

        Usage:
            # Convert text to speech and play
            self.play_speech("Start creating your story")
            
            # Play existing audio file
            self.play_speech(audio_file="audio/intro.wav")
        """
        audio_path = audio_file

        # Generate audio from text if not provided
        if not audio_path:
            if not text:
                logger.error("Either text or audio_file must be provided")
                return False
            audio_path = self.generate_speech(text, provider=provider)

        if not audio_path:
            logger.warning("No audio file to play")
            return False

        # We play audio LOCALLY on the host PC instead of on Miko.
        # Edge TTS generates MP3 files. We use a headless VBScript with WMPlayer 
        # to cleanly play it without popping up any UI windows.
        try:
            import os
            import subprocess
            import time
            
            audio_path = os.path.abspath(audio_path)
            logger.info(f"🔊 Playing audio locally on HOST PC to Miko: {audio_path}")
            
            vbs_script = f'''
Set wmp = CreateObject("WMPlayer.OCX")
wmp.URL = "{audio_path}"
wmp.controls.play
WScript.Sleep 500
While wmp.playState = 3
    WScript.Sleep 100
Wend
'''
            vbs_path = os.path.join(os.path.dirname(audio_path), "temp_play.vbs")
            with open(vbs_path, "w") as f:
                f.write(vbs_script)
                
            # Play the audio using cscript (blocks until playback finishes)
            subprocess.call(["cscript", "//nologo", vbs_path])
            
            # Cleanup
            if os.path.exists(vbs_path):
                os.remove(vbs_path)
                
            # Wait additional buffer if requested
            if wait_seconds > 0:
                time.sleep(wait_seconds)
                
            return True
        except Exception as e:
            logger.error(f"Failed to play audio locally via VBS: {e}")
            return False

    def play_audio_file(self, audio_path: str, wait_seconds: float = 5.0) -> bool:
        """
        Play an existing audio file on device.

        Args:
            audio_path: Local path to audio file.
            wait_seconds: How long to wait for playback.

        Returns:
            True if successful.

        Usage:
            self.play_audio_file("audio/adventure_intro.wav", wait_seconds=3)
        """
        return self.play_speech(audio_file=audio_path, wait_seconds=wait_seconds)

    def record_device_audio(
        self, output_filename: str = "recording.wav", duration_seconds: int = 5
    ) -> Optional[str]:
        """
        Record audio from device microphone.

        Args:
            output_filename: Name for the recording.
            duration_seconds: How long to record.

        Returns:
            Device path to recording if successful.

        Usage:
            device_path = self.record_device_audio(duration_seconds=3)
        """
        logger.info(f"Recording audio for {duration_seconds}s")
        return self.audio.record_audio(output_filename, duration_seconds)

    def batch_generate_speech(self, texts: dict, provider: str = "edge") -> dict:
        """
        Generate speech audio for multiple texts at once.

        Args:
            texts: Dict of {name: text} pairs.
            provider: TTS provider to use.

        Returns:
            Dict of {name: audio_path}.

        Usage:
            audio_files = self.batch_generate_speech({
                "greeting": "Welcome to the adventure",
                "start": "Tap the button to begin",
                "complete": "Great job! Story created!"
            })
            # audio_files = {
            #   "greeting": "audio/greeting.wav",
            #   "start": "audio/start.wav",
            #   "complete": "audio/complete.wav"
            # }
        """
        logger.info(f"Batch generating {len(texts)} audio files")
        return self.tts.batch_convert(texts, provider)

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

        # Get launch configuration early to determine navigation strategy
        talent_cfg = self.config.get("talents", {})
        launch_config = {}
        for key, cfg in talent_cfg.items():
            if cfg.get("package", "").lower() == self.package_name.lower():
                launch_config = cfg
                break
        
        launch_method = launch_config.get("launch_method", "am_start")

        # Step 1: Open Apps drawer
        self.step("Open Apps Drawer", "Ensuring apps drawer is visible")
        
        # If click-based with pre-clicks, perform them now to satisfy the mandatory "Apps" step
        if launch_method == "click" and launch_config.get("pre_clicks"):
            logger.info("Using coordinate-based navigation for Apps drawer")
            pre_clicks = launch_config["pre_clicks"]
            for idx, (x, y) in enumerate(pre_clicks, 1):
                logger.info("  Tapping pre-click %d: (%d, %d)", idx, x, y)
                self.adb.tap(x, y)
                self.wait(1)
            self.pass_step("Apps drawer opened via coordinates")
        else:
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

            # Step 2: Navigate to category tab (Skip if using click-based launching)
            self.step("Navigate to talent category", "Switching to appropriate category")
            
            talent_category = self._get_talent_category(self.package_name)
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
                    f"Could not find {talent_category} tab, proceeding anyway"
                )

            self.wait(2, "Waiting for category tab to load")
            self.pass_step()

        # --- Launch Talent via Package Name ---
        self.step("Force stop talent", "Clean state before test")
        self.discovery.force_stop(self.package_name)
        self.wait(1, "Waiting after force stop")
        self.pass_step()

        # Get intent extras from config if available
        intent_extras = None
        talent_cfg = self.config.get("talents", {})
        for key, cfg in talent_cfg.items():
            if cfg.get("package", "").lower() == self.package_name.lower():
                intent_extras = cfg.get("intent_extras")
                break

        self.step("Launch talent", f"Starting {self.package_name}")
        
        # Check if we should use click-based or search-based launching instead
        talent_cfg = self.config.get("talents", {})
        launch_config = {}
        for key, cfg in talent_cfg.items():
            if cfg.get("package", "").lower() == self.package_name.lower():
                launch_config = cfg
                break
        
        launch_method = launch_config.get("launch_method", "am_start")
        
        if launch_method == "search" and launch_config.get("search_enabled"):
            # Use search-based launching: Apps >> Search >> Type >> Click Result
            search_cfg = launch_config.get("search_config", {})
            apps_button = search_cfg.get("apps_button_coordinates")
            search_icon = search_cfg.get("search_icon_coordinates")
            search_text = search_cfg.get("search_text")
            search_result = search_cfg.get("search_result_coordinates")
            
            if apps_button and search_icon and search_text:
                if isinstance(apps_button, (list, tuple)) and len(apps_button) == 2 and \
                   isinstance(search_icon, (list, tuple)) and len(search_icon) == 2:
                    logger.info(f"Using search-based launching: Apps >> Search >> '{search_text}'")
                    success = self.discovery.launch_talent_via_search(
                        self.package_name,
                        tuple(apps_button),
                        tuple(search_icon),
                        search_text,
                        search_result_coords=tuple(search_result) if search_result and isinstance(search_result, (list, tuple)) and len(search_result) == 2 else None,
                        wait_before_apps=0.5,
                        wait_after_apps=1.5,
                        wait_after_type=1.5,
                        wait_after_click=2.0,
                    )
                else:
                    logger.warning(f"Invalid search coordinates, falling back to am_start")
                    success = self.discovery.launch_talent(
                        self.package_name, self.activity_name, extras=intent_extras
                    )
            else:
                logger.warning(f"Missing search_config parameters, falling back to am_start")
                success = self.discovery.launch_talent(
                    self.package_name, self.activity_name, extras=intent_extras
                )
        elif launch_method == "click" and launch_config.get("app_icon_coordinates"):
            # Use click-based launching
            icon_coords = launch_config["app_icon_coordinates"]
            if isinstance(icon_coords, (list, tuple)) and len(icon_coords) == 2:
                logger.info(f"Using click-based launching at {icon_coords}")
                success = self.discovery.launch_talent_by_click(
                    self.package_name,
                    tuple(icon_coords),
                    wait_before=1.0,
                    wait_after=2.0,
                    pre_clicks=None, # Already handled in setup Phase 1
                )
            else:
                logger.warning(f"Invalid app_icon_coordinates: {icon_coords}, falling back to am_start")
                success = self.discovery.launch_talent(
                    self.package_name, self.activity_name, extras=intent_extras
                )
        else:
            # Use am start (default)
            logger.info("Using default am_start launching")
            success = self.discovery.launch_talent(
                self.package_name, self.activity_name, extras=intent_extras
            )
        if not success:
            self.fail_step(f"Failed to launch {self.package_name}")
            raise ADBError(f"Could not launch talent: {self.package_name}")

        if intent_extras:
            logger.info(f"Launched with extras: {intent_extras}")

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
