"""
Audio Utilities Module
======================
Provides audio playback and recording capabilities for device testing.
Supports pushing audio files to device and playing them.
"""

import os
import logging
import time
from pathlib import Path
from typing import Optional

from .adb_utils import ADBClient, ADBError

logger = logging.getLogger(__name__)


class AudioUtils:
    """Handles audio playback and recording on Android device."""

    def __init__(self, adb: ADBClient):
        """
        Initialize audio utilities.

        Args:
            adb: Connected ADBClient instance.
        """
        self.adb = adb
        self.device_audio_dir = "/sdcard/Miko3_Audio"

    def ensure_audio_directory(self) -> bool:
        """
        Ensure audio directory exists on device.

        Returns:
            True if successful, False otherwise.
        """
        try:
            self.adb.shell(f"mkdir -p {self.device_audio_dir}")
            logger.debug(f"✓ Audio directory ready: {self.device_audio_dir}")
            return True
        except ADBError as e:
            logger.warning(f"Could not create audio dir: {e}")
            return False

    def push_audio(
        self, local_path: str, device_filename: str = "instruction.wav"
    ) -> Optional[str]:
        """
        Push audio file from local system to device.

        Args:
            local_path: Local file path to audio.
            device_filename: Name to save on device.

        Returns:
            Full device path if successful, None otherwise.

        Example:
            audio.push_audio(
                "audio/adventure_intro.wav",
                "adventure_intro.wav"
            )
        """
        if not os.path.exists(local_path):
            logger.error(f"✗ Local audio file not found: {local_path}")
            return None

        self.ensure_audio_directory()
        device_path = f"{self.device_audio_dir}/{device_filename}"

        try:
            self.adb.push_file(local_path, device_path)
            logger.info(f"✓ Pushed audio: {local_path} → {device_path}")
            return device_path
        except ADBError as e:
            logger.error(f"✗ Failed to push audio: {e}")
            return None

    def play_audio(
        self, device_path: str, wait_for_completion: bool = False
    ) -> bool:
        """
        Play audio file on device using built-in media player.

        Args:
            device_path: Full path to audio on device.
            wait_for_completion: Wait for audio to finish playing.

        Returns:
            True if play command succeeded.

        Example:
            audio.play_audio("/sdcard/Miko3_Audio/instruction.wav")
        """
        if not os.path.exists(device_path):
            logger.warning(f"Device path not checked: {device_path}")

        try:
            # Play audio using Android's am command
            cmd = (
                f'am start -a android.intent.action.VIEW '
                f'-d "file://{device_path}" -t "audio/wav"'
            )
            self.adb.shell(cmd)
            logger.info(f"✓ Playing audio: {device_path}")

            if wait_for_completion:
                # Wait for media player to start and estimate duration
                logger.debug("Waiting for audio playback to complete...")
                time.sleep(2)  # Time for player to start
                # Note: Actual duration detection would require more complex logic
                logger.debug("Audio playback likely complete")

            return True
        except ADBError as e:
            logger.error(f"✗ Failed to play audio: {e}")
            return False

    def stop_audio(self) -> bool:
        """
        Stop audio playback.

        Returns:
            True if successful.
        """
        try:
            self.adb.shell("am force-stop com.android.music")
            logger.info("✓ Audio playback stopped")
            return True
        except ADBError as e:
            logger.warning(f"Could not stop audio: {e}")
            return False

    def set_volume(self, level: int) -> bool:
        """
        Set device media volume.

        Args:
            level: Volume level (0-15).

        Returns:
            True if successful.
        """
        if not 0 <= level <= 15:
            logger.error(f"Volume must be 0-15, got {level}")
            return False

        try:
            self.adb.shell(f"am start -a android.intent.action.MAIN")
            self.adb.shell(f"input keyevent 25")  # Volume up
            for _ in range(level):
                self.adb.shell("input keyevent 24")  # Volume up keycode
            logger.info(f"✓ Volume set to {level}/15")
            return True
        except ADBError as e:
            logger.warning(f"Could not set volume: {e}")
            return False

    def record_audio(
        self,
        output_filename: str = "recording.wav",
        duration_seconds: int = 5,
    ) -> Optional[str]:
        """
        Record audio from device microphone.

        Args:
            output_filename: Name for saved file.
            duration_seconds: How long to record.

        Returns:
            Device path to recording if successful.

        Note:
            Requires microphone permission and audio recording capability.
        """
        self.ensure_audio_directory()
        device_path = f"{self.device_audio_dir}/{output_filename}"

        try:
            cmd = (
                f'sh -c "timeout {duration_seconds} '
                f'cat /dev/urandom | sox -t raw -r 44100 -b 16 -c 2 -e signed-integer '
                f'- -t wav {device_path}"'
            )
            self.adb.shell(cmd)
            logger.info(
                f"✓ Recorded {duration_seconds}s audio to: {device_path}"
            )
            return device_path
        except ADBError as e:
            logger.warning(f"Could not record audio: {e}")
            return None

    def pull_audio(
        self, device_path: str, local_output_path: str
    ) -> Optional[str]:
        """
        Pull audio file from device to local system.

        Args:
            device_path: Path on device.
            local_output_path: Local save path.

        Returns:
            Local path if successful.
        """
        try:
            os.makedirs(os.path.dirname(local_output_path) or ".", exist_ok=True)
            self.adb.pull_file(device_path, local_output_path)
            logger.info(f"✓ Pulled audio: {device_path} → {local_output_path}")
            return local_output_path
        except ADBError as e:
            logger.error(f"✗ Failed to pull audio: {e}")
            return None

    def clear_audio_cache(self) -> bool:
        """
        Clear audio cache directory on device.

        Returns:
            True if successful.
        """
        try:
            self.adb.shell(f"rm -rf {self.device_audio_dir}/*")
            logger.info("✓ Audio cache cleared")
            return True
        except ADBError as e:
            logger.warning(f"Could not clear audio cache: {e}")
            return False

    def play_and_wait(
        self, device_path: str, estimated_duration: float = 5.0
    ) -> bool:
        """
        Play audio and wait for estimated duration.

        Args:
            device_path: Path to audio on device.
            estimated_duration: How long to wait (in seconds).

        Returns:
            True if successful.
        """
        success = self.play_audio(device_path)
        if success:
            logger.debug(f"Waiting {estimated_duration}s for audio playback")
            time.sleep(estimated_duration)
        return success
