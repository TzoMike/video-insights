import streamlit as st
import openai
import os
import subprocess
from yt_dlp import YoutubeDL
from dotenv import load_dotenv
from googletrans import Translator

load_dotenv()
openai.api_key = st.secrets["openai_api_key"]

st.set_page_config(page_title="Video Insight AI", layout="wide")
st.title("🎬 Video Insight AI")
st.markdown("Ανάλυσε και κατάλαβε βίντεο από YouTube, Instagram, TikTok, κ.ά.")

# === 1. Εισαγωγή URL ===
video_url = st.text_input("📎 Επικόλλησε το URL του βίντεο")

# === 2. Κατέβασμα βίντεο ===
def download_video(url, output_path="video.mp4"):
    ydl_opts = {
        'outtmpl': output_path,
        'format': 'bestvideo+bestaudio/best',
        'quiet': True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

# === 3. Εξαγωγή ήχου με ffmpeg ===
def extract_audio(video_path, audio_path):
    try:
        command = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "44100",
            "-ac", "2",
            audio_path
        ]
        subprocess.run(command, check=True)
        return True
    except Exception as e:
        st.error(f"❌ Σφάλμα εξαγωγής ήχου: {e}")
        return False

# === 4. Μετατροπή ήχου σε κείμενο ===
def transcribe_audio(audio_path):
    with open(audio_path, "rb") as audio_file:
        transcript = openai.Audio.transcribe("whisper-1", audio_file)
        return transcript["text"]

# === 5. Περίληψη ===
def summarize_text(text):
    prompt = f"Σύνοψισε το παρακάτω κείμενο στα ελληνικά:\n\n{text}"
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

# === 6. Μετάφραση ===
def translate_text(text, dest_lang="el"):
    translator = Translator()
    translated = translator.translate(text, dest=dest_lang)
    return translated.text

# === Λογική Εκτέλεσης ===
if video_url:
    with st.spinner("⬇️ Κατέβασμα βίντεο..."):
        try:
            download_video(video_url)
            st.success("✅ Το βίντεο κατέβηκε με επιτυχία.")
        except Exception as e:
            st.error(f"❌ Σφάλμα στο κατέβασμα: {e}")
            st.stop()

    with st.spinner("🔊 Εξαγωγή ήχου..."):
        if not extract_audio("video.mp4", "audio.wav"):
            st.stop()
        else:
            st.success("✅ Ο ήχος εξήχθη με επιτυχία.")

    with st.spinner("🧠 Μετατροπή ήχου σε κείμενο..."):
        try:
            transcript_text = transcribe_audio("audio.wav")
            st.text_area("📜 Κείμενο από το βίντεο:", transcript_text, height=300)
        except Exception as e:
            st.error(f"❌ Σφάλμα μετατροπής σε κείμενο: {e}")
            st.stop()

    # === Περίληψη ===
    if st.button("📚 Δημιούργησε Περίληψη"):
        with st.spinner("✍️ Δημιουργία περίληψης..."):
            summary = summarize_text(transcript_text)
            st.success("Περίληψη:")
            st.write(summary)

    # === Μετάφραση ===
    if st.button("🌍 Μετάφρασε στα Ελληνικά"):
        with st.spinner("🔁 Μετάφραση..."):
            translation = translate_text(transcript_text, dest_lang="el")
            st.success("Μετάφραση:")
            st.write(translation)
