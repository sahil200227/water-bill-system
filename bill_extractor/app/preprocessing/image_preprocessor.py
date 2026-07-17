"""
OpenCV-based image preprocessing pipeline for improving OCR accuracy.

Each preprocessing step is an independent method that can be toggled or reordered.
The pipeline preserves the original image and returns a preprocessed copy.
"""
import math
from typing import Optional, Tuple

import cv2
import numpy as np
from PIL import Image

from app.utils.logger import get_logger

logger = get_logger(__name__)


class ImagePreprocessor:
    """
    Image preprocessing pipeline for utility bill documents.

    Applies a sequence of OpenCV operations to improve OCR accuracy
    without damaging document contents.
    """

    def __init__(
        self,
        enable_rotation: bool = True,
        enable_deskew: bool = True,
        enable_noise_removal: bool = True,
        enable_thresholding: bool = False,
        enable_contrast: bool = True,
        enable_sharpening: bool = True,
        enable_border_removal: bool = True,
        enable_resolution_enhancement: bool = True,
        target_dpi: int = 300,
    ):
        self.enable_rotation = enable_rotation
        self.enable_deskew = enable_deskew
        self.enable_noise_removal = enable_noise_removal
        self.enable_thresholding = enable_thresholding
        self.enable_contrast = enable_contrast
        self.enable_sharpening = enable_sharpening
        self.enable_border_removal = enable_border_removal
        self.enable_resolution_enhancement = enable_resolution_enhancement
        self.target_dpi = target_dpi

    def preprocess(self, image: Image.Image) -> Image.Image:
        """
        Run the full preprocessing pipeline on a PIL Image.

        Args:
            image: Input PIL Image (RGB).

        Returns:
            Preprocessed PIL Image (RGB).
        """
        logger.info(
            "Starting image preprocessing pipeline (size: %dx%d)",
            image.width,
            image.height,
        )

        # Convert PIL to OpenCV BGR
        img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        original_shape = img.shape[:2]

        # Step 1: Resolution enhancement
        if self.enable_resolution_enhancement:
            img = self._enhance_resolution(img)

        # Step 2: Border removal
        if self.enable_border_removal:
            img = self._remove_borders(img)

        # Step 3: Auto-rotation detection
        if self.enable_rotation:
            img = self._auto_rotate(img)

        # Step 4: Deskew
        if self.enable_deskew:
            img = self._deskew(img)

        # Step 5: Noise removal
        if self.enable_noise_removal:
            img = self._remove_noise(img)

        # Step 6: Contrast enhancement
        if self.enable_contrast:
            img = self._enhance_contrast(img)

        # Step 7: Image sharpening
        if self.enable_sharpening:
            img = self._sharpen(img)

        # Step 8: Adaptive thresholding (optional, can damage color docs)
        if self.enable_thresholding:
            img = self._adaptive_threshold(img)

        logger.info(
            "Preprocessing complete. Original: %s → Final: %s",
            original_shape,
            img.shape[:2],
        )

        # Convert back to PIL RGB
        if len(img.shape) == 2:
            # Grayscale from thresholding
            result = Image.fromarray(img).convert("RGB")
        else:
            result = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

        return result

    def _enhance_resolution(self, img: np.ndarray) -> np.ndarray:
        """Upscale low-resolution images to improve OCR accuracy."""
        h, w = img.shape[:2]
        min_dimension = min(h, w)

        if min_dimension < 1500:
            scale = max(2.0, 2000 / min_dimension)
            scale = min(scale, 4.0)  # Cap at 4x
            new_w = int(w * scale)
            new_h = int(h * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
            logger.debug(
                "Resolution enhanced: %dx%d → %dx%d (%.1fx)", w, h, new_w, new_h, scale
            )
        else:
            logger.debug("Resolution sufficient (%dx%d), skipping enhancement", w, h)

        return img

    def _remove_borders(self, img: np.ndarray) -> np.ndarray:
        """Remove dark scan borders from the image."""
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY)

            contours, _ = cv2.findContours(
                thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            if contours:
                largest = max(contours, key=cv2.contourArea)
                area_ratio = cv2.contourArea(largest) / (img.shape[0] * img.shape[1])

                if 0.5 < area_ratio < 0.98:
                    x, y, w, h = cv2.boundingRect(largest)
                    # Add small padding
                    pad = 5
                    x = max(0, x - pad)
                    y = max(0, y - pad)
                    w = min(img.shape[1] - x, w + 2 * pad)
                    h = min(img.shape[0] - y, h + 2 * pad)
                    img = img[y : y + h, x : x + w]
                    logger.debug("Borders removed, cropped to %dx%d", w, h)
                else:
                    logger.debug("No significant border detected, skipping removal")
            return img
        except Exception as e:
            logger.warning("Border removal failed: %s", e)
            return img

    def _auto_rotate(self, img: np.ndarray) -> np.ndarray:
        """Detect and correct image rotation (90°, 180°, 270°)."""
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            lines = cv2.HoughLinesP(
                edges,
                rho=1,
                theta=np.pi / 180,
                threshold=100,
                minLineLength=100,
                maxLineGap=10,
            )

            if lines is not None and len(lines) > 0:
                angles = []
                for line in lines:
                    val = line[0]
                    # Check if val is iterable and has 4 elements
                    if hasattr(val, "__len__") and len(val) == 4:
                        x1, y1, x2, y2 = val
                        angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
                        angles.append(angle)

                # Check for dominant near-vertical lines (90° rotation)
                vertical_count = sum(1 for a in angles if 80 < abs(a) < 100)
                horizontal_count = sum(1 for a in angles if abs(a) < 10 or abs(a) > 170)

                if vertical_count > horizontal_count * 2:
                    img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
                    logger.debug("Auto-rotated 90° clockwise")

            return img
        except Exception as e:
            logger.warning("Auto-rotation detection failed: %s", e)
            return img

    def _deskew(self, img: np.ndarray) -> np.ndarray:
        """Correct skewed document scans."""
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            gray = cv2.bitwise_not(gray)
            thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

            coords = np.column_stack(np.where(thresh > 0))

            if len(coords) < 100:
                logger.debug("Insufficient text pixels for deskew detection")
                return img

            angle = cv2.minAreaRect(coords)[-1]

            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle

            # Only deskew if angle is significant but not extreme
            if 0.5 < abs(angle) < 15:
                h, w = img.shape[:2]
                center = (w // 2, h // 2)
                matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
                img = cv2.warpAffine(
                    img,
                    matrix,
                    (w, h),
                    flags=cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_REPLICATE,
                )
                logger.debug("Deskewed by %.2f degrees", angle)
            else:
                logger.debug("Skew angle %.2f° within tolerance, skipping", angle)

            return img
        except Exception as e:
            logger.warning("Deskew failed: %s", e)
            return img

    def _remove_noise(self, img: np.ndarray) -> np.ndarray:
        """Remove noise using Gaussian blur and morphological operations."""
        try:
            # Light Gaussian blur to reduce noise
            denoised = cv2.GaussianBlur(img, (3, 3), 0)

            # Morphological opening to remove small noise spots
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
            denoised = cv2.morphologyEx(denoised, cv2.MORPH_OPEN, kernel)

            logger.debug("Noise removal applied")
            return denoised
        except Exception as e:
            logger.warning("Noise removal failed: %s", e)
            return img

    def _enhance_contrast(self, img: np.ndarray) -> np.ndarray:
        """Enhance contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)."""
        try:
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l_channel, a, b = cv2.split(lab)

            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            l_enhanced = clahe.apply(l_channel)

            enhanced = cv2.merge([l_enhanced, a, b])
            result = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)

            logger.debug("Contrast enhancement (CLAHE) applied")
            return result
        except Exception as e:
            logger.warning("Contrast enhancement failed: %s", e)
            return img

    def _sharpen(self, img: np.ndarray) -> np.ndarray:
        """Apply unsharp mask for image sharpening."""
        try:
            gaussian = cv2.GaussianBlur(img, (0, 0), 3)
            sharpened = cv2.addWeighted(img, 1.5, gaussian, -0.5, 0)
            logger.debug("Image sharpening applied")
            return sharpened
        except Exception as e:
            logger.warning("Sharpening failed: %s", e)
            return img

    def _adaptive_threshold(self, img: np.ndarray) -> np.ndarray:
        """
        Apply adaptive thresholding to binarize the image.

        Note: This converts to grayscale. Use only when needed for very
        low-quality scans, as it removes color information.
        """
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            binary = cv2.adaptiveThreshold(
                gray,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                blockSize=11,
                C=2,
            )
            logger.debug("Adaptive thresholding applied")
            return binary
        except Exception as e:
            logger.warning("Adaptive thresholding failed: %s", e)
            if len(img.shape) == 3:
                return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            return img
