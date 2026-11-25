<p align="center">
  <img src="assets/beena-logo.png" alt="Beena" width="130"/>
</p>

<h1 align="center">🐝 Beena</h1>

<p align="center">
  <b>The Watchful Eye of Your Home</b> · Smart, open-source home guardian · v2.0
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-2.0-3adce5" alt="version"/>
  <img src="https://img.shields.io/badge/RTSP-live_cameras-00B4D8" alt="RTSP"/>
  <img src="https://img.shields.io/badge/Rust-stable-DEA584?logo=rust&logoColor=white" alt="Rust"/>
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/OpenCV-4.10-5C3EE8" alt="OpenCV"/>
  <img src="https://img.shields.io/badge/YOLO26-ONNX%20Runtime-FF6F00" alt="YOLO26"/>
  <img src="https://img.shields.io/badge/Telegram-Bot-26A5E4?logo=telegram&logoColor=white" alt="Telegram"/>
</p>

Beena watches a camera feed the way a guard would, not the way a recorder does. It detects motion, confirms that a person or an animal is actually in the frame using a local neural network, saves an annotated snapshot of the moment that matters, and sends it to Telegram together with a short AI-generated description of the scene.

Motion detection and object detection run entirely on your own machine. Only the snapshot of a detected event is sent to a vision-language model to produce the scene description, and only to the endpoint you configure.

<<<<<<< HEAD
---

## Features (v1.0)

- **Motion detection that ignores noise.** MOG2 adaptive background subtraction with Gaussian blur, CLAHE contrast enhancement, shadow removal and morphological cleanup. Motion is accepted only after at least two consecutive frames above the changed-pixel threshold, so camera shake and gradual lighting changes do not trigger events.
- **Local object detection.** YOLO26 nano on ONNX Runtime (CPU) at 640x640. Of COCO's 80 classes, only the eleven that matter for home security are kept: `person`, `bird`, `cat`, `dog`, `horse`, `sheep`, `cow`, `elephant`, `bear`, `zebra`, `giraffe`.
- **Asynchronous pipeline.** Inference and notification HTTP calls run in dedicated worker threads, so slow model execution never stalls the camera loop.
- **AI scene analysis.** Every event is analyzed by a vision-language model that returns a schema-enforced result: a short title, a one-to-three sentence factual description, a severity level (`low` / `medium` / `high`) and an `is_unusual` flag.
- **Smart snapshots.** Only frames with a confirmed person or animal are saved, annotated with green boxes and confidence labels, under `shared/snapshots/`. Back-to-back events are rate-limited by a five-second cooldown.
- **Instant Telegram alerts.** The photo and its analysis reach your Telegram within seconds through a lightweight bot. Setup is a single `/start` message.
- **Privacy-first and ethics-aware.** No identification of people, no judgment of intent, strict image-path validation, and no file access outside the shared storage folder.
=======
**What's new in v2.0** — Beena now runs on **live RTSP network cameras**. The webcam / video-file source of v1.0 is gone; each camera is described in a validated YAML config and captured through a dedicated dual-stream worker stack (main + sub) with automatic reconnection and main/sub frame synchronization.

##  Beena at a Glance

-  **RTSP dual-stream capture** — every camera provides a `main` stream (high resolution, for snapshots) and a `sub` stream (low resolution, for analysis). Each stream runs in its own worker thread with automatic reconnection and exponential backoff (1s → 30s), so a network hiccup never kills the pipeline.
-  **Smart motion detection** — MOG2 background subtraction with Gaussian blur, CLAHE contrast enhancement and morphological cleanup; camera shake and subtle lighting changes are not mistaken for real movement.
-  **Local machine vision** — a **YOLO26** model on ONNX Runtime and CPU; of COCO's 80 classes, only the 11 that matter for home security: `person`, `bird`, `cat`, `dog`, `horse`, `sheep`, `cow`, `elephant`, `bear`, `zebra`, `giraffe`.
-  **Frame synchronization** — inference runs on the sub stream, but the saved snapshot is taken from the main frame closest in time (max delta 100 ms); detection boxes are rescaled to the main resolution automatically.
-  **AI scene analysis** — for every event it produces a **short title, a 1–3 sentence description, a severity level** (low / medium / high) and an **unusual** flag.
-  **Smart snapshots** — only when a person or animal is really in the frame; green boxes with class labels drawn on the image, and a **5-second cooldown** between events.
-  **Instant Telegram alerts** — photo + analysis through a lightweight teloxide bot; setting it up is a single `/start`.
-  **Privacy-first and ethics-aware** — no identification of people, no intent judgment, strict image-path validation, and no reads outside the shared folder.
>>>>>>> 9a1ebca (feat: RTSP-only vision pipeline with dual-stream capture and frame sync)

