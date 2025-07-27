import streamlit as st
import requests
import os
import json
from pytube import YouTube
from googletrans import Translator
from datetime import datetime
import uuid
from dotenv import load_dotenv
import subprocess

load_dotenv()
ASSEMBLYAI_API_KEY = st.secrets["ASSEMBLYAI_API_KEY"]

# 🧠 Αρχικοποίηση session state
if "user" not in st.session_state:
    st.session_state.user = None
if "favorites" not in st.session_state:
    st.session_state.favorites = []
if "visit_count" not in st.session_state:
    st.session_state.visit_count = 0

# 📥 Συνάρτηση λήψης video
def download_video(url):
    yt = YouTube(url)
    stream = yt.streams.filter(file_extension='mp4').get_highest_resolution()
    stream.download(filename="video.mp4")

# 🎵 Εξαγωγή ήχου με ffmpeg
def extract_audio():
    try:
        subprocess.run([
            'ffmpeg', '-y', '-i', 'video.mp4',
            '-vn', '-acodec', 'mp3', 'audio.mp3'
        ], check=True)
    except subprocess.CalledProcessError as e:
        st.error("Σφάλμα εξαγωγής ήχου.")
        raise e

# 📝 Μετατροπή σε κείμενο με AssemblyAI
def transcribe_audio():
    try:
        headers = {'authorization': ASSEMBLYAI_API_KEY}
        upload_response = requests.post(
            'https://api.assemblyai.com/v2/upload',
            headers=headers,
            files={'file': open("audio.mp3", 'rb')}
        )
        upload_url = upload_response.json()['upload_url']

        transcript_response = requests.post(
            'https://api.assemblyai.com/v2/transcript',
            headers=headers,
            json={"audio_url": upload_url}
        )
        transcript_id = transcript_response.json()['id']

        # Polling for status
        status = 'queued'
        while status not in ['completed', 'error']:
            result = requests.get(
                f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                headers=headers
            ).json()
            status = result['status']
        
        if status == 'completed':
            return result['text']
        else:
            st.error("Απέτυχε η μετατροπή ήχου σε κείμενο.")
            return ""
    except Exception as e:
        st.error("Σφάλμα μετατροπής ήχου σε κείμενο.")
        return ""

# 🌍 Μετάφραση & Περίληψη
def translate_and_summarize(text):
    translator = Translator()
    translated = translator.translate(text, dest='el').text
    summary = text[:500] + "..." if len(text) > 500 else text
    return translated, summary

# 🖼️ UI
st.title("📹 AI Ανάλυση Βίντεο")

# 👤 Σύνδεση χρήστη
st.sidebar.title("👤 Σύνδεση Χρήστη")
username = st.sidebar.text_input("Όνομα ή Email")
if st.sidebar.button("✅ Είσοδος"):
    if username:
        st.session_state.user = username
        st.success(f"Καλώς ήρθες, {username}!")
    else:
        st.warning("Συμπλήρωσε όνομα.")

# 📥 Ανάλυση βίντεο
url = st.text_input("📎 Επικόλλησε URL από Instagram / YouTube / TikTok")
if st.button("🔍 Ανάλυση"):
    if url:
        st.info("⏳ Γίνεται λήψη βίντεο...")
        download_video(url)

        st.info("🎵 Εξαγωγή ήχου...")
        extract_audio()

        st.info("📝 Μετατροπή ήχου σε κείμενο...")
        full_text = transcribe_audio()

        if full_text:
            st.success("✅ Ολοκληρώθηκε η μετατροπή σε κείμενο.")
            st.subheader("📄 Αρχικό Κείμενο")
            st.write(full_text)

            translated, summary = translate_and_summarize(full_text)
            st.subheader("🌐 Μετάφραση")
            st.write(translated)
            st.subheader("🧠 Περίληψη")
            st.write(summary)

            # ⭐ Αγαπημένα
            if st.session_state.user:
                if st.button("⭐ Αποθήκευση στα αγαπημένα"):
                    fav = {
                        "user": st.session_state.user,
                        "url": url,
                        "summary": summary,
                        "date": datetime.now().isoformat()
                    }
                    st.session_state.favorites.append(fav)
                    with open("favorites.json", "w") as f:
                        json.dump(st.session_state.favorites, f)
                    st.success("✅ Αποθηκεύτηκε στα αγαπημένα.")

# 📂 Φόρτωση αγαπημένων (αν υπάρχουν)
try:
    with open("favorites.json", "r") as f:
        st.session_state.favorites = json.load(f)
except:
    pass

# 📌 Sidebar – Προβολή αγαπημένων
if st.session_state.user:
    st.sidebar.subheader("⭐ Τα Αγαπημένα σου")
    user_favs = [f for f in st.session_state.favorites if f["user"] == st.session_state.user]
    for fav in user_favs[-5:]:
        st.sidebar.markdown(f"- {fav['summary'][:50]}...")

# 📊 Στατιστικά επισκεψιμότητας
st.session_state.visit_count += 1
st.sidebar.markdown(f"👁️ Επισκέψεις: {st.session_state.visit_count}")

# 📁 Log επισκέψεων
try:
    log = {
        "user": st.session_state.user or "anonymous",
        "url": url,
        "timestamp": datetime.now().isoformat()
    }
    with open("visits.json", "a") as f:
        f.write(json.dumps(log) + "\n")
except:
    pass
