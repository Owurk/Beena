from yaml import safe_load, YAMLError
from config.schema import CameraConfig


def load_config(path: str) -> CameraConfig:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = safe_load(f)

    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {path}")

    except YAMLError as e:
        raise YAMLError(f"Invalid YAML file: {e}") from e

    if data is None:
        raise ValueError("Configuration file is empty")

    return CameraConfig.model_validate(data)
