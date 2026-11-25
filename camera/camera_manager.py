
import threading

from config.schema import Camera
from camera.capture_worker import CaptureWorker
from camera.frame import Frame, StreamType


class CameraManager:

    def __init__(self,config: Camera,main_stream_url: str,sub_stream_url: str) -> None:

        self.main_worker = CaptureWorker(
            stream_url=main_stream_url,
            camera_id=config.id,
            stream_type=StreamType.MAIN
        )

        self.sub_worker = CaptureWorker(
            stream_url=sub_stream_url,
            camera_id=config.id,
            stream_type=StreamType.SUB
        )

        self._lifecycle_lock = threading.Lock()

    # Lifecycle

    def start(self) -> None:

        with self._lifecycle_lock:

            try:
                self.main_worker.start()
                self.sub_worker.start()

            except Exception as startup_error:

                cleanup_errors = []

                for worker in (self.sub_worker, self.main_worker):

                    try:
                        if not worker.stop():
                            cleanup_errors.append(
                                f"Could not stop {worker.stream_type.value} worker."
                            )

                    except Exception as exc:
                        cleanup_errors.append(
                            f"{worker.stream_type.value}: {exc}"
                        )

                if cleanup_errors:
                    raise RuntimeError(
                        "Camera startup failed. "
                        f"Original error: {startup_error}. "
                        "Cleanup was incomplete: "
                        + "; ".join(cleanup_errors)
                    ) from startup_error

                raise

    def stop(self) -> None:

        with self._lifecycle_lock:

            stop_errors = []

            for worker in (self.main_worker, self.sub_worker):

                try:
                    if not worker.stop():
                        stop_errors.append(
                            f"Could not stop {worker.stream_type.value} worker."
                        )

                except Exception as exc:
                    stop_errors.append(
                        f"{worker.stream_type.value}: {exc}"
                    )

            if stop_errors:
                raise RuntimeError(
                    "Camera stop failed: "
                    + "; ".join(stop_errors)
                )

    # Frame Access

    def get_main_frame(self) -> Frame:

        return self.main_worker.get_latest_frame()

    def get_sub_frame(self) -> Frame:

        return self.sub_worker.get_latest_frame()

    def get_closest_main_frame(self, timestamp: float) -> Frame:

        return self.main_worker.get_closest_frame(timestamp)

    # Status

    def get_status(self) -> dict[str, str]:

        return {
            "main_status": self.main_worker.get_state().value,
            "sub_status": self.sub_worker.get_state().value
        }

    def is_running(self) -> bool:

        return (
            self.main_worker.is_running()
            or self.sub_worker.is_running()
        )

    def is_connected(self) -> bool:

        return (
            self.main_worker.is_connected()
            and self.sub_worker.is_connected()
        )

    # Statistics

    def get_statistics(self) -> dict[str, dict[str, int]]:

        return {
            "main": {
                "reconnect_attempts": self.main_worker.get_reconnect_attempts(),
                "successful_reconnects": self.main_worker.get_successful_reconnects(),
                "total_failures": self.main_worker.get_total_failures(),
                "consecutive_failures": self.main_worker.get_consecutive_failures()
            },
            "sub": {
                "reconnect_attempts": self.sub_worker.get_reconnect_attempts(),
                "successful_reconnects": self.sub_worker.get_successful_reconnects(),
                "total_failures": self.sub_worker.get_total_failures(),
                "consecutive_failures": self.sub_worker.get_consecutive_failures()
            }
        }
