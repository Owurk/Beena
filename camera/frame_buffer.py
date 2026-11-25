
from collections import deque
import math
import threading

from camera.frame import Frame


class FrameBuffer:

    def __init__(self, capacity: int) -> None:

        if (isinstance(capacity, bool) or not isinstance(capacity, int) or capacity <= 0):
            raise ValueError(
                "Frame buffer capacity must be a positive integer."
            )

        self._dq: deque[Frame] = deque(maxlen=capacity)
        self._lock = threading.Lock()

    def push(self, frame: Frame) -> None:

        if not isinstance(frame, Frame):
            raise TypeError("frame must be an instance of Frame.")

        with self._lock:
            self._dq.append(frame)

    def get_latest(self) -> Frame:

        with self._lock:

            if not self._dq:
                raise LookupError("Frame buffer is empty.")

            return self._dq[-1]

    def get_closest(self, timestamp: float) -> Frame:

        if (isinstance(timestamp, bool)or not isinstance(timestamp, (int, float))or not math.isfinite(timestamp)):
            raise ValueError(
                "timestamp must be a finite number."
            )

        with self._lock:

            if not self._dq:
                raise LookupError("Frame buffer is empty.")

            return min(
                self._dq,
                key=lambda frame: abs(frame.timestamp - timestamp)
            )

    def clear(self) -> None:

        with self._lock:
            self._dq.clear()

    def __len__(self) -> int:

        with self._lock:
            return len(self._dq)
