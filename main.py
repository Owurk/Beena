import argparse
import json
import math
import os
import sys
import time
import urllib.request

from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
from typing import Optional
from uuid import uuid4

import cv2
import numpy as np

from dotenv import load_dotenv

from camera.camera_manager import CameraManager
from camera.frame import Frame
from camera.frame_synchronizer import FrameSynchronizer

from config.loader import load_config
from config.credentials import get_camera_credentials
from config.url_builder import build_rtsp_url

from motion_detector import MotionConfig, MotionDetector
from yolo_detector import Detection, YoloConfig, YoloDetector


load_dotenv(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "config",
        ".env"
    )
)




BEENA_CORE_URL = "http://127.0.0.1:8080/snapshot"

SNAPSHOT_COOLDOWN = 5.0

# Maximum allowed time difference between Main and Sub frames.
FRAME_SYNC_MAX_DELTA = 0.1

PERSON_OR_ANIMAL_CLASSES = frozenset(
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





def load_camera_manager() -> tuple[CameraManager, str]:
    """
    Load the single configured camera and create its manager.
    """

    config = load_config("config/cameras.yaml")

    if len(config.cameras) != 1:
        raise ValueError(
            "Beena 2.0 requires exactly one configured camera."
        )

    camera = config.cameras[0]

    credentials = get_camera_credentials(camera.id)

    main_url = build_rtsp_url(
        camera.connection.main_stream,
        credentials
    )

    sub_url = build_rtsp_url(
        camera.connection.sub_stream,
        credentials
    )

    manager = CameraManager(
        config=camera,
        main_stream_url=main_url,
        sub_stream_url=sub_url
    )

    return manager, camera.name





def _parse_float(text: str,minimum: float,maximum: float) -> float:

    value = float(text)

    if not math.isfinite(value):
        raise argparse.ArgumentTypeError(
            "Value must be finite."
        )

    if not minimum <= value <= maximum:
        raise argparse.ArgumentTypeError(
            f"Value must be between {minimum} and {maximum}."
        )

    return value


def _parse_positive_int(text: str) -> int:

    value = int(text)

    if value <= 0:
        raise argparse.ArgumentTypeError(
            "Value must be a positive integer."
        )

    return value


def _is_person_or_animal(class_name: str) -> bool:

    return class_name in PERSON_OR_ANIMAL_CLASSES


def _make_snapshot_timestamp() -> str:

    return datetime.now().astimezone().isoformat(
        timespec="seconds"
    )


def _build_snapshot_path(directory: str) -> str:

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    path = os.path.join(
        directory,
        f"detect_{timestamp}.jpg"
    )

    counter = 1

    while os.path.exists(path):

        path = os.path.join(
            directory,
            f"detect_{timestamp}_{counter}.jpg"
        )

        counter += 1

    return path




def _scale_detections(detections: list[Detection],source_frame: np.ndarray,target_frame: np.ndarray) -> list[Detection]:
    """
    Transform bounding boxes from Sub resolution
    to Main resolution.
    """

    source_height, source_width = source_frame.shape[:2]
    target_height, target_width = target_frame.shape[:2]

    scale_x = target_width / source_width
    scale_y = target_height / source_height

    scaled = []

    for detection in detections:

        x, y, width, height = detection.box

        left = round(x * scale_x)
        top = round(y * scale_y)

        right = round((x + width) * scale_x)
        bottom = round((y + height) * scale_y)

        left = max(0, min(left, target_width - 1))
        top = max(0, min(top, target_height - 1))

        right = max(0, min(right, target_width - 1))
        bottom = max(0, min(bottom, target_height - 1))

        scaled_width = right - left
        scaled_height = bottom - top

        if scaled_width <= 0 or scaled_height <= 0:
            continue

        scaled.append(
            Detection(
                class_id=detection.class_id,
                class_name=detection.class_name,
                confidence=detection.confidence,
                box=(
                    left,
                    top,
                    scaled_width,
                    scaled_height
                )
            )
        )

    return scaled




def _save_snapshot(directory: str,frame: np.ndarray,detections: list[Detection]) -> Optional[str]:
    """
    Save an annotated frame.

    Detection.box uses (x, y, width, height).
    """

    annotated = frame.copy()

    for detection in detections:

        x, y, width, height = detection.box

        top_left = (x, y)
        bottom_right = (x + width, y + height)

        cv2.rectangle(
            annotated,
            top_left,
            bottom_right,
            (0, 255, 0),
            2
        )

        label = (
            f"{detection.class_name} "
            f"{detection.confidence:.2f}"
        )

        (text_width, text_height), _ = cv2.getTextSize(
            label,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            2
        )

        label_x = x
        label_y = y - 10

        if label_y < text_height:
            label_y = y + text_height + 5

        cv2.putText(
            annotated,
            label,
            (label_x, label_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2
        )

    path = _build_snapshot_path(directory)

    if not cv2.imwrite(path, annotated):

        print(
            f"Failed to write snapshot: {path}",
            file=sys.stderr
        )

        return None

    print(f"Snapshot saved: {path}")

    return path




def send_snapshot_event(snapshot_path: str,detections: list[Detection],camera_name: str,timestamp: str,shared_storage_root: str) -> bool:
    """
    Notify Beena Core about a saved snapshot.
    """

    valid_detections = [
        detection
        for detection in detections
        if _is_person_or_animal(detection.class_name)
    ]

    if not valid_detections:
        return False

    primary_detection = max(
        valid_detections,
        key=lambda detection: detection.confidence
    )

    payload = {
        "event_id": str(uuid4()),

        "image_path": os.path.relpath(
            snapshot_path,
            shared_storage_root
        ).replace("\\", "/"),

        "local_time": timestamp,

        "detected_class": primary_detection.class_name,

        "confidence": float(
            primary_detection.confidence
        ),

        "camera_name": camera_name,
    }

    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        BEENA_CORE_URL,
        data=data,
        headers={
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=150
        ) as response:

            print(
                f"Rust notification status: {response.status}"
            )

            return response.status == 202

    except Exception as exc:

        print(
            f"Failed to notify Rust: {exc}",
            file=sys.stderr
        )

        return False



def _handle_yolo_result(future: Future,pending_frame: Frame,frame_synchronizer: FrameSynchronizer,snapshot_dir: str,camera_name: str,shared_storage_root: str,event_executor: ThreadPoolExecutor,last_snapshot_time: float) -> float:
    """
    Process a completed YOLO inference.

    The exact Sub Frame submitted to YOLO is used for synchronization.
    """

    try:

        detections = future.result()

    except Exception as exc:

        print(
            f"YOLO inference failed: {exc}",
            file=sys.stderr
        )

        return last_snapshot_time

    valid_detections = [
        detection
        for detection in detections
        if _is_person_or_animal(detection.class_name)
    ]

    if not valid_detections:
        return last_snapshot_time

    current_time = time.monotonic()

    if current_time - last_snapshot_time < SNAPSHOT_COOLDOWN:
        return last_snapshot_time

    sync_result = frame_synchronizer.process(pending_frame)

    if sync_result.main_frame is not None:

        snapshot_frame = sync_result.main_frame.image

        snapshot_detections = _scale_detections(
            valid_detections,
            pending_frame.image,
            snapshot_frame
        )

        print(
            f"Using synchronized Main frame "
            f"(delta: {sync_result.time_delta:.4f}s)"
        )

    else:

        snapshot_frame = pending_frame.image

        snapshot_detections = valid_detections

        print(
            "Main frame synchronization unavailable. "
            "Using Sub frame."
        )

    if not snapshot_detections:
        return last_snapshot_time

    snapshot_path = _save_snapshot(
        snapshot_dir,
        snapshot_frame,
        snapshot_detections
    )

    if snapshot_path is None:
        return last_snapshot_time

    event_timestamp = _make_snapshot_timestamp()

    event_executor.submit(
        send_snapshot_event,
        snapshot_path,
        snapshot_detections,
        camera_name,
        event_timestamp,
        shared_storage_root
    )

    return current_time




def main(argv: list[str]) -> int:

    parser = argparse.ArgumentParser(
        description="Beena local-first smart security camera."
    )

    parser.add_argument(
        "min_changed_ratio",
        nargs="?",
        type=lambda value: _parse_float(
            value, 0.0, 1.0
        ),
        default=0.002
    )

    parser.add_argument(
        "confidence_threshold",
        nargs="?",
        type=lambda value: _parse_float(
            value, 0.0, 1.0
        ),
        default=0.5
    )

    parser.add_argument(
        "yolo_interval",
        nargs="?",
        type=_parse_positive_int,
        default=10
    )

    parser.add_argument(
        "--no-show",
        action="store_true",
        help="Run without a preview window."
    )

    args = parser.parse_args(argv)



    motion_config = MotionConfig(
        min_changed_ratio=args.min_changed_ratio
    )

    yolo_config = YoloConfig(
        confidence_threshold=args.confidence_threshold
    )



    project_root = os.path.dirname(
        os.path.abspath(__file__)
    )

    shared_storage_root = os.path.join(
        project_root,
        "shared"
    )

    snapshot_dir = os.path.join(
        shared_storage_root,
        "snapshots"
    )

    try:

        os.makedirs(
            snapshot_dir,
            exist_ok=True
        )

    except OSError as exc:

        print(
            f"Failed to create snapshots directory: {exc}",
            file=sys.stderr
        )

        return 1



    try:

        camera_manager, camera_name = load_camera_manager()

    except Exception as exc:

        print(
            f"Camera configuration failed: {exc}",
            file=sys.stderr
        )

        return 1



    motion_detector = MotionDetector(
        motion_config
    )

    yolo_detector = YoloDetector(
        yolo_config
    )

    if not yolo_detector.load():
        return 1

    frame_synchronizer = FrameSynchronizer(
        camera_manager,
        FRAME_SYNC_MAX_DELTA
    )



    yolo_executor = ThreadPoolExecutor(
        max_workers=1,
        thread_name_prefix="beena-yolo"
    )

    event_executor = ThreadPoolExecutor(
        max_workers=1,
        thread_name_prefix="beena-events"
    )

    yolo_future: Optional[Future] = None

    pending_yolo_frame: Optional[Frame] = None



    frame_counter = 0

    last_processed_frame_id: Optional[int] = None

    last_snapshot_time = (
        time.monotonic() - SNAPSHOT_COOLDOWN
    )

    show = not args.no_show

    window_name = "Beena"

    manager_started = False

    ok = True

    try:


        camera_manager.start()

        manager_started = True

        print(f"Beena started. Camera: {camera_name}")

        if show:

            cv2.namedWindow(
                window_name,
                cv2.WINDOW_NORMAL
            )

            cv2.resizeWindow(
                window_name,
                1280,
                720
            )



        while True:

            try:

                sub_frame = camera_manager.get_sub_frame()

            except LookupError:

                # Sub stream has not delivered its first frame yet.
                time.sleep(0.01)
                continue

            # Avoid processing the same buffered frame repeatedly.
            if sub_frame.frame_id == last_processed_frame_id:

                time.sleep(0.005)
                continue

            last_processed_frame_id = sub_frame.frame_id

            frame = sub_frame.image



            if (
                yolo_future is not None
                and yolo_future.done()
                and pending_yolo_frame is not None
            ):

                last_snapshot_time = _handle_yolo_result(
                    yolo_future,
                    pending_yolo_frame,
                    frame_synchronizer,
                    snapshot_dir,
                    camera_name,
                    shared_storage_root,
                    event_executor,
                    last_snapshot_time
                )

                yolo_future = None
                pending_yolo_frame = None



            motion = motion_detector.detect(frame)

            if motion:

                frame_counter += 1

                if (
                    frame_counter >= args.yolo_interval
                    and yolo_future is None
                ):

                    frame_counter = 0

                    try:

                        pending_yolo_frame = sub_frame

                        yolo_future = yolo_executor.submit(
                            yolo_detector.detect,
                            frame.copy()
                        )

                    except Exception as exc:

                        print(
                            f"Failed to launch YOLO: {exc}",
                            file=sys.stderr
                        )

                        yolo_future = None
                        pending_yolo_frame = None

            else:

                frame_counter = 0



            if show:

                preview = frame.copy()

                text_color = (
                    (0, 0, 255)
                    if motion
                    else (0, 255, 0)
                )

                status_text = (
                    "Motion: TRUE"
                    if motion
                    else "Motion: FALSE"
                )

                ratio_text = (
                    f"Ratio: "
                    f"{motion_detector.get_last_ratio():.4f}"
                )

                threshold_text = (
                    f"Threshold: "
                    f"{motion_config.min_changed_ratio:.4f}"
                )

                confidence_text = (
                    f"Confidence: "
                    f"{yolo_detector.get_confidence_threshold():.2f}"
                )

                cv2.putText(
                    preview,
                    status_text,
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,
                    text_color,
                    2
                )

                cv2.putText(
                    preview,
                    ratio_text,
                    (20, 75),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    text_color,
                    2
                )

                cv2.putText(
                    preview,
                    threshold_text,
                    (20, 110),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    text_color,
                    2
                )

                cv2.putText(
                    preview,
                    confidence_text,
                    (20, 145),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    text_color,
                    2
                )

                cv2.imshow(
                    window_name,
                    preview
                )

                if (cv2.waitKey(1) & 0xFF) == ord("q"):
                    break

    except KeyboardInterrupt:

        print("\nStopping Beena...")

    except Exception as exc:

        print(
            f"Vision pipeline error: {exc}",
            file=sys.stderr
        )

        ok = False

    finally:



        if manager_started:

            try:

                camera_manager.stop()

            except Exception as exc:

                print(
                    f"Camera shutdown error: {exc}",
                    file=sys.stderr
                )

                ok = False



        if yolo_future is not None:

            try:

                detections = yolo_future.result()

                if pending_yolo_frame is not None:

                    last_snapshot_time = _handle_yolo_result(
                        _completed_future(detections),
                        pending_yolo_frame,
                        frame_synchronizer,
                        snapshot_dir,
                        camera_name,
                        shared_storage_root,
                        event_executor,
                        last_snapshot_time
                    )

            except Exception as exc:

                print(
                    f"YOLO shutdown error: {exc}",
                    file=sys.stderr
                )



        yolo_executor.shutdown(
            wait=True
        )

        event_executor.shutdown(
            wait=True
        )

        if show:
            cv2.destroyAllWindows()

        print("Beena stopped.")

    return 0 if ok else 1


def _completed_future(result) -> Future:
    """
    Create an already-completed Future for shutdown handling.
    """

    future = Future()
    future.set_result(result)

    return future


if __name__ == "__main__":

    try:

        sys.exit(
            main(sys.argv[1:])
        )

    except KeyboardInterrupt:

        sys.exit(130)
