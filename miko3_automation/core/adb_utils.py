"""
ADB Utilities Module
====================
Low-level ADB wrapper providing all device interaction primitives.
Supports both Windows and Linux with automatic platform detection.
"""

import subprocess
import platform
import time
import os
import logging
import shutil
import re
import xml.etree.ElementTree as ET
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)


class ADBError(Exception):
    """Custom exception for ADB-related errors."""

    pass


class ConnectionError(Exception):
    """Raised when device connection is lost or unstable."""

    pass


class ADBClient:
    """
    Low-level ADB wrapper for device interaction.

    Provides methods for:
    - Shell command execution
    - Touch simulation (tap, swipe, long press)
    - Text input and key events
    - Screenshot and screen recording
    - App management (install, uninstall, push, pull)
    - Activity monitoring

    Usage:
        adb = ADBClient(device_serial="192.168.1.100:5555")
        adb.tap(500, 300)
        adb.screenshot("screen.png")
    """

    # Common Android key codes
    KEYCODE_HOME = 3
    KEYCODE_BACK = 4
    KEYCODE_POWER = 26
    KEYCODE_ENTER = 66
    KEYCODE_MENU = 82
    KEYCODE_VOLUME_UP = 24
    KEYCODE_VOLUME_DOWN = 25
    KEYCODE_TAB = 61
    KEYCODE_ESCAPE = 111
    KEYCODE_DPAD_UP = 19
    KEYCODE_DPAD_DOWN = 20
    KEYCODE_DPAD_LEFT = 21
    KEYCODE_DPAD_RIGHT = 22
    KEYCODE_DPAD_CENTER = 23

    def __init__(
        self,
        device_serial: str = "",
        adb_path: str = "adb",
        command_timeout: int = 15,
        retry_attempts: int = 3,
        retry_delay: int = 2,
    ):
        """
        Initialize the ADB client.

        Args:
            device_serial: Target device serial (empty for single-device auto-detect).
            adb_path: Full path to ADB binary, or "adb" if in system PATH.
            command_timeout: Default timeout in seconds for ADB commands.
            retry_attempts: Number of retries on command failure.
            retry_delay: Seconds to wait between retries.
        """
        self.device_serial = device_serial
        self.adb_path = adb_path
        self.command_timeout = command_timeout
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.is_windows = platform.system() == "Windows"

        # Validate ADB is accessible
        self._validate_adb()

    def _validate_adb(self):
        """Verify ADB binary is accessible."""
        adb_bin = shutil.which(self.adb_path)
        if adb_bin is None and not os.path.isfile(self.adb_path):
            raise ADBError(
                f"ADB not found at '{self.adb_path}'. "
                "Ensure ADB is installed and in your PATH.\n"
                "  Windows: Download from https://developer.android.com/tools/releases/platform-tools\n"
                "  Linux:   sudo apt install adb  OR  sudo yum install android-tools"
            )
        logger.info("ADB binary validated: %s", self.adb_path)

    def _build_command(self, *args: str) -> List[str]:
        """Build a full ADB command with device serial prefix."""
        cmd = [self.adb_path]
        if self.device_serial:
            cmd.extend(["-s", self.device_serial])
        cmd.extend(args)
        return cmd

    def _execute(
        self,
        *args: str,
        timeout: Optional[int] = None,
        retry: bool = True,
    ) -> str:
        """
        Execute an ADB command with retry logic.

        Args:
            *args: ADB command arguments.
            timeout: Override default timeout.
            retry: Whether to retry on failure.

        Returns:
            Command stdout as string.

        Raises:
            ADBError: If command fails after all retries.
        """
        cmd = self._build_command(*args)
        effective_timeout = timeout or self.command_timeout
        attempts = self.retry_attempts if retry else 1

        last_error: Optional[Exception] = None
        for attempt in range(1, attempts + 1):
            try:
                logger.debug(
                    "ADB [attempt %d/%d]: %s", attempt, attempts, " ".join(cmd)
                )
                # No shell=True on Windows unless necessary; it can lead to hangs.
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=effective_timeout,
                    shell=False,
                )
                if result.returncode != 0:
                    error_msg = result.stderr.strip() or result.stdout.strip()
                    if (
                        "no such device" in error_msg.lower()
                        or "device not found" in error_msg.lower()
                    ):
                        raise ConnectionError(f"Device connection lost: {error_msg}")
                    raise ADBError(f"ADB command failed: {error_msg}")

                output = result.stdout.strip()
                logger.debug("ADB output: %s", output[:200])
                return output

            except subprocess.TimeoutExpired:
                last_error = ConnectionError(
                    f"Connection timeout after {effective_timeout}s: {' '.join(cmd)}"
                )
                logger.warning(
                    "Attempt %d timed out - possible connection issue", attempt
                )
            except ConnectionError as e:
                last_error = e
                logger.warning("Attempt %d connection lost: %s", attempt, e)
            except ADBError as e:
                last_error = e
                logger.warning("Attempt %d failed: %s", attempt, e)
            except Exception as e:
                last_error = ADBError(f"Unexpected error: {e}")
                logger.warning("Attempt %d unexpected error: %s", attempt, e)

            if attempt < attempts:
                logger.info("Retrying in %ds...", self.retry_delay)
                time.sleep(self.retry_delay)

        if last_error:
            raise last_error
        raise ADBError("ADB command failed with no error information")

    # -------------------------------------------------------------------------
    # Connection
    # -------------------------------------------------------------------------

    def connect(self, address: str = "") -> str:
        """
        Connect to a device over TCP/IP.

        Args:
            address: Device address (e.g., "192.168.1.100:5555").

        Returns:
            Connection result message.
        """
        addr = address or self.device_serial
        if not addr:
            raise ADBError("No device address provided for connection.")
        result = self._execute("connect", addr)
        logger.info("Connected to %s: %s", addr, result)
        return result

    def disconnect(self, address: str = "") -> str:
        """Disconnect from a TCP/IP device."""
        addr = address or self.device_serial
        if addr:
            return self._execute("disconnect", addr)
        return self._execute("disconnect")

    def get_connected_devices(self) -> List[dict]:
        """
        List all connected devices.

        Returns:
            List of dicts with 'serial' and 'status' keys.
        """
        output = self._execute("devices", retry=False)
        devices = []
        for line in output.splitlines()[1:]:  # Skip header
            line = line.strip()
            if line and "\t" in line:
                serial, status = line.split("\t", 1)
                devices.append({"serial": serial.strip(), "status": status.strip()})
        return devices

    # -------------------------------------------------------------------------
    # Shell Commands
    # -------------------------------------------------------------------------

    def shell(self, command: str, timeout: Optional[int] = None) -> str:
        """
        Execute a shell command on the device.

        Args:
            command: Shell command string.
            timeout: Override default timeout.

        Returns:
            Command output.
        """
        return self._execute("shell", command, timeout=timeout)

    # -------------------------------------------------------------------------
    # Input Simulation
    # -------------------------------------------------------------------------

    def tap(self, x: int, y: int) -> str:
        """
        Simulate a tap at (x, y) coordinates.

        Args:
            x: X coordinate.
            y: Y coordinate.

        Returns:
            Command output.
        """
        logger.info("Tapping at (%d, %d)", x, y)
        return self._execute("shell", f"input tap {x} {y}")

    def double_tap(self, x: int, y: int, interval: float = 0.1) -> None:
        """Simulate a double-tap at (x, y)."""
        self.tap(x, y)
        time.sleep(interval)
        self.tap(x, y)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> str:
        """
        Simulate a swipe gesture.

        Args:
            x1, y1: Start coordinates.
            x2, y2: End coordinates.
            duration_ms: Swipe duration in milliseconds.

        Returns:
            Command output.
        """
        logger.info("Swiping (%d,%d) -> (%d,%d) in %dms", x1, y1, x2, y2, duration_ms)
        return self._execute("shell", f"input swipe {x1} {y1} {x2} {y2} {duration_ms}")

    def swipe_left(self, screen_width: int = 1280, screen_height: int = 800) -> str:
        """Swipe left (scroll forward)."""
        mid_y = screen_height // 2
        return self.swipe(
            int(screen_width * 0.8), mid_y, int(screen_width * 0.2), mid_y
        )

    def swipe_right(self, screen_width: int = 1280, screen_height: int = 800) -> str:
        """Swipe right (scroll back)."""
        mid_y = screen_height // 2
        return self.swipe(
            int(screen_width * 0.2), mid_y, int(screen_width * 0.8), mid_y
        )

    def swipe_up(self, screen_width: int = 1280, screen_height: int = 800) -> str:
        """Swipe up (scroll down)."""
        mid_x = screen_width // 2
        return self.swipe(
            mid_x, int(screen_height * 0.8), mid_x, int(screen_height * 0.2)
        )

    def swipe_down(self, screen_width: int = 1280, screen_height: int = 800) -> str:
        """Swipe down (scroll up)."""
        mid_x = screen_width // 2
        return self.swipe(
            mid_x, int(screen_height * 0.2), mid_x, int(screen_height * 0.8)
        )

    def long_press(self, x: int, y: int, duration_ms: int = 1000) -> str:
        """
        Simulate a long press at (x, y).

        Args:
            x: X coordinate.
            y: Y coordinate.
            duration_ms: Hold duration in milliseconds.

        Returns:
            Command output.
        """
        logger.info("Long press at (%d, %d) for %dms", x, y, duration_ms)
        return self._execute("shell", f"input swipe {x} {y} {x} {y} {duration_ms}")

    def input_text(self, text: str) -> str:
        """
        Type text on the device (replaces spaces with %s for ADB).

        Args:
            text: Text string to type.

        Returns:
            Command output.
        """
        sanitized = text.replace(" ", "%s").replace("&", "\\&").replace("<", "\\<")
        logger.info("Inputting text: %s", text[:50])
        return self._execute("shell", f"input text '{sanitized}'")

    def key_event(self, keycode: int) -> str:
        """
        Send a key event.

        Args:
            keycode: Android keycode integer.

        Returns:
            Command output.
        """
        logger.info("Key event: %d", keycode)
        return self._execute("shell", f"input keyevent {keycode}")

    def press_home(self) -> str:
        """Press the HOME button."""
        return self.key_event(self.KEYCODE_HOME)

    def press_back(self) -> str:
        """Press the BACK button."""
        return self.key_event(self.KEYCODE_BACK)

    def press_enter(self) -> str:
        """Press ENTER."""
        return self.key_event(self.KEYCODE_ENTER)

    def press_power(self) -> str:
        """Press the POWER button."""
        return self.key_event(self.KEYCODE_POWER)

    # -------------------------------------------------------------------------
    # Screen Capture
    # -------------------------------------------------------------------------

    def screenshot(self, save_path: str) -> str:
        """
        Capture a screenshot and save to local path.

        Args:
            save_path: Local file path to save the screenshot.

        Returns:
            Path to the saved screenshot.
        """
        remote_path = "/sdcard/miko3_screenshot.png"
        self._execute("shell", f"screencap -p {remote_path}")
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        self._execute("pull", remote_path, save_path)
        self._execute("shell", f"rm {remote_path}", retry=False)
        logger.info("Screenshot saved: %s", save_path)
        return save_path

    def screenrecord(self, save_path: str, duration: int = 10, size: str = "") -> str:
        """
        Record the screen for a given duration (runs in background).

        Args:
            save_path: Local file path to save the recording.
            duration: Recording duration in seconds (max 180).
            size: Optional resolution e.g. "1280x800".

        Returns:
            Path to the saved recording.
        """
        remote_path = "/sdcard/miko3_recording.mp4"
        cmd = f"screenrecord --time-limit {min(duration, 180)} {remote_path}"
        if size:
            cmd = f"screenrecord --size {size} --time-limit {min(duration, 180)} {remote_path}"

        # Start recording (blocks for duration)
        self._execute("shell", cmd, timeout=duration + 10)
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        self._execute("pull", remote_path, save_path)
        self._execute("shell", f"rm {remote_path}", retry=False)
        logger.info("Screen recording saved: %s", save_path)
        return save_path

    # -------------------------------------------------------------------------
    # App Management
    # -------------------------------------------------------------------------

    def install_apk(self, apk_path: str, replace: bool = True) -> str:
        """
        Install an APK on the device.

        Args:
            apk_path: Local path to the APK file.
            replace: Whether to replace existing app.

        Returns:
            Installation result.
        """
        args = ["install"]
        if replace:
            args.append("-r")
        args.append(apk_path)
        return self._execute(*args, timeout=60)

    def uninstall(self, package: str) -> str:
        """Uninstall a package."""
        return self._execute("shell", f"pm uninstall {package}")

    def push_file(self, local_path: str, remote_path: str) -> str:
        """Push a local file to the device."""
        return self._execute("push", local_path, remote_path)

    def pull_file(self, remote_path: str, local_path: str) -> str:
        """Pull a file from the device to local filesystem."""
        os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)
        return self._execute("pull", remote_path, local_path)

    # -------------------------------------------------------------------------
    # Activity & Process Monitoring
    # -------------------------------------------------------------------------

    def get_current_activity(self) -> str:
        """
        Get the current foreground activity.

        Returns:
            Activity name string (e.g., "com.miko.video/.MainActivity").
        """
        # Try modern approach first (Android 10+)
        try:
            output = self._execute(
                "shell",
                "dumpsys activity activities | grep -E 'mResumedActivity|mFocusedActivity'",
                retry=False,
            )
            if output:
                # Extract component name from output
                for part in output.split():
                    if "/" in part and "." in part:
                        return part.rstrip("}")
        except ADBError:
            pass

        # Fallback for older Android
        try:
            output = self._execute(
                "shell",
                "dumpsys window windows | grep -E 'mCurrentFocus|mFocusedApp'",
                retry=False,
            )
            if output:
                for part in output.split():
                    if "/" in part and "." in part:
                        return part.rstrip("}")
        except ADBError:
            pass

        return ""

    def get_current_package(self) -> str:
        """Get the package name of the foreground app."""
        activity = self.get_current_activity()
        if "/" in activity:
            return activity.split("/")[0]
        return activity

    def wait_for_activity(
        self, activity_substring: str, timeout: int = 30, poll_interval: float = 1.0
    ) -> bool:
        """
        Wait until a specific activity is in the foreground.

        Args:
            activity_substring: Substring to match in the activity name.
            timeout: Maximum seconds to wait.
            poll_interval: Seconds between polls.

        Returns:
            True if activity appeared, False if timed out.
        """
        logger.info("Waiting for activity containing '%s'...", activity_substring)
        start = time.time()
        while time.time() - start < timeout:
            current = self.get_current_activity()
            if activity_substring.lower() in current.lower():
                logger.info("Activity found: %s", current)
                return True
            time.sleep(poll_interval)
        logger.warning(
            "Timed out waiting for activity '%s' (last: %s)",
            activity_substring,
            self.get_current_activity(),
        )
        return False

    def is_package_running(self, package: str) -> bool:
        """Check if a package is currently running."""
        try:
            output = self._execute("shell", f"pidof {package}", retry=False)
            return bool(output.strip())
        except ADBError:
            return False

    # -------------------------------------------------------------------------
    # Device Properties
    # -------------------------------------------------------------------------

    def get_device_properties(self) -> dict:
        """
        Get device properties.

        Returns:
            Dict with model, android_version, sdk, screen_size, battery, etc.
        """
        props = {}
        prop_map = {
            "model": "ro.product.model",
            "brand": "ro.product.brand",
            "android_version": "ro.build.version.release",
            "sdk_version": "ro.build.version.sdk",
            "device_name": "ro.product.device",
            "build_id": "ro.build.display.id",
        }
        for key, prop in prop_map.items():
            try:
                props[key] = self._execute("shell", f"getprop {prop}", retry=False)
            except ADBError:
                props[key] = "unknown"

        # Screen size
        try:
            wm_output = self._execute("shell", "wm size", retry=False)
            if "Physical size:" in wm_output:
                props["screen_size"] = wm_output.split(":")[-1].strip()
        except ADBError:
            props["screen_size"] = "unknown"

        # Battery
        try:
            battery = self._execute(
                "shell", "dumpsys battery | grep level", retry=False
            )
            props["battery_level"] = (
                battery.split(":")[-1].strip() if ":" in battery else "unknown"
            )
        except ADBError:
            props["battery_level"] = "unknown"

        return props

    def get_screen_resolution(self) -> Tuple[int, int]:
        """
        Get screen resolution.

        Returns:
            Tuple of (width, height).
        """
        try:
            output = self._execute("shell", "wm size", retry=False)
            if "Physical size:" in output:
                size_str = output.split(":")[-1].strip()
                w, h = size_str.split("x")
                return int(w), int(h)
        except (ADBError, ValueError):
            pass
        return 1280, 800  # Miko3 default

    # -------------------------------------------------------------------------
    # Logcat
    # -------------------------------------------------------------------------

    def get_logcat(
        self,
        lines: int = 200,
        filter_tag: str = "",
        level: str = "",
    ) -> str:
        """
        Capture logcat output.

        Args:
            lines: Number of lines to capture.
            filter_tag: Optional tag filter (e.g., "ActivityManager").
            level: Optional level filter (V, D, I, W, E, F).

        Returns:
            Logcat output string.
        """
        cmd = f"logcat -d -t {lines}"
        if filter_tag and level:
            cmd += f" {filter_tag}:{level} *:S"
        elif filter_tag:
            cmd += f" -s {filter_tag}"
        return self._execute("shell", cmd, timeout=10, retry=False)

    def clear_logcat(self) -> str:
        """Clear the logcat buffer."""
        return self._execute("shell", "logcat -c", retry=False)

    # -------------------------------------------------------------------------
    # Device Control
    # -------------------------------------------------------------------------

    def wake_screen(self) -> None:
        """Wake the device screen if it's off."""
        try:
            output = self._execute(
                "shell", "dumpsys power | grep 'mWakefulness'", retry=False
            )
            if "Asleep" in output or "Dozing" in output:
                # Use KEYCODE_WAKEUP (224) instead of power toggle
                self.key_event(224)
                time.sleep(1)
                logger.info("Screen woken up via KEYCODE_WAKEUP")
            else:
                logger.debug("Screen is already awake")
        except ADBError:
            # Fallback to power button if wakeup event fails
            self.press_power()
            time.sleep(1)

    def unlock_screen(self) -> None:
        """Attempt to unlock the screen (swipe up)."""
        self.wake_screen()
        w, h = self.get_screen_resolution()
        self.swipe(w // 2, int(h * 0.8), w // 2, int(h * 0.2), 300)
        time.sleep(0.5)

    def is_screen_on(self) -> bool:
        """Check if the screen is currently on."""
        try:
            output = self._execute(
                "shell", "dumpsys power | grep 'mWakefulness'", retry=False
            )
            return "Awake" in output
        except ADBError:
            return True  # Assume on if we can't check

    def set_screen_brightness(self, level: int = 255) -> str:
        """
        Set the screen brightness (0-255).

        Args:
            level: Brightness level (0 is dark, 255 is maximum).
        """
        level = max(0, min(255, level))
        logger.info("Setting screen brightness to %d", level)
        return self.shell(f"settings put system screen_brightness {level}")

    def set_stay_awake(self, enabled: bool = True) -> str:
        """
        Keep the screen on during tests.

        Args:
            enabled: If True, screen will stay on when connected to USB.
        """
        # stayon values: 0=never, 1=ac, 2=usb, 3=ac+usb
        value = 3 if enabled else 0
        mode = "Stay On" if enabled else "Normal"
        logger.info("Setting power mode to %s", mode)
        return self.shell(f"svc power stayon {'usb' if enabled else 'false'}")

    def reboot(self) -> str:
        """Reboot the device."""
        return self._execute("reboot", timeout=5, retry=False)

    def wait_for_device(self, timeout: int = 60) -> str:
        """Wait for device to come online."""
        return self._execute("wait-for-device", timeout=timeout, retry=False)

    # -------------------------------------------------------------------------
    # UI Automator / Element Search
    # -------------------------------------------------------------------------

    def dump_ui_hierarchy(self) -> str:
        """
        Dump the current UI hierarchy to an XML string.

        Returns:
            XML string of the UI hierarchy.
        """
        remote_path = "/data/local/tmp/uidump.xml"
        try:
            self.shell(f"uiautomator dump {remote_path}")
            xml_content = self.shell(f"cat {remote_path}")
            return xml_content
        except ADBError as e:
            logger.error("Failed to dump UI hierarchy: %s", e)
            return ""

    def find_elements_by_text(self, text: str, exact: bool = False) -> List[dict]:
        """
        Find all elements containing the specified text.

        Args:
            text: Text to search for.
            exact: Whether to match the exact text.

        Returns:
            List of element dicts with 'text', 'resource-id', 'class', and 'bounds'.
        """
        xml_content = self.dump_ui_hierarchy()
        if not xml_content:
            return []

        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError:
            # Handle cases where cat output might have extra junk
            if "<?xml" in xml_content:
                xml_content = xml_content[xml_content.find("<?xml") :]
                root = ET.fromstring(xml_content)
            else:
                return []

        elements = []
        for node in root.iter("node"):
            node_text = node.get("text", "")
            node_desc = node.get("content-desc", "")

            match = False
            if exact:
                match = (text.lower() == node_text.lower()) or (
                    text.lower() == node_desc.lower()
                )
            else:
                match = (text.lower() in node_text.lower()) or (
                    text.lower() in node_desc.lower()
                )

            if match:
                elements.append(
                    {
                        "text": node_text,
                        "resource-id": node.get("resource-id", ""),
                        "class": node.get("class", ""),
                        "bounds": node.get("bounds", ""),
                    }
                )
        return elements

    def get_element_center(self, bounds_str: str) -> Optional[Tuple[int, int]]:
        """
        Parse ADB bounds string [x1,y1][x2,y2] and return the center (x, y).
        """
        match = re.search(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds_str)
        if match:
            x1, y1, x2, y2 = map(int, match.groups())
            return (x1 + x2) // 2, (y1 + y2) // 2
        return None

    def tap_text(self, text: str, exact: bool = False) -> bool:
        """
        Find an element by text and tap its center.
        """
        elements = self.find_elements_by_text(text, exact)
        if not elements:
            logger.warning("Could not find element with text: '%s'", text)
            return False

        # Tap the first match
        center = self.get_element_center(elements[0]["bounds"])
        if center:
            self.tap(center[0], center[1])
            return True
        return False

    def count_ui_elements(self, keywords: list) -> dict:
        """
        Count UI elements matching given keywords in the UI hierarchy dump.

        Used by Video Talent to count videos displayed on screen by looking
        for text/content-desc entries containing specified keywords.

        Args:
            keywords: List of strings to match against element text and content-desc.

        Returns:
            Dict with:
                - 'count': Total unique element count matching any keyword
                - 'elements': List of matched element dicts (text, resource-id, class, bounds)
        """
        xml_content = self.dump_ui_hierarchy()
        if not xml_content:
            return {"count": 0, "elements": []}

        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError:
            if "<?xml" in xml_content:
                xml_content = xml_content[xml_content.find("<?xml") :]
                root = ET.fromstring(xml_content)
            else:
                return {"count": 0, "elements": []}

        keywords_lower = [kw.lower() for kw in keywords]
        matched = []
        seen_texts = set()

        for node in root.iter("node"):
            node_text = node.get("text", "").strip()
            node_desc = node.get("content-desc", "").strip()
            combined = (node_text + " " + node_desc).lower()

            for kw in keywords_lower:
                if kw in combined:
                    dedup_key = f"{node_text}|{node_desc}|{node.get('resource-id', '')}"
                    if dedup_key not in seen_texts:
                        seen_texts.add(dedup_key)
                        matched.append(
                            {
                                "text": node_text,
                                "resource-id": node.get("resource-id", ""),
                                "class": node.get("class", ""),
                                "bounds": node.get("bounds", ""),
                            }
                        )
                    break

        logger.info(
            "UI element count (keywords=%s): %d matches", keywords, len(matched)
        )
        return {"count": len(matched), "elements": matched}
