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
            logger.warning("Listening mode not detected after intro, proceeding anyway")
            
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
                logger.warning(f"Listening mode not detected for round {i+1}, proceeding anyway")
            
            phrase = topics[i % len(topics)]
            self._play_and_wait_ack(phrase, step_name=f"conversation_step_{i+1}")
            
        self.pass_step()

        # --- Wait for Story Building ---
        self.step("Story Building", "Waiting for story to build")
        build_max_wait = conv_cfg.get("story_build_max_wait",60)
        logger.info(f"Waiting up to {build_max_wait}s for story to build...")
        self._wait_for_listening_mode(max_wait=build_max_wait)
        self.pass_step()
        
        # --- Final Feedback ---
        self.step("Final Feedback", "Providing feedback to the story")
        final_feedback = conv_cfg.get("final_feedback", "Yes I like this story")
        self._play_and_wait_ack(final_feedback, step_name="final_feedback", wait_after=3)
        self.pass_step()
        
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
        self.step("Final Verification")
        if self.verify_no_crash().passed:
            self.pass_step("Test completed without crashes")
        else:
            self.fail_step("Crash detected during test")

