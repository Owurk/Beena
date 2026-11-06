import sys
from typing import Optional

import cv2
import numpy as np


class Capture:

    def __init__(self, index: int = 0) -> None:
        self._cap = cv2.VideoCapture()
        self._camera_index = index

    def open(self) -> bool:
        """Open the webcam. Returns ``True`` on success."""
        if self.is_opened():
            return True

        self._cap.open(self._camera_index)
        if not self._cap.isOpened():
            print("Could not open webcam!", file=sys.stderr)
            return False
        return True

    def read(self) -> Optional[np.ndarray]:
        """Read a single frame.

        Returns the BGR frame, or ``None`` if the capture is not opened or
        the read failed.
        """
        if not self.is_opened():
            print("Camera is not opened!", file=sys.stderr)
            return None

        ok, frame = self._cap.read()
        return frame if ok else None

    def release(self) -> None:
        """Release the camera."""
        if self.is_opened():
            self._cap.release()

    def is_opened(self) -> bool:
        """Return whether the camera is open."""
        return self._cap.isOpened()
