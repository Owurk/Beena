import sys
from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np
import onnxruntime as ort


@dataclass
class YoloConfig:
    model_path: str = "models/yolo26n.onnx"
    classes_path: str = "models/coco.names"
    confidence_threshold: float = 0.5
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
        self._session = None
        self._input_name = None
        self._output_name = None
        self._class_names: List[str] = []
        self._loaded = False

    def load(self) -> bool:
        try:
            self._session = ort.InferenceSession(
                self._cfg.model_path, providers=["CPUExecutionProvider"]
            )
        except Exception as e:
            print(f"Failed to load ONNX model: {e}", file=sys.stderr)
            self._loaded = False
            return False

        inputs = self._session.get_inputs()
        outputs = self._session.get_outputs()

        if len(inputs) != 1 or len(outputs) != 1:
            print("Unexpected ONNX model structure!", file=sys.stderr)
            self._loaded = False
            return False

        self._input_name = inputs[0].name
        self._output_name = outputs[0].name

        try:
            with open(self._cfg.classes_path, "r", encoding="utf-8") as f:
                self._class_names = [line.strip() for line in f if line.strip()]
        except OSError:
            print(
                f"Could not open classes file: {self._cfg.classes_path}",
                file=sys.stderr,
            )
            self._loaded = False
            return False

        if not self._class_names:
            print("Classes file is empty!", file=sys.stderr)
            self._loaded = False
            return False

        self._loaded = True
        return True

    def detect(self, frame: Optional[np.ndarray]) -> List[Detection]:
        if not self._loaded or frame is None or frame.size == 0:
            return []

        blob = self._preprocess(frame)

        try:
            outputs = self._session.run([self._output_name], {self._input_name: blob})
        except Exception as e:
            print(f"ONNX inference failed: {e}", file=sys.stderr)
            return []

        output = outputs[0]

        return self._postprocess(output, (frame.shape[1], frame.shape[0]))

    def has_person_or_animal(self, frame: np.ndarray) -> bool:
        return len(self.detect(frame)) > 0

    def get_confidence_threshold(self) -> float:
        return self._cfg.confidence_threshold

    def set_confidence_threshold(self, value: float) -> None:
        if 0.0 <= value <= 1.0:
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

    def _postprocess(
        self, output: np.ndarray, original_size: Tuple[int, int]
    ) -> List[Detection]:

        original_width, original_height = original_size

        if (
            output is None
            or output.ndim != 3
            or output.shape[0] != 1
            or output.shape[2] != 6
        ):
            print("Unexpected YOLO26 output shape!", file=sys.stderr)
            return []

        predictions = output[0]

        sx = original_width / self._cfg.input_width
        sy = original_height / self._cfg.input_height

        result: List[Detection] = []

        for row in predictions:
            x1, y1, x2, y2, confidence, class_value = row

            confidence = float(confidence)
            class_id = int(class_value)

            if confidence < self._cfg.confidence_threshold:
                continue

            if not _is_allowed_class(class_id):
                continue

            if class_id < 0 or class_id >= len(self._class_names):
                continue

            left = int(x1 * sx)
            top = int(y1 * sy)
            right = int(x2 * sx)
            bottom = int(y2 * sy)

            left = max(0, min(left, original_width))
            top = max(0, min(top, original_height))
            right = max(0, min(right, original_width))
            bottom = max(0, min(bottom, original_height))

            width = right - left
            height = bottom - top

            if width <= 0 or height <= 0:
                continue

            result.append(
                Detection(
                    class_id=class_id,
                    class_name=self._class_names[class_id],
                    confidence=confidence,
                    box=(left, top, width, height),
                )
            )

        return result
