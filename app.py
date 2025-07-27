import streamlit as st
import os
import yt_dlp
from pydub import AudioSegment
import openai

# Δημιουργία client OpenAI (σύμφωνα με νέο API)
client = openai.OpenAI(api_key=st.secrets["openai_api_key"])

# Τίτλος εφαρμογής
st.title("🎬 Video Analyzer AI")
st.write("Επικόλλησε ένα URL από Instagram, TikTok ή YouTube για ανάλυση του περιεχομένου.")

# Εισαγωγή URL από χρήστη
url = st.text_input("📎 Link του βίντεο:")

if url:
    try:
        with st.spinner("📥 Κατεβάζουμε το βίντεο..."):
            video_filename = "video.mp4"
            ydl_opts = {
                'format': 'mp4',
                'outtmpl': video_filename,
                'quiet': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        with st.spinner("🎧 Εξαγωγή ήχου..."):
            audio = AudioSegment.from_file(video_filename)
            audio.export("audio.wav", format="wav")

        with st.spinner("🧠 Ανάλυση μέσω OpenAI Whisper..."):
            with open("audio.wav", "rb") as f:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f
                )

            st.subheader("📋 Κείμενο από το βίντεο:")
            st.write(transcript.text)

        # Καθάρισμα προσωρινών αρχείων
        os.remove("video.mp4")
        os.remove("audio.wav")

    except Exception as e:
        st.error(f"⚠️ Κάτι πήγε στραβά:\n\n{e}")
