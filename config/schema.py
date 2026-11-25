from pydantic import BaseModel,ConfigDict,field_validator,model_validator,Field
from urllib.parse import urlparse

class CameraConnection(BaseModel):
    model_config = ConfigDict(extra="forbid",strict=True)
    main_stream : str
    sub_stream : str
    @field_validator("main_stream", "sub_stream", mode="before")
    @classmethod
    def check_streams(cls,value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Stream URL must be a non-empty string.")

        value = value.strip()
        url = urlparse(value)
        scheme = url.scheme
        netloc = url.netloc
        if scheme not in ("rtsp","rtsps") or netloc.strip() == "":
            raise ValueError("main/sub Stream Url Is Invalid.")

        return value


    @model_validator(mode="after")
    def check_streams_equality(self):
        if self.main_stream == self.sub_stream:
            raise ValueError("Main and Sub Stream URLs cannot be equal.")

        return self

class Camera(BaseModel):
    model_config = ConfigDict(extra="forbid",strict=True)
    id : str
    name : str
    connection : CameraConnection


    @field_validator("id", "name")
    @classmethod
    def validate_strings(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Field cannot be empty")
        return value.strip()

class CameraConfig(BaseModel):
    model_config = ConfigDict(extra="forbid",strict=True)
    cameras: list[Camera] = Field(min_length=1)
    @model_validator(mode="after")
    def check_ids(self):
        ids = set()
        for camera in self.cameras:
            if camera.id in ids:
                raise ValueError("Camera Id Must Be Unique.")
            ids.add(camera.id)

        return self
