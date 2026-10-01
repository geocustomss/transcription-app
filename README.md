# Local Transcription Studio
A local-first app for recording speech, transcribing audio or video, extracting text from a document, or entering text directly. Each input produces one automatically cleaned, editable transcript.

## What it does

- Records through the browser microphone.
- Accepts existing audio and video files containing an audio track.
- Extracts text locally from `.txt`, `.md`, `.docx`, and text-based `.pdf` documents.
- Accepts typed or pasted text without requiring speech recognition.
- Transcribes locally with `faster-whisper` and an int8 CPU model.
- Automatically corrects punctuation and grammar, removes fillers and immediate repetitions, and improves readability in one result.
- Keeps the original visible beside one editable cleaned transcript with `.txt` download.
- Does not save recordings or transcripts to the project or a database.

## Requirements

- Windows, Python 3.11, and a current browser.
- Internet access the first time a Whisper model is downloaded. Transcription runs locally after the download.
- Ollama running on this computer for automatic cleanup. Ollama is optional; input and transcription remain available without it, and the original remains editable if cleanup cannot connect.

## Build and run

Open PowerShell in this project folder (`projects/local-transcription-cleanup`) and create an isolated environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m streamlit run app.py --server.address 127.0.0.1
```

Open the `http://127.0.0.1:8501` URL printed by Streamlit. The app is bound to loopback so it is available on this computer only. If that port is occupied, start it on another port:

```powershell
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8765
```

The first transcription downloads the Whisper model configured by `WHISPER_MODEL` (default `small`) to the user-level Hugging Face cache, outside this project. If Ollama cleanup is wanted, make the configured model available locally:

```powershell
ollama pull qwen3-coder:30b
```

## Use the app

1. Choose **Type or paste**, **Record voice**, **Upload audio or video**, or **Upload text document**.
2. Enter text, record with the browser microphone, or choose a file. For a document, choose a `.txt`, `.md`, `.docx`, or text-based `.pdf` file.
3. Select **Create transcript** once. Audio/video is transcribed first; document and typed text go directly to cleanup. Cleanup applies punctuation and grammar fixes, removes fillers and immediate repetitions, and improves readability in one local Ollama request.
4. Review the unchanged original and the single editable cleaned result. Select **Download transcript** when ready.

The model can still alter or misunderstand text. The original remains visible so you can compare and restore wording before exporting.

## Supported media and limits

- Audio/video extensions: AAC, AVI, FLAC, M4A, MKV, MOV, MP3, MP4, OGG, WAV, WebM, and WMA. Actual codec support depends on the bundled PyAV/FFmpeg libraries.
- Maximum upload: 100 MB. Maximum recording: 30 minutes.
- Text documents: TXT, Markdown, DOCX, or text-based PDF; maximum 20 MB and 50,000 extracted characters.
- Scanned/image-only PDFs are not OCR-processed and must contain selectable text.
- Video is decoded for its audio track; video is not saved or displayed.
- Model: `faster-whisper` on CPU with int8 quantization. Smaller Whisper models generally download and run faster, with a quality tradeoff.

## Configure local models

Edit `.env` in this folder. `.env` is ignored by Git; `.env.example` documents the setting names without credentials.

| Setting | Default | Purpose |
| --- | --- | --- |
| `WHISPER_MODEL` | `small` | Whisper model name, downloaded on first use. |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Local Ollama server address. |
| `OLLAMA_MODEL_TEXT` | `qwen3-coder:30b` | Locally available Ollama model used for cleanup. |

No cloud transcription or cleanup provider is configured.

## How it is built

```text
Microphone / file -> validate -> PyAV decode + resample -> faster-whisper -> original transcript
Typed text ---------------------------------------------------------------> original transcript
Text document -> local extraction --+
Typed text ------------------------+-> original text -> local Ollama cleanup -> editable transcript -> TXT download
Audio/video -> local transcription-+
```

- `app.py` contains the Streamlit workflow, session state, and download controls.
- `src/transcriber.py` validates media, decodes audio/video audio with PyAV, and calls the local Whisper model.
- `src/document_reader.py` extracts selectable document text locally and enforces size limits.
- `src/cleanup.py` combines punctuation/grammar correction, filler removal, and readability cleanup into one result.
- `tests/` covers document extraction, media handling, cleanup, and the UI submit flow with mocked model/API boundaries.
- `.streamlit/config.toml` sets the local theme, upload limit, and disables Streamlit usage statistics.

To change the app, edit the relevant module, run the tests below, then rerun or refresh Streamlit. No build or bundling step is required.

## Tests

From this project folder, activate `.venv` and run:

```powershell
python -m unittest discover -s tests -v
```

The tests do not need a microphone, model download, or running Ollama server. Calls to those boundaries are mocked.

## Privacy and data handling

Speech recognition runs on this computer. Cleanup text is sent only to the configured Ollama server; the default is loopback. The app does not write uploaded media or transcripts to project files or a database. Streamlit session state and uploaded objects are held in memory while the app session is active; stop the app to end that session. The initial Whisper download uses Hugging Face and is cached outside the project. Usage statistics are disabled in the project Streamlit configuration.

## Troubleshooting

- **Microphone unavailable:** open the loopback URL in a current browser and grant microphone permission.
- **First transcription is slow or cannot load the model:** confirm internet access for the first download; retry after checking the model name. A smaller Whisper model can reduce download time and CPU use.
- **Cleanup is unavailable:** start Ollama, then check `OLLAMA_BASE_URL` and `OLLAMA_MODEL_TEXT` in `.env`. Submit the input again to retry; the original remains editable if Ollama stays offline.
- **Media is rejected:** check its extension, 100 MB size limit, 30-minute limit, and whether it contains audio. Codec support varies; WAV or MP4 is a useful compatibility check.
- **PDF text is missing:** only text-based PDFs are supported; image-only/scanned PDFs require OCR outside this app.
- **Port 8501 is already in use:** use the alternate `--server.port` command above.

## Creator attribution

See [CREATOR-STATEMENT.md](CREATOR-STATEMENT.md) for the project creator declaration template and ways to preserve attributable development history. Replace its identity placeholder with the name or GitHub handle you want to publish before making a release.