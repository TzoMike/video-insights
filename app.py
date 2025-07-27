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

# Initialize favorites
if "favorites" not in st.session_state:
    st.session_state.favorites = []

# Γλώσσες μετάφρασης & μεταγραφής
lang_map = {
    "Ελληνικά": ("el", "el"),
    "Αγγλικά": ("en", "en"),
    "Γαλλικά": ("fr", "fr"),
    "Ισπανικά": ("es", "es"),
    "Γερμανικά": ("de", "de"),
    "Ινδικά": ("hi", "hi"),
    "Κινεζικά": ("zh-cn", "zh"),
    "Ρωσικά": ("ru", "ru"),
    "Ολλανδικά": ("nl", "nl"),
    "Αραβικά": ("ar", "ar"),
}

selected_language = st.selectbox("🌍 Επιλογή Γλώσσας Μετάφρασης & Αναγνώρισης", list(lang_map.keys()))
target_lang, transcript_lang = lang_map[selected_language]

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
        st.error(f"Σφάλμα εξαγωγής ήχου: {e}")
        return False

def transcribe_audio(language_code="en"):
    try:
        # Upload audio
        headers = {
            "authorization": ASSEMBLYAI_API_KEY,
            "content-type": "application/octet-stream"
        }

        with open("audio.mp3", "rb") as f:
            audio_data = f.read()

        upload_response = requests.post(
            "https://api.assemblyai.com/v2/upload",
            headers=headers,
            data=audio_data
        )

        if upload_response.status_code != 200:
            st.error(f"Σφάλμα ανέβασματος ήχου: {upload_response.text}")
            return ""

        upload_url = upload_response.json()["upload_url"]

        # Create transcript request
        json_data = {
            "audio_url": upload_url,
            "language_code": language_code
        }

        transcript_response = requests.post(
            "https://api.assemblyai.com/v2/transcript",
            json=json_data,
            headers={"authorization": ASSEMBLYAI_API_KEY}
        )

        if transcript_response.status_code != 200:
            st.error(f"Σφάλμα αιτήματος μεταγραφής: {transcript_response.text}")
            return ""

        transcript_id = transcript_response.json()["id"]

        # Poll for result
        status = "queued"
        while status not in ("completed", "error"):
            polling_response = requests.get(
                f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                headers={"authorization": ASSEMBLYAI_API_KEY}
            )
            polling_data = polling_response.json()
            status = polling_data["status"]
            time.sleep(3)

        if status == "completed":
            return polling_data["text"]
        else:
            st.error("Η μεταγραφή απέτυχε.")
            return ""

    except Exception as e:
        st.error(f"Σφάλμα μετατροπής ήχου σε κείμενο: {e}")
        return ""

def summarize_text(text):
    return text[:300] + "..." if len(text) > 300 else text

def translate_text(text, dest_lang="el"):
    translator = Translator()
    try:
        translated = translator.translate(text, dest=dest_lang)
        return translated.text
    except Exception as e:
        st.error(f"Σφάλμα μετάφρασης: {e}")
        return ""

def create_pdf(transcript, summary, translation):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, "📄 Αναφορά Βίντεο\n", align='L')
    pdf.multi_cell(0, 10, f"🧾 Κείμενο:\n{transcript}\n", align='L')
    pdf.multi_cell(0, 10, f"📌 Περίληψη:\n{summary}\n", align='L')
    pdf.multi_cell(0, 10, f"🌐 Μετάφραση:\n{translation}\n", align='L')
    pdf.output("analysis.pdf")
    with open("analysis.pdf", "rb") as f:
        st.download_button("⬇️ Κατέβασε ως PDF", f, file_name="analysis.pdf", mime="application/pdf")

# Εισαγωγή URL
url = st.text_input("📥 Επικόλλησε URL από YouTube")
if st.button("Ανάλυση Βίντεο") and url:
    try:
        with st.spinner("📥 Κατεβάζω βίντεο..."):
            download_video(url)

        with st.spinner("🎧 Εξάγω ήχο..."):
            if not extract_audio():
                st.stop()

        with st.spinner("📝 Μετατροπή σε κείμενο..."):
            transcript = transcribe_audio(language_code=transcript_lang)
            if not transcript:
                st.warning("Δεν βρέθηκε κείμενο.")
                st.stop()

        st.subheader("🧾 Κείμενο Βίντεο")
        st.write(transcript)

        summary = summarize_text(transcript)
        st.subheader("📌 Περίληψη")
        st.write(summary)

        translation = translate_text(transcript, dest_lang=target_lang)
        st.subheader("🌐 Μετάφραση")
        st.write(translation)

        create_pdf(transcript, summary, translation)

        if st.button("⭐ Αποθήκευση στα Αγαπημένα"):
            st.session_state.favorites.append({
                "url": url,
                "summary": summary,
                "translation": translation
            })
            st.success("Αποθηκεύτηκε!")

    except Exception as e:
        st.error(f"Σφάλμα: {e}")

# Προβολή αγαπημένων
if st.session_state.favorites:
    st.subheader("📌 Αγαπημένα")
    for fav in st.session_state.favorites:
        st.markdown(f"🔗 {fav['url']}")
        st.markdown(f"📌 {fav['summary']}")
        st.markdown(f"🌐 {fav['translation']}")
        st.markdown("---")