<p align="center">
  <img src="assets/detection-demo.jpg" alt="Real Beena output" width="720"/>
  <br/>
<<<<<<< HEAD
  <sub>Real output of v1.0 - a person detected at 0.94 confidence, with automatic analysis of the same frame.</sub>
=======
  <sub>Real output of v1.0 — a <code>person</code> detected at 0.94 confidence, with automatic analysis of the same frame</sub>
>>>>>>> 9a1ebca (feat: RTSP-only vision pipeline with dual-stream capture and frame sync)
</p>

---

## Architecture

Beena is built from four independent processes that talk to each other over localhost HTTP and one shared disk folder. Each process can be started, restarted, or later moved to another machine on its own.

```mermaid
flowchart LR
<<<<<<< HEAD
    subgraph V["main.py - Vision pipeline"]
        A["Webcam or video file<br/>--source"] --> B["Motion detection<br/>OpenCV"]
        B --> C["YOLO26 on ONNX Runtime<br/>person and animal classes"]
        C --> D["Annotated snapshot<br/>shared/snapshots"]
    end
    D -- "POST /snapshot - port 8080" --> S
    subgraph S["beena-server - Rust, Axum"]
        E["Event validation<br/>and forwarding"]
    end
    S -- "POST /api/v1/analyze - port 8001" --> Z
    subgraph Z["ai.py - FastAPI, LangChain"]
        F["Vision-language model<br/>title, description,<br/>severity, unusual flag"]
=======
    C["📡 RTSP camera<br/>main · sub"] --> V
    subgraph V["🐍 main.py — Vision Pipeline"]
        A["camera/ — CaptureWorker ×2<br/>reconnect · backoff · buffers"] --> B["Motion detection<br/>on sub stream"]
        B -- "sustained motion" --> D["YOLO26 · ONNX<br/>11 person & animal classes"]
        D -- "valid detection" --> E["Sync main ↔ sub (≤100 ms)<br/>Snapshot + green boxes<br/>shared/snapshots"]
    end
    E -- "POST /snapshot · port 8080" --> S
    subgraph S["🦀 beena-server — Axum"]
        F["Event & image path<br/>validation"]
    end
    S -- "POST /api/v1/analyze · port 8001" --> Z
    subgraph Z["🧠 ai.py — FastAPI · LangChain"]
        G["GPT-6-luna Vision<br/>title · description<br/>severity · unusual?"]
>>>>>>> 9a1ebca (feat: RTSP-only vision pipeline with dual-stream capture and frame sync)
    end
    Z -- "JSON response" --> S
    S -- "photo + analysis caption" --> T["Telegram alert"]
    U["beena-telegram<br/>registers receiver via /start"] -.-> T
```

