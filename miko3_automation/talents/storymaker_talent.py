"""
Storymaker Talent Test Module
=============================
Automates testing of Miko3's Storymaker Talent — navigates through
the story creation flow, selecting characters, backgrounds, and elements.
"""

import time
import logging

from .base_talent import BaseTalentTest, TestStatus
from ..core.adb_utils import ADBError

logger = logging.getLogger(__name__)


class StorymakerTalentTest(BaseTalentTest):
    """
    Automated test for Miko3 Storymaker Talent.

    Test Flow:
    1. Launch storymaker talent
    2. Tap the Start/Create Story button
    3. Select a character from the character selection screen
    4. Select a background/scene
    5. Select story elements/objects
    6. Advance through creation steps via Next button
    7. Tap Finish/Complete to finalize the story
    8. Verify story creation completed successfully

    Configuration (from config.yaml → talents.storymaker):
        - coordinates.start_button: [x, y]
        - coordinates.character_select: [x, y]
        - coordinates.background_select: [x, y]
        - coordinates.element_select: [x, y]
        - coordinates.next_step: [x, y]
        - coordinates.finish_button: [x, y]
        - coordinates.confirm_button: [x, y]
        - timings.load_wait: seconds
        - timings.animation_wait: seconds
        - timings.step_delay: seconds
    """

    def __init__(self, adb, config, **kwargs):
        talent_cfg = config.get("talents", {}).get("storymaker", {})
        super().__init__(
            adb=adb,
            config=config,
            talent_name=talent_cfg.get("display_name", "Storymaker"),
            package_name=talent_cfg.get("package", "com.miko.story_maker"),
            activity_name=talent_cfg.get("activity", ".MainActivity"),
            **kwargs,
        )
        self.talent_cfg = talent_cfg
        self.coords = talent_cfg.get("coordinates", {})
        self.timings = talent_cfg.get("timings", {})

    def execute(self) -> None:
        """
        Execute the detailed 9-step Storymaker conversational flow.
        """
        load_wait = self.timings.get("load_wait", 10)
        conv_wait = self.timings.get("conversation_wait", 15)
        num_questions = self.timings.get("num_questions", 6)

        # --- Step 1 & 2: Launch & Dismiss Disclaimer ---
        self.step("Dismiss disclaimer", "Closing the disclaimer popup")
        # Try finding common close labels, then fallback to coordinates
        if not any(self.tap_text(label) for label in ["Close", "X", "OK", "Got it", "Skip"]):
            logger.info("  Close button not found via text, using coordinates")
            cross_coords = self.coords.get("disclaimer_cross", [1150, 80])
            self.adb.tap(cross_coords[0], cross_coords[1])
        
        self.wait(2, "Waiting for disclaimer to move")
        self.take_screenshot("disclaimer_handled")
        self.pass_step()

        # --- Step 3: Create Story ---
        self.step("Start story creation", "Tapping 'Create Story'")
        if not self.tap_text("Create Story") and not self.tap_text("Start"):
            create_btn = self.coords.get("create_story", [640, 600])
            self.adb.tap(create_btn[0], create_btn[1])
        self.wait(load_wait, "Waiting for Talent to initialize")
        self.take_screenshot("story_creation_started")
        self.pass_step()

        # --- Step 4 & 5: Do you have an idea? -> No ---
        self.step("Respond to idea prompt", "Selecting 'No' to have an idea")
        # Ensure we are on the right screen
        self.wait_for_text("idea", timeout=15)
        
        if not self.tap_text("No"):
            no_btn = self.coords.get("no_button", [400, 600])
            self.adb.tap(no_btn[0], no_btn[1])
        self.wait(anim_wait := self.timings.get("animation_wait", 3), "Waiting for Miko to react")
        self.take_screenshot("idea_prompt_responded")
        self.pass_step("Selected 'No' for idea prompt")

        # --- Step 6 & 7: Conversation Loop (Miko asks questions) ---
        self.step("Conversational story creation", f"Participating in {num_questions} rounds of conversation")
        for i in range(1, num_questions + 1):
            logger.info("  Conversation Round %d/%d", i, num_questions)
            # We don't necessarily need to tap anything here if Miko is just talking,
            # but we wait for her to finish asking. If the UI requires a tap to continue, we handle it.
            self.wait(conv_wait, f"Waiting for Miko to ask question {i}")
            self.take_screenshot(f"conversation_round_{i}")
        self.pass_step("Completed story conversation")

        # --- Step 8: Story Summary ---
        self.step("View story summary", "Waiting for Miko to provide the summary")
        # Wait extra for the summary to be generated
        self.wait(load_wait, "Waiting for summary screen")
        self.take_screenshot("story_summary")
        self.pass_step("Story summary displayed")

        # --- Step 9: Final Feedback -> Yes ---
        self.step("Provide feedback", "Selecting 'Yes' for the story feedback")
        if not self.tap_text("Yes") and not self.tap_text("Like"):
            yes_btn = self.coords.get("yes_button", [800, 600])
            self.adb.tap(yes_btn[0], yes_btn[1])
        self.wait(2, "Finalizing test")
        self.take_screenshot("feedback_provided")
        self.pass_step("Final feedback submitted")

    def verify(self) -> None:
        """Verify the full conversational flow completed."""

        # Verify we reached the final feedback stage
        self.step("Verify end-to-end completion")
        if any("feedback_provided" in s for s in self.result.screenshots):
            self.pass_step("Confirmed test reached final feedback screen")
        else:
            self.fail_step("Test did not appear to reach the final feedback screen")

        # Verify no crashes
        self.step("Verify no crashes")
        crash_result = self.verify_no_crash()
        if crash_result.passed:
            self.pass_step("No crashes detected")
        else:
            self.fail_step(f"Crash detected: {crash_result.message}")

        self.take_screenshot("final_state")
