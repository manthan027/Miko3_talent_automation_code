"""
Connection Monitor Module
========================
Monitors ADB connection health and detects interruptions.
Provides automatic reconnection capabilities.
"""

import logging
import time
import threading
from typing import Optional, Callable

from .adb_utils import ADBClient, ADBError, ConnectionError

logger = logging.getLogger(__name__)


class ConnectionMonitor:
    """
    Monitors ADB connection health and detects interruptions.

    Can run in background thread for continuous monitoring or
    be used for manual connection checks.

    Usage:
        monitor = ConnectionMonitor(adb_client)

        # Manual check
        if not monitor.check_connection():
            monitor.reconnect()

        # Continuous monitoring in background
        monitor.start_monitoring()
        # ... run tests ...
        monitor.stop_monitoring()
    """

    def __init__(
        self,
        adb_client: ADBClient,
        check_interval: int = 5,
        on_disconnect: Optional[Callable[["ConnectionMonitor"], None]] = None,
    ):
        """
        Initialize connection monitor.

        Args:
            adb_client: The ADB client to monitor.
            check_interval: Seconds between connection checks (default: 5).
            on_disconnect: Optional callback when disconnection is detected.
        """
        self.adb = adb_client
        self.check_interval = check_interval
        self.on_disconnect = on_disconnect

        self._is_connected = True
        self._last_ping_time = 0
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        self._connection_loss_count = 0
        self._last_disconnect_time: Optional[float] = None

    def check_connection(self) -> bool:
        """
        Check if device is still reachable.

        Returns:
            True if connection is alive, False otherwise.
        """
        try:
            self.adb.shell("echo ping", timeout=5)
            self._last_ping_time = time.time()

            if not self._is_connected:
                logger.info("Connection restored!")
                self._is_connected = True
                self._connection_loss_count = 0

            return True

        except (ConnectionError, ADBError) as e:
            logger.warning("Connection check failed: %s", e)
            self._is_connected = False
            self._connection_loss_count += 1
            self._last_disconnect_time = time.time()
            return False

    def is_connected(self) -> bool:
        """Return current connection status."""
        return self._is_connected

    def get_connection_stats(self) -> dict:
        """Get connection statistics."""
        return {
            "is_connected": self._is_connected,
            "connection_loss_count": self._connection_loss_count,
            "last_ping_time": self._last_ping_time,
            "last_disconnect_time": self._last_disconnect_time,
        }

    def wait_for_connection(
        self,
        timeout: int = 30,
        initial_delay: float = 1.0,
        backoff_factor: float = 1.5,
        max_delay: float = 10.0,
    ) -> bool:
        """
        Wait for connection to be restored.

        Args:
            timeout: Maximum seconds to wait.
            initial_delay: Initial delay between retries.
            backoff_factor: Multiplier for each retry delay.
            max_delay: Maximum delay between retries.

        Returns:
            True if connection restored, False if timeout.
        """
        delay = initial_delay
        start_time = time.time()

        logger.info("Waiting for connection to restore (timeout: %ds)...", timeout)

        while time.time() - start_time < timeout:
            if self.check_connection():
                logger.info("Connection restored after %.1fs", time.time() - start_time)
                return True

            logger.debug("Connection not ready, retrying in %.1fs...", delay)
            time.sleep(delay)
            delay = min(delay * backoff_factor, max_delay)

        logger.warning("Connection restore timed out after %ds", timeout)
        return False

    def reconnect(
        self,
        max_attempts: int = 3,
        reconnect_delay: float = 2.0,
    ) -> bool:
        """
        Attempt to reconnect to the device.

        Args:
            max_attempts: Number of reconnection attempts.
            reconnect_delay: Seconds between attempts.

        Returns:
            True if reconnection successful, False otherwise.
        """
        serial = self.adb.device_serial
        logger.info("Attempting to reconnect to %s...", serial)

        for attempt in range(1, max_attempts + 1):
            try:
                # Try adb connect
                result = self.adb.connect(serial)
                logger.debug("Connect result: %s", result)

                # Verify connection
                if self.check_connection():
                    logger.info("Reconnection successful on attempt %d", attempt)
                    return True

            except (ADBError, ConnectionError) as e:
                logger.warning("Reconnect attempt %d failed: %s", attempt, e)

            if attempt < max_attempts:
                time.sleep(reconnect_delay)

        # Try reconnect command
        try:
            self.adb._execute("reconnect", retry=False)
            time.sleep(reconnect_delay)
            if self.check_connection():
                logger.info("Reconnection via 'reconnect' command successful")
                return True
        except (ADBError, ConnectionError) as e:
            logger.warning("Reconnect command failed: %s", e)

        logger.error("All reconnection attempts failed")
        return False

    def start_monitoring(self) -> None:
        """Start background connection monitoring."""
        if self._monitoring:
            logger.warning("Monitoring already running")
            return

        self._stop_event.clear()
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True, name="ConnectionMonitor"
        )
        self._monitor_thread.start()
        logger.info(
            "Connection monitoring started (interval: %ds)", self.check_interval
        )

    def stop_monitoring(self) -> None:
        """Stop background connection monitoring."""
        if not self._monitoring:
            return

        logger.info("Stopping connection monitoring...")
        self._stop_event.set()

        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)

        self._monitoring = False
        logger.info("Connection monitoring stopped")

    def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while not self._stop_event.is_set():
            if not self.check_connection():
                logger.warning("Connection lost detected!")

                if self.on_disconnect:
                    try:
                        self.on_disconnect(self)
                    except Exception as e:
                        logger.error("Error in disconnect callback: %s", e)

            self._stop_event.wait(self.check_interval)


