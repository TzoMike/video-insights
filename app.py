import streamlit as st
from pytube import YouTube
import os
from pydub import AudioSegment
import openai
from fpdf import FPDF
from googletrans import Translator
from dotenv import load_dotenv
from mimetypes import guess_type
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv()
openai.api_key = st.secrets["OPENAI_API_KEY"]

st.set_page_config(page_title="Video Insights App")
st.title("🎥 Video Insights Analyzer")

# Session state
if "favorites" not in st.session_state:
    st.session_state.favorites = []

TRANSLATION_LANGUAGES = {
    "Greek": "el",
    "English": "en",
    "French": "fr",
    "Spanish": "es",
    "German": "de",
    "Hindi": "hi",
    "Chinese": "zh-cn",
    "Russian": "ru",
    "Dutch": "nl",
    "Arabic": "ar"
}

translate_lang = st.selectbox("🌍 Target translation language", list(TRANSLATION_LANGUAGES.keys()))
translate_lang_code = TRANSLATION_LANGUAGES[translate_lang]

# File paths for temp usage
VIDEO_PATH = "/tmp/video.mp4"
AUDIO_PATH = "/tmp/audio.mp3"

def download_video(url):
    yt = YouTube(url)
    stream = yt.streams.filter(file_extension='mp4').get_highest_resolution()
    stream.download(filename=VIDEO_PATH)

def extract_audio():
    try:
        audio = AudioSegment.from_file(VIDEO_PATH)
        audio.export(AUDIO_PATH, format="mp3", codec="libmp3lame")

        if os.path.getsize(AUDIO_PATH) == 0:
            st.error("Extracted audio file is empty.")
            return False

        mime_type, _ = guess_type(AUDIO_PATH)
        if not mime_type or not mime_type.startswith("audio"):
            st.error("File is not recognized as audio.")
            return False

        if os.path.getsize(AUDIO_PATH) > 25 * 1024 * 1024:
            st.error("Audio file exceeds OpenAI size limit (25MB).")
            return False

        return True
    except Exception as e:
        logger.exception("Audio extraction failed")
        st.error(f"Audio extraction error: {e}")
        return False

def transcribe_audio_openai():
    try:
        with open(AUDIO_PATH, "rb") as audio_file:
            transcript = openai.Audio.transcribe("whisper-1", audio_file)
            return transcript["text"]
    except openai.error.OpenAIError as e:
        logger.exception("OpenAI API error")
        st.error(f"OpenAI error: {e}")
        return ""
    except Exception as e:
        logger.exception("Unexpected transcription error")
        st.error(f"Unexpected transcription error: {e}")
        return ""

def summarize_text(text):
    return text[:300] + "..." if len(text) > 300 else text

def translate_text(text, dest_lang='el'):
    translator = Translator()
    try:
        return translator.translate(text, dest=dest_lang).text
    except Exception as e:
        logger.exception("Translation failed")
        st.error(f"Translation error: {e}")
        return ""

def create_pdf(transcript, summary, translation):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, "📄 Video Report\n", align='L')
    pdf.multi_cell(0, 10, f"🧾 Transcript:\n{transcript}\n", align='L')
    pdf.multi_cell(0, 10, f"📌 Summary:\n{summary}\n", align='L')
    pdf.multi_cell(0, 10, f"🌐 Translation:\n{translation}\n", align='L')
    pdf.output("/tmp/analysis.pdf")
    with open("/tmp/analysis.pdf", "rb") as f:
        st.download_button("⬇️ Download PDF Report", f, file_name="analysis.pdf", mime="application/pdf")

# User input
url = st.text_input("📥 Paste a YouTube URL")

if st.button("Analyze Video") and url:
    try:
        with st.spinner("📥 Downloading video..."):
            download_video(url)

        with st.spinner("🎧 Extracting audio..."):
            if not extract_audio():
                st.stop()

        with st.spinner("📝 Transcribing using OpenAI Whisper..."):
            transcript = transcribe_audio_openai()
            if not transcript:
                st.warning("Transcription returned empty.")
                st.stop()

        st.subheader("🧾 Transcript")
        st.write(transcript)

        summary = summarize_text(transcript)
        st.subheader("📌 Summary")
        st.write(summary)

        translation = translate_text(transcript, dest_lang=translate_lang_code)
        st.subheader("🌐 Translation")
        st.write(translation)

        create_pdf(transcript, summary, translation)

        if st.button("⭐ Save to Favorites"):
            st.session_state.favorites.append({
                "url": url,
                "summary": summary,
                "translation": translation
            })
            st.success("Saved to favorites!")

    except Exception as e:
        logger.exception("Unexpected app error")
        st.error(f"Error: {e}")

if st.session_state.favorites:
    st.subheader("📌 Favorites")
    for fav in st.session_state.favorites:
        st.markdown(f"🔗 {fav['url']}")
        st.markdown(f"📌 {fav['summary']}")
        st.markdown(f"🌐 {fav['translation']}")
        st.markdown("---")
