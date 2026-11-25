
from dataclasses import dataclass
from enum import Enum
import math

import numpy as np


class StreamType(Enum):
    MAIN = "main"
    SUB = "sub"


@dataclass(frozen=True, slots=True)
class Frame:

    image: np.ndarray
    timestamp: float
    frame_id: int
    camera_id: str
    stream_type: StreamType

    def __post_init__(self) -> None:

        if not isinstance(self.image, np.ndarray):
            raise TypeError("image must be a NumPy array.")

        if self.image.size == 0 or self.image.ndim not in (2, 3):
            raise ValueError("image must be a non-empty 2D or 3D array.")

        if (
            isinstance(self.timestamp, bool)
            or not isinstance(self.timestamp, (int, float))
            or not math.isfinite(self.timestamp)
        ):
            raise ValueError("timestamp must be a finite number.")

        if (
            isinstance(self.frame_id, bool)
            or not isinstance(self.frame_id, int)
            or self.frame_id < 0
        ):
            raise ValueError("frame_id must be a non-negative integer.")

        if not isinstance(self.camera_id, str) or not self.camera_id.strip():
            raise ValueError("camera_id must be a non-empty string.")

        if not isinstance(self.stream_type, StreamType):
            raise TypeError("stream_type must be a StreamType.")