class ResilientADBClient:
    """
    Wrapper around ADBClient that automatically handles disconnections.

    Provides automatic reconnection and retry on connection loss.

    Usage:
        resilient_adb = ResilientADBClient(adb_client)
        resilient_adb.shell("some command")  # Auto-reconnects if needed
    """

    def __init__(
        self,
        adb_client: ADBClient,
        max_reconnect_attempts: int = 3,
        reconnect_delay: float = 2.0,
    ):
        """
        Initialize resilient ADB client.

        Args:
            adb_client: The underlying ADB client.
            max_reconnect_attempts: Max reconnection attempts before giving up.
            reconnect_delay: Seconds between reconnection attempts.
        """
        self._adb = adb_client
        self._max_reconnect = max_reconnect_attempts
        self._reconnect_delay = reconnect_delay
        self._monitor = ConnectionMonitor(adb_client)

    @property
    def adb_client(self) -> ADBClient:
        """Get the underlying ADB client."""
        return self._adb

    def _ensure_connected(self) -> bool:
        """Ensure device is connected, attempt reconnect if not."""
        if self._monitor.check_connection():
            return True

        return self._monitor.reconnect(
            max_attempts=self._max_reconnect,
            reconnect_delay=self._reconnect_delay,
        )

    def shell(self, command: str, timeout: Optional[int] = None) -> str:
        """Execute shell command with automatic reconnection."""
        self._ensure_connected()
        return self._adb.shell(command, timeout=timeout)

    def tap(self, x: int, y: int) -> str:
        """Simulate tap with automatic reconnection."""
        self._ensure_connected()
        return self._adb.tap(x, y)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> str:
        """Simulate swipe with automatic reconnection."""
        self._ensure_connected()
        return self._adb.swipe(x1, y1, x2, y2, duration_ms)

    def get_current_activity(self) -> str:
        """Get current activity with automatic reconnection."""
        self._ensure_connected()
        return self._adb.get_current_activity()

    def screenshot(self, save_path: str) -> str:
        """Capture screenshot with automatic reconnection."""
        self._ensure_connected()
        return self._adb.screenshot(save_path)

    def __getattr__(self, name: str):
        """Delegate other attribute access to underlying ADB client."""
        return getattr(self._adb, name)
