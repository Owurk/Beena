
import math

from dataclasses import dataclass

from camera.frame import Frame
from camera.camera_manager import CameraManager


@dataclass(frozen=True, slots=True)
class SyncResult:

    main_frame: Frame | None
    sub_frame: Frame
    time_delta: float | None
    is_synchronized: bool


class FrameSynchronizer:

    def __init__(self,camera_manager: CameraManager,max_delta: float) -> None:

        if not isinstance(camera_manager, CameraManager):
            raise TypeError(
                "camera_manager must be an instance of CameraManager."
            )

        if (isinstance(max_delta, bool) or not isinstance(max_delta, (int, float))or not math.isfinite(max_delta)or max_delta < 0):
            raise ValueError(
                "max_delta must be a non-negative finite number."
            )

        self.camera_manager = camera_manager
        self.max_delta = float(max_delta)

    def process(self, sub_frame: Frame) -> SyncResult:

        if not isinstance(sub_frame, Frame):
            raise TypeError(
                "sub_frame must be an instance of Frame."
            )

        if (isinstance(sub_frame.timestamp, bool)or not isinstance(sub_frame.timestamp, (int, float))or not math.isfinite(sub_frame.timestamp)):
            raise ValueError(
                "Sub frame timestamp must be a finite number."
            )

        try:

            closest_main_frame = (
                self.camera_manager.get_closest_main_frame(
                    sub_frame.timestamp
                )
            )

            diff = abs(
                sub_frame.timestamp - closest_main_frame.timestamp
            )

            if diff <= self.max_delta:

                return SyncResult(
                    main_frame=closest_main_frame,
                    sub_frame=sub_frame,
                    time_delta=diff,
                    is_synchronized=True
                )

            return SyncResult(
                main_frame=None,
                sub_frame=sub_frame,
                time_delta=diff,
                is_synchronized=False
            )

        except LookupError:

            return SyncResult(
                main_frame=None,
                sub_frame=sub_frame,
                time_delta=None,
                is_synchronized=False
            )
