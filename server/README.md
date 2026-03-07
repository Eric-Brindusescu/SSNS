# Speech & Render Server

FastAPI server providing a Romanian speech-to-text API (using `upb-nlp/ro-wav2vec2`), a Jinja2 template rendering API, and a web interface for both.

## Features

- **Speech-to-Text API** — Upload audio files (WAV, MP3, FLAC, OGG, etc.) and get Romanian transcription using wav2vec2 with LM-boosted CTC decoding
- **Template Rendering API** — Submit text with Jinja2 `{{ variable }}` syntax and a dictionary of values, receive a rendered HTML page
- **Web UI** — Drag-and-drop audio upload, dynamic key-value editor for template variables, live HTML preview

## Project Structure

```
server/
├── main.py                     # Application entry point
├── requirements.txt            # Python dependencies
├── app/
│   ├── config.py               # Settings (model name, limits, CORS)
│   ├── dependencies.py         # wav2vec2 model singleton
│   ├── routers/
│   │   ├── speech.py           # POST /api/speech-to-text
│   │   ├── render.py           # POST /api/render-html
│   │   └── web.py              # GET / (web UI)
│   ├── services/
│   │   ├── speech_service.py   # Audio processing & inference
│   │   └── render_service.py   # Sandboxed Jinja2 rendering
│   ├── schemas/                # Pydantic request/response models
│   └── templates/              # Jinja2 HTML templates
└── static/                     # CSS and JavaScript
```

## Requirements

- Python 3.10+
- ~2 GB RAM (for the wav2vec2 model)
- ~1.5 GB disk (model downloaded on first run)

## Setup

```bash
cd server

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# (Optional) For better transcription accuracy, install LM dependencies.
# Note: kenlm does NOT compile on Python 3.12+. Use Python 3.10 or 3.11 for LM support.
# On Python 3.12+, the server falls back to plain CTC decoding automatically.
pip install pyctcdecode kenlm
```

### Downloading the Speech Model

The server uses the [upb-nlp/ro-wav2vec2](https://huggingface.co/upb-nlp/ro-wav2vec2) model from Hugging Face. By default, the model is **downloaded automatically** on first server startup and cached at `~/.cache/huggingface/`.

The download includes:
- Model weights (`model.safetensors`) — ~1.26 GB
- Language model (`language_model/lm.bin`) — ~284 MB
- Tokenizer and config files — ~1 MB

**Total: ~1.55 GB** (one-time download, subsequent starts load from cache).

To pre-download the model before starting the server:

```bash
python -c "
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
Wav2Vec2ForCTC.from_pretrained('upb-nlp/ro-wav2vec2')
Wav2Vec2Processor.from_pretrained('upb-nlp/ro-wav2vec2')
print('Model downloaded successfully')
"
```

To use a different model, set the `APP_MODEL_NAME` environment variable:

```bash
export APP_MODEL_NAME=upb-nlp/ro-wav2vec2   # default
```

### Environment Variables (optional)

| Variable | Default | Description |
|---|---|---|
| `APP_MODEL_NAME` | `upb-nlp/ro-wav2vec2` | Hugging Face model ID |
| `APP_DEVICE` | `cpu` | Inference device (`cpu` or `cuda`) |
| `APP_MAX_AUDIO_DURATION_SECONDS` | `120` | Max audio length in seconds |
| `APP_MAX_AUDIO_FILE_SIZE_MB` | `50` | Max upload size in MB |
| `APP_CORS_ORIGINS` | `["*"]` | Allowed CORS origins |

You can also create a `.env` file in the `server/` directory with these values.

## Running the Server

```bash
python main.py
```

The server starts on `http://0.0.0.0:8000`. On first run, the wav2vec2 model is downloaded from Hugging Face (~1.5 GB) and cached locally.

- **Web UI**: http://localhost:8000/
- **API Docs (Swagger)**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Usage

### Speech-to-Text

```bash
curl -X POST http://localhost:8000/api/speech-to-text \
  -F "file=@recording.wav"
```

**Response:**

```json
{
  "text": "bună ziua cum vă numiți",
  "duration_seconds": 3.21,
  "language": "ro"
}
```

Supported formats: WAV, MP3, FLAC, OGG, Opus, WebM, M4A.

### Render HTML (JSON response)

```bash
curl -X POST http://localhost:8000/api/render-html \
  -H "Content-Type: application/json" \
  -d '{
    "text": "<h1>Salut, {{ name }}!</h1><p>Ai {{ count }} mesaje noi.</p>",
    "variables": {"name": "Maria", "count": "5"}
  }'
```

**Response:**

```json
{
  "html": "<!DOCTYPE html>..."
}
```

### Render HTML (direct preview)

```bash
curl -X POST http://localhost:8000/api/render-html/preview \
  -H "Content-Type: application/json" \
  -d '{
    "text": "<h1>Hello, {{ name }}!</h1>",
    "variables": {"name": "World"}
  }'
```

Returns the rendered HTML page directly (suitable for browser display or iframe embedding).

## Architecture

- **Routers** handle HTTP concerns (validation, status codes, file uploads)
- **Services** contain business logic (audio processing, template rendering)
- **Schemas** define request/response contracts with Pydantic
- **Dependencies** manage the ML model lifecycle (loaded once at startup)
- **Templates** use Jinja2 sandboxed environment to prevent injection attacks

The speech-to-text pipeline: load audio → convert to mono → resample to 16kHz → wav2vec2 inference → CTC decode (with optional LM boosting).
