
import cv2
import logging
import math
import threading
import time

from camera.worker_state import WorkerState
from camera.frame import Frame, StreamType
from camera.frame_buffer import FrameBuffer


logger = logging.getLogger(__name__)


class CaptureWorker:

    def __init__(
        self,
        stream_url: str,
        camera_id: str,
        stream_type: StreamType,
        buffer_capacity: int = 30,
        open_timeout_ms: int = 5000,
        read_timeout_ms: int = 5000,
        stop_timeout: float = 10.0,
        stable_connection_seconds: float = 10.0
    ) -> None:

        if not isinstance(stream_url, str) or not stream_url.strip():
            raise ValueError("Stream URL must be a non-empty string.")

        if not isinstance(camera_id, str) or not camera_id.strip():
            raise ValueError("Camera ID must be a non-empty string.")

        if not isinstance(stream_type, StreamType):
            raise TypeError("stream_type must be a StreamType.")

        if isinstance(buffer_capacity, bool) or not isinstance(buffer_capacity, int) or buffer_capacity <= 0:
            raise ValueError("Buffer capacity must be a positive integer.")

        if isinstance(open_timeout_ms, bool) or not isinstance(open_timeout_ms, int) or open_timeout_ms <= 0:
            raise ValueError("Open timeout must be a positive integer.")

        if isinstance(read_timeout_ms, bool) or not isinstance(read_timeout_ms, int) or read_timeout_ms <= 0:
            raise ValueError("Read timeout must be a positive integer.")

        self._validate_positive_number(stop_timeout, "Stop timeout")
        self._validate_positive_number(
            stable_connection_seconds,
            "Stable connection duration"
        )

        self.stream_url = stream_url
        self.camera_id = camera_id
        self.stream_type = stream_type

        self.open_timeout_ms = open_timeout_ms
        self.read_timeout_ms = read_timeout_ms
        self.stop_timeout = float(stop_timeout)
        self.stable_connection_seconds = float(stable_connection_seconds)

        self.frame_buffer = FrameBuffer(buffer_capacity)

        # Thread lifecycle
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

        self._lock = threading.Lock()
        self._lifecycle_lock = threading.Lock()

        self._state = WorkerState.DISCONNECTED

        # Statistics
        self._reconnect_attempts = 0
        self._successful_reconnects = 0
        self._total_failures = 0
        self._consecutive_failures = 0

        self._has_connected_once = False

    # Validation

    @staticmethod
    def _validate_positive_number(value: float, name: str) -> None:

        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value <= 0
        ):
            raise ValueError(f"{name} must be a finite positive number.")

    # Lifecycle

    def start(self) -> None:

        with self._lifecycle_lock:

            if self.is_running():
                return

            # Do not start a new thread while an old one is still alive.
            self._stop_event.clear()
            self.frame_buffer.clear()

            self._set_state(WorkerState.DISCONNECTED)

            thread = threading.Thread(
                target=self._run,
                name=f"{self.camera_id}-{self.stream_type.value}",
                daemon=False
            )

            self._thread = thread

            try:
                thread.start()
            except Exception:
                self._thread = None
                self._set_state(WorkerState.DISCONNECTED)
                raise

    def stop(self, timeout: float | None = None) -> bool:

        if timeout is None:
            timeout = self.stop_timeout

        self._validate_positive_number(timeout, "Stop timeout")

        with self._lifecycle_lock:

            thread = self._thread

            if thread is None:
                self._set_state(WorkerState.STOPPED)
                return True

            self._stop_event.set()

            if threading.current_thread() is thread:
                return False

            if thread.ident is None:
                self._thread = None
                self._set_state(WorkerState.STOPPED)
                return True

            thread.join(timeout=float(timeout))

            stopped = not thread.is_alive()

            if stopped:
                self._set_state(WorkerState.STOPPED)

            return stopped

    def is_running(self) -> bool:

        return (
            self._thread is not None
            and self._thread.is_alive()
        )

    # Frame Access

    def get_latest_frame(self) -> Frame:

        return self.frame_buffer.get_latest()

    def get_last_frame_time(self) -> float | None:

        try:
            return self.frame_buffer.get_latest().timestamp
        except LookupError:
            return None

    def get_closest_frame(self, timestamp: float) -> Frame:

        return self.frame_buffer.get_closest(timestamp)

    # State Management

    def _set_state(self, state: WorkerState) -> None:

        with self._lock:
            self._state = state

    def get_state(self) -> WorkerState:

        with self._lock:
            return self._state

    # Statistics Management

    def _record_failure(self) -> None:

        with self._lock:
            self._total_failures += 1
            self._consecutive_failures += 1

    def _record_success(self) -> None:

        with self._lock:
            self._consecutive_failures = 0

    def _record_reconnect_attempt(self) -> None:

        with self._lock:
            self._reconnect_attempts += 1

    def _record_successful_reconnect(self) -> None:

        with self._lock:
            self._successful_reconnects += 1

    def get_reconnect_attempts(self) -> int:

        with self._lock:
            return self._reconnect_attempts

    def get_successful_reconnects(self) -> int:

        with self._lock:
            return self._successful_reconnects

    def get_total_failures(self) -> int:

        with self._lock:
            return self._total_failures

    def get_consecutive_failures(self) -> int:

        with self._lock:
            return self._consecutive_failures

    # Capture Management

    def _open_capture(self, cap: cv2.VideoCapture) -> bool:

        params = [
            cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,
            self.open_timeout_ms,
            cv2.CAP_PROP_READ_TIMEOUT_MSEC,
            self.read_timeout_ms
        ]

        opened = cap.open(
            self.stream_url,
            cv2.CAP_FFMPEG,
            params
        )

        return opened and cap.isOpened()

    # Capture Loop

    def _run(self) -> None:

        reconnect_delay = 1.0
        max_reconnect_delay = 30.0

        frame_id = 0

        try:

            while not self._stop_event.is_set():

                self._set_state(WorkerState.CONNECTING)

                cap = None
                connection_failed = False

                try:

                    cap = cv2.VideoCapture()

                    if self._has_connected_once:
                        self._record_reconnect_attempt()

                    if not self._open_capture(cap):

                        logger.warning(
                            "Could not open stream for camera %s (%s).",
                            self.camera_id,
                            self.stream_type.value
                        )

                        self._record_failure()
                        connection_failed = True

                    else:

                        first_frame_in_session = True
                        connected_since = None
                        backoff_reset = False

                        while not self._stop_event.is_set():

                            success, image = cap.read()

                            if not success or image is None:

                                if not self._stop_event.is_set():

                                    logger.warning(
                                        "Failed to read frame from camera %s (%s).",
                                        self.camera_id,
                                        self.stream_type.value
                                    )

                                    self._record_failure()
                                    connection_failed = True

                                break

                            timestamp = time.monotonic()

                            frame = Frame(
                                image=image,
                                timestamp=timestamp,
                                frame_id=frame_id,
                                camera_id=self.camera_id,
                                stream_type=self.stream_type
                            )

                            self.frame_buffer.push(frame)

                            frame_id += 1

                            self._record_success()

                            if first_frame_in_session:

                                if self._has_connected_once:
                                    self._record_successful_reconnect()
                                else:
                                    self._has_connected_once = True

                                self._set_state(WorkerState.CONNECTED)

                                connected_since = timestamp
                                first_frame_in_session = False

                            # Reset backoff after a stable connection.

                            if (
                                not backoff_reset
                                and connected_since is not None
                                and timestamp - connected_since
                                >= self.stable_connection_seconds
                            ):

                                reconnect_delay = 1.0
                                backoff_reset = True

                except Exception:

                    logger.exception(
                        "CaptureWorker error for camera %s (%s).",
                        self.camera_id,
                        self.stream_type.value
                    )

                    if not self._stop_event.is_set():
                        self._record_failure()
                        connection_failed = True

                finally:

                    if connection_failed and not self._stop_event.is_set():
                        self._set_state(WorkerState.BACKOFF)

                    if cap is not None:
                        cap.release()

                self.frame_buffer.clear()

                if self._stop_event.is_set():
                    break

                self._set_state(WorkerState.BACKOFF)

                self._stop_event.wait(reconnect_delay)

                reconnect_delay = min(
                    reconnect_delay * 2,
                    max_reconnect_delay
                )

        finally:

            self.frame_buffer.clear()
            self._set_state(WorkerState.STOPPED)

    # Connection Status

    def is_connected(self) -> bool:

        return self.get_state() == WorkerState.CONNECTED
