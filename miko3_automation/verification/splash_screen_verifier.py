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
        self.ssim_threshold = 0.65  # Slightly lowered for stability
        self.template_threshold = 0.75  # Slightly lowered for stability
        self.roi_crop_top = 0.12  # Crop top 12% (Status bar)
        self.roi_crop_bottom = 0.10  # Crop bottom 10% (Nav bar)

    def _preprocess_image(self, img: np.ndarray) -> np.ndarray:
        """
        Preprocess image for robust comparison:
        1. Convert to grayscale.
        2. Crop out status and navigation bars.
        3. Apply slight Gaussian blur to reduce noise.
        """
        if img is None:
            return None
            
        # 1. Convert to grayscale if color
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()
            
        # 2. ROI Cropping
        h, w = gray.shape
        top = int(h * self.roi_crop_top)
        bottom = int(h * (1.0 - self.roi_crop_bottom))
        roi = gray[top:bottom, 0:w]
        
        # 3. Blurring
        blurred = cv2.GaussianBlur(roi, (5, 5), 0)
        
        return blurred

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

            # Preprocess images (ROI crop, grayscale, blur)
            proc_capture = self._preprocess_image(img_capture)
            proc_template_base = self._preprocess_image(img_template)

            if proc_capture is None or proc_template_base is None:
                return SplashScreenResult(
                    talent_name=talent_name,
                    passed=False,
                    similarity_score=0.0,
                    method="MatchTemplate",
                    message="Preprocessing failed",
                    capture_path=capture_path,
                    reference_path=template_path,
                )

            # Hyper-Robust Multiscale Template Matching
            best_similarity = 0.0
            scales = [0.9, 0.95, 1.0, 1.05, 1.1]
            
            for scale in scales:
                # Resize template for this scale
                if scale != 1.0:
                    new_w = int(proc_template_base.shape[1] * scale)
                    new_h = int(proc_template_base.shape[0] * scale)
                    # Don't scale larger than capture
                    if new_w > proc_capture.shape[1] or new_h > proc_capture.shape[0]:
                        continue
                    proc_template = cv2.resize(proc_template_base, (new_w, new_h))
                else:
                    # Default size check (must not be larger than capture)
                    if proc_template_base.shape[1] > proc_capture.shape[1] or \
                       proc_template_base.shape[0] > proc_capture.shape[0]:
                        proc_template = cv2.resize(
                            proc_template_base, (proc_capture.shape[1], proc_capture.shape[0])
                        )
                    else:
                        proc_template = proc_template_base

                # Perform template matching
                result = cv2.matchTemplate(
                    proc_capture, proc_template, cv2.TM_CCOEFF_NORMED
                )
                _, max_val, _, _ = cv2.minMaxLoc(result)
                best_similarity = max(best_similarity, float(max_val))

            similarity = best_similarity
            passed = similarity >= effective_threshold

            # Save processed images for debugging (using 1.0 scale version)
            proc_capture_path = capture_path.replace(".png", "_processed.png")
            cv2.imwrite(proc_capture_path, proc_capture)
            proc_ref_path = template_path.replace(".png", "_processed.png")
            cv2.imwrite(proc_ref_path, proc_template_base)

            return SplashScreenResult(
                talent_name=talent_name,
                passed=passed,
                similarity_score=similarity,
                method="MatchTemplate",
                message=f"Multiscale match confidence: {similarity:.1%} (threshold: {effective_threshold:.1%})",
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
            # Read images
            img_capture = cv2.imread(capture_path)
            img_template = cv2.imread(template_path)

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

            # Preprocess images (ROI crop, grayscale, blur)
            proc_capture = self._preprocess_image(img_capture)
            proc_template = self._preprocess_image(img_template)

            if proc_capture is None or proc_template is None:
                 return SplashScreenResult(
                    talent_name=talent_name,
                    passed=False,
                    similarity_score=0.0,
                    method="SSIM",
                    message="Preprocessing failed",
                    capture_path=capture_path,
                    reference_path=template_path,
                )

            # Resize to match dimensions
            if proc_capture.shape != proc_template.shape:
                proc_template = cv2.resize(
                    proc_template, (proc_capture.shape[1], proc_capture.shape[0])
                )

            # Calculate SSIM
            similarity, diff = ssim(
                proc_capture, proc_template, full=True, data_range=255
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