| Service | Run | Technology | Address | Role |
|---|---|---|---|---|
<<<<<<< HEAD
| Vision pipeline | `python main.py` | Python, OpenCV, ONNX Runtime | - | camera input, motion, YOLO, snapshots |
| AI service | `python ai.py` | Python, FastAPI, LangChain | `127.0.0.1:8001` | visual analysis of each event |
| Coordination core | `cargo run --bin beena-server` | Rust, Axum, Tokio | `127.0.0.1:8080` | receive events, request analysis, send alerts |
| Telegram bot | `cargo run --bin beena-telegram` | Rust, teloxide | polling | register the alert receiver via `/start` |
=======
| **Vision pipeline** | `python main.py` | Python · OpenCV · ONNX Runtime | — | RTSP capture, motion, YOLO, snapshots |
| **AI service** | `python ai.py` | Python · FastAPI · LangChain | `127.0.0.1:8001` | visual analysis of each event |
| **Coordination core** | `cargo run --bin beena-server` | Rust · Axum · Tokio | `127.0.0.1:8080` | receive events, analyze, send alerts |
| **Telegram bot** | `cargo run --bin beena-telegram` | Rust · teloxide | polling | register the alert receiver via `/start` |
>>>>>>> 9a1ebca (feat: RTSP-only vision pipeline with dual-stream capture and frame sync)

### The journey of an event

<<<<<<< HEAD
1. **Frame acquisition.** Frames come from the live webcam (no arguments) or a video file via `--source`. Video files are paced at their real FPS and exit cleanly when playback ends.
2. **Motion detection.** Each frame is grayscaled, blurred, contrast-enhanced and passed through an adaptive background subtractor; morphology removes noise and shadows. Motion counts as real only after at least 2 consecutive frames above the threshold.
3. **Machine vision.** After every N motion frames (`yoloInterval`, default 10), a copy of the frame goes asynchronously to YOLO26. The camera loop never waits for inference.
4. **Snapshot.** If a person or animal is present with enough confidence, the annotated frame is saved to `shared/snapshots/`. A five-second cooldown separates consecutive events.
5. **AI analysis.** The Rust core validates the event (the image path must resolve inside the shared folder) and forwards it to the AI service, which loads the image, applies size and type checks, and returns a structured analysis.
6. **Notification.** The core sends the photo with the analysis caption to the registered Telegram chat and returns `202 Accepted` to the pipeline.
=======
1. **Frame acquisition** — the main and sub RTSP streams are captured by two independent workers into bounded frame buffers; if a stream drops, the worker reconnects on its own with growing backoff.
2. **Motion detection** — each sub frame is grayscaled, enhanced and compared against the background model; motion only counts as "real" after at least **2 consecutive frames** above the changed-pixel ratio.
3. **Machine vision** — after every **10 frames of sustained motion**, a copy of the sub frame goes **asynchronously** to YOLO26, so the camera loop never stalls for inference.
4. **Snapshot** — if a person or animal is present with enough confidence, the **synchronized main frame** (closest in time to the analyzed sub frame) is saved with boxes and labels to `shared/snapshots/`; back-to-back events are rate-limited by a **5-second cooldown**.
5. **AI analysis** — the Rust core forwards the event to the AI service; the image (with a size limit and path checks) reaches the vision model and comes back as a **guaranteed structured response** (JSON Schema).
6. **Notification** — the core sends the photo with the analysis caption to Telegram and returns `202 Accepted` to the pipeline.
>>>>>>> 9a1ebca (feat: RTSP-only vision pipeline with dual-stream capture and frame sync)

---

## Repository layout

