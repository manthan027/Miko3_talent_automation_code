#!/usr/bin/env python3
"""
Example: Using Audio and TTS in Talent Tests
==============================================
This script demonstrates how to integrate TTS and audio playback
in your Miko3 talent tests.

Usage:
    python examples/example_audio_in_talents.py
"""

import logging
from miko3_automation.core.adb_utils import ADBClient
from miko3_automation.core.device_manager import DeviceManager
from miko3_automation.talents.base_talent import BaseTalentTest, TestStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AudioEnabledStorymakerTest(BaseTalentTest):
    """
    Example: Storymaker test with TTS narration and guidance.
    
    This demonstrates:
    - Generating speech from text
    - Playing audio on device
    - Using different voices
    - Batch generating dialogue
    """

    def __init__(self, adb, config, **kwargs):
        super().__init__(
            adb=adb,
            config=config,
            talent_name="Storymaker",
            package_name="com.miko.story_maker",
            **kwargs,
        )

    def execute(self):
        """Execute storymaker test with audio narration."""
        
        # --- Batch generate all dialogue at start ---
        self.step("Pre-generate dialogue")
        logger.info("Generating all audio files...")
        
        dialogue = {
            "greeting": "Welcome to the story maker talent",
            "disclaimer_close": "Let me close this disclaimer for you",
            "start_creation": "Now let's create your story",
            "no_idea": "I'll decide for you, let's say no to having an idea",
            "listen_questions": "Miko will now ask us some questions",
            "almost_done": "We're almost done creating the story",
            "completed": "Your story has been created successfully",
        }
        
        self.audio_files = self.batch_generate_speech(dialogue)
        self.pass_step("All audio generated")
        
        # --- Step 1: Launch and Play Greeting ---
        self.step("Launch talent with greeting")
        self.play_audio_file(self.audio_files["greeting"], wait_seconds=3)
        self.pass_step()
        
        # --- Step 2: Dismiss Disclaimer ---
        self.step("Dismiss disclaimer with audio cue")
        self.play_audio_file(
            self.audio_files["disclaimer_close"], 
            wait_seconds=2
        )
        
        if not any(self.tap_text(label) for label in ["Close", "X", "OK"]):
            self.adb.tap(1150, 80)
        
        self.wait(2)
        self.take_screenshot("disclaimer_closed")
        self.pass_step()
        
        # --- Step 3: Start Story Creation ---
        self.step("Start story creation with audio")
        self.play_audio_file(
            self.audio_files["start_creation"],
            wait_seconds=2
        )
        
        if not self.tap_text("Create Story"):
            self.adb.tap(640, 600)
        
        self.wait_for_text("Create", timeout=15)
        self.take_screenshot("creation_started")
        self.pass_step()
        
        # --- Step 4: Respond to Idea Prompt ---
        self.step("Respond to idea prompt with audio")
        self.play_audio_file(
            self.audio_files["no_idea"],
            wait_seconds=3
        )
        
        self.wait_for_text("idea", timeout=15)
        if not self.tap_text("No"):
            self.adb.tap(400, 600)
        
        self.wait(3)
        self.take_screenshot("idea_responded")
        self.pass_step()
        
        # --- Step 5: Conversation Loop ---
        self.step("Interactive conversation with audio cues")
        self.play_audio_file(
            self.audio_files["listen_questions"],
            wait_seconds=2
        )
        
        # In a real test, you'd automate actual responses
        # For now, just simulate conversation
        for i in range(3):
            logger.info(f"Question {i+1}")
            self.wait(2)
            
            # Simulate response
            if self.find_text("Next"):
                self.tap_text("Next")
            elif self.find_text("Continue"):
                self.tap_text("Continue")
            else:
                self.adb.tap(640, 500)
            
            self.wait(2)
        
        self.take_screenshot("conversation_complete")
        self.pass_step()
        
        # --- Step 6: Complete Story ---
        self.step("Complete story creation")
        self.play_audio_file(
            self.audio_files["almost_done"],
            wait_seconds=2
        )
        
        if self.tap_text("Finish"):
            self.wait(2)
        else:
            self.adb.tap(640, 100)
        
        self.wait(3)
        self.take_screenshot("story_finished")
        
        # --- Step 7: Success ---
        self.play_audio_file(
            self.audio_files["completed"],
            wait_seconds=3
        )
        
        self.pass_step("Story creation completed successfully")

    def verify(self):
        """Verify test results."""
        self.step("Verify app is still running")
        self.verify_activity(self.package_name)
        
        self.step("Verify no crashes")
        self.verify_no_crash()


