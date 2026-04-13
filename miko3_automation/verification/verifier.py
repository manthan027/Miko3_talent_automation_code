"""
Verification Engine
===================
Provides assertion methods for validating Miko3 talent test outcomes.
Supports activity checks, screenshot diffs, crash detection, and log analysis.
"""

import os
import logging
import time
from dataclasses import dataclass
from typing import List, Optional

from ..core.adb_utils import ADBClient, ADBError

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    """Result of a single verification check."""
    check_name: str
    passed: bool
    message: str
    evidence_path: str = ""
    details: str = ""

    def to_dict(self) -> dict:
        return {
            "check_name": self.check_name,
            "passed": self.passed,
            "message": self.message,
            "evidence_path": self.evidence_path,
            "details": self.details,
        }


class Verifier:
    """
    Verification engine for Miko3 talent testing.

    Provides assertion-style methods that return VerificationResult objects
    instead of raising exceptions, allowing tests to continue and collect
    all results.

    Methods:
        - assert_activity: Check foreground activity
        - assert_screen_changed: Pixel diff between screenshots
        - assert_package_running: Check if process is alive
        - assert_no_crash: Search logcat for crash patterns
        - assert_log_contains: Search logcat for expected patterns
        - capture_evidence: Collect screenshot + logcat snapshot
    """

    def __init__(self, adb: ADBClient, config: dict):
        """
        Initialize verifier.

        Args:
            adb: Connected ADBClient.
            config: Verification config section from config.yaml.
        """
        self.adb = adb
        verify_cfg = config.get("verification", {})
        self.screenshot_dir = verify_cfg.get("screenshot_dir", "reports/screenshots")
        self.diff_threshold = verify_cfg.get("screenshot_diff_threshold", 0.05)
        self.logcat_lines = verify_cfg.get("logcat_buffer_size", 4096)
        self.crash_patterns = verify_cfg.get("crash_patterns", [
            "FATAL EXCEPTION",
            "ANR in",
            "has died",
            "Force finishing activity",
        ])
        self.success_patterns = verify_cfg.get("success_patterns", [
            "Activity resumed",
            "Displayed",
        ])

    def assert_activity(self, expected_package: str) -> VerificationResult:
        """
        Verify the expected package is in the foreground.

        Args:
            expected_package: Package name substring to match.

        Returns:
            VerificationResult.

        Commands:
            Windows & Linux:
              adb shell dumpsys activity activities | grep mResumedActivity
        """
        try:
            current = self.adb.get_current_activity()
            if expected_package.lower() in current.lower():
                return VerificationResult(
                    check_name="Activity Check",
                    passed=True,
                    message=f"Expected package '{expected_package}' is in foreground: {current}",
                )
            else:
                return VerificationResult(
                    check_name="Activity Check",
                    passed=False,
                    message=f"Expected '{expected_package}' but found: {current}",
                    details=f"Current activity: {current}",
                )
        except ADBError as e:
            return VerificationResult(
                check_name="Activity Check",
                passed=False,
                message=f"Could not check activity: {e}",
            )

    def assert_screen_changed(
        self,
        before_path: str,
        after_path: str,
        threshold: Optional[float] = None,
    ) -> VerificationResult:
        """
        Verify the screen content changed between two screenshots.

        Uses pixel-level comparison. If Pillow is not available,
        falls back to file size comparison.

        Args:
            before_path: Path to the "before" screenshot.
            after_path: Path to the "after" screenshot.
            threshold: Minimum pixel difference ratio (default from config).

        Returns:
            VerificationResult.
        """
        effective_threshold = threshold or self.diff_threshold

        if not os.path.exists(before_path) or not os.path.exists(after_path):
            return VerificationResult(
                check_name="Screen Change",
                passed=False,
                message="Screenshot file(s) not found",
                details=f"Before: {before_path}, After: {after_path}",
            )

        try:
            # Try Pillow-based comparison
            from PIL import Image
            import math

            img1 = Image.open(before_path).convert("RGB")
            img2 = Image.open(after_path).convert("RGB")

            if img1.size != img2.size:
                return VerificationResult(
                    check_name="Screen Change",
                    passed=True,
                    message="Screenshots have different dimensions (screen changed)",
                    details=f"Before: {img1.size}, After: {img2.size}",
                )

            # Calculate pixel difference
            pixels1 = list(img1.getdata())
            pixels2 = list(img2.getdata())
            total_pixels = len(pixels1)
            diff_count = 0

            for p1, p2 in zip(pixels1, pixels2):
                # Calculate color distance
                distance = math.sqrt(
                    sum((c1 - c2) ** 2 for c1, c2 in zip(p1, p2))
                )
                if distance > 30:  # Threshold for "different" pixel
                    diff_count += 1

            diff_ratio = diff_count / total_pixels if total_pixels > 0 else 0

            if diff_ratio >= effective_threshold:
                return VerificationResult(
                    check_name="Screen Change",
                    passed=True,
                    message=f"Screen changed: {diff_ratio:.1%} pixels different (threshold: {effective_threshold:.1%})",
                    details=f"Changed pixels: {diff_count}/{total_pixels}",
                )
            else:
                return VerificationResult(
                    check_name="Screen Change",
                    passed=False,
                    message=f"Screen barely changed: {diff_ratio:.1%} pixels different (threshold: {effective_threshold:.1%})",
                    details=f"Changed pixels: {diff_count}/{total_pixels}",
                )

        except ImportError:
            # Fallback: file size comparison
            size1 = os.path.getsize(before_path)
            size2 = os.path.getsize(after_path)
            size_diff = abs(size1 - size2) / max(size1, size2, 1)

            if size_diff > 0.01:  # 1% file size change
                return VerificationResult(
                    check_name="Screen Change",
                    passed=True,
                    message=f"Screen likely changed (file size diff: {size_diff:.1%})",
                    details="Pillow not available; used file size comparison",
                )
            else:
                return VerificationResult(
                    check_name="Screen Change",
                    passed=False,
                    message=f"Screen may not have changed (file size diff: {size_diff:.1%})",
                    details="Pillow not available; used file size comparison",
                )

    def assert_package_running(self, package: str) -> VerificationResult:
        """
        Verify a package's process is running.

        Args:
            package: Package name.

        Commands:
            Windows & Linux: adb shell pidof <package>
        """
        try:
            is_running = self.adb.is_package_running(package)
            if is_running:
                return VerificationResult(
                    check_name="Process Running",
                    passed=True,
                    message=f"Package '{package}' is running",
                )
            else:
                return VerificationResult(
                    check_name="Process Running",
                    passed=False,
                    message=f"Package '{package}' is NOT running",
                )
        except ADBError as e:
            return VerificationResult(
                check_name="Process Running",
                passed=False,
                message=f"Could not check process: {e}",
            )

    def assert_no_crash(self, package: str = "") -> VerificationResult:
        """
        Verify no crashes or ANRs in logcat.

        Args:
            package: Optional package name to filter logcat.

        Commands:
            Windows & Linux: adb shell logcat -d -t <lines>
        """
        try:
            logcat_output = self.adb.get_logcat(lines=self.logcat_lines)
            found_crashes = []

            for pattern in self.crash_patterns:
                if pattern.lower() in logcat_output.lower():
                    # Find the actual matching lines
                    for line in logcat_output.splitlines():
                        if pattern.lower() in line.lower():
                            if not package or package.lower() in line.lower():
                                found_crashes.append(line.strip()[:200])

            if found_crashes:
                return VerificationResult(
                    check_name="Crash Detection",
                    passed=False,
                    message=f"Found {len(found_crashes)} crash indicator(s) in logcat",
                    details="\n".join(found_crashes[:10]),
                )
            else:
                return VerificationResult(
                    check_name="Crash Detection",
                    passed=True,
                    message="No crashes or ANRs detected in logcat",
                )

        except ADBError as e:
            return VerificationResult(
                check_name="Crash Detection",
                passed=False,
                message=f"Could not read logcat: {e}",
            )

    def assert_log_contains(
        self, pattern: str, lines: int = 500
    ) -> VerificationResult:
        """
        Verify logcat contains a specific pattern.

        Args:
            pattern: Text pattern to search for.
            lines: Number of logcat lines to search.

        Returns:
            VerificationResult.
        """
        try:
            logcat_output = self.adb.get_logcat(lines=lines)
            matching_lines = [
                line.strip()
                for line in logcat_output.splitlines()
                if pattern.lower() in line.lower()
            ]

            if matching_lines:
                return VerificationResult(
                    check_name=f"Log Contains '{pattern}'",
                    passed=True,
                    message=f"Found {len(matching_lines)} matching log entries",
                    details="\n".join(matching_lines[:5]),
                )
            else:
                return VerificationResult(
                    check_name=f"Log Contains '{pattern}'",
                    passed=False,
                    message=f"Pattern '{pattern}' not found in last {lines} logcat lines",
                )

        except ADBError as e:
            return VerificationResult(
                check_name=f"Log Contains '{pattern}'",
                passed=False,
                message=f"Could not read logcat: {e}",
            )

    def capture_evidence(
        self, test_name: str, screenshot_dir: str = ""
    ) -> dict:
        """
        Capture a complete evidence snapshot (screenshot + logcat).

        Args:
            test_name: Name for labeling the evidence files.
            screenshot_dir: Override screenshot directory.

        Returns:
            Dict with paths to evidence files.
        """
        evidence = {}
        save_dir = screenshot_dir or self.screenshot_dir
        os.makedirs(save_dir, exist_ok=True)

        # Screenshot
        try:
            ss_path = os.path.join(
                save_dir, f"evidence_{test_name}_{int(time.time())}.png"
            )
            self.adb.screenshot(ss_path)
            evidence["screenshot"] = ss_path
        except ADBError as e:
            evidence["screenshot"] = f"Failed: {e}"
            logger.warning("Evidence screenshot failed: %s", e)

        # Logcat
        try:
            logcat = self.adb.get_logcat(lines=self.logcat_lines)
            log_path = os.path.join(
                save_dir, f"evidence_{test_name}_{int(time.time())}.log"
            )
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(logcat)
            evidence["logcat"] = log_path
        except (ADBError, IOError) as e:
            evidence["logcat"] = f"Failed: {e}"
            logger.warning("Evidence logcat failed: %s", e)

        return evidence

    def verify_splash_screen(
        self,
        talent_name: str,
        screenshot_path: str,
        comparison_method: str = "auto",
    ) -> VerificationResult:
        """
        Verify a talent's splash screen against reference template.

        Uses OpenCV for visual comparison. Supports template matching and SSIM.

        Args:
            talent_name: Name of the talent (e.g., "adventure_book").
            screenshot_path: Path to captured screenshot.
            comparison_method: "template", "ssim", or "auto" (auto-selects best).

        Returns:
            VerificationResult indicating if splash screen matches reference.

        Notes:
            - Requires reference template at templates/splash_screens/{talent_name}_splash.png
            - Auto method tries SSIM first (more robust), falls back to template matching
        """
        try:
            from .splash_screen_verifier import SplashScreenVerifier

            verifier = SplashScreenVerifier()
            result = verifier.verify_talent_splash(talent_name, screenshot_path)

            return VerificationResult(
                check_name=f"Splash Screen: {talent_name}",
                passed=result.passed,
                message=result.message,
                evidence_path=result.evidence_path or result.capture_path,
                details=f"Method: {result.method} | Score: {result.similarity_score:.1%} ({result.reference_path})",
            )

        except ImportError as e:
            logger.error(f"OpenCV dependencies not available: {e}")
            return VerificationResult(
                check_name=f"Splash Screen: {talent_name}",
                passed=False,
                message="OpenCV dependencies not installed. Run: pip install opencv-python scikit-image",
                details=str(e),
            )
        except Exception as e:
            logger.error(f"Splash screen verification error: {e}")
            return VerificationResult(
                check_name=f"Splash Screen: {talent_name}",
                passed=False,
                message=f"Splash screen verification failed: {str(e)}",
                details=f"Screenshot: {screenshot_path}",
            )
