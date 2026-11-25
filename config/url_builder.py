
from config.credentials import CameraCredentials
from urllib.parse import urlunsplit, urlsplit, quote


def build_rtsp_url(stream_url: str,credentials: CameraCredentials) -> str:

    url_pieces = urlsplit(stream_url)

    if "@" in url_pieces.netloc:
        raise ValueError("Username or password shouldn't be in RTSP URL.")

    if credentials.username is None and credentials.password is None:
        return stream_url

    if credentials.username is None or credentials.password is None:
        raise ValueError("Both username and password are required.")

    username = quote(credentials.username, safe="")
    password = quote(credentials.password, safe="")

    authenticated_url = urlunsplit((
        url_pieces.scheme,
        f"{username}:{password}@{url_pieces.netloc}",
        url_pieces.path,
        url_pieces.query,
        url_pieces.fragment
    ))

    return authenticated_url