class QuickTTSExample(BaseTalentTest):
    """
    Simple example showing quick TTS usage.
    """

    def execute(self):
        """Quick example of TTS."""
        
        # One-liner: convert and play
        self.step("Simple TTS example")
        self.play_speech("Welcome to this test")
        
        # Generate speech only (don't play)
        self.step("Generate and save audio")
        audio = self.generate_speech("This is a saved message", "saved.wav")
        logger.info(f"Saved to: {audio}")
        
        # Use different voice
        self.step("Try different voices")
        self.play_speech(
            "Male voice narration",
            voice="en-US-GuyNeural",
            provider="edge"
        )
        
        # Use Google TTS
        self.step("Google TTS example")
        self.play_speech(
            "Google TTS sounds basic",
            provider="google"
        )
        
        self.pass_step()

    def verify(self):
        """Minimal verification."""
        logger.info("Quick example completed")


def example_1_audio_enabled_test():
    """Run full audio-enabled storymaker test."""
    logger.info("=" * 60)
    logger.info("Example 1: Audio-Enabled Storymaker Test")
    logger.info("=" * 60)
    
    try:
        from pathlib import Path
        import yaml
        
        # Load config
        config_path = Path(__file__).parent.parent / "config" / "config.yaml"
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
        # Connect device
        device_mgr = DeviceManager(config)
        adb = device_mgr.connect()
        
        # Run test
        test = AudioEnabledStorymakerTest(adb, config)
        result = test.run()
        
        logger.info(f"\nTest {result.status.value}")
        logger.info(f"Duration: {result.duration:.1f}s")
        logger.info(f"Steps: {result.step_summary}")
        
    except Exception as e:
        logger.error(f"Example failed: {e}", exc_info=True)


def example_2_quick_tts():
    """Quick TTS example without full device setup."""
    logger.info("=" * 60)
    logger.info("Example 2: Quick TTS Generation")
    logger.info("=" * 60)
    
    from miko3_automation.core.tts_utils import TextToSpeech
    
    # Create TTS instance
    tts = TextToSpeech()
    
    # Example 1: Edge TTS (recommended)
    logger.info("\n1. Edge TTS (female voice)")
    audio = tts.edge_tts(
        "Welcome to the adventure",
        "audio/example_edge.wav"
    )
    logger.info(f"✓ Generated: {audio}")
    
    # Example 2: Edge TTS with male voice
    logger.info("\n2. Edge TTS (male voice)")
    audio = tts.edge_tts(
        "Let's create a story",
        "audio/example_male.wav",
        voice="en-US-GuyNeural"
    )
    logger.info(f"✓ Generated: {audio}")
    
    # Example 3: Google TTS
    logger.info("\n3. Google TTS")
    audio = tts.google_tts(
        "Google TTS example",
        "audio/example_google.wav"
    )
    logger.info(f"✓ Generated: {audio}")
    
    # Example 4: Batch generation
    logger.info("\n4. Batch Generation")
    texts = {
        "greeting": "Hello everyone",
        "instruction": "Tap the button below",
        "success": "Great job!"
    }
    results = tts.batch_convert(texts)
    for name, path in results.items():
        logger.info(f"  ✓ {name}: {path}")


def example_3_display_voices():
    """Display available voices."""
    logger.info("=" * 60)
    logger.info("Example 3: Available Voices")
    logger.info("=" * 60)
    
    from miko3_automation.core.tts_utils import TextToSpeech
    
    tts = TextToSpeech()
    tts.list_edge_voices()


if __name__ == "__main__":
    import sys
    
    examples = {
        "1": ("Full Audio Test", example_1_audio_enabled_test),
        "2": ("Quick TTS Examples", example_2_quick_tts),
        "3": ("Show Voices", example_3_display_voices),
    }
    
    print("\nMiko3 Audio & TTS Examples")
    print("=" * 60)
    print("\nAvailable examples:")
    for key, (name, _) in examples.items():
        print(f"  {key}. {name}")
    print(f"  {len(examples)+1}. Run all")
    
    choice = input("\nSelect example (1-{}, or 'q' to quit): ".format(len(examples)+1))
    
    if choice.lower() == 'q':
        sys.exit(0)
    elif choice == str(len(examples)+1):
        for name, func in examples.values():
            try:
                func()
                print()
            except Exception as e:
                logger.error(f"Example failed: {e}")
    elif choice in examples:
        name, func = examples[choice]
        logger.info(f"Running: {name}")
        try:
            func()
        except Exception as e:
            logger.error(f"Example failed: {e}", exc_info=True)
    else:
        print("Invalid choice")
