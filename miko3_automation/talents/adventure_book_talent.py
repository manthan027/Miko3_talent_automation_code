"""
Adventure Book Talent Test Module
=============================
Automates testing of Miko3's Adventure Book Talent.
"""

import logging
from .base_talent import BaseTalentTest

logger = logging.getLogger(__name__)

class AdventureBookTalentTest(BaseTalentTest):
    """
    Automated test for Miko3 Adventure Book Talent.
    Uses the robust base class for launch and execution.
    """

    def __init__(self, adb, config, **kwargs):
        talent_cfg = config.get("talents", {}).get("adventure_book", {})
        super().__init__(
            adb=adb,
            config=config,
            talent_name=talent_cfg.get("display_name", "Adventure Book"),
            package_name=talent_cfg.get("package", "com.miko.story_maker"),
            activity_name=talent_cfg.get("activity", ".MainActivity"),
            **kwargs,
        )
        self.coords = talent_cfg.get("coordinates", {})
        self.timings = talent_cfg.get("timings", {})

    def execute(self) -> None:
        """Execute the adventure book talent test steps."""
        load_wait = self.timings.get("load_wait", 10)
        
        # Step 1: Select first story
        self.step("Select story from list", "Tapping the first story in the list")
        story_btn = self.coords.get("story_list_first", [640, 200])
        # Try text-based first for robustness
        if not self.tap_text("Adventure") and not self.tap_text("Book"):
            self.adb.tap(story_btn[0], story_btn[1])
        
        self.wait(load_wait, "Waiting for story details to load")
        self.take_screenshot("story_selected")
        self.pass_step("Story selected")

        # Step 2: Start session
        self.step("Start session", "Tapping Play/Start")
        if not self.tap_text("Play") and not self.tap_text("Start"):
            # Fallback to coordinates
            self.adb.tap(640, 500) # Probable play button position
        
        self.wait(5, "Waiting for session to begin")
        self.take_screenshot("session_started")
        self.pass_step()

    def verify(self) -> None:
        """Verify the test results."""
        self.step("Verify activity foreground")
        self.verify_activity(self.package_name)

        self.step("Verify no crashes")
        self.verify_no_crash()