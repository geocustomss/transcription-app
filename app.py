import os

import streamlit as st
from dotenv import load_dotenv

from src.cleanup import CleanupError, cleanup_transcript
from src.document_reader import DocumentInputError, extract_document_text
from src.transcriber import MediaInputError, TranscriptionError, transcribe_media, validate_media

load_dotenv()

APP_TITLE = "Local Transcription Studio"
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL_TEXT", "qwen3-coder:30b")
MAX_TEXT_CHARACTERS = 50_000

st.set_page_config(page_title=APP_TITLE, page_icon="✳", layout="wide")
st.markdown(
    """
    <style>
    :root {
        --paper: #f3f5f0;
        --surface: #ffffff;
        --ink: #202b28;
        --muted: #66736e;
        --line: #d8dfd8;
        --green: #286b58;
        --green-dark: #1f5144;
        --coral: #bd654d;
        --wash: #e7eee8;
    }
    .stApp { background: var(--paper); color: var(--ink); }
    .block-container { max-width: 1080px; padding: 4rem 2rem 4rem; }
    [data-testid="stHeading"] h1, [data-testid="stHeading"] h2, [data-testid="stHeading"] h3 {
        color:var(--ink); font-family:Georgia,'Times New Roman',serif;
    }
    [data-testid="stHeading"] h1 { font-size:2.65rem; line-height:1.08; margin-bottom:.45rem; }
    p, label, [data-testid="stMarkdownContainer"] { color: var(--ink); }
    .lede { color:var(--muted); font-size:1rem; max-width:760px; margin-bottom:1.4rem; }
    .section-kicker {
        color:var(--green); font:600 .74rem 'Consolas','Courier New',monospace;
        letter-spacing:.08em; text-transform:uppercase; margin:0 0 .4rem;
    }
    .step-heading { margin:0 0 .25rem; font:700 1.45rem Georgia,'Times New Roman',serif; }
    .step-note { color:var(--muted); margin-bottom:1rem; }
    [data-testid="stFileUploader"] section,
    [data-testid="stAudioInput"] section {
        background:var(--surface); border:1px dashed #9bac9f; border-radius:5px;
    }
    [data-testid="stTextArea"] textarea {
        background:var(--surface); border:1px solid var(--line); border-radius:4px;
        color:var(--ink); line-height:1.55;
    }
    div.stButton > button[kind="primary"] {
        background:var(--green); border:1px solid var(--green); border-radius:4px;
        color:white; font-size:1rem; font-weight:700; min-height:3rem; padding:.65rem 1rem;
        box-shadow:0 2px 0 var(--green-dark);
    }
    div.stButton > button[kind="primary"]:hover {
        background:var(--green-dark); border-color:var(--green-dark); color:white;
    }
    div[data-testid="stDownloadButton"] button {
        background:var(--surface); border:1px solid var(--line); border-radius:4px;
    }
    [data-testid="stAlert"] { border-radius:4px; }
    hr { border-color:var(--line); }
    .privacy-note { color:var(--muted); font-size:.88rem; }
    @media (max-width: 700px) {
        .block-container { padding:2.5rem 1rem 2.5rem; }
        [data-testid="stHeading"] h1 { font-size:2rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def set_source(text: str, source_label: str, language: str | None = None, duration: float | None = None) -> None:
    st.session_state["source_text"] = text
    st.session_state["edited_text"] = text
    st.session_state["source_label"] = source_label
    st.session_state["language"] = language
    st.session_state["duration"] = duration
    st.session_state.pop("cleanup_error", None)
    st.session_state.pop("cleanup_model", None)


def generate_cleanup() -> None:
    try:
        with st.spinner(f"Cleaning transcript locally with {OLLAMA_MODEL}..."):
            cleaned = cleanup_transcript(
                st.session_state["source_text"],
                base_url=OLLAMA_BASE_URL,
                model=OLLAMA_MODEL,
            )
        st.session_state["edited_text"] = cleaned
        st.session_state["cleanup_model"] = OLLAMA_MODEL
        st.session_state.pop("cleanup_error", None)
    except (CleanupError, ValueError) as error:
        st.session_state["cleanup_error"] = str(error)


def process_media(filename: str, data: bytes, source_label: str) -> None:
    validate_media(filename, data)
    with st.spinner("Listening locally. Longer recordings can take a little while..."):
        result = transcribe_media(filename, data, model_name=WHISPER_MODEL)
    set_source(result.text, source_label, result.language, result.duration_seconds)


def process_document(filename: str, data: bytes) -> None:
    text = extract_document_text(filename, data)
    set_source(text, f"Document: {filename}")


st.title("Local Transcription Studio")
st.markdown(
    "<div class='lede'>Type, record, or upload a file. Your transcript is automatically cleaned for readability.</div>",
    unsafe_allow_html=True,
)

st.markdown("<div class='section-kicker'>01 / Add your words</div>", unsafe_allow_html=True)
input_mode = st.segmented_control(
    "Choose an input",
    ["Type or paste", "Record voice", "Upload audio or video", "Upload text document"],
    default="Type or paste",
    key="input_mode",
    label_visibility="collapsed",
    width="stretch",
    wrap=True,
)

recording = None
uploaded_media = None
uploaded_document = None
typed_text = ""
if input_mode == "Type or paste":
    st.markdown("<div class='step-note'>Enter or paste text to clean up.</div>", unsafe_allow_html=True)
    typed_text = st.text_area(
        "Transcript or notes",
        max_chars=MAX_TEXT_CHARACTERS,
        height=180,
        placeholder="Type or paste your words here...",
        key="typed_input",
    )
elif input_mode == "Record voice":
    st.markdown("<div class='step-note'>Use your microphone. Recording stays in this browser session.</div>", unsafe_allow_html=True)
    recording = st.audio_input("Start or stop recording", key="microphone_input")
elif input_mode == "Upload audio or video":
    st.markdown("<div class='step-note'>Audio files and videos with an audio track are supported; maximum 100 MB and 30 minutes.</div>", unsafe_allow_html=True)
    uploaded_media = st.file_uploader(
        "Choose an audio or video file",
        type=["aac", "avi", "flac", "m4a", "mkv", "mov", "mp3", "mp4", "ogg", "wav", "webm", "wma"],
        key="media_upload",
    )
elif input_mode == "Upload text document":
    st.markdown("<div class='step-note'>Upload a text, Markdown, Word, or text-based PDF document. Maximum 20 MB.</div>", unsafe_allow_html=True)
    uploaded_document = st.file_uploader(
        "Choose a text document",
        type=["txt", "md", "docx", "pdf"],
        key="document_upload",
    )
else:
    st.error("Choose one of the available input methods.")

if st.button("Create transcript", type="primary", icon=":material/auto_awesome:", width="stretch"):
    try:
        if input_mode == "Type or paste":
            if not typed_text.strip():
                st.error("Add some text first.")
            else:
                set_source(typed_text.strip(), "Typed text")
                generate_cleanup()
        elif input_mode == "Record voice":
            if recording is None:
                st.error("Record something first, then create the transcript.")
            else:
                process_media("microphone.wav", recording.getvalue(), "Microphone recording")
                generate_cleanup()
        elif input_mode == "Upload audio or video" and uploaded_media is not None:
            process_media(uploaded_media.name, uploaded_media.getvalue(), uploaded_media.name)
            generate_cleanup()
        elif input_mode == "Upload text document" and uploaded_document is not None:
            process_document(uploaded_document.name, uploaded_document.getvalue())
            generate_cleanup()
        else:
            st.error("Choose or record an input first.")
    except MediaInputError as error:
        st.error(str(error))
    except DocumentInputError as error:
        st.error(str(error))
    except TranscriptionError as error:
        st.error(str(error))

if st.session_state.get("source_text"):
    st.divider()
    if st.session_state.get("cleanup_error"):
        st.warning(st.session_state["cleanup_error"])
    st.markdown("<div class='section-kicker'>02 / Original</div>", unsafe_allow_html=True)
    details = [st.session_state.get("source_label", "Input")]
    if st.session_state.get("language"):
        details.append(f"Detected {st.session_state['language']}")
    if st.session_state.get("duration") is not None:
        details.append(f"{st.session_state['duration']:.0f} sec")
    st.caption(" · ".join(details))
    st.text_area(
        "Original text",
        value=st.session_state["source_text"],
        height=160,
        disabled=True,
        label_visibility="collapsed",
    )

    st.markdown("<div class='section-kicker'>03 / Cleaned transcript</div>", unsafe_allow_html=True)
    st.caption(
        f"Automatically cleaned locally with {st.session_state['cleanup_model']} · editable"
        if st.session_state.get("cleanup_model")
        else "Cleanup unavailable; original text is shown and remains editable."
    )
    st.text_area(
        "Cleaned transcript",
        max_chars=MAX_TEXT_CHARACTERS,
        height=300,
        key="edited_text",
    )
    st.download_button(
        "Download transcript",
        data=st.session_state["edited_text"],
        file_name="transcript.txt",
        mime="text/plain; charset=utf-8",
        icon=":material/download:",
    )
    st.markdown(
        "<p class='privacy-note'>Audio and text are held in this app session only. Speech recognition runs on this computer; cleanup uses Ollama on this computer.</p>",
        unsafe_allow_html=True,
    )
else:
    st.divider()
    st.markdown(
        "<p class='privacy-note'>Speech model: <b>" + WHISPER_MODEL + "</b> on CPU · Cleanup model: <b>" + OLLAMA_MODEL + "</b> via local Ollama</p>",
        unsafe_allow_html=True,
    )