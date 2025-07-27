import streamlit as st
import subprocess
import os
from pydub import AudioSegment
import openai
from fpdf import FPDF

# 🔐 OpenAI API key
openai.api_key = st.secrets["openai_api_key"]

st.title("📽️ Instagram Reel AI Ανάλυση")
st.write("Επικόλλησε ένα link από Instagram Reel για ανάλυση και μετάφραση!")

video_url = st.text_input("🔗 Εισάγετε Instagram Video Link")

if st.button("Ανάλυσε"):
    if video_url:
        st.info("📥 Λήψη ήχου...")
        subprocess.run(["yt-dlp", "-f", "bestaudio", "-o", "video.mp4", video_url])
        audio = AudioSegment.from_file("video.mp4")
        audio.export("audio.wav", format="wav")

        st.info("🔊 Μετατροπή σε κείμενο...")
        with open("audio.wav", "rb") as file:
            transcript = openai.Audio.transcribe("whisper-1", file)

        st.subheader("📜 Transcript:")
        st.write(transcript["text"])

        st.info("📚 GPT Ανάλυση...")
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Εξήγησε και μετάφρασε το περιεχόμενο του βίντεο στα ελληνικά."},
                {"role": "user", "content": transcript["text"]}
            ]
        )

        analysis = response.choices[0].message.content
        st.subheader("🧠 Ανάλυση:")
        st.write(analysis)

        if st.button("📄 Κατέβασέ το σε PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.multi_cell(0, 10, analysis)
            pdf.output("analysis.pdf")
            with open("analysis.pdf", "rb") as f:
                st.download_button("⬇️ Κατέβασμα PDF", f, file_name="analysis.pdf")
