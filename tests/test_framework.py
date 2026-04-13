"""
Unit Tests for Miko3 Talents Automation Framework
==================================================
Tests framework modules without requiring a physical device.
Uses mocking to simulate ADB responses.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import dataclass

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from miko3_automation.core.adb_utils import ADBClient, ADBError
from miko3_automation.core.device_manager import DeviceManager, DeviceNotFoundError
from miko3_automation.core.talent_discovery import TalentDiscovery, TalentInfo
from miko3_automation.verification.verifier import Verifier, VerificationResult
from miko3_automation.rice_pot.analyzer import RICEPOTAnalyzer, RICEScore
from miko3_automation.reporting.html_report import HTMLReportGenerator
from miko3_automation.talents.base_talent import TestResult, TestStep, TestStatus
from miko3_automation.talents.mikoji_talent import MikojiTalentTest


# ============================================================================
# ADB Utils Tests
# ============================================================================


class TestADBClient(unittest.TestCase):
    """Test ADBClient methods with mocked subprocess."""

    @patch("miko3_automation.core.adb_utils.shutil.which")
    def test_init_validates_adb(self, mock_which):
        """ADBClient should validate ADB binary exists."""
        mock_which.return_value = "/usr/bin/adb"
        client = ADBClient(adb_path="adb")
        self.assertEqual(client.adb_path, "adb")

    @patch("miko3_automation.core.adb_utils.shutil.which")
    def test_init_raises_on_missing_adb(self, mock_which):
        """ADBClient should raise ADBError when ADB is not found."""
        mock_which.return_value = None
        with self.assertRaises(ADBError):
            ADBClient(adb_path="nonexistent_adb_binary")

    @patch("miko3_automation.core.adb_utils.shutil.which")
    def test_build_command_without_serial(self, mock_which):
        """Command builder should work without device serial."""
        mock_which.return_value = "/usr/bin/adb"
        client = ADBClient(adb_path="adb", device_serial="")
        cmd = client._build_command("devices")
        self.assertEqual(cmd, ["adb", "devices"])

    @patch("miko3_automation.core.adb_utils.shutil.which")
    def test_build_command_with_serial(self, mock_which):
        """Command builder should include -s flag when serial is set."""
        mock_which.return_value = "/usr/bin/adb"
        client = ADBClient(adb_path="adb", device_serial="192.168.1.100:5555")
        cmd = client._build_command("shell", "ls")
        self.assertEqual(cmd, ["adb", "-s", "192.168.1.100:5555", "shell", "ls"])

    @patch("miko3_automation.core.adb_utils.shutil.which")
    @patch("miko3_automation.core.adb_utils.subprocess.run")
    def test_execute_success(self, mock_run, mock_which):
        """Successful ADB command execution."""
        mock_which.return_value = "/usr/bin/adb"
        mock_run.return_value = MagicMock(
            returncode=0, stdout="success output", stderr=""
        )
        client = ADBClient(adb_path="adb")
        result = client._execute("devices")
        self.assertEqual(result, "success output")

    @patch("miko3_automation.core.adb_utils.shutil.which")
    @patch("miko3_automation.core.adb_utils.subprocess.run")
    def test_execute_failure_retries(self, mock_run, mock_which):
        """ADB command should retry on failure."""
        mock_which.return_value = "/usr/bin/adb"
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="error: device not found"
        )
        client = ADBClient(adb_path="adb", retry_attempts=2, retry_delay=0)
        with self.assertRaises(ADBError):
            client._execute("shell", "ls")
        self.assertEqual(mock_run.call_count, 2)

    @patch("miko3_automation.core.adb_utils.shutil.which")
    @patch("miko3_automation.core.adb_utils.subprocess.run")
    def test_get_connected_devices(self, mock_run, mock_which):
        """Should parse device list correctly."""
        mock_which.return_value = "/usr/bin/adb"
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="List of devices attached\n192.168.1.100:5555\tdevice\nemulator-5554\toffline\n",
            stderr="",
        )
        client = ADBClient(adb_path="adb")
        devices = client.get_connected_devices()
        self.assertEqual(len(devices), 2)
        self.assertEqual(devices[0]["serial"], "192.168.1.100:5555")
        self.assertEqual(devices[0]["status"], "device")
        self.assertEqual(devices[1]["status"], "offline")


# ============================================================================
# Device Manager Tests
# ============================================================================


class TestDeviceManager(unittest.TestCase):
    """Test DeviceManager with mocked ADBClient."""

    def test_init_from_config(self):
        """DeviceManager should read config correctly."""
        config = {
            "device": {
                "serial": "test-serial",
                "adb_path": "/opt/adb",
                "connection_timeout": 60,
                "command_timeout": 20,
                "retry_attempts": 5,
                "retry_delay": 3,
            }
        }
        dm = DeviceManager(config)
        self.assertEqual(dm.serial, "test-serial")
        self.assertEqual(dm.adb_path, "/opt/adb")
        self.assertEqual(dm.retry_attempts, 5)

    def test_init_with_empty_config(self):
        """DeviceManager should use defaults for missing config."""
        dm = DeviceManager({})
        self.assertEqual(dm.serial, "")
        self.assertEqual(dm.adb_path, "adb")
        self.assertEqual(dm.connection_timeout, 30)


# ============================================================================
# Talent Discovery Tests
# ============================================================================


class TestTalentInfo(unittest.TestCase):
    """Test TalentInfo dataclass."""

    def test_default_app_name(self):
        """App name should default to last segment of package."""
        info = TalentInfo(package="com.miko.disney.stories")
        self.assertEqual(info.app_name, "stories")

    def test_custom_app_name(self):
        """App name should use provided value."""
        info = TalentInfo(package="com.miko.disney.stories", app_name="Disney Stories")
        self.assertEqual(info.app_name, "Disney Stories")

    def test_to_dict(self):
        """to_dict should include all fields."""
        info = TalentInfo(
            package="com.miko.disney.stories",
            main_activity=".MainActivity",
            is_miko=True,
        )
        d = info.to_dict()
        self.assertEqual(d["package"], "com.miko.disney.stories")
        self.assertEqual(d["main_activity"], ".MainActivity")
        self.assertTrue(d["is_miko"])


# ============================================================================
# Verification Engine Tests
# ============================================================================


class TestVerificationResult(unittest.TestCase):
    """Test VerificationResult dataclass."""

    def test_passed_result(self):
        """Passed result should have passed=True."""
        result = VerificationResult(check_name="Test", passed=True, message="All good")
        self.assertTrue(result.passed)

    def test_failed_result(self):
        """Failed result should have passed=False."""
        result = VerificationResult(
            check_name="Test", passed=False, message="Something wrong"
        )
        self.assertFalse(result.passed)

    def test_to_dict(self):
        """to_dict should serialize correctly."""
        result = VerificationResult(
            check_name="Activity Check",
            passed=True,
            message="OK",
            evidence_path="/screenshots/test.png",
        )
        d = result.to_dict()
        self.assertEqual(d["check_name"], "Activity Check")
        self.assertTrue(d["passed"])
        self.assertEqual(d["evidence_path"], "/screenshots/test.png")


# ============================================================================
# RICE POT Analyzer Tests
# ============================================================================


class TestRICEScore(unittest.TestCase):
    """Test RICE score calculation."""

    def test_rice_score_calculation(self):
        """RICE score should be (R×I×C)/E."""
        score = RICEScore(
            talent_name="Video",
            reach=9,
            impact=8,
            confidence=7,
            effort=5,
        )
        expected = (9 * 8 * 7) / 5  # = 100.8
        self.assertAlmostEqual(score.rice_score, expected)

    def test_rice_score_zero_effort(self):
        """Zero effort should return 0 (avoid division by zero)."""
        score = RICEScore(
            talent_name="Test",
            reach=5,
            impact=5,
            confidence=5,
            effort=0,
        )
        self.assertEqual(score.rice_score, 0)

    def test_priority_label_critical(self):
        """High score should be CRITICAL priority."""
        score = RICEScore(
            talent_name="Video",
            reach=9,
            impact=8,
            confidence=7,
            effort=5,
        )
        self.assertIn("CRITICAL", score.priority_label)

    def test_priority_label_low(self):
        """Low score should be LOW priority."""
        score = RICEScore(
            talent_name="Test",
            reach=2,
            impact=2,
            confidence=2,
            effort=8,
        )
        self.assertIn("LOW", score.priority_label)


class TestRICEPOTAnalyzer(unittest.TestCase):
    """Test RICE POT Analyzer."""

    def setUp(self):
        self.config = {
            "rice_pot": {
                "mikoji": {"reach": 9, "impact": 8, "confidence": 7, "effort": 5},
                "storymaker": {"reach": 7, "impact": 7, "confidence": 6, "effort": 4},
                "vooks": {"reach": 8, "impact": 8, "confidence": 7, "effort": 6},
                "thirdparty": {"reach": 5, "impact": 6, "confidence": 4, "effort": 3},
            }
        }
        self.analyzer = RICEPOTAnalyzer(self.config)

    def test_analyze_all_returns_four(self):
        """Should return scores for all four talents."""
        scores = self.analyzer.analyze_all()
        self.assertEqual(len(scores), 4)

    def test_prioritized_list_sorted(self):
        """Prioritized list should be sorted by score descending."""
        prioritized = self.analyzer.get_prioritized_list()
        scores = [s.rice_score for s in prioritized]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_generate_summary_contains_content(self):
        """Summary should contain talent names and scores."""
        summary = self.analyzer.generate_summary()
        self.assertIn("Mikoji Talent", summary)
        self.assertIn("RICE POT", summary)
        self.assertIn("RECOMMENDATION", summary)

    def test_to_report_data_structure(self):
        """Report data should have expected keys."""
        data = self.analyzer.to_report_data()
        self.assertIn("scores", data)
        self.assertIn("summary", data)
        self.assertIn("justifications", data)
        self.assertEqual(len(data["scores"]), 4)


# ============================================================================
# Test Result / Step Tests
# ============================================================================


class TestTestResult(unittest.TestCase):
    """Test TestResult dataclass."""

    def test_passed_property(self):
        """passed property should reflect status."""
        result = TestResult(
            talent_name="Disney Stories",
            package_name="com.miko.disney.stories",
            status=TestStatus.PASSED,
        )
        self.assertTrue(result.passed)

    def test_failed_property(self):
        """passed should be False for non-PASSED status."""
        result = TestResult(
            talent_name="Disney Stories",
            package_name="com.miko.disney.stories",
            status=TestStatus.FAILED,
        )
        self.assertFalse(result.passed)

    def test_step_summary(self):
        """step_summary should show pass/fail counts."""
        result = TestResult(
            talent_name="Disney Stories",
            package_name="com.miko.disney.stories",
            steps=[
                TestStep(name="Step 1", status=TestStatus.PASSED),
                TestStep(name="Step 2", status=TestStatus.PASSED),
                TestStep(name="Step 3", status=TestStatus.FAILED),
            ],
        )
        self.assertIn("2/3 passed", result.step_summary)
        self.assertIn("1 failed", result.step_summary)

    def test_to_dict(self):
        """to_dict should serialize all fields."""
        result = TestResult(
            talent_name="Disney Stories",
            package_name="com.miko.disney.stories",
            status=TestStatus.PASSED,
            duration=10.5,
        )
        d = result.to_dict()
        self.assertEqual(d["talent_name"], "Video")
        self.assertEqual(d["status"], "PASSED")
        self.assertAlmostEqual(d["duration"], 10.5)


# ============================================================================
# HTML Report Generator Tests
# ============================================================================


class TestHTMLReportGenerator(unittest.TestCase):
    """Test HTML report generation."""

    def setUp(self):
        self.config = {
            "reporting": {
                "output_dir": "reports",
                "embed_screenshots": False,
            },
            "rice_pot": {
                "mikoji": {"reach": 9, "impact": 8, "confidence": 7, "effort": 5},
                "storymaker": {"reach": 7, "impact": 7, "confidence": 6, "effort": 4},
                "disney.stories": {
                    "reach": 8,
                    "impact": 8,
                    "confidence": 7,
                    "effort": 6,
                },
                "thirdparty": {"reach": 5, "impact": 6, "confidence": 4, "effort": 3},
            },
        }

    def test_init_defaults(self):
        """Generator should initialize with config defaults."""
        gen = HTMLReportGenerator(self.config)
        self.assertEqual(gen.output_dir, "reports")
        self.assertFalse(gen.embed_screenshots)

    def test_add_result(self):
        """Should accumulate results."""
        gen = HTMLReportGenerator(self.config)
        result = TestResult(
            talent_name="Disney Stories",
            package_name="com.miko.disney.stories",
            status=TestStatus.PASSED,
        )
        gen.add_result(result)
        self.assertEqual(len(gen.results), 1)

    def test_status_badge(self):
        """Status badge should return HTML span."""
        gen = HTMLReportGenerator(self.config)
        badge = gen._status_badge("PASSED")
        self.assertIn("PASSED", badge)
        self.assertIn("background", badge)

    def test_generate_creates_file(self):
        """Generate should create an HTML file."""
        gen = HTMLReportGenerator(self.config)
        result = TestResult(
            talent_name="Disney Stories",
            package_name="com.miko.disney.stories",
            status=TestStatus.PASSED,
            duration=5.0,
        )
        gen.add_result(result)

        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            output_path = f.name

        try:
            path = gen.generate(output_path)
            self.assertTrue(os.path.exists(path))
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("Miko3 Talents Test Report", content)
            self.assertIn("Disney Stories", content)
            self.assertIn("PASSED", content)
        finally:
            os.unlink(output_path)


# ============================================================================
# Mikoji Talent - CLEAR Framework Validation Tests
# ============================================================================


class TestVideoCountBaseline(unittest.TestCase):
    """Test baseline file load/save for video count validation."""

    def setUp(self):
        import tempfile

        self.baseline_file = tempfile.mktemp(suffix=".json")

    def tearDown(self):
        if os.path.exists(self.baseline_file):
            os.unlink(self.baseline_file)

    def _make_test(self, **config_overrides):
        """Create a MikojiTalentTest with mocked ADB."""
        mock_adb = MagicMock()
        mock_adb.get_current_activity.return_value = ""
        mock_adb.get_current_package.return_value = ""
        mock_adb.dump_ui_hierarchy.return_value = ""
        mock_adb.count_ui_elements.return_value = {"count": 0, "elements": []}
        config = {
            "talents": {
                "mikoji": {
                    "package": "com.miko.test",
                    "display_name": "Test Video",
                    "activity": ".MainActivity",
                    "video_count_validation": {
                        "enabled": True,
                        "baseline_file": self.baseline_file,
                        "unexpected_drop_threshold": 0,
                        "unexpected_spike_threshold": 50,
                        "video_text_keywords": ["video", "play"],
                    },
                    **config_overrides,
                }
            },
            "verification": {},
            "device": {},
        }
        return MikojiTalentTest(adb=mock_adb, config=config)

    def test_save_and_load_baseline(self):
        """Baseline file should save and load correctly."""
        test = self._make_test()
        test._save_baseline(10)
        loaded = test._load_baseline()
        self.assertEqual(loaded, 10)

    def test_load_baseline_missing_file(self):
        """Loading from non-existent baseline should return 0."""
        test = self._make_test()
        test.baseline_file = "/nonexistent/path/baseline.json"
        self.assertEqual(test._load_baseline(), 0)

    def test_load_baseline_corrupt_file(self):
        """Loading corrupt JSON baseline should return 0."""
        with open(self.baseline_file, "w") as f:
            f.write("not valid json {{{")
        test = self._make_test()
        self.assertEqual(test._load_baseline(), 0)


class TestVideoCountValidation(unittest.TestCase):
    """Test CLEAR Framework video count validation logic."""

    def setUp(self):
        import tempfile

        self.baseline_file = tempfile.mktemp(suffix=".json")

    def tearDown(self):
        if os.path.exists(self.baseline_file):
            os.unlink(self.baseline_file)

    def _make_test(self, current_count=10, previous_count=10):
        """Create a MikojiTalentTest with mocked ADB and preset counts."""
        mock_adb = MagicMock()
        mock_adb.get_current_activity.return_value = ""
        mock_adb.get_current_package.return_value = ""
        config = {
            "talents": {
                "mikoji": {
                    "package": "com.miko.test",
                    "display_name": "Test Video",
                    "activity": ".MainActivity",
                    "video_count_validation": {
                        "enabled": True,
                        "baseline_file": self.baseline_file,
                        "unexpected_drop_threshold": 0,
                        "unexpected_spike_threshold": 50,
                        "video_text_keywords": ["video", "play"],
                    },
                }
            },
            "verification": {},
            "device": {},
        }
        test = MikojiTalentTest(adb=mock_adb, config=config)
        test.current_video_count = current_count
        test._save_baseline(previous_count)
        return test

    def test_videos_added(self):
        """Count increase should be detected as Videos Added."""
        test = self._make_test(current_count=15, previous_count=10)
        test._validate_video_count()
        self.assertEqual(test.video_count_difference, 5)
        self.assertIn("Videos Added", test.video_count_result)

    def test_videos_removed(self):
        """Count decrease should be detected as Videos Removed."""
        test = self._make_test(current_count=7, previous_count=10)
        test._validate_video_count()
        self.assertEqual(test.video_count_difference, -3)
        self.assertIn("Videos Removed", test.video_count_result)

    def test_no_change(self):
        """Same count should be detected as No Change."""
        test = self._make_test(current_count=10, previous_count=10)
        test._validate_video_count()
        self.assertEqual(test.video_count_difference, 0)
        self.assertEqual(test.video_count_result, "No Change")

    def test_unexpected_drop_fails(self):
        """Count at or below drop threshold should fail."""
        test = self._make_test(current_count=0, previous_count=10)
        test._validate_video_count()
        failed_steps = [s for s in test.result.steps if s.status == TestStatus.FAILED]
        self.assertTrue(any("drop" in s.error_message.lower() for s in failed_steps))

    def test_unexpected_spike_fails(self):
        """Count at or above spike threshold should fail."""
        test = self._make_test(current_count=200, previous_count=10)
        test._validate_video_count()
        failed_steps = [s for s in test.result.steps if s.status == TestStatus.FAILED]
        self.assertTrue(any("spike" in s.error_message.lower() for s in failed_steps))

    def test_normal_change_passes(self):
        """Normal count change should pass validation."""
        test = self._make_test(current_count=15, previous_count=10)
        test._validate_video_count()
        passed_steps = [s for s in test.result.steps if s.status == TestStatus.PASSED]
        self.assertTrue(any("passed" in s.description.lower() for s in passed_steps))

    def test_baseline_updated_after_validation(self):
        """Validation should save current count as new baseline."""
        test = self._make_test(current_count=15, previous_count=10)
        test._validate_video_count()
        new_baseline = test._load_baseline()
        self.assertEqual(new_baseline, 15)


class TestVideoBestPracticesValidation(unittest.TestCase):
    """Test best practice validation logic."""

    def _make_test(self):
        mock_adb = MagicMock()
        config = {
            "talents": {
                "mikoji": {
                    "package": "com.miko.test",
                    "display_name": "Test Video",
                    "activity": ".MainActivity",
                    "video_count_validation": {
                        "enabled": True,
                        "baseline_file": "/tmp/test.json",
                    },
                }
            },
            "verification": {},
            "device": {},
        }
        return MikojiTalentTest(adb=mock_adb, config=config)

    def test_best_practices_pass_with_titles(self):
        """Should pass when video titles are found and no duplicates."""
        test = self._make_test()
        test.video_titles = ["Video A", "Video B"]
        test.video_ids = ["id_1", "id_2"]
        test.has_duplicate_videos = False
        test._validate_best_practices()
        passed = [s for s in test.result.steps if s.status == TestStatus.PASSED]
        self.assertTrue(any("passed" in s.description.lower() for s in passed))

    def test_best_practices_fail_no_titles(self):
        """Should fail when no video titles found."""
        test = self._make_test()
        test.video_titles = []
        test.has_duplicate_videos = False
        test._validate_best_practices()
        failed = [s for s in test.result.steps if s.status == TestStatus.FAILED]
        self.assertTrue(any("titles" in s.error_message.lower() for s in failed))

    def test_best_practices_fail_duplicates(self):
        """Should fail when duplicates detected."""
        test = self._make_test()
        test.video_titles = ["Video A"]
        test.has_duplicate_videos = True
        test._validate_best_practices()
        failed = [s for s in test.result.steps if s.status == TestStatus.FAILED]
        self.assertTrue(any("duplicate" in s.error_message.lower() for s in failed))


class TestCountUIElements(unittest.TestCase):
    """Test ADBClient.count_ui_elements method."""

    @patch("miko3_automation.core.adb_utils.shutil.which")
    def _make_client(self, mock_which):
        mock_which.return_value = "/usr/bin/adb"
        return ADBClient(adb_path="adb")

    @patch("miko3_automation.core.adb_utils.shutil.which")
    @patch("miko3_automation.core.adb_utils.subprocess.run")
    def test_count_matches_keywords(self, mock_run, mock_which):
        """count_ui_elements should match elements containing keywords."""
        mock_which.return_value = "/usr/bin/adb"
        client = self._make_client()

        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy>
  <node text="Funny Video 1" content-desc="play" resource-id="v1" class="android.widget.TextView" bounds="[10,10][100,50]"/>
  <node text="Fun Video 2" content-desc="thumbnail" resource-id="v2" class="android.widget.TextView" bounds="[10,60][100,100]"/>
  <node text="Settings" content-desc="menu" resource-id="s1" class="android.widget.Button" bounds="[10,110][100,150]"/>
</hierarchy>"""

        # Mock the shell command for dump_ui_hierarchy and cat
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="OK", stderr=""),  # uiautomator dump
            MagicMock(returncode=0, stdout=xml_content, stderr=""),  # cat xml
        ]

        result = client.count_ui_elements(["video", "play", "thumbnail"])
        self.assertEqual(result["count"], 2)

    @patch("miko3_automation.core.adb_utils.shutil.which")
    @patch("miko3_automation.core.adb_utils.subprocess.run")
    def test_count_no_matches(self, mock_run, mock_which):
        """count_ui_elements should return 0 when no keywords match."""
        mock_which.return_value = "/usr/bin/adb"
        client = self._make_client()

        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy>
  <node text="Settings" content-desc="menu" resource-id="s1" class="android.widget.Button" bounds="[10,10][100,50]"/>
</hierarchy>"""

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="OK", stderr=""),
            MagicMock(returncode=0, stdout=xml_content, stderr=""),
        ]

        result = client.count_ui_elements(["video", "play"])
        self.assertEqual(result["count"], 0)

    @patch("miko3_automation.core.adb_utils.shutil.which")
    @patch("miko3_automation.core.adb_utils.subprocess.run")
    def test_count_deduplicates(self, mock_run, mock_which):
        """count_ui_elements should not count duplicate elements."""
        mock_which.return_value = "/usr/bin/adb"
        client = self._make_client()

        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy>
  <node text="Video A" content-desc="" resource-id="v1" class="android.widget.TextView" bounds="[10,10][100,50]"/>
  <node text="Video A" content-desc="" resource-id="v1" class="android.widget.TextView" bounds="[10,10][100,50]"/>
  <node text="Video B" content-desc="" resource-id="v2" class="android.widget.TextView" bounds="[10,60][100,100]"/>
</hierarchy>"""

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="OK", stderr=""),
            MagicMock(returncode=0, stdout=xml_content, stderr=""),
        ]

        result = client.count_ui_elements(["video"])
        self.assertEqual(result["count"], 2)


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
