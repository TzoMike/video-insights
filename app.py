import streamlit as st
import subprocess
import os
import requests
import time
from fpdf import FPDF

# === AssemblyAI API key ===
ASSEMBLYAI_API_KEY = st.secrets["ASSEMBLYAI_API_KEY"]

# === UI ===
st.title("🎥 Video Analyzer")
video_url = st.text_input("📎 Επικόλλησε το URL του βίντεο (YouTube, TikTok, Instagram):")

if st.button("Ανάλυση"):
    if not video_url:
        st.error("⚠️ Δώσε URL πρώτα.")
    else:
        with st.spinner("📥 Κατέβασμα βίντεο..."):
            subprocess.run(["yt-dlp", "-o", "video.mp4", video_url])

        with st.spinner("🎧 Εξαγωγή ήχου..."):
            subprocess.run(["ffmpeg", "-y", "-i", "video.mp4", "-vn", "-acodec", "mp3", "audio.mp3"])

        with st.spinner("🧠 Μετατροπή σε κείμενο..."):

            # 1. Upload audio
            headers = {'authorization': ASSEMBLYAI_API_KEY}
            upload_res = requests.post(
                'https://api.assemblyai.com/v2/upload',
                headers=headers,
                files={'file': open("audio.mp3", 'rb')}
            )
            audio_url = upload_res.json()['upload_url']

            # 2. Start transcription
            json_data = {'audio_url': audio_url}
            transcribe_res = requests.post(
                'https://api.assemblyai.com/v2/transcript',
                headers=headers,
                json=json_data
            )
            transcript_id = transcribe_res.json()['id']

            # 3. Poll for completion
            status = 'queued'
            while status not in ['completed', 'error']:
                poll_res = requests.get(
                    f'https://api.assemblyai.com/v2/transcript/{transcript_id}',
                    headers=headers
                )
                status = poll_res.json()['status']
                time.sleep(3)

            if status == 'completed':
                transcript_text = poll_res.json()['text']
                st.success("📝 Κείμενο εξήχθη!")
                st.text_area("🧾 Κείμενο", transcript_text, height=300)

                # === Περίληψη ===
                if st.button("🧠 Περίληψη"):
                    summary = transcript_text[:400] + "..."  # Προσωρινή περίληψη
                    st.write("✍️ **Περίληψη:**", summary)

                # === Μετάφραση ===
                if st.button("🌍 Μετάφραση στα Ελληνικά"):
                    try:
                        translate_url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=el&dt=t&q=" + transcript_text[:4000]
                        result = requests.get(translate_url).json()
                        translated = ''.join([part[0] for part in result[0]])
                        st.write("🇬🇷 **Μετάφραση:**", translated)
                    except:
                        st.error("⚠️ Αποτυχία μετάφρασης.")

                # === Λήψη PDF ===
                if st.button("📄 Λήψη PDF"):
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", size=12)
                    pdf.multi_cell(0, 10, transcript_text)
                    pdf.output("analysis.pdf")
                    with open("analysis.pdf", "rb") as file:
                        st.download_button("📥 Κατέβασε το PDF", file, "analysis.pdf")

            else:
                st.error("❌ Απέτυχε η μεταγραφή.")

