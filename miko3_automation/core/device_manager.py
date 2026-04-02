"""
Device Manager Module
=====================
Manages Miko3 device connections, health checks, and multi-device support.
"""

import logging
import time
from typing import Optional, List

from .adb_utils import ADBClient, ADBError

logger = logging.getLogger(__name__)


class DeviceNotFoundError(Exception):
    """Raised when no target device is found."""

    pass


class DeviceHealthError(Exception):
    """Raised when device health checks fail."""

    pass


class DeviceManager:
    """
    Manages Miko3 device connections and health monitoring.

    Features:
    - Auto-detect single connected device
    - Multi-device support with serial targeting
    - Device health checks (battery, screen, connectivity)
    - Connection retry with exponential backoff
    - Wake and unlock device before testing

    Usage:
        dm = DeviceManager(config)
        adb = dm.get_device()
        dm.ensure_ready()
    """

    MIN_BATTERY_LEVEL = 15  # Minimum battery % to run tests

    def __init__(self, config: dict):
        """
        Initialize DeviceManager from config dict.

        Args:
            config: Configuration dictionary (from config.yaml).
        """
        device_cfg = config.get("device", {})
        self.serial = device_cfg.get("serial", "")
        self.adb_path = device_cfg.get("adb_path", "adb")
        self.connection_timeout = device_cfg.get("connection_timeout", 30)
        self.command_timeout = device_cfg.get("command_timeout", 15)
        self.retry_attempts = device_cfg.get("retry_attempts", 3)
        self.retry_delay = device_cfg.get("retry_delay", 2)

        self._adb_client: Optional[ADBClient] = None

    def get_device(self) -> ADBClient:
        """
        Get an ADBClient connected to the target device.

        Returns:
            Configured ADBClient instance.

        Raises:
            DeviceNotFoundError: If no device is found or connected.
        """
        if self._adb_client:
            return self._adb_client

        self._adb_client = ADBClient(
            device_serial=self.serial,
            adb_path=self.adb_path,
            command_timeout=self.command_timeout,
            retry_attempts=self.retry_attempts,
            retry_delay=self.retry_delay,
        )

        # Verify device is connected
        self._verify_connection()
        return self._adb_client

    def _verify_connection(self) -> None:
        """Verify device is connected with retry and backoff."""
        delay = self.retry_delay
        for attempt in range(1, self.retry_attempts + 1):
            try:
                devices = self._adb_client.get_connected_devices()

                if not devices:
                    raise DeviceNotFoundError(
                        "No devices found. Ensure:\n"
                        "  1. Miko3 is connected via USB\n"
                        "  2. USB debugging is enabled on Miko3\n"
                        "  3. ADB drivers are installed\n"
                        "  Commands to verify:\n"
                        "    Windows: adb devices\n"
                        "    Linux:   adb devices"
                    )

                if self.serial:
                    # Look for specific device
                    device = next(
                        (d for d in devices if d["serial"] == self.serial), None
                    )
                    if not device:
                        available = [d["serial"] for d in devices]
                        raise DeviceNotFoundError(
                            f"Device '{self.serial}' not found. "
                            f"Available devices: {available}"
                        )
                    if device["status"] != "device":
                        raise DeviceNotFoundError(
                            f"Device '{self.serial}' status is '{device['status']}' "
                            f"(expected 'device'). Try: adb reconnect"
                        )
                else:
                    # Auto-detect: use first available device
                    online = [d for d in devices if d["status"] == "device"]
                    if not online:
                        statuses = [f"{d['serial']}={d['status']}" for d in devices]
                        raise DeviceNotFoundError(
                            f"No online devices. Device statuses: {statuses}"
                        )
                    if len(online) > 1:
                        logger.warning(
                            "Multiple devices found: %s. Using first: %s",
                            [d["serial"] for d in online],
                            online[0]["serial"],
                        )
                    self.serial = online[0]["serial"]
                    self._adb_client.device_serial = self.serial

                logger.info("✓ Device connected: %s", self.serial)
                return

            except DeviceNotFoundError:
                if attempt == self.retry_attempts:
                    raise
                logger.warning(
                    "Connection attempt %d/%d failed. Retrying in %ds...",
                    attempt,
                    self.retry_attempts,
                    delay,
                )
                time.sleep(delay)
                delay = min(delay * 2, 30)  # Exponential backoff, max 30s

    def get_device_info(self) -> dict:
        """
        Get comprehensive device information.

        Returns:
            Dict with device model, Android version, battery, etc.
        """
        adb = self.get_device()
        info = adb.get_device_properties()
        info["serial"] = self.serial
        info["screen_resolution"] = "x".join(map(str, adb.get_screen_resolution()))
        return info

    def check_health(self) -> dict:
        """
        Run device health checks.

        Returns:
            Dict with health check results:
            {
                "overall": "PASS" | "WARN" | "FAIL",
                "battery": {"level": int, "status": str},
                "screen": {"on": bool, "status": str},
                "connectivity": {"adb": bool, "status": str},
            }
        """
        adb = self.get_device()
        health = {
            "overall": "PASS",
            "checks": {},
        }

        # Battery check
        try:
            props = adb.get_device_properties()
            battery = int(props.get("battery_level", "0"))
            if battery < self.MIN_BATTERY_LEVEL:
                health["checks"]["battery"] = {
                    "level": battery,
                    "status": f"WARN - Low battery ({battery}%)",
                }
                health["overall"] = "WARN"
            else:
                health["checks"]["battery"] = {
                    "level": battery,
                    "status": f"OK ({battery}%)",
                }
        except (ADBError, ValueError) as e:
            health["checks"]["battery"] = {"level": -1, "status": f"ERROR - {e}"}
            health["overall"] = "WARN"

        # Screen check
        try:
            screen_on = adb.is_screen_on()
            health["checks"]["screen"] = {
                "on": screen_on,
                "status": "ON" if screen_on else "OFF (will wake)",
            }
        except ADBError as e:
            health["checks"]["screen"] = {"on": False, "status": f"ERROR - {e}"}

        # ADB connectivity check
        try:
            adb.shell("echo ping")
            health["checks"]["connectivity"] = {
                "adb": True,
                "status": "OK",
            }
        except ADBError as e:
            health["checks"]["connectivity"] = {
                "adb": False,
                "status": f"FAIL - {e}",
            }
            health["overall"] = "FAIL"

        logger.info("Health check result: %s", health["overall"])
        return health

    def ensure_ready(self) -> None:
        """
        Ensure the device is ready for testing.

        - Verifies connection
        - Checks health
        - Wakes and unlocks screen
        - Navigates to home screen

        Raises:
            DeviceHealthError: If device fails critical health checks.
        """
        adb = self.get_device()
        health = self.check_health()

        if health["overall"] == "FAIL":
            raise DeviceHealthError(f"Device health check failed: {health['checks']}")

        if health["overall"] == "WARN":
            logger.warning("Device health warnings: %s", health["checks"])

        # Wake and unlock
        adb.wake_screen()
        adb.set_screen_brightness(255)
        adb.set_stay_awake(True)
        adb.unlock_screen()
        time.sleep(1)

        # Go to home screen
        adb.press_home()
        time.sleep(0.5)

        logger.info("✓ Device is ready for testing")

    def get_all_devices(self) -> List[dict]:
        """
        List all connected devices with their info.

        Returns:
            List of device info dicts.
        """
        temp_adb = ADBClient(adb_path=self.adb_path)
        devices = temp_adb.get_connected_devices()
        result = []
        for dev in devices:
            if dev["status"] == "device":
                client = ADBClient(
                    device_serial=dev["serial"],
                    adb_path=self.adb_path,
                )
                try:
                    props = client.get_device_properties()
                    props["serial"] = dev["serial"]
                    result.append(props)
                except ADBError:
                    result.append(
                        {
                            "serial": dev["serial"],
                            "model": "unknown",
                            "error": "Could not retrieve properties",
                        }
                    )
        return result

    def disconnect(self) -> None:
        """Disconnect from the device."""
        if self._adb_client and self.serial:
            try:
                self._adb_client.disconnect()
                logger.info("Disconnected from %s", self.serial)
            except ADBError:
                pass
        self._adb_client = None

    def is_device_online(self) -> bool:
        """
        Check if target device is currently online.

        Returns:
            True if device is connected and responding, False otherwise.
        """
        if not self.serial:
            return False

        try:
            temp_client = ADBClient(adb_path=self.adb_path)
            devices = temp_client.get_connected_devices()
            for dev in devices:
                if dev["serial"] == self.serial and dev["status"] == "device":
                    return True
            return False
        except (ADBError, Exception):
            return False

    def reconnect(self, max_attempts: int = 3, delay: float = 2.0) -> bool:
        """
        Attempt to reconnect to the device.

        Args:
            max_attempts: Number of reconnection attempts.
            delay: Seconds between attempts.

        Returns:
            True if reconnection successful, False otherwise.
        """
        if not self.serial:
            logger.warning("No serial configured, cannot reconnect")
            return False

        logger.info("Attempting to reconnect to %s...", self.serial)

        for attempt in range(1, max_attempts + 1):
            try:
                # Create fresh ADB client and try to connect
                temp_client = ADBClient(adb_path=self.adb_path)

                # First try regular connect
                try:
                    result = temp_client.connect(self.serial)
                    logger.debug("Connect result: %s", result)
                except ADBError:
                    pass

                # Check if device is now online
                time.sleep(1)
                if self.is_device_online():
                    logger.info("Reconnection successful on attempt %d", attempt)
                    # Reinitialize the ADB client
                    self._adb_client = ADBClient(
                        device_serial=self.serial,
                        adb_path=self.adb_path,
                        command_timeout=self.command_timeout,
                        retry_attempts=self.retry_attempts,
                        retry_delay=self.retry_delay,
                    )
                    return True

            except Exception as e:
                logger.warning("Reconnect attempt %d failed: %s", attempt, e)

            if attempt < max_attempts:
                time.sleep(delay)

        # Try adb reconnect command as last resort
        try:
            temp_client = ADBClient(adb_path=self.adb_path)
            temp_client._execute("reconnect", retry=False)
            time.sleep(2)
            if self.is_device_online():
                logger.info("Reconnection via 'reconnect' command successful")
                self._adb_client = ADBClient(
                    device_serial=self.serial,
                    adb_path=self.adb_path,
                    command_timeout=self.command_timeout,
                    retry_attempts=self.retry_attempts,
                    retry_delay=self.retry_delay,
                )
                return True
        except Exception as e:
            logger.warning("Reconnect command failed: %s", e)

        logger.error("All reconnection attempts failed for %s", self.serial)
        return False
