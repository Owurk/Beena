from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np


@dataclass
class MotionConfig:
    pixel_threshold: int = 25
    min_changed_ratio: float = 0.002
    required_consecutive_frames: int = 2


class MotionDetector:
    def __init__(self, cfg: MotionConfig) -> None:
        self._cfg = cfg
        self._prev_gray: Optional[np.ndarray] = None
        self._last_ratio = 0.0
        self._motion_streak = 0

    def get_last_ratio(self) -> float:

        return self._last_ratio

    def detect(self, frame: Optional[np.ndarray]) -> bool:
        """Process one frame and report sustained motion."""
        if frame is None or frame.size == 0:
            self._motion_streak = 0
            return False

        if frame.ndim == 2:
            current_gray = frame.copy()
        elif frame.ndim == 3 and frame.shape[2] == 3:
            current_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            self._motion_streak = 0
            return False

        current_gray = cv2.GaussianBlur(current_gray, (5, 5), 0)

        if self._prev_gray is None:
            self._prev_gray = current_gray.copy()
            return False

        if current_gray.shape[:2] != self._prev_gray.shape[:2]:
            self._motion_streak = 0
            self._prev_gray = current_gray.copy()
            return False

        diff = cv2.absdiff(current_gray, self._prev_gray)

        _, thresholded = cv2.threshold(
            diff,
            self._cfg.pixel_threshold,
            255,
            cv2.THRESH_BINARY,
        )

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        thresholded = cv2.morphologyEx(thresholded, cv2.MORPH_OPEN, kernel)

        non_zero = cv2.countNonZero(thresholded)
        pixels = current_gray.shape[0] * current_gray.shape[1]
        ratio = non_zero / pixels

        self._last_ratio = ratio
        self._prev_gray = current_gray.copy()

        if ratio >= self._cfg.min_changed_ratio:
            self._motion_streak += 1
        else:
            self._motion_streak = 0

        return self._motion_streak >= self._cfg.required_consecutive_frames

    def get_config(self) -> MotionConfig:

        return self._cfg

    def set_config(self, cfg: MotionConfig) -> None:

        self._cfg = cfg
