from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np


@dataclass
class MotionConfig:
    min_changed_ratio: float = 0.002
    required_consecutive_frames: int = 2
    history: int = 500
    var_threshold: float = 25.0
    learning_rate: float = -1.0


class MotionDetector:
    def __init__(self, cfg: MotionConfig) -> None:
        self._cfg = cfg
        self._last_ratio = 0.0
        self._motion_streak = 0

        self._background = cv2.createBackgroundSubtractorMOG2(
            history=cfg.history,
            varThreshold=cfg.var_threshold,
            detectShadows=True,
        )

        self._clahe = cv2.createCLAHE(
            clipLimit=2.0,
            tileGridSize=(8, 8),
        )

    def detect(self, frame: Optional[np.ndarray]) -> bool:
        if frame is None or frame.size == 0:
            self._motion_streak = 0
            return False

        if frame.ndim == 2:
            gray = frame.copy()
        elif frame.ndim == 3 and frame.shape[2] == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            self._motion_streak = 0
            return False

        # Reduce sensor noise
        gray = cv2.GaussianBlur(gray, (5, 5), 0)

        # Improve local contrast
        enhanced = self._clahe.apply(gray)

        # Background subtraction
        mask = self._background.apply(
            enhanced,
            learningRate=self._cfg.learning_rate,
        )

        # Remove shadows (MOG2 represents shadows with value 127)
        _, mask = cv2.threshold(
            mask,
            200,
            255,
            cv2.THRESH_BINARY,
        )

        # Remove small noise
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (3, 3),
        )

        mask = cv2.morphologyEx(
            mask,
            cv2.MORPH_OPEN,
            kernel,
        )

        # Calculate foreground ratio
        total_pixels = mask.shape[0] * mask.shape[1]
        changed_pixels = cv2.countNonZero(mask)

        ratio = changed_pixels / total_pixels
        self._last_ratio = ratio

        if ratio >= self._cfg.min_changed_ratio:
            self._motion_streak += 1
        else:
            self._motion_streak = 0

        return (
            self._motion_streak
            >= self._cfg.required_consecutive_frames
        )

    def get_last_ratio(self) -> float:
        return self._last_ratio

    def get_config(self) -> MotionConfig:
        return self._cfg

    def set_config(self, cfg: MotionConfig) -> None:
        self._cfg = cfg

        self._background = cv2.createBackgroundSubtractorMOG2(
            history=cfg.history,
            varThreshold=cfg.var_threshold,
            detectShadows=True,
        )

        self._last_ratio = 0.0
        self._motion_streak = 0
