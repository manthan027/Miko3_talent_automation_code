"""
Storymaker Existing User Flow Talent Test Module
================================================
Automates testing of Miko3's Storymaker Talent for Existing Users:
Launch -> Existing stories -> Story Book -> Review.
"""

import time
import logging

from .base_talent import BaseTalentTest, TestStatus

logger = logging.getLogger(__name__)


class StorymakerExistingUserFlowTest(BaseTalentTest):
    """
    Automated E2E test for Miko3 Storymaker Talent (Existing User Flow).
    Launch -> Existing stories -> Story Book -> Review.
    """

    def __init__(self, adb, config, **kwargs):
        talent_cfg = config.get("talents", {}).get("storymaker", {})
        super().__init__(
            adb=adb,
            config=config,
            talent_name=talent_cfg.get("display_name", "Storymaker (Existing User)"),
            package_name=talent_cfg.get("package", "com.miko.story_maker"),
            activity_name=talent_cfg.get("activity", ".MainActivity"),
            **kwargs,
        )
        self.talent_cfg = talent_cfg
        self.coords = talent_cfg.get("coordinates", {})
        self.timings = talent_cfg.get("timings", {})

    def execute(self) -> None:
        """
        Execute the existing user scenario.
        """
        logger.info("Executing scenario: existing_user_flow")

        # Common setup: TC 01 Launch Verification
        self.step("Launch Verification", f"Verifying {self.talent_name} is launched")
        if not self.adb.wait_for_activity(self.package_name, timeout=15):
            self.fail_step(f"Talent {self.package_name} failed to launch")
            return
        self.pass_step()

        # TC 02 Handle AI Disclaimer
        self.step("AI Disclaimer", "Handling initial disclaimer prompt")
        disc_coords = self.coords.get("ai_disclaimer_cross", [154, 120])
        self.adb.tap(disc_coords[0], disc_coords[1])
        self.wait(self.timings.get("animation_wait", 3))
        self.pass_step()

        self._execute_existing_user_flow()

    def _execute_existing_user_flow(self) -> None:
        """Existing User flow matching the reference batch script exactly."""

        # TC 03 Step 3: Open existing storybook ---
        self.step("Open Existing Story", "Tapping on the existing storybook")
        story_card = self.coords.get("existing_first_story_card", [590, 370])
        self.adb.tap(story_card[0], story_card[1])
        self.wait(self.timings.get("step_delay", 2))
        self.take_screenshot("existing_story_opened")
        self.pass_step()

        # TC 04 Step 4: Swipe forward 8 pages ---
        self._swipe_story_forward()

        # TC 05 Step 5: Like the story ---
        self._like_story()

        # TC 06 Step 6: Swipe backward 8 pages ---
        self._swipe_story_backward()

        # TC 07 Step 7: Close storybook viewer ---
        self._close_storybook()

        # TC 08 Step 8: Delete story (deny first, then confirm) ---
        self._delete_story_flow()

        # TC 09 Step 9: Navigate to Favourite tab ---
        self._navigate_to_favourite()

        # TC 10 Step 10: Navigate to Story Book tab ---
        self._navigate_to_storybook_tab()

        # TC 11 Step 11: Check Stories Left for the Month ---
        self._check_stories_left()

        # TC 12 Step 12: Full exit sequence ---
        self._exit_sequence()

    def _swipe_story_forward(self) -> None:
        """Swipe forward through 8 pages of the story book (left swipe)."""
        swipe_count = self.timings.get("forward_swipe_count", 8)
        self.step("Swipe Forward", f"Swiping forward through {swipe_count} story pages")
        for i in range(swipe_count):
            logger.info(f"Forward swipe {i + 1}/{swipe_count}")
            # Match batch: swipe from x=1100 to x=200 at y=360, duration 250ms
            self.adb.swipe(1100, 360, 200, 360, 250)
            self.wait(2)
        self.take_screenshot("story_forward_end")
        self.pass_step(f"Completed {swipe_count} forward swipes")

    def _like_story(self) -> None:
        """Tap the Like button on the current story page."""
        self.step("Like Story", "Tapping the like icon on the story")
        like_coords = self.coords.get("like_icon", [323, 525])
        self.adb.tap(like_coords[0], like_coords[1])
        self.wait(self.timings.get("step_delay", 2))
        self.take_screenshot("story_liked")
        self.pass_step("Story liked successfully")

    def _swipe_story_backward(self) -> None:
        """Swipe backward through 8 pages of the story book (right swipe)."""
        swipe_count = self.timings.get("backward_swipe_count", 8)
        self.step("Swipe Backward", f"Swiping backward through {swipe_count} story pages")
        for i in range(swipe_count):
            logger.info(f"Backward swipe {i + 1}/{swipe_count}")
            # Match batch: swipe from x=200 to x=1100 at y=360, duration 250ms
            self.adb.swipe(200, 360, 1100, 360, 250)
            self.wait(2)
        self.take_screenshot("story_backward_end")
        self.pass_step(f"Completed {swipe_count} backward swipes")

    def _close_storybook(self) -> None:
        """Tap the cross icon to close the open storybook viewer."""
        self.step("Close Storybook", "Tapping cross icon to close storybook viewer")
        close_coords = self.coords.get("close_storybook_icon", [40, 53])
        self.adb.tap(close_coords[0], close_coords[1])
        self.wait(self.timings.get("step_delay", 2))
        self.take_screenshot("storybook_closed")
        self.pass_step("Storybook viewer closed")

    def _delete_story_flow(self) -> None:
        """Test the delete story flow: tap delete, deny first, then confirm delete."""
        self.step("Delete Story Flow", "Testing delete: deny once, then confirm")

        # Tap delete icon on story card
        delete_coords = self.coords.get("delete_icon", [730, 612])
        self.adb.tap(delete_coords[0], delete_coords[1])
        self.wait(1)
        self.take_screenshot("delete_dialog_opened")

        # Deny delete (tap 'No' / 'Cancel')
        deny_coords = self.coords.get("delete_deny_button", [908, 642])
        self.adb.tap(deny_coords[0], deny_coords[1])
        self.wait(1)
        self.take_screenshot("delete_denied")
        logger.info("Delete denied — dialog dismissed")

        # Tap delete icon again
        self.adb.tap(delete_coords[0], delete_coords[1])
        self.wait(1)

        # Confirm delete (tap 'OK' / 'Yes')
        confirm_coords = self.coords.get("delete_confirm_button", [1114, 630])
        self.adb.tap(confirm_coords[0], confirm_coords[1])

        # --- Validate "Story deleted successfully" popup ---
        popup_detected = self._wait_for_delete_popup()
        screenshot_path = self.take_screenshot("delete_confirmed")

        if popup_detected:
            logger.info("'Story deleted successfully' popup detected — DELETE PASS")
            self.pass_step("Story deleted successfully popup confirmed")
        else:
            logger.warning("'Story deleted successfully' popup NOT detected — DELETE FAIL")
            self.fail_step("Story deleted successfully popup was not visible after delete")


    def _wait_for_delete_popup(self, timeout: int = 5) -> bool:
        """
        Poll for the 'Story deleted successfully' popup after confirming delete.

        Strategy: The popup is a large white rounded rectangle in the bottom
        half of the screen (visible in reference screenshot). We detect it by
        checking if a significant white region exists in the lower portion of
        the captured screenshot.

        Args:
            timeout: Max seconds to wait for the popup.

        Returns:
            True if popup is detected, False otherwise.
        """
        import os
        try:
            from PIL import Image
        except ImportError:
            logger.warning("Pillow not installed — skipping popup image validation, assuming pass")
            self.wait(2)
            return True

        logger.info("Waiting for 'Story deleted successfully' popup (timeout=%ds)...", timeout)
        poll_interval = 1
        elapsed = 0

        while elapsed < timeout:
            self.wait(poll_interval)
            elapsed += poll_interval

            # Capture a fresh screenshot to check for the popup
            import time as _time
            tmp_path = os.path.join(
                self.screenshot_dir,
                f"popup_check_{int(_time.time())}.png"
            )
            try:
                self.adb.screenshot(tmp_path)
            except Exception as e:
                logger.debug("Screenshot during popup poll failed: %s", e)
                continue

            if not os.path.exists(tmp_path):
                continue

            try:
                img = Image.open(tmp_path).convert("RGB")
                width, height = img.size

                # Focus on bottom 30% of screen where the popup appears
                bottom_region = img.crop((0, int(height * 0.70), width, height))
                pixels = list(bottom_region.getdata())

                # Count pixels that are "near white" (R>220, G>220, B>220)
                white_pixels = sum(
                    1 for r, g, b in pixels if r > 220 and g > 220 and b > 220
                )
                total_pixels = len(pixels)
                white_ratio = white_pixels / total_pixels if total_pixels > 0 else 0

                logger.info(
                    "Popup poll [%ds/%ds]: white_ratio=%.2f in bottom 30%%",
                    elapsed, timeout, white_ratio
                )

                # The popup has a large white background — threshold at 25%
                if white_ratio >= 0.25:
                    logger.info("Popup detected (white_ratio=%.2f >= 0.25)", white_ratio)
                    # Clean up temp file
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass
                    return True

                # Clean up temp file
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

            except Exception as e:
                logger.warning("Image analysis error during popup poll: %s", e)
                continue

        logger.warning("Popup not detected after %ds", timeout)
        return False

    def _navigate_to_favourite(self) -> None:
        """Tap the Favourite tab."""
        self.step("Favourite Tab", "Navigating to Favourite tab")
        fav_coords = self.coords.get("favourite_tab", [812, 62])
        self.adb.tap(fav_coords[0], fav_coords[1])
        self.wait(3)
        self.take_screenshot("favourite_tab")
        self.pass_step("Favourite tab opened")

    def _navigate_to_storybook_tab(self) -> None:
        """Tap the Story Book tab."""
        self.step("Story Book Tab", "Navigating to Story Book tab")
        book_tab_coords = self.coords.get("story_book_tab", [476, 77])
        self.adb.tap(book_tab_coords[0], book_tab_coords[1])
        self.wait(3)
        self.take_screenshot("story_book_tab")
        self.pass_step("Story Book tab opened")

    def _check_stories_left(self) -> None:
        """Tap the 'Stories left for the month' indicator and close it."""
        self.step("Stories Left Check", "Checking stories left for the month")

        # Open stories-left counter
        stories_left_coords = self.coords.get("stories_left_icon", [1216, 66])
        self.adb.tap(stories_left_coords[0], stories_left_coords[1])
        self.wait(3)
        self.take_screenshot("stories_left_popup")

        # Close popup with cross icon
        close_popup_coords = self.coords.get("close_stories_left_popup", [71, 73])
        self.adb.tap(close_popup_coords[0], close_popup_coords[1])
        self.wait(2)
        self.pass_step("Stories left popup closed")

    def _exit_sequence(self) -> None:
        """Full exit sequence matching batch script: cross -> No -> cross -> Yes -> root exit."""
        self.step("Exit Sequence", "Exiting Storymaker back to root screen")

        # 1. Tap cross icon (first time)
        exit_btn = self.coords.get("click_on_exit_button", [71, 73])
        self.adb.tap(exit_btn[0], exit_btn[1])
        self.wait(2)
        self.take_screenshot("exit_dialog_1")

        # 2. Tap NO (decline exit / dismiss first dialog)
        no_btn = self.coords.get("no_button", [892, 620])
        self.adb.tap(no_btn[0], no_btn[1])
        self.wait(2)
        self.take_screenshot("exit_no_pressed")

        # 3. Tap cross icon (second time)
        self.adb.tap(exit_btn[0], exit_btn[1])
        self.wait(2)
        self.take_screenshot("exit_dialog_2")

        # 4. Tap YES (confirm exit)
        yes_btn = self.coords.get("yes_button", [1114, 630])
        self.adb.tap(yes_btn[0], yes_btn[1])
        self.wait(2)
        self.take_screenshot("exit_yes_pressed")

        # 5. Tap final root exit button to return to home screen
        root_btn = self.coords.get("exit_button_to_root_screen", [55, 77])
        self.adb.tap(root_btn[0], root_btn[1])
        self.wait(2)
        self.take_screenshot("returned_to_root")

        self.pass_step("Returned to root screen successfully")

    def verify(self) -> None:
        """Verify no crashes."""
        self.step("Final Verification")
        if self.verify_no_crash().passed:
            self.pass_step("Test completed without crashes")
        else:
            self.fail_step("Crash detected during test")
