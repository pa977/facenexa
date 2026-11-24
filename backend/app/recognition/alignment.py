"""
FaceAligner — normalises detected faces before embedding generation.

Uses a similarity transform based on facial landmarks (eyes) to produce
a 112×112 aligned face image as expected by InsightFace/ArcFace models.

If landmarks are unavailable, falls back to a simple centre-crop resize.
"""

from __future__ import annotations

import logging
import time

import cv2
import numpy as np
from typing import Optional

from backend.app.recognition.recognition_models import BoundingBox, FaceLandmarks

logger = logging.getLogger("facenexa.alignment")

# Standard destination landmarks for a 112×112 aligned face (InsightFace convention)
# These are the reference positions where the eyes should end up after alignment.
_REFERENCE_LANDMARKS_112 = np.array(
    [
        [38.2946, 51.6963],   # left eye
        [73.5318, 51.5014],   # right eye
        [56.0252, 71.7366],   # nose
        [41.5493, 92.3655],   # mouth left
        [70.7299, 92.2041],   # mouth right
    ],
    dtype=np.float32,
)


class FaceAligner:
    """Align a face region to a canonical 112×112 image."""

    OUTPUT_SIZE = (112, 112)

    def align(
        self,
        frame: np.ndarray,
        bbox: BoundingBox,
        landmarks: Optional[FaceLandmarks],
    ) -> tuple[np.ndarray, float]:
        """Align the face and return (aligned_face, elapsed_ms).

        If landmarks are available, uses a similarity transform.
        Otherwise falls back to crop + resize.
        """
        t0 = time.perf_counter()

        if landmarks is not None:
            aligned = self._align_with_landmarks(frame, landmarks)
        else:
            aligned = self._crop_and_resize(frame, bbox)

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return aligned, elapsed_ms

    # ── Landmark-based alignment ──────────────────────────────────────

    def _align_with_landmarks(self, frame: np.ndarray, landmarks: FaceLandmarks) -> np.ndarray:
        """Apply a similarity transform using 5-point landmarks."""
        src = np.array(
            [
                landmarks.left_eye,
                landmarks.right_eye,
                landmarks.nose,
                landmarks.mouth_left,
                landmarks.mouth_right,
            ],
            dtype=np.float32,
        )

        tform = self._estimate_similarity_transform(src, _REFERENCE_LANDMARKS_112)
        aligned = cv2.warpAffine(
            frame,
            tform,
            self.OUTPUT_SIZE,
            borderValue=(0, 0, 0),
        )
        return aligned

    # ── Fallback crop + resize ────────────────────────────────────────

    def _crop_and_resize(self, frame: np.ndarray, bbox: BoundingBox) -> np.ndarray:
        """Simple centre-crop and resize when landmarks are unavailable."""
        h, w = frame.shape[:2]
        # Expand bbox by 20% for context
        pad_w = int(bbox.width * 0.2)
        pad_h = int(bbox.height * 0.2)
        x1 = max(0, bbox.x1 - pad_w)
        y1 = max(0, bbox.y1 - pad_h)
        x2 = min(w, bbox.x2 + pad_w)
        y2 = min(h, bbox.y2 + pad_h)
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return np.zeros((*self.OUTPUT_SIZE, 3), dtype=np.uint8)
        return cv2.resize(crop, self.OUTPUT_SIZE)

    # ── Similarity transform ──────────────────────────────────────────

    @staticmethod
    def _estimate_similarity_transform(
        src: np.ndarray, dst: np.ndarray
    ) -> np.ndarray:
        """Estimate a 2×3 affine (similarity) matrix from src→dst point pairs.

        Uses a least-squares approach equivalent to skimage.transform.SimilarityTransform
        but without the scikit-image dependency.
        """
        num = src.shape[0]
        dim = 2

        # Build the linear system
        src_mean = src.mean(axis=0)
        dst_mean = dst.mean(axis=0)

        src_demean = src - src_mean
        dst_demean = dst - dst_mean

        A = dst_demean.T @ src_demean / num
        d = np.ones(dim)

        U, S, Vt = np.linalg.svd(A)

        rank = np.linalg.matrix_rank(A)
        if rank < dim:
            # Degenerate — fallback to identity-ish
            return np.eye(2, 3, dtype=np.float32)

        det_sign = np.linalg.det(U) * np.linalg.det(Vt)
        if det_sign < 0:
            d[dim - 1] = -1

        T = np.eye(dim + 1, dtype=np.float64)
        T[:dim, :dim] = U @ np.diag(d) @ Vt

        src_var = src_demean.var(axis=0).sum()
        if src_var < 1e-10:
            return np.eye(2, 3, dtype=np.float32)

        scale = (S * d).sum() / src_var
        T[:dim, dim] = dst_mean - scale * (T[:dim, :dim] @ src_mean)
        T[:dim, :dim] *= scale

        return T[:2, :].astype(np.float32)
