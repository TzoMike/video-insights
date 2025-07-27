import streamlit as st
import openai
import yt_dlp
import os
from pydub import AudioSegment

# 🔐 OpenAI API Key
openai.api_key = st.secrets["openai_api_key"]

# 🌟 Εμφάνιση τίτλου
st.title("🎬 Video Analyzer AI")
st.write("Δώσε link από YouTube, TikTok, Instagram και θα σου κάνουμε ανάλυση του περιεχομένου.")

# 📥 URL input
url = st.text_input("📎 Επικόλλησε το link του βίντεο:")

if url:
    try:
        with st.spinner("📥 Κατέβασμα βίντεο..."):
            video_filename = "video.mp4"

            # Ρυθμίσεις yt-dlp
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

        with st.spinner("🧠 Ανάλυση περιεχομένου..."):
            with open("audio.wav", "rb") as f:
                transcript = openai.Audio.transcribe("whisper-1", f)

            st.subheader("📋 Κείμενο από το βίντεο:")
            st.write(transcript["text"])

        # 🧹 Καθάρισμα προσωρινών αρχείων
        os.remove("video.mp4")
        os.remove("audio.wav")

    except Exception as e:
        st.error(f"⚠️ Κάτι πήγε στραβά: {e}")

