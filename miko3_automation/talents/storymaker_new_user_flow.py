"""
Storymaker New User Flow Talent Test Module
===========================================
Automates testing of Miko3's Storymaker Talent for New Users:
Launch -> Create -> Conversation -> Review.
"""

import time
import logging

from .base_talent import BaseTalentTest, TestStatus

logger = logging.getLogger(__name__)


class StorymakerNewUserFlowTest(BaseTalentTest):
    """
    Automated E2E test for Miko3 Storymaker Talent (New User Flow).
    Launch -> Create -> Conversation -> Review.
    """

    def __init__(self, adb, config, **kwargs):
        talent_cfg = config.get("talents", {}).get("storymaker", {})
        super().__init__(
            adb=adb,
            config=config,
            talent_name=talent_cfg.get("display_name", "Storymaker (New User)"),
            package_name=talent_cfg.get("package", "com.miko.story_maker"),
            activity_name=talent_cfg.get("activity", ".MainActivity"),
            **kwargs,
        )
        self.talent_cfg = talent_cfg
        self.coords = talent_cfg.get("coordinates", {})
        self.timings = talent_cfg.get("timings", {})
        self.response_phrases = talent_cfg.get("response_phrases", [
            "A brave knight",
            "In a magical forest",
            "A friendly dragon"
        ])

    def execute(self) -> None:
        """
        Execute the new user scenario.
        """
        logger.info("Executing scenario: new_user_flow")

        # Common setup: Launch Verification
        self.step("Launch Verification", f"Verifying {self.talent_name} is launched")
        if not self.adb.wait_for_activity(self.package_name, timeout=15):
            self.fail_step(f"Talent {self.package_name} failed to launch")
            return
        self.pass_step()

        # Talent Stabilization
        self.step("Stabilization", "Waiting for Storymaker to load")
        logger.info("Waiting 8 seconds for talent to stabilize...")
        self.wait(8, "Stabilization wait")
        self.pass_step()

        # Handle AI Disclaimer
        self.step("AI Disclaimer", "Handling initial disclaimer prompt")
        disc_coords = self.coords.get("ai_disclaimer_cross", [154, 120])
        self.adb.tap(disc_coords[0], disc_coords[1])
        self.wait(self.timings.get("animation_wait", 3))
        self.pass_step()

        self._execute_new_user_flow()

    def _execute_new_user_flow(self) -> None:
        """New User: Create -> Converse -> Review."""
        conv_cfg = self.talent_cfg.get("conversation", {})
        
        # --- Step 4: Create Story ---
        self.step("Create Story", "Starting story creation process")
        create_coords = self.coords.get("create_story", [186, 591])
        self.adb.tap(create_coords[0], create_coords[1])
        self.pass_step()

        # --- Step 5: Conversational Loop ---
        self.step("Conversational Interaction", "Detecting listening mode and interacting")
        
        # Wait for Intro to finish and detect listening mode
        logger.info("Waiting for intro to finish...")
        intro_max_wait = conv_cfg.get("intro_max_wait", 45)
        if not self._wait_for_listening_mode(max_wait=intro_max_wait):
            self.fail_step("Listening mode not detected after intro.")
            logger.error("Execution aborted: Listening mode failed.")
            return
            
        # Initial Response ("Yes")
        initial_resp = conv_cfg.get("initial_response", "Yes")
        self._play_and_wait_ack(initial_resp, step_name="initial_response")
        
        num_rounds = conv_cfg.get("num_rounds", 6)
        topics = conv_cfg.get("topic_sentences", self.response_phrases)
        
        for i in range(num_rounds):
            logger.info(f"--- Conversation Round {i+1}/{num_rounds} ---")
            
            # Wait for bot to ask question and enter listening mode
            listening_max_wait = conv_cfg.get("listening_max_wait", 30)
            if not self._wait_for_listening_mode(max_wait=listening_max_wait):
                self.fail_step(f"Listening mode not detected for round {i+1}.")
                logger.error("Execution aborted: Listening mode failed.")
                return
            
            phrase = topics[i % len(topics)]
            self._play_and_wait_ack(phrase, step_name=f"conversation_step_{i+1}")
            
        self.pass_step()

        # --- Wait for Story Building ---
        self.step("Story Building", "Waiting for story to build")
        build_max_wait = conv_cfg.get("story_build_max_wait",60)
        logger.info(f"Waiting up to {build_max_wait}s for story to build...")
        if not self._wait_for_listening_mode(max_wait=build_max_wait):
            self.fail_step("Listening mode not detected after story building.")
            logger.error("Execution aborted: Listening mode failed.")
            return
        self.pass_step()
        
        # --- Final Feedback ---
        self.step("Final Feedback", "Providing feedback to the story")
        final_feedback = conv_cfg.get("final_feedback", "Yes I like this story")
        self._play_and_wait_ack(final_feedback, step_name="final_feedback", wait_after=3)
        self.pass_step()
        
        # --- Phase 4: Read Story & Trigger Like Feature ---
        # We automatically land on the Story Book tab after feedback.
        # Open the newly created story directly using the updated card coordinate.
        self._open_new_story()
        
        # Read through the story to reach the Like button
        self._swipe_story_forward()
        self._like_story()           # Adds the story to the Favorites section
        
        # Close the storybook
        self._swipe_story_backward()
        self._close_storybook()
        
        # --- Phase 5: Validate Favourites & Dislike Toggle State ---
        # Traverse to the Favourites tab to ensure the story appeared
        self._navigate_to_favourite()
        
        # Open the story directly from the Favorites tab
        self._open_story_from_favourite()
        
        # Read through to reach the Like/Dislike toggle
        self._swipe_story_forward()
        self._dislike_story()        # Toggles the Like off, removing it from Favorites
        
        # Close the storybook
        self._swipe_story_backward()
        self._close_storybook()
        
        # --- Exit ---
        self._exit_sequence()

    def _wait_for_listening_mode(self, max_wait: int = 30) -> bool:
        """
        Poll screenshots to detect listening mode (blue waves).
        """
        from PIL import Image
        import os
        import time
        
        conv_cfg = self.talent_cfg.get("conversation", {})
        poll_interval = conv_cfg.get("listening_poll_interval", 3)
        temp_screenshot = os.path.join(self.screenshot_dir, "temp_listening_check.png")
        os.makedirs(self.screenshot_dir, exist_ok=True)
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                # Take temporary screenshot
                self.adb.screenshot(temp_screenshot)
                
                # Analyze image
                img = Image.open(temp_screenshot).convert('RGB')
                width, height = img.size
                
                blue_pixels = 0
                total_pixels = 0
                
                # Sample the left side where blue waves appear
                for x in range(30, min(200, width)):
                    for y in range(100, max(101, height - 100)):
                        r, g, b = img.getpixel((x, y))
                        if b > 150 and r < 100 and g < 200 and b > r * 1.5 and b > g * 1.1:
                            blue_pixels += 1
                        total_pixels += 1
                        
                # Clean up
                img.close()
                if os.path.exists(temp_screenshot):
                    os.remove(temp_screenshot)
                
                ratio = blue_pixels / max(1, total_pixels)
                if ratio > 0.005:  # more than 0.5% blue pixels
                    logger.info(f"✓ Listening mode detected (blue pixel ratio: {ratio:.4f})")
                    return True
                    
            except Exception as e:
                logger.debug(f"Error checking listening mode: {e}")
                
            logger.debug("Listening mode not detected, waiting...")
            time.sleep(poll_interval)
            
        return False

    def _play_and_wait_ack(self, phrase: str, step_name: str, wait_after: int = 2) -> None:
        """Plays speech and waits a moment for the bot to acknowledge it."""
        logger.info(f"Playing response: '{phrase}'")
        self.play_speech(phrase, wait_seconds=5)
        self.wait(wait_after, "Waiting for bot acknowledgement")
        self.take_screenshot(step_name)

    # =========================================================================
    # Extended Read / Like / Dislike Feature Setup
    # =========================================================================
    def _navigate_to_storybook_tab(self) -> None:
        self.step("Navigate to Story Book", "Tapping on the Story Book tab")
        tab_coords = self.coords.get("story_book_tab", [476, 77])
        self.adb.tap(tab_coords[0], tab_coords[1])
        self.wait(1)
        self.take_screenshot("storybook_tab_selected")
        self.pass_step()

    def _navigate_to_favourite(self) -> None:
        self.step("Navigate to Favourite", "Tapping on the Favourite tab")
        tab_coords = self.coords.get("my_adventure_tab", [663, 67])
        self.adb.tap(tab_coords[0], tab_coords[1])
        self.wait(1)
        self.take_screenshot("favourite_tab_selected")
        self.pass_step()

    def _open_new_story(self) -> None:
        self.step("Open New Story", "Tapping on the first newly created story")
        story_card = self.coords.get("new_first_story_card", [300, 400])
        self.adb.tap(story_card[0], story_card[1])
        self.wait(self.timings.get("step_delay", 2))
        self.take_screenshot("new_story_opened")
        self.pass_step()

    def _open_story_from_favourite(self) -> None:
        self.step("Open Story from Favourites", "Tapping on the first story in the Favourites tab")
        story_card = self.coords.get("existing_first_story_card", [590, 370])
        self.adb.tap(story_card[0], story_card[1])
        self.wait(self.timings.get("step_delay", 2))
        self.take_screenshot("favourite_story_opened")
        self.pass_step()

    def _swipe_story_forward(self) -> None:
        swipe_count = self.timings.get("forward_swipe_count", 8)
        self.step("Swipe Forward", f"Swiping forward through {swipe_count} story pages")
        for i in range(swipe_count):
            self.adb.swipe(1100, 360, 200, 360, 250)
            self.wait(2)
        self.pass_step()

    def _swipe_story_backward(self) -> None:
        swipe_count = self.timings.get("backward_swipe_count", 8)
        self.step("Swipe Backward", f"Swiping backward through {swipe_count} story pages")
        for i in range(swipe_count):
            self.adb.swipe(200, 360, 1100, 360, 250)
            self.wait(2)
        self.pass_step()

    def _like_story(self) -> None:
        self.step("Like Story", "Tapping the like icon on the story")
        like_coords = self.coords.get("like_icon", [325, 525])
        self.adb.tap(640, 360)
        self.wait(1)
        self.adb.swipe(like_coords[0], like_coords[1], like_coords[0], like_coords[1], 250)
        self.wait(self.timings.get("step_delay", 2))
        self.take_screenshot("story_liked")
        self.pass_step()

    def _dislike_story(self) -> None:
        self.step("Dislike Story", "Tapping the dislike icon to remove from favorites")
        dislike_coords = self.coords.get("dislike_icon", [307, 475])
        self.adb.tap(640, 360)
        self.wait(1)
        self.adb.swipe(dislike_coords[0], dislike_coords[1], dislike_coords[0], dislike_coords[1], 250)
        self.wait(self.timings.get("step_delay", 2))
        self.take_screenshot("story_disliked")
        self.pass_step()

    def _close_storybook(self) -> None:
        self.step("Close Storybook", "Tapping cross icon to close storybook viewer")
        close_coords = self.coords.get("close_storybook_icon", [40, 53])
        self.adb.tap(close_coords[0], close_coords[1])
        self.wait(self.timings.get("step_delay", 2))
        self.take_screenshot("storybook_closed")
        self.pass_step()

    def _exit_sequence(self) -> None:
        """Common exit logic to return to home."""
        self.step("Exit Sequence", "Exiting Storymaker to root")
        
        # 1. Exit button
        exit_btn = self.coords.get("click_on_exit_button", [71, 73])
        self.adb.tap(exit_btn[0], exit_btn[1])
        self.wait(2)
        
        # 2. Confirm (Yes)
        confirm_btn = self.coords.get("yes_button", [1114, 630])
        self.adb.tap(confirm_btn[0], confirm_btn[1])
        self.wait(3)
        
        # 3. Root Exit
        root_btn = self.coords.get("exit_button_to_root_screen", [55, 77])
        self.adb.tap(root_btn[0], root_btn[1])
        self.wait(2)
        
        self.pass_step()

    def verify(self) -> None:
        """Verify no crashes."""
        # If any step previously failed, we abort verification immediately to save time
        if any(s.status == TestStatus.FAILED for s in self.result.steps):
            logger.info("Skipping verification due to previous test failure.")
            return

        self.step("Final Verification")
        if self.verify_no_crash().passed:
            self.pass_step("Test completed without crashes")
        else:
            self.fail_step("Crash detected during test")

