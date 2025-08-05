import streamlit as st
from pytube import YouTube
import os
from pydub import AudioSegment
import requests
from fpdf import FPDF
from googletrans import Translator
from dotenv import load_dotenv
import time

load_dotenv()

ASSEMBLYAI_API_KEY = st.secrets["ASSEMBLYAI_API_KEY"]

st.set_page_config(page_title="Video Insights App")
st.title("🎥 Video Insights Analyzer")

# Initialize favorites
if "favorites" not in st.session_state:
    st.session_state.favorites = []

# Language selection
lang_map = {
    "English": "en",
    "Greek": "el",
    "French": "fr",
    "Spanish": "es",
    "German": "de",
    "Hindi": "hi",
    "Chinese": "zh",
    "Russian": "ru",
    "Dutch": "nl",
    "Arabic": "ar"
}
selected_language = st.selectbox("🌍 Translation Language", options=list(lang_map.keys()))
target_lang = lang_map[selected_language]

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
        # Upload audio to AssemblyAI
        headers_upload = {
            "authorization": ASSEMBLYAI_API_KEY,
            "content-type": "application/octet-stream"
        }

        with open("audio.mp3", "rb") as f:
            audio_data = f.read()

        upload_response = requests.post(
            "https://api.assemblyai.com/v2/upload",
            headers=headers_upload,
            data=audio_data
        )

        if upload_response.status_code != 200:
            st.error(f"Upload failed: {upload_response.text}")
            return ""

        upload_url = upload_response.json()["upload_url"]

        # Request transcription
        headers_transcript = {
            "authorization": ASSEMBLYAI_API_KEY,
            "content-type": "application/json"
        }

        json_data = {
            "audio_url": upload_url,
            "language_code": language_code
        }

        transcript_response = requests.post(
            "https://api.assemblyai.com/v2/transcript",
            json=json_data,
            headers=headers_transcript
        )

        if transcript_response.status_code != 200:
            st.error(f"Transcription request failed: {transcript_response.text}")
            return ""

        transcript_id = transcript_response.json()["id"]

        # Poll for completion
        status = "queued"
        while status not in ("completed", "error"):
            poll_response = requests.get(
                f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                headers={"authorization": ASSEMBLYAI_API_KEY}
            )
            result = poll_response.json()
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
        st.download_button("⬇️ Download PDF", f, file_name="analysis.pdf", mime="application/pdf")

url = st.text_input("📥 Paste YouTube URL here")
if st.button("Analyze Video") and url:
    try:
        with st.spinner("📥 Downloading video..."):
            download_video(url)

        with st.spinner("🎧 Extracting audio..."):
            if not extract_audio():
                st.stop()

        with st.spinner("📝 Transcribing audio..."):
            transcript = transcribe_audio(language_code="en")  # default to English
            if not transcript:
                st.warning("No transcript found.")
                st.stop()

        st.subheader("🧾 Video Transcript")
        st.write(transcript)

        summary = summarize_text(transcript)
        st.subheader("📌 Summary")
        st.write(summary)

        translation = translate_text(transcript, dest_lang=target_lang)
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

# Display Favorites
if st.session_state.favorites:
    st.subheader("📌 Favorites")
    for fav in st.session_state.favorites:
        st.markdown(f"🔗 {fav['url']}")
        st.markdown(f"📌 {fav['summary']}")
        st.markdown(f"🌐 {fav['translation']}")
        st.markdown("---")
