"""
Talent Discovery Module
=======================
Discovers, inspects, and launches Miko3 talents (apps/activities).
"""

import logging
import re
from typing import List, Optional

from .adb_utils import ADBClient, ADBError

logger = logging.getLogger(__name__)


class TalentInfo:
    """Data class representing a discovered talent."""

    def __init__(
        self,
        package: str,
        main_activity: str = "",
        app_name: str = "",
        version: str = "",
        is_system: bool = False,
        is_miko: bool = False,
    ):
        self.package = package
        self.main_activity = main_activity
        self.app_name = app_name or package.split(".")[-1]
        self.version = version
        self.is_system = is_system
        self.is_miko = is_miko

    def __repr__(self):
        return (
            f"TalentInfo(package='{self.package}', "
            f"activity='{self.main_activity}', "
            f"name='{self.app_name}', miko={self.is_miko})"
        )

    def to_dict(self) -> dict:
        return {
            "package": self.package,
            "main_activity": self.main_activity,
            "app_name": self.app_name,
            "version": self.version,
            "is_system": self.is_system,
            "is_miko": self.is_miko,
        }


class TalentDiscovery:
    """
    Discovers and manages Miko3 talents on the device.

    Features:
    - List all installed packages
    - Filter Miko-specific packages
    - Auto-detect main activity for any package
    - Launch/stop/clear individual talents
    - Identify foreground talent

    Usage:
        td = TalentDiscovery(adb_client)
        talents = td.find_miko_talents()
        td.launch_talent("com.miko.video", ".MainActivity")
    """

    # Common Miko package patterns
    MIKO_PATTERNS = [
        "miko",
        "com.miko",
        "com.irobot.miko",
        "com.emotix",
    ]

    def __init__(self, adb: ADBClient):
        """
        Initialize TalentDiscovery.

        Args:
            adb: Connected ADBClient instance.
        """
        self.adb = adb

    def list_all_packages(self, include_system: bool = False) -> List[str]:
        """
        List all installed packages on the device.

        Args:
            include_system: Include system packages (default: third-party only).

        Returns:
            List of package name strings.

        Commands:
            Windows & Linux: adb shell pm list packages [-3]
        """
        flag = "" if include_system else "-3"
        output = self.adb.shell(f"pm list packages {flag}".strip())
        packages = []
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("package:"):
                packages.append(line.replace("package:", "").strip())
        packages.sort()
        logger.info("Found %d packages (system=%s)", len(packages), include_system)
        return packages

    def find_miko_packages(self) -> List[str]:
        """
        Find all Miko-related packages.

        Returns:
            List of Miko package names.

        Commands:
            Windows: adb shell pm list packages | findstr miko
            Linux:   adb shell pm list packages | grep miko
        """
        all_packages = self.list_all_packages(include_system=True)
        miko_packages = []
        for pkg in all_packages:
            pkg_lower = pkg.lower()
            if any(pattern in pkg_lower for pattern in self.MIKO_PATTERNS):
                miko_packages.append(pkg)
        logger.info("Found %d Miko packages: %s", len(miko_packages), miko_packages)
        return miko_packages

    def get_main_activity(self, package: str) -> str:
        """
        Discover the main launcher activity for a package.

        Args:
            package: Package name.

        Returns:
            Activity name (e.g., ".MainActivity" or full path).

        Commands:
            Windows & Linux:
              adb shell dumpsys package <package> | grep -A1 'android.intent.action.MAIN'
              adb shell cmd package resolve-activity --brief <package>
        """
        # Method 1: dumpsys package (most reliable)
        try:
            output = self.adb.shell(
                f"dumpsys package {package} | grep -B5 'android.intent.action.MAIN'"
            )
            # Look for activity class name pattern
            for line in output.splitlines():
                line = line.strip()
                # Match patterns like "com.miko.video/.MainActivity" or activity names
                match = re.search(r'(\S+/\S+)', line)
                if match:
                    component = match.group(1)
                    if package in component:
                        activity = component.split("/")[-1]
                        logger.info("Found main activity for %s: %s", package, activity)
                        return activity
        except ADBError:
            pass

        # Method 2: resolve-activity (Android 7+)
        try:
            output = self.adb.shell(
                f"cmd package resolve-activity --brief {package}"
            )
            for line in output.splitlines():
                line = line.strip()
                if "/" in line and package in line:
                    activity = line.split("/")[-1]
                    logger.info("Found main activity via resolve: %s", activity)
                    return activity
        except ADBError:
            pass

        # Method 3: monkey approach - launch and check
        try:
            self.adb.shell(
                f"monkey -p {package} -c android.intent.category.LAUNCHER 1"
            )
            import time
            time.sleep(2)
            current = self.adb.get_current_activity()
            if package in current and "/" in current:
                activity = current.split("/")[-1]
                self.adb.shell(f"am force-stop {package}")
                logger.info("Found main activity via monkey: %s", activity)
                return activity
        except ADBError:
            pass

        logger.warning("Could not determine main activity for %s", package)
        return ".MainActivity"  # Common default

    def get_talent_info(self, package: str) -> TalentInfo:
        """
        Get comprehensive info about a talent/package.

        Args:
            package: Package name.

        Returns:
            TalentInfo object.
        """
        main_activity = self.get_main_activity(package)
        version = ""
        is_system = False

        # Get version info
        try:
            output = self.adb.shell(f"dumpsys package {package} | grep versionName")
            for line in output.splitlines():
                if "versionName" in line:
                    version = line.split("=")[-1].strip()
                    break
        except ADBError:
            pass

        # Check if system app
        try:
            output = self.adb.shell(f"pm path {package}")
            is_system = "/system/" in output
        except ADBError:
            pass

        is_miko = any(p in package.lower() for p in self.MIKO_PATTERNS)

        return TalentInfo(
            package=package,
            main_activity=main_activity,
            app_name=package.split(".")[-1].replace("_", " ").title(),
            version=version,
            is_system=is_system,
            is_miko=is_miko,
        )

    def discover_all_talents(self) -> List[TalentInfo]:
        """
        Discover all talents with full info.

        Returns:
            List of TalentInfo objects for all Miko and third-party packages.
        """
        miko_pkgs = self.find_miko_packages()
        third_party_pkgs = self.list_all_packages(include_system=False)

        # Combine and deduplicate
        all_pkgs = list(set(miko_pkgs + third_party_pkgs))
        all_pkgs.sort()

        talents = []
        for pkg in all_pkgs:
            try:
                info = self.get_talent_info(pkg)
                talents.append(info)
            except ADBError as e:
                logger.warning("Failed to inspect package %s: %s", pkg, e)

        logger.info("Discovered %d total talents", len(talents))
        return talents

    # -------------------------------------------------------------------------
    # Talent Lifecycle
    # -------------------------------------------------------------------------

    def launch_talent(
        self,
        package: str,
        activity: str = "",
        extras: Optional[dict] = None,
        wait: bool = True,
    ) -> bool:
        """
        Launch a talent by package and activity.

        Args:
            package: Package name.
            activity: Activity name (auto-discovered if empty).
            extras: Optional intent extras dict.
            wait: Wait for activity to appear.

        Returns:
            True if talent launched successfully.

        Commands:
            Windows & Linux: adb shell am start -n <package>/<activity>
        """
        if not activity:
            activity = self.get_main_activity(package)

        # Build component name
        if not activity.startswith(".") and not activity.startswith(package):
            activity = f".{activity}"
        component = f"{package}/{activity}"

        # Build intent command
        # -W: wait for launch to complete
        # -f 0x10000000: FLAG_ACTIVITY_NEW_TASK
        # --activity-brought-to-front: ensures it comes to top
        cmd = f"am start -W -n {component} -f 0x10000000 --activity-brought-to-front"
        if extras:
            for key, value in extras.items():
                if isinstance(value, str):
                    cmd += f" --es {key} '{value}'"
                elif isinstance(value, int):
                    cmd += f" --ei {key} {value}"
                elif isinstance(value, bool):
                    cmd += f" --ez {key} {str(value).lower()}"

        try:
            result = self.adb.shell(cmd)
            logger.info("Launched: %s -> %s", component, result)

            if wait:
                # am start -W already waits, but we add a small buffer for safety
                import time
                time.sleep(1)
                if not self.adb.wait_for_activity(package, timeout=10):
                    logger.warning("Activity did not appear in foreground")
                    return False
            return True

        except ADBError as e:
            logger.error("Failed to launch %s: %s", component, e)
            return False

    def launch_talent_by_click(
        self,
        package: str,
        coordinates: tuple,
        wait_before: float = 1.0,
        wait_after: float = 3.0,
        pre_clicks: Optional[List[tuple]] = None,
    ) -> bool:
        """
        Launch a talent by clicking on its icon or location.

        Args:
            package: Package name to verify after launch.
            coordinates: (x, y) tuple for clicking the app icon.
            wait_before: Seconds to wait before clicking (for screen prep).
            wait_after: Seconds to wait after clicking (for app to launch).
            pre_clicks: Optional list of [(x, y), ...] to click before launching.

        Returns:
            True if talent launched successfully.
        """
        import time

        try:
            # Execute pre-launch clicks if provided
            if pre_clicks:
                logger.info("Executing %d pre-launch clicks", len(pre_clicks))
                for idx, (x, y) in enumerate(pre_clicks, 1):
                    logger.info("Pre-click %d: (%d, %d)", idx, x, y)
                    self.adb.tap(x, y)
                    time.sleep(0.5)  # Brief pause between pre-clicks

            # Wait before main launch click
            if wait_before > 0:
                time.sleep(wait_before)

            # Click the app icon
            logger.info("Clicking app icon at (%d, %d)", coordinates[0], coordinates[1])
            self.adb.tap(coordinates[0], coordinates[1])

            # Wait after click for app to launch
            if wait_after > 0:
                time.sleep(wait_after)

            # Verify the app launched
            if not self.adb.wait_for_activity(package, timeout=10):
                logger.warning("Activity did not appear after click: %s", package)
                return False

            logger.info("Successfully launched %s via click", package)
            return True

        except Exception as e:
            logger.error("Failed to launch %s by click: %s", package, e)
            return False

    def launch_talent_via_search(
        self,
        package: str,
        apps_button_coords: tuple,
        search_icon_coords: tuple,
        search_text: str,
        search_result_coords: Optional[tuple] = None,
        wait_before_apps: float = 0.5,
        wait_after_apps: float = 1.5,
        wait_after_type: float = 1.5,
        wait_after_click: float = 2.0,
    ) -> bool:
        """
        Launch a talent by searching for it in the apps drawer.

        Flow:
        1. Click on Apps button (from home screen)
        2. Wait for apps drawer to open
        3. Click on search icon
        4. Wait for search box to appear
        5. Type talent name
        6. Wait for search results
        7. Click on search result
        8. Close keyboard
        9. Wait for app to launch

        Args:
            package: Package name to verify after launch.
            apps_button_coords: (x, y) coordinates of Apps button on home screen.
            search_icon_coords: (x, y) coordinates of search icon inside apps drawer.
            search_text: Text to search (e.g., "Storymaker", "Vooks").
            search_result_coords: (x, y) coordinates of search result to click.
                                  If None, tries to auto-detect by finding text.
            wait_before_apps: Seconds to wait before clicking apps button.
            wait_after_apps: Seconds to wait after apps drawer opens.
            wait_after_type: Seconds to wait after typing search text.
            wait_after_click: Seconds to wait after clicking search result.

        Returns:
            True if talent launched successfully.
        """
        import time

        try:
            # Step 1: Click Apps button
            if wait_before_apps > 0:
                time.sleep(wait_before_apps)

            logger.info("Clicking Apps button at (%d, %d)", apps_button_coords[0], apps_button_coords[1])
            self.adb.tap(apps_button_coords[0], apps_button_coords[1])
            time.sleep(wait_after_apps)
            logger.info("Apps drawer opened")

            # Step 2: Click search icon
            logger.info("Clicking search icon at (%d, %d)", search_icon_coords[0], search_icon_coords[1])
            self.adb.tap(search_icon_coords[0], search_icon_coords[1])
            time.sleep(0.5)
            logger.info("Search box opened")

            # Step 3: Type search text
            logger.info("Typing search text: %s", search_text)
            self.adb.input_text(search_text)
            time.sleep(wait_after_type)
            logger.info("Search results loaded")

            # Step 4: Click on search result
            if search_result_coords:
                logger.info("Clicking search result at (%d, %d)", search_result_coords[0], search_result_coords[1])
                self.adb.tap(search_result_coords[0], search_result_coords[1])
            else:
                # Try to auto-detect search result by tapping on text matching the search query
                logger.info("Auto-detecting search result for text: %s", search_text)
                # Fallback: try clicking in the center area where results typically appear
                result_y = search_icon_coords[1] + 150  # Below search icon
                result_x = search_icon_coords[0]
                logger.info("Clicking auto-detected result area at (%d, %d)", result_x, result_y)
                self.adb.tap(result_x, result_y)

            time.sleep(0.5)

            # Step 5: Close keyboard (KEYCODE_BACK = 4)
            logger.info("Closing keyboard")
            self.adb.key_event(4)
            time.sleep(0.5)

            # Step 6: Wait for app to launch
            if wait_after_click > 0:
                time.sleep(wait_after_click)

            # Verify the app launched
            if not self.adb.wait_for_activity(package, timeout=10):
                logger.warning("Activity did not appear after search launch: %s", package)
                return False

            logger.info("Successfully launched %s via search", package)
            return True

        except Exception as e:
            logger.error("Failed to launch %s via search: %s", package, e)
            return False

    def force_stop(self, package: str) -> str:
        """
        Force stop a talent.

        Commands:
            Windows & Linux: adb shell am force-stop <package>
        """
        result = self.adb.shell(f"am force-stop {package}")
        logger.info("Force stopped: %s", package)
        return result

    def clear_data(self, package: str) -> str:
        """
        Clear all data for a talent.

        Commands:
            Windows & Linux: adb shell pm clear <package>
        """
        result = self.adb.shell(f"pm clear {package}")
        logger.info("Cleared data: %s -> %s", package, result)
        return result

    def get_foreground_talent(self) -> Optional[TalentInfo]:
        """
        Identify the currently running foreground talent.

        Returns:
            TalentInfo for the foreground app, or None.

        Commands:
            Windows & Linux:
              adb shell dumpsys activity activities | grep mResumedActivity
              adb shell dumpsys window windows | grep mFocusedApp
        """
        current = self.adb.get_current_activity()
        if not current or "/" not in current:
            return None

        package = current.split("/")[0]
        try:
            return self.get_talent_info(package)
        except ADBError:
            return TalentInfo(package=package)

    def is_talent_installed(self, package: str) -> bool:
        """Check if a talent is installed on the device."""
        try:
            output = self.adb.shell(f"pm path {package}")
            return "package:" in output
        except ADBError:
            return False
