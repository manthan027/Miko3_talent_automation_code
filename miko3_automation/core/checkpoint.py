"""
Checkpoint Manager Module
========================
Manages test progress checkpoints for resume capability.
Allows tests to save state and resume after network interruption.
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


class CheckpointManager:
    """
    Manages test progress checkpoints for resume capability.

    Usage:
        checkpoint = CheckpointManager()

        # Save checkpoint after each step
        checkpoint.save_checkpoint("video_test", {
            "current_step": 3,
            "step_name": "play_video",
            "activity": "com.miko.video/.MainActivity",
            "data": {"video_played": True}
        })

        # Load checkpoint to resume
        saved = checkpoint.load_checkpoint("video_test")
        if saved:
            resume_from(saved)

        # Clear after successful completion
        checkpoint.clear_checkpoint("video_test")
    """

    def __init__(self, checkpoint_dir: str = "checkpoints"):
        """
        Initialize checkpoint manager.

        Args:
            checkpoint_dir: Directory to store checkpoint files.
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def _get_checkpoint_path(self, test_name: str) -> Path:
        """Get path for checkpoint file."""
        safe_name = test_name.replace(" ", "_").replace("/", "_")
        return self.checkpoint_dir / f"{safe_name}.json"

    def save_checkpoint(
        self,
        test_name: str,
        state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Save test state to checkpoint file.

        Args:
            test_name: Name of the test.
            state: State dictionary to save (current_step, activity, data, etc.)
            metadata: Optional metadata (test_name, timestamp, etc.)

        Returns:
            Path to the saved checkpoint file.
        """
        checkpoint_path = self._get_checkpoint_path(test_name)

        checkpoint_data = {
            "test_name": test_name,
            "timestamp": datetime.now().isoformat(),
            "timestamp_unix": time.time(),
            "state": state,
            "metadata": metadata or {},
        }

        # Add default metadata if not provided
        checkpoint_data["metadata"].setdefault(
            "step_count", state.get("current_step", 0)
        )
        checkpoint_data["metadata"].setdefault(
            "last_action", state.get("step_name", "unknown")
        )

        try:
            with open(checkpoint_path, "w", encoding="utf-8") as f:
                json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)

            logger.debug(
                "Checkpoint saved: %s (step %d)",
                test_name,
                state.get("current_step", 0),
            )
            return str(checkpoint_path)

        except Exception as e:
            logger.error("Failed to save checkpoint: %s", e)
            raise

    def load_checkpoint(self, test_name: str) -> Optional[Dict[str, Any]]:
        """
        Load latest checkpoint for a test.

        Args:
            test_name: Name of the test.

        Returns:
            Checkpoint data dict, or None if no checkpoint exists.
        """
        checkpoint_path = self._get_checkpoint_path(test_name)

        if not checkpoint_path.exists():
            logger.debug("No checkpoint found for: %s", test_name)
            return None

        try:
            with open(checkpoint_path, "r", encoding="utf-8") as f:
                checkpoint_data = json.load(f)

            logger.info(
                "Checkpoint loaded for %s (step %d)",
                test_name,
                checkpoint_data.get("state", {}).get("current_step", 0),
            )
            return checkpoint_data

        except json.JSONDecodeError as e:
            logger.warning("Corrupted checkpoint file for %s: %s", test_name, e)
            return None
        except Exception as e:
            logger.error("Failed to load checkpoint: %s", e)
            return None

    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """
        List all available checkpoints.

        Returns:
            List of checkpoint info dicts.
        """
        checkpoints = []

        for checkpoint_file in self.checkpoint_dir.glob("*.json"):
            try:
                with open(checkpoint_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                checkpoints.append(
                    {
                        "test_name": data.get("test_name", checkpoint_file.stem),
                        "timestamp": data.get("timestamp", ""),
                        "step": data.get("state", {}).get("current_step", 0),
                        "last_action": data.get("state", {}).get(
                            "step_name", "unknown"
                        ),
                        "path": str(checkpoint_file),
                    }
                )
            except Exception as e:
                logger.warning("Could not read checkpoint %s: %s", checkpoint_file, e)

        return sorted(checkpoints, key=lambda x: x.get("timestamp", ""), reverse=True)

    def has_checkpoint(self, test_name: str) -> bool:
        """Check if a checkpoint exists for the test."""
        return self._get_checkpoint_path(test_name).exists()

    def clear_checkpoint(self, test_name: str) -> bool:
        """
        Clear checkpoint after successful completion.

        Args:
            test_name: Name of the test.

        Returns:
            True if checkpoint was cleared, False if it didn't exist.
        """
        checkpoint_path = self._get_checkpoint_path(test_name)

        if checkpoint_path.exists():
            try:
                checkpoint_path.unlink()
                logger.info("Checkpoint cleared for: %s", test_name)
                return True
            except Exception as e:
                logger.error("Failed to clear checkpoint: %s", e)
                return False

        return False

    def clear_all_checkpoints(self) -> int:
        """
        Clear all checkpoint files.

        Returns:
            Number of checkpoints cleared.
        """
        count = 0
        for checkpoint_file in self.checkpoint_dir.glob("*.json"):
            try:
                checkpoint_file.unlink()
                count += 1
            except Exception as e:
                logger.warning("Failed to delete %s: %s", checkpoint_file, e)

        logger.info("Cleared %d checkpoints", count)
        return count

    def get_checkpoint_age(self, test_name: str) -> Optional[float]:
        """
        Get age of checkpoint in seconds.

        Args:
            test_name: Name of the test.

        Returns:
            Age in seconds, or None if no checkpoint exists.
        """
        checkpoint = self.load_checkpoint(test_name)
        if not checkpoint:
            return None

        return time.time() - checkpoint.get("timestamp_unix", 0)


class TestCheckpointMixin:
    """
    Mixin class to add checkpoint capability to test classes.

    Usage:
        class MyTest(TestCheckpointMixin, BaseTalentTest):
            def run(self):
                # Save checkpoint before each step
                self.save_checkpoint(current_step=1, step_name="launch_app")
                # ... do step ...

                # Resume from checkpoint if available
                checkpoint = self.load_checkpoint()
                if checkpoint:
                    self.resume_from_checkpoint(checkpoint)
    """

    def __init__(self, *args, checkpoint_name: Optional[str] = None, **kwargs):
        """
        Initialize with checkpoint support.

        Args:
            checkpoint_name: Name for checkpoint file (defaults to class name).
        """
        super().__init__(*args, **kwargs)
        self._checkpoint_manager = CheckpointManager()
        self._checkpoint_name = checkpoint_name or self.__class__.__name__

    def save_checkpoint(
        self,
        current_step: int,
        step_name: str,
        additional_state: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Save current test progress.

        Args:
            current_step: Current step number.
            step_name: Name/description of current step.
            additional_state: Any additional state data to save.
        """
        state = {
            "current_step": current_step,
            "step_name": step_name,
        }

        if additional_state:
            state.update(additional_state)

        try:
            self._checkpoint_manager.save_checkpoint(self._checkpoint_name, state)
        except Exception as e:
            logger.warning("Failed to save checkpoint: %s", e)

    def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Load saved checkpoint if exists."""
        return self._checkpoint_manager.load_checkpoint(self._checkpoint_name)

    def has_checkpoint(self) -> bool:
        """Check if checkpoint exists."""
        return self._checkpoint_manager.has_checkpoint(self._checkpoint_name)

    def clear_checkpoint(self) -> None:
        """Clear checkpoint after successful completion."""
        self._checkpoint_manager.clear_checkpoint(self._checkpoint_name)

    def resume_from_checkpoint(self, checkpoint_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resume test from checkpoint.

        Args:
            checkpoint_data: Loaded checkpoint data.

        Returns:
            The state dict from checkpoint for resuming.
        """
        state = checkpoint_data.get("state", {})

        logger.info(
            "Resuming %s from step %d (%s)",
            self._checkpoint_name,
            state.get("current_step", 0),
            state.get("step_name", "unknown"),
        )

        return state
