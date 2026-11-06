import sys
from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np


@dataclass
class YoloConfig:

    model_path: str = "models/yolov8n.onnx"
    classes_path: str = "models/coco.names"
    confidence_threshold: float = 0.5
    nms_threshold: float = 0.45
    input_width: int = 640
    input_height: int = 640


@dataclass
class Detection:

    class_id: int = -1
    class_name: str = ""
    confidence: float = 0.0
    box: Tuple[int, int, int, int] = (0, 0, 0, 0)



_ALLOWED_CLASS_IDS = frozenset({0, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23})


def _is_allowed_class(class_id: int) -> bool:
    return class_id in _ALLOWED_CLASS_IDS


class YoloDetector:

    def __init__(self, cfg: Optional[YoloConfig] = None) -> None:
        self._cfg = cfg if cfg is not None else YoloConfig()
        self._net = None
        self._class_names: List[str] = []
        self._loaded = False

    def load(self) -> bool:
        """Load the ONNX model and the class names."""
        try:
            self._net = cv2.dnn.readNetFromONNX(self._cfg.model_path)
        except cv2.error as e:
            print(f"Failed to load ONNX model: {e}", file=sys.stderr)
            self._loaded = False
            return False

        if self._net is None or self._net.empty():
            print("ONNX model is empty!", file=sys.stderr)
            self._loaded = False
            return False

        self._net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self._net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

        try:
            with open(self._cfg.classes_path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
        except OSError:
            print(f"Could not open classes file: {self._cfg.classes_path}",file=sys.stderr)
            self._loaded = False
            return False

        self._class_names = [line for line in lines if line]

        if not self._class_names:
            print("Classes file is empty!", file=sys.stderr)
            self._loaded = False
            return False

        self._loaded = True
        return True

    def detect(self, frame: Optional[np.ndarray]) -> List[Detection]:
        """Run inference on one frame."""
        if not self._loaded or frame is None or frame.size == 0:
            return []

        blob = self._preprocess(frame)

        self._net.setInput(blob)
        output = self._net.forward()

        original_size = (frame.shape[1], frame.shape[0])  
        return self._postprocess(output, original_size)

    def has_person_or_animal(self, frame: np.ndarray) -> bool:
        
        return len(self.detect(frame)) > 0

    def get_confidence_threshold(self) -> float:
    
        return self._cfg.confidence_threshold

    def set_confidence_threshold(self, value: float) -> None:
        
        self._cfg.confidence_threshold = value

    def get_config(self) -> YoloConfig:
        
        return self._cfg

    def set_config(self, cfg: YoloConfig) -> None:

        self._cfg = cfg

    def _preprocess(self, frame: np.ndarray) -> np.ndarray:

        return cv2.dnn.blobFromImage(
            frame,
            1.0 / 255.0,
            (self._cfg.input_width, self._cfg.input_height),
            0.0,          
            swapRB=True,   
            crop=False,   
            ddepth=cv2.CV_32F,
        )

    def _postprocess(self, output: np.ndarray, original_size: Tuple[int, int] ) -> List[Detection]:
  
        original_width, original_height = original_size

        if output is None or output.size == 0 or output.ndim != 3:
            dims = -1 if output is None else output.ndim
            print(f"Unexpected YOLO output: dims={dims}", file=sys.stderr)
            return []

        num_classes = len(self._class_names)

        if output.shape[1] != num_classes + 4:
            print(f"YOLO output size mismatch: got {output.shape[1]}, "
                  f"expected {num_classes + 4}", file=sys.stderr)
            return []


        predictions = output.reshape(output.shape[1], -1).T

        boxes: List[Tuple[int, int, int, int]] = []
        confidences: List[float] = []
        class_ids: List[int] = []

        sx = original_width / self._cfg.input_width
        sy = original_height / self._cfg.input_height

        conf_threshold = self._cfg.confidence_threshold

        for row in predictions:
            scores = row[4:]
            best_id = int(np.argmax(scores))
            best_score = float(scores[best_id])

            if best_score < conf_threshold:
                continue

            if not _is_allowed_class(best_id):
                continue

            cx = float(row[0]) * sx
            cy = float(row[1]) * sy
            w = float(row[2]) * sx
            h = float(row[3]) * sy

            left = int(cx - w / 2)
            top = int(cy - h / 2)

            boxes.append((left, top, int(w), int(h)))
            confidences.append(best_score)
            class_ids.append(best_id)


        keep: np.ndarray = np.empty(0, dtype=int)
        if boxes:
            raw = cv2.dnn.NMSBoxes(
                boxes,
                confidences,
                conf_threshold,
                self._cfg.nms_threshold,
            )
            keep = np.array(raw, dtype=int).reshape(-1)

        result: List[Detection] = []

        for idx in keep:
            idx = int(idx)

            if class_ids[idx] < 0 or class_ids[idx] >= len(self._class_names):
                continue


            x, y, w, h = boxes[idx]
            x1 = max(x, 0)
            y1 = max(y, 0)
            x2 = min(x + w, original_width)
            y2 = min(y + h, original_height)
            box = (x1, y1, x2 - x1, y2 - y1)

            if box[2] <= 0 or box[3] <= 0:
                continue

            result.append(
                Detection(
                    class_id=class_ids[idx],
                    class_name=self._class_names[class_ids[idx]],
                    confidence=confidences[idx],
                    box=box,
                )
            )

        return result
