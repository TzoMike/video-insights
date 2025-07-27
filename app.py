import streamlit as st
import subprocess
from yt_dlp import YoutubeDL
from pydub import AudioSegment
import os
from io import BytesIO
import openai
from googletrans import Translator

# Ορισμός API Key από Streamlit secrets
openai.api_key = st.secrets["openai_api_key"]

st.title("Video Insights - Ανάλυση και Μετάφραση Βίντεο")

def download_video(url, filename="video.mp4"):
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': filename,
        'quiet': True,
        'no_warnings': True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

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
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            st.error(f"Σφάλμα ffmpeg: {result.stderr}")
            return False
        return True
    except Exception as e:
        st.error(f"❌ Σφάλμα εξαγωγής ήχου: {e}")
        return False

def audio_to_text(audio_path):
    try:
        audio_file= open(audio_path, "rb")
        transcript = openai.Audio.transcribe("whisper-1", audio_file)
        return transcript['text']
    except Exception as e:
        st.error(f"❌ Σφάλμα μετατροπής ήχου σε κείμενο: {e}")
        return None

def translate_text(text, dest_lang="el"):
    translator = Translator()
    try:
        translated = translator.translate(text, dest=dest_lang)
        return translated.text
    except Exception as e:
        st.error(f"❌ Σφάλμα μετάφρασης: {e}")
        return None

def summarize_text(text):
    try:
        prompt = f"Παρακαλώ κάνε μια σύντομη περίληψη του παρακάτω κειμένου:\n\n{text}\n\nΠερίληψη:"
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.5,
        )
        summary = response['choices'][0]['message']['content'].strip()
        return summary
    except Exception as e:
        st.error(f"❌ Σφάλμα περίληψης: {e}")
        return None

# UI

url = st.text_input("Επικόλλησε το URL του βίντεο (YouTube, TikTok, Instagram)")

if st.button("Ανάλυση Βίντεο"):
    if not url:
        st.warning("Παρακαλώ εισάγετε URL βίντεο.")
    else:
        with st.spinner("Κατέβασμα βίντεο..."):
            try:
                download_video(url)
                st.success("Το βίντεο κατέβηκε επιτυχώς.")
            except Exception as e:
                st.error(f"❌ Σφάλμα στο κατέβασμα βίντεο: {e}")
                st.stop()

        if not os.path.exists("video.mp4"):
            st.error("Το αρχείο video.mp4 δεν βρέθηκε μετά το κατέβασμα.")
            st.stop()

        with st.spinner("Εξαγωγή ήχου..."):
            success = extract_audio("video.mp4", "audio.wav")
            if not success:
                st.stop()
            else:
                st.success("Εξαγωγή ήχου ολοκληρώθηκε.")

        with st.spinner("Μετατροπή ήχου σε κείμενο..."):
            transcript = audio_to_text("audio.wav")
            if not transcript:
                st.stop()
            st.success("Μετατροπή σε κείμενο ολοκληρώθηκε.")

        st.subheader("Κείμενο από το βίντεο:")
        st.write(transcript)

        # Επιλογή μετάφρασης
        lang = st.selectbox("Επέλεξε γλώσσα μετάφρασης:", ["el", "en", "fr", "de", "es", "it", "ru", "zh-cn"])
        if st.button("Μετάφραση Κειμένου"):
            with st.spinner("Μετάφραση..."):
                translated_text = translate_text(transcript, dest_lang=lang)
                if translated_text:
                    st.subheader(f"Μετάφραση σε {lang}:")
                    st.write(translated_text)

        # Περίληψη
        if st.button("Περίληψη Κειμένου"):
            with st.spinner("Δημιουργία περίληψης..."):
                summary = summarize_text(transcript)
                if summary:
                    st.subheader("Περίληψη:")
                    st.write(summary)

# Καθαρισμός αρχείων (προαιρετικό)
if os.path.exists("video.mp4"):
    os.remove("video.mp4")
if os.path.exists("audio.wav"):
    os.remove("audio.wav")

