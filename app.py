import streamlit as st
from pytube import YouTube
import os
from pydub import AudioSegment
import requests
import time
from fpdf import FPDF
from googletrans import Translator
from dotenv import load_dotenv
from mimetypes import guess_type
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv()

ASSEMBLYAI_API_KEY = st.secrets["ASSEMBLYAI_API_KEY"]

st.set_page_config(page_title="Video Insights App")
st.title("🎥 Video Insights Analyzer")

if "favorites" not in st.session_state:
    st.session_state.favorites = []

SUPPORTED_ASSEMBLYAI_LANGUAGES = {
    "English": "en",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Portuguese": "pt",
    "Italian": "it",
    "Hindi": "hi",
    "Japanese": "ja",
    "Korean": "ko",
    "Chinese": "zh",
    "Russian": "ru",
    "Dutch": "nl",
    "Arabic": "ar"
}

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

transcribe_lang = st.selectbox("🗣️ Audio language for transcription", list(SUPPORTED_ASSEMBLYAI_LANGUAGES.keys()))
transcribe_lang_code = SUPPORTED_ASSEMBLYAI_LANGUAGES[transcribe_lang]

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
            st.error("Extracted file is not recognized as audio.")
            return False
        return True
    except Exception as e:
        logger.exception("Audio extraction failed")
        st.error(f"Audio extraction error: {e}")
        return False

def transcribe_audio(language_code="en"):
    try:
        headers = {"authorization": ASSEMBLYAI_API_KEY}

        with open("audio.mp3", "rb") as f:
            data = f.read()
            upload_response = requests.post(
                "https://api.assemblyai.com/v2/upload",
                headers=headers,
                data=data
            )

        logger.debug("Upload status code: %s", upload_response.status_code)
        try:
            logger.debug("Upload response: %s", upload_response.json())
        except:
            logger.warning("Upload response not in JSON format")

        if upload_response.status_code != 200:
            st.error(f"Upload failed: {upload_response.text}")
            return ""

        upload_url = upload_response.json().get("upload_url")
        if not upload_url:
            st.error("Upload URL not found in response.")
            return ""

        json_payload = {
            "audio_url": upload_url,
            "language_code": language_code,
            "auto_chapters": False
        }

        transcript_response = requests.post(
            "https://api.assemblyai.com/v2/transcript",
            headers={"authorization": ASSEMBLYAI_API_KEY, "content-type": "application/json"},
            json=json_payload
        )

        logger.debug("Transcription request status: %s", transcript_response.status_code)
        try:
            logger.debug("Transcript response: %s", transcript_response.json())
        except:
            logger.warning("Transcript response not in JSON format")

        if transcript_response.status_code != 200:
            st.error(f"Transcription request failed: {transcript_response.text}")
            return ""

        transcript_id = transcript_response.json()["id"]
        status = "queued"
        while status not in ["completed", "error"]:
            poll_response = requests.get(
                f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                headers=headers
            )
            result = poll_response.json()
            logger.debug("Polling result: %s", result)
            status = result.get("status", "error")
            time.sleep(3)

        if status == "completed":
            return result["text"]
        else:
            st.error("Transcription failed:")
            st.json(result)
            return ""
    except Exception as e:
        logger.exception("Transcription error")
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

        with st.spinner("📝 Transcribing audio..."):
            transcript = transcribe_audio(language_code=transcribe_lang_code)
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
