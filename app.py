import streamlit as st
from pytube import YouTube
from pydub import AudioSegment
from fpdf import FPDF
from googletrans import Translator
from dotenv import load_dotenv
import openai
import os
import logging
from mimetypes import guess_type

# Setup
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
load_dotenv()
openai.api_key = st.secrets["OPENAI_API_KEY"]

st.set_page_config(page_title="Video Insights App")
st.title("🎥 Video Insights Analyzer")

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

translate_lang = st.selectbox("🌍 Target language for translation", list(TRANSLATION_LANGUAGES.keys()))
translate_lang_code = TRANSLATION_LANGUAGES[translate_lang]

def download_video(url):
    yt = YouTube(url)
    stream = yt.streams.filter(file_extension='mp4').get_highest_resolution()
    stream.download(filename="video.mp4")

def extract_audio():
    try:
        audio = AudioSegment.from_file("video.mp4")
        audio.export("audio.mp3", format="mp3")
        if os.path.getsize("audio.mp3") == 0:
            st.error("Audio file is empty after extraction.")
            return False
        mime_type, _ = guess_type("audio.mp3")
        if not mime_type or not mime_type.startswith("audio"):
            st.error("Extracted file is not valid audio.")
            return False
        return True
    except Exception as e:
        logger.exception("Audio extraction failed")
        st.error(f"Audio extraction error: {e}")
        return False

def transcribe_audio_whisper():
    try:
        with open("audio.mp3", "rb") as f:
            transcript = openai.Audio.transcribe("whisper-1", f)
        return transcript["text"]
    except Exception as e:
        logger.exception("Transcription failed")
        st.error(f"Transcription error: {e}")
        return ""

def summarize_text(text):
    return text[:300] + "..." if len(text) > 300 else text

def translate_text(text, dest_lang='el'):
    translator = Translator()
    return translator.translate(text, dest=dest_lang).text

def create_pdf(transcript, summary, translation):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, "📄 Video Report\n", align='L')
    pdf.multi_cell(0, 10, f"🧾 Transcript:\n{transcript}\n", align='L')
    pdf.multi_cell(0, 10, f"📌 Summary:\n{summary}\n", align='L')
    pdf.multi_cell(0, 10, f"🌐 Translation:\n{translation}\n", align='L')
    pdf.output("analysis.pdf")
    with open("analysis.pdf", "rb") as f:
        st.download_button("⬇️ Download PDF Report", f, file_name="analysis.pdf", mime="application/pdf")

url = st.text_input("📥 Paste a YouTube URL")
if st.button("Analyze Video") and url:
    try:
        with st.spinner("📥 Downloading video..."):
            download_video(url)

        with st.spinner("🎧 Extracting audio..."):
            if not extract_audio():
                st.stop()

        with st.spinner("📝 Transcribing with Whisper..."):
            transcript = transcribe_audio_whisper()
            if not transcript:
                st.warning("No transcription returned.")
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
        logger.exception("Processing error")
        st.error(f"Error: {e}")

if st.session_state.favorites:
    st.subheader("📌 Favorites")
    for fav in st.session_state.favorites:
        st.markdown(f"🔗 {fav['url']}")
        st.markdown(f"📌 {fav['summary']}")
        st.markdown(f"🌐 {fav['translation']}")
        st.markdown("---")