<<<<<<< HEAD
```text
.
├── main.py                    # Vision pipeline: capture, motion, YOLO, snapshots, event dispatch
├── capture.py                 # Video source wrapper (webcam index, file, RTSP URL)
├── motion_detector.py         # MOG2 background subtraction with CLAHE and morphology
├── yolo_detector.py           # YOLO26 ONNX inference and class filtering
├── ai.py                      # FastAPI analysis service (vision-language model)
├── requirements.txt           # Python dependencies (vision pipeline)
├── .env.example               # Configuration template for the AI service
├── models/
│   ├── yolo26n.onnx           # YOLO26 nano model, ONNX format
│   └── coco.names             # COCO class names
├── assets/                    # Logo and demo output image
└── beena-core/
    ├── Cargo.toml             # Rust workspace (beena-server, beena-telegram)
    ├── .env.example           # Configuration template for the Rust services
    └── src/bin/
        ├── server.rs          # Axum event core on 127.0.0.1:8080
        └── telegram.rs        # teloxide bot that registers the alert receiver
```
=======
- **Rust** (stable) — via [rustup](https://rustup.rs)
- **Python 3.11+**
- An RTSP camera (or a test setup: [mediamtx](https://github.com/bluenviron/mediamtx) + FFmpeg, see below)
- An OpenAI-compatible API key (or any compatible service)
- A Telegram bot: get a token from [@BotFather](https://t.me/BotFather)
>>>>>>> 9a1ebca (feat: RTSP-only vision pipeline with dual-stream capture and frame sync)

---

## Requirements

- Python 3.11 or newer
- Rust (stable toolchain) to build the two Rust services, via [rustup](https://rustup.rs)
- OpenCV 4.10 and ONNX Runtime (installed with the Python requirements)
- An OpenAI-compatible API key for the vision-language model used by `ai.py`
- A Telegram bot token, obtained from [@BotFather](https://t.me/BotFather)

A webcam (built-in or USB) for live input, or any video file for testing. Network camera support is on the roadmap (see below).

---

## Configuration

Two `.env` files configure the services. Run each service from the directory that contains its `.env` file, and point both at the **same shared folder** so the pipeline, the core and the AI service agree on where snapshots live. An absolute path is recommended.

**Project root - `.env`** (used by `ai.py`):

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | - | API key for the vision-language model (required) |
| `OPENAI_BASE_URL` | - | Override the API base URL for compatible providers (optional) |
| `AI_PROVIDER` | `openai` | Analysis provider; only `openai`-compatible providers are supported |
| `AI_MODEL` | `gpt-6-luna` | Model name used for scene analysis |
| `AI_TIMEOUT_SECONDS` | `30` | Timeout for a single analysis request |
| `SHARED_STORAGE_ROOT` | `./shared` | Shared folder; image paths are validated inside it |
| `MAX_IMAGE_SIZE_MB` | `10` | Maximum accepted snapshot size |

**`beena-core/.env`** (used by both Rust binaries):

| Variable | Default | Description |
|---|---|---|
| `TELOXIDE_TOKEN` | - | Telegram bot token (required) |
| `SHARED_STORAGE_ROOT` | `./shared` | Must point to the same folder as above |

---

## Installation and startup

```bash
git clone https://github.com/Owurk/Beena.git
cd Beena

# Python dependencies
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

<<<<<<< HEAD
# Configuration
cp .env.example .env                 # fill in the values, see the tables above
cp beena-core/.env.example beena-core/.env
```

Run the four processes in this order (four terminals):
=======
# Rust dependencies (beena-core is unchanged in v2.0)
cd beena-core && cargo build && cd ..
```

>  **Important:** run all commands from the **project root**; the model path (`models/yolo26n.onnx`) is resolved relative to it.

### Configuration

**1. Camera** — `config/cameras.yaml` (exactly one camera in v2.0):

```yaml
cameras:
  - id: test_camera            # used to look up credentials below
    name: Beena Test Camera    # shown in Telegram alerts
    connection:
      main_stream: rtsp://192.168.1.10:554/stream1   # high resolution
      sub_stream: rtsp://192.168.1.10:554/stream2    # low resolution
```

**2. Camera credentials** — `config/.env` (create it from `config/env.example`). Variable names are built from the camera `id`: `CAMERA_<ID>_USERNAME` / `CAMERA_<ID>_PASSWORD`. Leave both empty for a camera without authentication.

**3. AI service** — `.env` in the project root (create it from `.env.example`): `OPENAI_API_KEY`, optional `OPENAI_BASE_URL`, `AI_MODEL`.

**4. Rust core** — `beena-core/.env` (create it from `beena-core/.env.example`): `TELOXIDE_TOKEN` and `SHARED_STORAGE_ROOT` — set it to the **absolute path** of this project's `shared/` folder.

### Test setup without a real camera

[mediamtx](https://github.com/bluenviron/mediamtx) can turn any video file into the two RTSP streams Beena expects. Put `test.mp4` in the project root, start mediamtx (listens on `8554`), then run `start_streams.bat` — it publishes `rtsp://127.0.0.1:8554/main` (1920×1080) and `rtsp://127.0.0.1:8554/sub` (640×360 @ 10 fps) with FFmpeg. Verify with:

```bash
ffprobe -v error rtsp://127.0.0.1:8554/main
ffprobe -v error rtsp://127.0.0.1:8554/sub
```

### Run — four terminals
>>>>>>> 9a1ebca (feat: RTSP-only vision pipeline with dual-stream capture and frame sync)

```bash
# 1) AI service (127.0.0.1:8001) - from the project root
python ai.py

# 2) Coordination core (127.0.0.1:8080) - from beena-core/
cd beena-core
cargo run --bin beena-server

# 3) Telegram bot - from beena-core/
cargo run --bin beena-telegram
#    Open your bot in Telegram and send /start so your chat_id
#    is stored in telegram.json. This registers the alert receiver.

<<<<<<< HEAD
# 4) Vision pipeline - from the project root
python main.py                          # live webcam
python main.py --source walking.mp4     # video file
python main.py --source walking.mp4 --no-show   # headless
```

`main.py` resolves the model files relative to the project root, so start it from there. The Rust binaries read `telegram.json` from their working directory, so start both of them from `beena-core/`.

With a live source the preview window shows the current motion status, the changed-pixel ratio, the thresholds and the camera index. Press `q` to quit. A video file plays to the end and then exits cleanly.
=======
# 4) Vision pipeline
python main.py                # with preview window
python main.py --no-show      # headless
```

The preview window shows the live sub stream with `Motion: TRUE/FALSE`, the changed-pixel ratio, the threshold and the confidence. Press `q` to quit.
>>>>>>> 9a1ebca (feat: RTSP-only vision pipeline with dual-stream capture and frame sync)

### `main.py` command-line parameters

| Parameter | Default | Description |
|---|---|---|
<<<<<<< HEAD
| `pixelThreshold` | `25` | per-pixel difference threshold, 1 to 255 |
| `minChangedRatio` | `0.002` | minimum changed-pixel ratio per frame, 0 to 1 |
| `confidenceThreshold` | `0.5` | minimum confidence to accept a YOLO detection |
| `yoloInterval` | `10` | run YOLO once every N frames with sustained motion |
| `cameraIndex` | `0` | webcam index, 0 to 10, used when `--source` is not given |
| `--source` | - | path to a video file, or an RTSP URL (experimental, see roadmap) |
| `--no-show` | - | run headless, no preview window |
=======
| `min_changed_ratio` | `0.002` | minimum changed-pixel ratio per frame to count as motion — 0 to 1 |
| `confidence_threshold` | `0.5` | minimum confidence to accept a YOLO detection — 0 to 1 |
| `yolo_interval` | `10` | run YOLO after every N consecutive motion frames |
| `--no-show` | — | run without the preview window |

##  Configuration files

| File | Used by | Contents |
|---|---|---|
| `config/cameras.yaml` | `main.py` | camera list (`id`, `name`, `main_stream`, `sub_stream`) — validated with Pydantic; RTSP/RTSPS URLs only |
| `config/.env` | `main.py` | `CAMERA_<ID>_USERNAME` / `CAMERA_<ID>_PASSWORD` per camera |
| `.env` (root) | `ai.py` | `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `AI_PROVIDER`, `AI_MODEL`, `AI_TIMEOUT_SECONDS`, `SHARED_STORAGE_ROOT`, `MAX_IMAGE_SIZE_MB` |
| `beena-core/.env` | both Rust binaries | `TELOXIDE_TOKEN`, `SHARED_STORAGE_ROOT` |
| `telegram.json` (auto-created in `beena-core/`) | both Rust binaries | the chat ID registered via `/start` |

##  API

### `POST /snapshot` — coordination core (port 8080)

Every verified event reported by `main.py` uses this structure:

```json
{
  "event_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "image_path": "snapshots/detect_20261112_155123.jpg",
  "local_time": "2026-11-12T15:51:23+03:30",
  "detected_class": "person",
  "confidence": 0.94,
  "camera_name": "Beena Test Camera"
}
```

- `image_path` is always **relative** to `SHARED_STORAGE_ROOT`; absolute paths or paths containing `..` are rejected with `400`.
- If the Telegram bot is not configured yet, the response is `503`; if the AI analysis fails, `502`.
- On success: `202 Accepted`.

### `POST /api/v1/analyze` — AI service (port 8001)

Takes the same event payload, loads the image from the shared space (allowed extensions: `jpg` / `jpeg` / `png` / `webp`, at most `MAX_IMAGE_SIZE_MB`) and returns a structured response:

```json
{
  "event_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "analysis": {
    "title": "Person Standing in Hallway",
    "description": "A person wearing a pink button-up shirt stands facing the camera in a dim hallway.",
    "severity": "low",
    "is_unusual": false
  }
}
```

Errors: `404` image not found · `400` invalid image · `502` analysis failed.

### `GET /health` — AI service health check

```json
{ "status": "ok", "service": "Beena-ai" }
```

##  Project structure

```
.
├── main.py                  # main vision loop: motion → YOLO → sync → snapshot → alert
├── ai.py                    # AI analysis service (FastAPI · 127.0.0.1:8001)
├── motion_detector.py       # motion detection: MOG2 + CLAHE + morphology
├── yolo_detector.py         # YOLO26 on ONNX Runtime (CPU) + class filtering
├── camera/
│   ├── camera_manager.py    # owns the main & sub workers for one camera
│   ├── capture_worker.py    # RTSP capture thread: reconnect, backoff, buffers
│   ├── frame_buffer.py      # bounded, thread-safe frame buffer
│   ├── frame_synchronizer.py# picks the main frame closest to a sub frame
│   ├── frame.py             # Frame dataclass (image, timestamp, id, stream)
│   └── worker_state.py      # worker lifecycle states
├── config/
│   ├── cameras.yaml         # camera definitions (exactly one camera in v2.0)
│   ├── schema.py            # Pydantic validation for cameras.yaml
│   ├── loader.py            # YAML loader
│   ├── credentials.py       # per-camera credentials from environment
│   └── url_builder.py       # injects credentials into the RTSP URL (percent-encoded)
├── start_streams.bat        # test publisher: test.mp4 → mediamtx main/sub streams
├── requirements.txt
├── .env.example             # template for the AI service (project root)
├── config/env.example       # template for camera credentials
├── models/
│   ├── yolo26n.onnx         # object detection model (640×640, CPUExecutionProvider)
│   └── coco.names           # the 80 COCO class names; 11 person/animal classes are used
└── beena-core/
    ├── Cargo.toml
    └── src/bin/
        ├── server.rs        # beena-server — coordination core (Axum · 127.0.0.1:8080)
        └── telegram.rs      # beena-telegram — alert receiver registration (teloxide)
```

##  Privacy & design principles

These principles are not just slogans; they are written directly into the system prompt and the code:

- **Describe behavior, never judge intent** — the analysis never calls anyone a thief or an intruder; a person's mere presence is not suspicious.
- **No identification of people** — age, gender, ethnicity or other personal traits are never guessed; clothing and visible actions are fine.
- **Cautious by default** — when unsure, it picks the lower severity and sets `is_unusual: false`.
- **Trust the image, not the label** — the green boxes are just detector output; if the image disagrees with the detector's claim, the scene is described as it really is.
- **Immune to in-image instructions** — text visible inside the scene is never followed as an instruction.
- **Minimal data** — motion and object detection are fully local; only the snapshot of that event is used to analyze that event.
- **Path validation** — neither the Rust core nor the AI service will read an image from outside the shared folder.
- **Single receiver** — only the first user who sends `/start` receives notifications.

##  Roadmap

- [x] **RTSP network camera support** (done in v2.0)
- [ ] Multiple simultaneous cameras
- [ ] Receiver management through the bot itself (multi-user)
- [ ] Event storage and search
- [ ] GPU inference (CUDA Execution Provider)
- [ ] One-command deployment with Docker

##  Troubleshooting

| Problem | Likely cause and fix |
|---|---|
| `Camera configuration failed: ...` | `config/cameras.yaml` is missing, has more than one camera, or the stream URLs are not valid RTSP/RTSPS addresses. |
| `Could not open stream for camera ...` | Wrong IP/port/credentials, or the camera is offline. Check the URL in `config/cameras.yaml` and the credentials in `config/.env`. The worker keeps retrying with backoff. |
| Camera connects but no frames | Some cameras require TCP transport and their credentials in the URL; make sure both `main_stream` and `sub_stream` are reachable (test with `ffprobe`). |
| `Failed to load ONNX model` | You are not running from the project root; the `models/` path is relative. |
| Snapshot boxes are offset | Main and sub streams should show the same field of view (same camera); boxes are rescaled by resolution ratio only. |
| `OPENAI_API_KEY is not configured.` | Create the `.env` file in the project root with a valid key. |
| Telegram message never arrives | You have not sent `/start` to the bot (`telegram.json` missing in `beena-core/`) or `TELOXIDE_TOKEN` is wrong. Also check that `SHARED_STORAGE_ROOT` in `beena-core/.env` points to this project's `shared/` folder. |
| `503` response when sending an event | The Telegram bot is not configured yet — send `/start` and try again. |
| Event sent but `502` | `ai.py` is not running, the API key is wrong, or the snapshot path cannot be resolved inside the shared folder. |
>>>>>>> 9a1ebca (feat: RTSP-only vision pipeline with dual-stream capture and frame sync)

---

## Service endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `POST 127.0.0.1:8080/snapshot` | POST | Event intake for the vision pipeline; validates the image path and returns `202 Accepted` |
| `POST 127.0.0.1:8001/api/v1/analyze` | POST | Scene analysis of one event; returns a schema-validated JSON response |
| `GET 127.0.0.1:8001/health` | GET | Health check for the AI service |

The event payload contains `event_id`, `image_path` (relative to the shared folder), `local_time`, `detected_class`, `confidence` and `camera_name`.

All endpoints bind to `127.0.0.1` only. Nothing is exposed to the network in v1.0.

---

## Privacy and data handling

- Motion detection and object detection run **fully locally**. No video ever leaves the machine.
- Only the snapshot of a detected event is sent to the vision-language model endpoint you configure, together with the event metadata.
- The system never identifies people, never judges intent, and prefers the lower severity when the scene is ambiguous.
- Image paths are validated twice (in the Rust core and in the AI service): relative paths only, no traversal, resolved inside the shared storage root, restricted to `jpg`, `jpeg`, `png`, `webp`, with a size cap.
- Instructions found inside scene images are ignored by the analysis model; scene content cannot steer the system.

---

## Roadmap

Version 1.0 is a deliberately small, well-tested foundation: a single local camera (USB webcam or video file), one analysis pipeline, one Telegram receiver. The goal for the next versions is different in kind: **let users run Beena against their own camera systems** - the IP cameras they already own.

This matters because of how the camera industry actually works. Consumer cameras run closed, signed embedded firmware on very small chips; third-party software cannot be installed on them. Every mainstream surveillance application therefore follows the same model: the software runs on a separate host (a mini PC, a NAS, a Raspberry Pi) and **pulls video from the cameras over the network** using RTSP, with ONVIF as the discovery and configuration standard. Beena already fits this model architecturally - the work ahead is an ingestion and packaging project, not a rewrite.

The roadmap below is ordered by priority; each phase is independently useful and ends in a demonstrable release.

### Phase 1 - Hardened RTSP ingestion (planned)

Bring network cameras in as first-class video sources.

- Force TCP transport for RTSP (UDP streams stall or corrupt behind routers), with bounded buffering so Beena always analyzes the newest frame.
- Replace the current five-retries-then-exit behavior with continuous reconnection using exponential backoff.
- Add a stale-frame watchdog that detects a frozen stream.
- Parse and encode credentials safely, and produce actionable errors (wrong password, unreachable host, bad URL).
- Analyze the camera's low-resolution **sub stream** for motion and detection, and grab the snapshot from the high-resolution **main stream** so alerts stay sharp. This keeps CPU cost per camera low.
- Pace network sources by their real frame rate.

*Acceptance: a 24-hour soak test against a real camera, including camera reboots and network interruptions, recovers automatically and drops no events.*

### Phase 2 - Camera abstraction and multi-camera support (planned)

Run N cameras with one Beena installation.

- A `CameraSource` interface with three implementations: USB webcam, video file, RTSP source - so today's paths become special cases of one abstraction.
- One worker process per camera, so a slow or failed camera cannot stall the others.
- A camera registry (YAML at first, a database later) holding each camera's id, friendly name, source, credentials, enabled flag and thresholds.
- A stable `camera_id` in every event, per-camera snapshot subfolders, and per-camera handling in the Rust core.

*Acceptance: three cameras (one USB, two RTSP) produce correctly attributed Telegram alerts concurrently on one host.*

### Phase 3 - ONVIF discovery and setup wizard (planned)

Make onboarding work for non-experts.

- Discover cameras on the local network via WS-Discovery (ONVIF), read device information, list media profiles, and request the stream URI automatically.
- Test the discovered stream with a live probe before saving it.
- Provide a manual path for RTSP-only cameras (vendor-specific URL patterns plus a free-text field), since not every camera implements ONVIF.
- Ship the wizard first as a CLI/TUI flow, later as the first screen of the web dashboard.

*Acceptance: a user who only knows the Wi-Fi password connects a camera in under five minutes.*

### Phase 4 - Packaging and hardware acceleration (planned)

Turn "clone and run four terminals" into "one command".

- Dockerfiles for all four services and a `docker-compose.yml` with one shared volume, mirroring the current architecture exactly.
- A non-Docker path with systemd units.
- Configurable ONNX Runtime execution providers (CPU, OpenVINO, CUDA, CoreML) so the same model benefits from whatever hardware the host offers.
- Documented target hosts: Raspberry Pi 4/5, Intel N100-class mini PCs, NAS containers.

*Acceptance: `docker compose up` on a clean machine yields a working system; the quick start shrinks to three commands.*

### Phase 5 - Product layer: storage, dashboard, notifications (planned)

Grow the pipeline into a small self-hosted product.

- An event database (SQLite) with a retention policy; searchable history.
- Short video clips around events (pre-roll and post-roll) recorded from the live stream, not only single frames.
- A web dashboard: live views via HLS/WebRTC (through a relay such as go2rtc or MediaMTX), an event timeline with AI titles and severity filters, and settings screens that replace `.env` editing.
- Multi-user Telegram: receiver management through bot commands, per-user severity filters, plus a generic webhook channel.
- Token authentication on the core API and the dashboard before anything is exposed beyond localhost.

*Acceptance: a user reviews the last night's events in a browser and adds a second Telegram receiver without editing a config file.*

### Camera compatibility expectations

| Camera type | Examples | Expected support |
|---|---|---|
| ONVIF + RTSP (wired/PoE) | Hikvision, Dahua, Axis, Reolink, wired Tapo | Best case: automatic discovery and onboarding (Phase 3) |
| RTSP only | Wyze with RTSP firmware, many generic cameras | Supported with a manually entered URL |
| USB webcam / video file | any UVC webcam, test footage | Supported today (v1.0) |
| Cloud-locked or battery-powered | most battery and doorbell cameras | Not a target; these expose no local stream |

### Non-goals

- Installing software on camera firmware. Cameras run signed embedded operating systems and are not application platforms; Beena runs beside them, on a host.
- Vendor cloud integrations. Beena's design keeps everything on the local network except the single event snapshot sent to your configured analysis endpoint.

---

## Contributing

Issues and pull requests are welcome. If you test Beena against a specific camera model or vendor, sharing the stream URL pattern and the ONVIF behavior you observed directly improves Phase 1 and Phase 3.
