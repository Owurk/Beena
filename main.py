import math
import os
import sys
import time
import json
import urllib.request
from concurrent.futures import Future, ThreadPoolExecutor
from typing import List, Optional
from datetime import datetime
from uuid import uuid4

import cv2
import numpy as np

from capture import Capture
from motion_detector import MotionConfig, MotionDetector
from yolo_detector import Detection, YoloConfig, YoloDetector


USAGE = (
    "Usage: main.py [pixelThreshold] [minChangedRatio] "
    "[confidenceThreshold] [yoloInterval] [cameraIndex] "
    "[--source VIDEO_OR_RTSP_URL] [--no-show]\n"
    "  pixelThreshold      : 1..255  (default 25)\n"
    "  minChangedRatio     : 0..1    (default 0.002)\n"
    "  confidenceThreshold : 0..1    (default 0.5)\n"
    "  yoloInterval        : 1..1000 (default 10)\n"
    "  cameraIndex         : 0..10   (default 0)\n"
    "  --source            : video file or RTSP URL\n"
    "  --no-show           : run headless\n"
)

# Local Beena Core endpoint for snapshot event notifications.
BEENA_CORE_URL = "http://127.0.0.1:8080/snapshot"



def get_camera_name(source) -> str:
    if source is None:
        return "Webcam"

    return os.path.basename(source)


def _parse_float(text: str, minimum: float, maximum: float) -> Optional[float]:

    if text is None or text == "":
        return None

    try:
        value = float(text)
    except ValueError:
        return None

    if not math.isfinite(value):
        return None

    if value < minimum or value > maximum:
        return None

    return value


def _parse_int(text: str, minimum: int, maximum: int) -> Optional[int]:

    if text is None or text == "":
        return None

    try:
        value = int(text, 10)
    except ValueError:
        return None

    if value < minimum or value > maximum:
        return None

    return value


_PERSON_OR_ANIMAL_CLASSES = frozenset(
    {
        "person",
        "bird",
        "cat",
        "dog",
        "horse",
        "sheep",
        "cow",
        "elephant",
        "bear",
        "zebra",
        "giraffe",
    }
)


def _is_person_or_animal(class_name: str) -> bool:
    return class_name in _PERSON_OR_ANIMAL_CLASSES


