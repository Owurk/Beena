
from dataclasses import dataclass
import os


@dataclass(frozen=True, slots=True)
class CameraCredentials:
    username: str | None
    password: str | None


def get_camera_credentials(camera_id: str) -> CameraCredentials:
    camera_id = camera_id.upper()

    username = os.getenv(f"CAMERA_{camera_id}_USERNAME")
    password = os.getenv(f"CAMERA_{camera_id}_PASSWORD")

    username = username.strip() if username else None
    password = password.strip() if password else None

    if username is None and password is None:
        return CameraCredentials(
            username=None,
            password=None
        )

    if username is None:
        raise ValueError("Username is missing.")

    if password is None:
        raise ValueError("Password is missing.")

    return CameraCredentials(
        username=username,
        password=password
    )
