"""
Splash Screen Verification Module
==================================
Provides visual verification for talent launch splash screens using OpenCV.
Supports template matching and structural similarity comparison.
"""

import os
import logging
import cv2
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple
from skimage.metrics import structural_similarity as ssim

logger = logging.getLogger(__name__)


@dataclass
class SplashScreenResult:
    """Result of splash screen verification."""
    talent_name: str
    passed: bool
    similarity_score: float  # 0.0 to 1.0
    method: str  # "SSIM", "MatchTemplate", or "FileSize"
    message: str
    evidence_path: str = ""
    reference_path: str = ""
    capture_path: str = ""


class SplashScreenVerifier:
    """
    Verifies splash screens using multiple comparison methods.

    Methods:
        - compare_with_template: Template matching (best for exact matches)
        - compare_with_ssim: Structural similarity (tolerates slight variations)
        - compare_images: Auto-selects best method
    """

    def __init__(self, reference_dir: str = "templates/splash_screens"):
        """
        Initialize splash screen verifier.

        Args:
            reference_dir: Directory containing reference splash screen images.
        """
        self.reference_dir = reference_dir
        self.ssim_threshold = 0.7  # 70% similarity required
        self.template_threshold = 0.8  # 80% confidence for template matching

    def get_reference_template(self, talent_name: str) -> Optional[str]:
        """
        Get the reference template path for a talent.

        Args:
            talent_name: Name of the talent (e.g., "adventure_book").

        Returns:
            Path to reference template, or None if not found.
        """
        template_path = os.path.join(
            self.reference_dir, f"{talent_name}_splash.png"
        )
        if os.path.exists(template_path):
            logger.debug(f"Found reference template: {template_path}")
            return template_path
        else:
            logger.warning(f"Reference template not found: {template_path}")
            return None

    def compare_with_template(
        self,
        capture_path: str,
        template_path: str,
        threshold: Optional[float] = None,
    ) -> SplashScreenResult:
        """
        Compare captured splash screen with reference template using template matching.

        Best for exact splash screen matches. Returns high confidence if template
        is found in the captured image.

        Args:
            capture_path: Path to captured screenshot.
            template_path: Path to reference splash screen template.
            threshold: Confidence threshold (default 0.8).

        Returns:
            SplashScreenResult with similarity score and verdict.
        """
        effective_threshold = threshold or self.template_threshold
        talent_name = os.path.basename(template_path).replace("_splash.png", "")

        if not os.path.exists(capture_path):
            logger.error(f"Capture not found: {capture_path}")
            return SplashScreenResult(
                talent_name=talent_name,
                passed=False,
                similarity_score=0.0,
                method="MatchTemplate",
                message=f"Capture file not found: {capture_path}",
                capture_path=capture_path,
                reference_path=template_path,
            )

        if not os.path.exists(template_path):
            logger.error(f"Template not found: {template_path}")
            return SplashScreenResult(
                talent_name=talent_name,
                passed=False,
                similarity_score=0.0,
                method="MatchTemplate",
                message=f"Reference template not found: {template_path}",
                capture_path=capture_path,
                reference_path=template_path,
            )

        try:
            # Read images
            img_capture = cv2.imread(capture_path)
            img_template = cv2.imread(template_path)

            if img_capture is None or img_template is None:
                return SplashScreenResult(
                    talent_name=talent_name,
                    passed=False,
                    similarity_score=0.0,
                    method="MatchTemplate",
                    message="Could not load image files",
                    capture_path=capture_path,
                    reference_path=template_path,
                )

            # Convert to grayscale
            gray_capture = cv2.cvtColor(img_capture, cv2.COLOR_BGR2GRAY)
            gray_template = cv2.cvtColor(img_template, cv2.COLOR_BGR2GRAY)

            # Perform template matching
            result = cv2.matchTemplate(
                gray_capture, gray_template, cv2.TM_CCOEFF_NORMED
            )
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

            similarity = float(max_val)
            passed = similarity >= effective_threshold

            return SplashScreenResult(
                talent_name=talent_name,
                passed=passed,
                similarity_score=similarity,
                method="MatchTemplate",
                message=f"Template match confidence: {similarity:.1%} (threshold: {effective_threshold:.1%})",
                capture_path=capture_path,
                reference_path=template_path,
            )

        except Exception as e:
            logger.error(f"Template matching error: {e}")
            return SplashScreenResult(
                talent_name=talent_name,
                passed=False,
                similarity_score=0.0,
                method="MatchTemplate",
                message=f"Template matching failed: {str(e)}",
                capture_path=capture_path,
                reference_path=template_path,
            )

    def compare_with_ssim(
        self,
        capture_path: str,
        template_path: str,
        threshold: Optional[float] = None,
    ) -> SplashScreenResult:
        """
        Compare splash screens using Structural Similarity Index (SSIM).

        More robust to minor variations in lighting, compression, and positioning.
        Better for detecting if two splash screens are "similar enough".

        Args:
            capture_path: Path to captured screenshot.
            template_path: Path to reference splash screen template.
            threshold: Similarity threshold (default 0.7).

        Returns:
            SplashScreenResult with SSIM score (0.0 to 1.0).
        """
        effective_threshold = threshold or self.ssim_threshold
        talent_name = os.path.basename(template_path).replace("_splash.png", "")

        if not os.path.exists(capture_path) or not os.path.exists(template_path):
            logger.error(
                f"File not found - Capture: {capture_path}, Template: {template_path}"
            )
            return SplashScreenResult(
                talent_name=talent_name,
                passed=False,
                similarity_score=0.0,
                method="SSIM",
                message="Image files not found",
                capture_path=capture_path,
                reference_path=template_path,
            )

        try:
            # Read images in grayscale
            img_capture = cv2.imread(capture_path, cv2.IMREAD_GRAYSCALE)
            img_template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)

            if img_capture is None or img_template is None:
                return SplashScreenResult(
                    talent_name=talent_name,
                    passed=False,
                    similarity_score=0.0,
                    method="SSIM",
                    message="Could not load image files",
                    capture_path=capture_path,
                    reference_path=template_path,
                )

            # Resize to match dimensions
            if img_capture.shape != img_template.shape:
                img_template = cv2.resize(
                    img_template, (img_capture.shape[1], img_capture.shape[0])
                )

            # Calculate SSIM
            similarity, diff = ssim(
                img_capture, img_template, full=True, data_range=255
            )
            similarity = float(similarity)
            passed = similarity >= effective_threshold

            # Save difference map for debugging
            diff_path = (
                capture_path.replace(".png", "_diff.png")
                if ".png" in capture_path
                else capture_path + "_diff.png"
            )
            diff_uint8 = (diff * 255).astype(np.uint8)
            cv2.imwrite(diff_path, diff_uint8)

            return SplashScreenResult(
                talent_name=talent_name,
                passed=passed,
                similarity_score=similarity,
                method="SSIM",
                message=f"SSIM similarity: {similarity:.1%} (threshold: {effective_threshold:.1%})",
                capture_path=capture_path,
                reference_path=template_path,
                evidence_path=diff_path,
            )

        except Exception as e:
            logger.error(f"SSIM comparison error: {e}")
            return SplashScreenResult(
                talent_name=talent_name,
                passed=False,
                similarity_score=0.0,
                method="SSIM",
                message=f"SSIM comparison failed: {str(e)}",
                capture_path=capture_path,
                reference_path=template_path,
            )

    def compare_images(
        self,
        capture_path: str,
        reference_path: str,
        method: str = "auto",
    ) -> SplashScreenResult:
        """
        Compare two splash screen images with auto-selection of best method.

        Args:
            capture_path: Path to captured screenshot.
            reference_path: Path to reference splash screen.
            method: Comparison method - "template", "ssim", or "auto".

        Returns:
            SplashScreenResult with comparison verdict.
        """
        if method == "template":
            return self.compare_with_template(capture_path, reference_path)
        elif method == "ssim":
            return self.compare_with_ssim(capture_path, reference_path)
        else:  # auto
            # Try SSIM first (more robust), fallback to template matching
            logger.info(f"Auto-selecting comparison method for {reference_path}")
            result = self.compare_with_ssim(capture_path, reference_path)
            if result.similarity_score < 0.5:
                logger.info("SSIM score low, trying template matching")
                result = self.compare_with_template(capture_path, reference_path)
            return result

    def verify_talent_splash(
        self,
        talent_name: str,
        capture_path: str,
    ) -> SplashScreenResult:
        """
        Verify splash screen for a specific talent.

        Automatically locates the reference template and compares.

        Args:
            talent_name: Name of the talent (e.g., "adventure_book").
            capture_path: Path to captured screenshot.

        Returns:
            SplashScreenResult with verification verdict.
        """
        logger.info(f"Verifying splash screen for {talent_name}")

        # Find reference template
        template_path = self.get_reference_template(talent_name)
        if not template_path:
            logger.warning(f"No reference template found for {talent_name}")
            return SplashScreenResult(
                talent_name=talent_name,
                passed=False,
                similarity_score=0.0,
                method="N/A",
                message=f"No reference template found. Create one at: {os.path.join(self.reference_dir, f'{talent_name}_splash.png')}",
                capture_path=capture_path,
            )

        # Perform comparison
        result = self.compare_images(capture_path, template_path, method="auto")
        result.talent_name = talent_name
        return result