def _make_snapshot_timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _build_snapshot_path(directory: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    path = os.path.join(directory, f"detect_{timestamp}.jpg")

    counter = 1

    while os.path.exists(path):
        path = os.path.join(
            directory,
            f"detect_{timestamp}_{counter}.jpg"
        )
        counter += 1

    return path


def send_snapshot_event(snapshot_path: str,detections: List[Detection],camera_name: str,timestamp: str,shared_storage_root : str) -> bool:
    """Notify Beena Core that a snapshot has been successfully saved.

    Sends the snapshot's absolute file path and event metadata
    to the local HTTP server. Returns True if the server accepts
    the event, otherwise False.
    """

    valid_detections = [
        d for d in detections
        if _is_person_or_animal(d.class_name)
    ]

    if not valid_detections:
        return False

    primary_detection = max(
        valid_detections,
        key=lambda d: d.confidence
    )

    payload = {
        "event_id": str(uuid4()),
        "image_path": os.path.relpath(snapshot_path,shared_storage_root).replace("\\", "/"),
        "local_time": timestamp,
        "detected_class": primary_detection.class_name,
        "confidence": float(primary_detection.confidence),
        "camera_name": camera_name,
    }

    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        BEENA_CORE_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            print(f"Rust notification status: {response.status}")
            return response.status == 202

    except Exception as e:
        print(f"Failed to notify Rust: {e}", file=sys.stderr)
        return False


def _save_snapshot(
    directory: str, frame: np.ndarray, detections: List[Detection]
) -> str | None:
    """Save an annotated frame and return its path on success.

    Returns None if the snapshot cannot be written.
    """

    annotated = frame.copy()

    for d in detections:
        cv2.rectangle(annotated, d.box, (0, 255, 0), 2)

        label = f"{d.class_name} {d.confidence:.2f}"

        (text_width, text_height), _baseline = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
        )

        label_x = d.box[0]
        label_y = d.box[1] - 10

        if label_y < text_height:
            label_y = d.box[3] + text_height + 5

        cv2.putText(
            annotated,
            label,
            (label_x, label_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2,
        )

    path = _build_snapshot_path(directory)

    if not cv2.imwrite(path, annotated):
        print(f"Failed to write snapshot: {path}", file=sys.stderr)
        return None

    print(f"Snapshot saved: {path}")

    return path


def main(argv: List[str]) -> int:

    show = "--no-show" not in argv

    args = argv.copy()
    source = None

    if "--source" in args:
        index = args.index("--source")

        if index + 1 >= len(args):
            print("--source requires a video path or RTSP URL", file=sys.stderr)
            return 1

        source = args[index + 1]
        del args[index : index + 2]

    positional = [a for a in args if a != "--no-show"]

    motion_config = MotionConfig()
    yolo_config = YoloConfig()

    yolo_interval = 10
    camera_index = 0

    if len(positional) == 0:
        print(USAGE, end="")

    if len(positional) > 0:
        value = _parse_int(positional[0], 1, 255)

        if value is None:
            print(
                f"Invalid pixelThreshold (expected 1..255): {positional[0]}",
                file=sys.stderr,
            )
            return 1

        motion_config.pixel_threshold = value

    if len(positional) > 1:
        value = _parse_float(positional[1], 0.0, 1.0)

        if value is None:
            print(
                f"Invalid minChangedRatio (expected 0..1): {positional[1]}",
                file=sys.stderr,
            )
            return 1

        motion_config.min_changed_ratio = value

    if len(positional) > 2:
        value = _parse_float(positional[2], 0.0, 1.0)

        if value is None:
            print(
                f"Invalid confidenceThreshold (expected 0..1): {positional[2]}",
                file=sys.stderr,
            )
            return 1

        yolo_config.confidence_threshold = value

    if len(positional) > 3:
        value = _parse_int(positional[3], 1, 1000)

        if value is None:
            print(
                f"Invalid yoloInterval (expected 1..1000): {positional[3]}",
                file=sys.stderr,
            )
            return 1

        yolo_interval = value

    if len(positional) > 4:
        value = _parse_int(positional[4], 0, 10)

        if value is None:
            print(
                f"Invalid cameraIndex (expected 0..10): {positional[4]}",
                file=sys.stderr,
            )
            return 1

        camera_index = value

    # Determine the camera/source name for event metadata.
    camera_name = get_camera_name(source) if source is not None else "Webcam"

    SHARED_STORAGE_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)),"shared")

    snapshot_dir = os.path.join(
        SHARED_STORAGE_ROOT,
        "snapshots"
    )

    try:
        os.makedirs(snapshot_dir, exist_ok=True)

    except OSError as e:
        print(f"Failed to create snapshots directory: {e}", file=sys.stderr)
        return 1

    motion_detector = MotionDetector(motion_config)

    yolo_detector = YoloDetector(yolo_config)

    if not yolo_detector.load():
        return 1

    window_name = "Webcam"

    window_initialized = False

    if show:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    max_consecutive_failures = 5
    retry_delay = 0.030

    if source is not None:
        camera = Capture(source)
    else:
        camera = Capture(camera_index)

    if not camera.open():
        return 1

    is_video_file = source is not None and not source.lower().startswith(
        ("rtsp://", "rtsps://")
    )

    if is_video_file:
        fps = camera._cap.get(cv2.CAP_PROP_FPS)

        if not math.isfinite(fps) or fps <= 0:
            print("Could not determine video FPS. Using 30 FPS.", file=sys.stderr)
            fps = 30.0

        frame_delay = 1.0 / fps

        next_frame_time = time.monotonic()

        print(f"Video FPS: {fps:.2f}")

    # Dedicated worker pools keep YOLO inference and HTTP notifications
    # from blocking the main camera-processing loop.
    executor = ThreadPoolExecutor(max_workers=1)
    event_executor = ThreadPoolExecutor(max_workers=1)

    yolo_future: Optional[Future] = None
    pending_yolo_frame: Optional[np.ndarray] = None

    consecutive_failures = 0
    frame_counter = 0

    snapshot_cooldown = 5.0

    last_snapshot_time = time.monotonic() - snapshot_cooldown

    ok = True

    try:
        while True:
            frame = camera.read()

            if frame is None or frame.size == 0:
                if is_video_file:
                    print("Video playback completed.")
                    break

                consecutive_failures += 1

                if consecutive_failures >= max_consecutive_failures:
                    print(
                        f"Stream lost after {consecutive_failures} "
                        "consecutive failed reads.",
                        file=sys.stderr,
                    )

                    ok = False
                    break

                time.sleep(retry_delay)
                continue

            consecutive_failures = 0

            if yolo_future is not None and yolo_future.done():
                try:
                    detections = yolo_future.result()

                except Exception as e:
                    print(f"YOLO inference failed: {e}", file=sys.stderr)

                    detections = []

                person_or_animal_present = any(
                    _is_person_or_animal(d.class_name) for d in detections
                )

                current_time = time.monotonic()

                if (
                    pending_yolo_frame is not None
                    and person_or_animal_present
                    and current_time - last_snapshot_time >= snapshot_cooldown
                ):
                    # Save the annotated frame and notify Beena Core only after
                    # the snapshot has been successfully written.
                    snapshot_path = _save_snapshot(
                        snapshot_dir, pending_yolo_frame, detections
                    )

                    if snapshot_path is not None:
                        last_snapshot_time = current_time

                        # Dispatch the HTTP notification asynchronously so network
                        # latency does not interrupt camera processing.
                        event_timestamp = _make_snapshot_timestamp()

                        event_executor.submit(
                            send_snapshot_event,
                            snapshot_path,
                            detections,
                            camera_name,
                            event_timestamp,
                            SHARED_STORAGE_ROOT
                        )

                yolo_future = None
                pending_yolo_frame = None

            motion = motion_detector.detect(frame)

            if motion:
                frame_counter += 1

                if frame_counter >= yolo_interval and yolo_future is None:
                    frame_counter = 0

                    yolo_frame = frame.copy()

                    try:
                        pending_yolo_frame = yolo_frame

                        yolo_future = executor.submit(yolo_detector.detect, yolo_frame)

                    except Exception as e:
                        print(f"Failed to launch async YOLO: {e}", file=sys.stderr)

                        yolo_future = None
                        pending_yolo_frame = None

            text_color = (0, 0, 255) if motion else (0, 255, 0)

            ratio_text = f"Ratio: {motion_detector.get_last_ratio():.4f}"

            text = "Motion: TRUE" if motion else "Motion: FALSE"

            cv2.putText(
                frame, text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, text_color, 2
            )

            cv2.putText(
                frame,
                ratio_text,
                (20, 75),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                text_color,
                2,
            )

            threshold_text = (
                f"Threshold: {motion_detector.get_config().min_changed_ratio:.4f}"
            )

            cv2.putText(
                frame,
                threshold_text,
                (20, 110),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                text_color,
                2,
            )

            conf_text = f"Conf: {yolo_detector.get_confidence_threshold():.2f}"

            cv2.putText(
                frame,
                conf_text,
                (20, 145),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                text_color,
                2,
            )

            cam_text = f"Cam: {camera_index}"

            cv2.putText(
                frame, cam_text, (20, 180), cv2.FONT_HERSHEY_SIMPLEX, 1.0, text_color, 2
            )

            if show:
                cv2.imshow(window_name, frame)

                if not window_initialized:
                    cv2.resizeWindow(window_name, 1280, 720)
                    window_initialized = True

                if (cv2.waitKey(1) & 0xFF) == ord("q"):
                    break

            if is_video_file:
                next_frame_time += frame_delay

                now = time.monotonic()

                if now < next_frame_time:
                    time.sleep(next_frame_time - now)
                else:
                    next_frame_time = now

    finally:
        if yolo_future is not None:
            try:
                yolo_future.result()

            except Exception as e:
                print(f"YOLO inference failed at shutdown: {e}", file=sys.stderr)

        executor.shutdown(wait=True)
        event_executor.shutdown(wait=True)

        camera.release()

        if show:
            cv2.destroyWindow(window_name)

    return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))

    except KeyboardInterrupt:
        sys.exit(130)
