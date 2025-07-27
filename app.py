import streamlit as st
from pytube import YouTube
import os
from pydub import AudioSegment
import requests
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

# Language selection
lang_map = {
    "Ελληνικά": "el",
    "Αγγλικά": "en",
    "Γαλλικά": "fr",
    "Ισπανικά": "es",
    "Γερμανικά": "de"
}
selected_language = st.selectbox("🌍 Γλώσσα Μετάφρασης", options=list(lang_map.keys()))
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
        st.error(f"Σφάλμα εξαγωγής ήχου: {e}")
        return False

def transcribe_audio():
    try:
        headers = {
            "authorization": ASSEMBLYAI_API_KEY
        }
        response = requests.post(
            "https://api.assemblyai.com/v2/upload",
            headers=headers,
            files={'file': open("audio.mp3", 'rb')}
        )
        upload_url = response.json()['upload_url']

        json = {"audio_url": upload_url}
        transcript_response = requests.post(
            "https://api.assemblyai.com/v2/transcript",
            json=json,
            headers=headers
        )
        transcript_id = transcript_response.json()['id']

        status = 'queued'
        while status not in ['completed', 'error']:
            polling = requests.get(
                f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                headers=headers
            ).json()
            status = polling['status']

        if status == 'completed':
            return polling['text']
        else:
            return ""
    except Exception as e:
        st.error(f"Σφάλμα μετατροπής ήχου σε κείμενο: {e}")
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
    pdf.multi_cell(0, 10, "📄 Αναφορά Βίντεο\n", align='L')
    pdf.multi_cell(0, 10, f"🧾 Κείμενο:\n{transcript}\n", align='L')
    pdf.multi_cell(0, 10, f"📌 Περίληψη:\n{summary}\n", align='L')
    pdf.multi_cell(0, 10, f"🌐 Μετάφραση:\n{translation}\n", align='L')
    pdf.output("analysis.pdf")
    with open("analysis.pdf", "rb") as f:
        st.download_button("⬇️ Κατέβασε ως PDF", f, file_name="analysis.pdf", mime="application/pdf")

url = st.text_input("📥 Επικόλλησε URL από YouTube")
if st.button("Ανάλυση Βίντεο") and url:
    try:
        with st.spinner("📥 Κατεβάζω βίντεο..."):
            download_video(url)

        with st.spinner("🎧 Εξάγω ήχο..."):
            if not extract_audio():
                st.stop()

        with st.spinner("📝 Μετατροπή σε κείμενο..."):
            transcript = transcribe_audio()
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

if st.session_state.favorites:
    st.subheader("📌 Αγαπημένα")
    for fav in st.session_state.favorites:
        st.markdown(f"🔗 {fav['url']}")
        st.markdown(f"📌 {fav['summary']}")
        st.markdown(f"🌐 {fav['translation']}")
        st.markdown("---")
