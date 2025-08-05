import streamlit as st
from pytube import YouTube
import os
from pydub import AudioSegment
import requests
import time
from fpdf import FPDF
from googletrans import Translator
from dotenv import load_dotenv

load_dotenv()

ASSEMBLYAI_API_KEY = st.secrets["ASSEMBLYAI_API_KEY"]

st.set_page_config(page_title="Video Insights App")
st.title("🎥 Video Insights Analyzer")

if "favorites" not in st.session_state:
    st.session_state.favorites = []

# Supported transcription languages by AssemblyAI
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

# All translation languages supported by Google Translate
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

# User selects transcription and translation languages
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
        return True
    except Exception as e:
        st.error(f"Audio extraction error: {e}")
        return False

def transcribe_audio(language_code="en"):
    try:
        headers = {"authorization": ASSEMBLYAI_API_KEY}
        with open("audio.mp3", "rb") as f:
            upload_response = requests.post(
                "https://api.assemblyai.com/v2/upload",
                headers=headers,
                files={"file": f}
            )

        if upload_response.status_code != 200:
            st.error(f"Upload failed: {upload_response.text}")
            return ""

        upload_url = upload_response.json()["upload_url"]

        json_payload = {"audio_url": upload_url, "language_code": language_code}
        transcript_response = requests.post(
            "https://api.assemblyai.com/v2/transcript",
            headers={"authorization": ASSEMBLYAI_API_KEY, "content-type": "application/json"},
            json=json_payload
        )

        if transcript_response.status_code != 200:
            st.error(f"Transcription request failed: {transcript_response.text}")
            return ""

        transcript_id = transcript_response.json()["id"]
        status = "queued"
        while status not in ["completed", "error"]:
            result = requests.get(
                f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                headers=headers
            ).json()
            status = result["status"]
            time.sleep(3)

        if status == "completed":
            return result["text"]
        else:
            st.error("Transcription failed.")
            return ""
    except Exception as e:
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
        st.error(f"Error: {e}")

if st.session_state.favorites:
    st.subheader("📌 Favorites")
    for fav in st.session_state.favorites:
        st.markdown(f"🔗 {fav['url']}")
        st.markdown(f"📌 {fav['summary']}")
        st.markdown(f"🌐 {fav['translation']}")
        st.markdown("---")
