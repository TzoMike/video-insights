import streamlit as st
import openai
import yt_dlp
import os
from pathlib import Path

st.set_page_config(page_title="Video Analyzer", layout="centered")

# === OpenAI API key ===
openai.api_key = st.secrets["openai_api_key"]

# === UI ===
st.title("📥 Ανάλυση Βίντεο από URL")
url = st.text_input("🔗 Επικόλλησε το URL από Instagram, TikTok ή YouTube")

if url:
    if st.button("📥 Λήψη Βίντεο"):
        with st.spinner("Κατεβάζω το βίντεο..."):
            try:
                output_dir = "downloads"
                os.makedirs(output_dir, exist_ok=True)

                ydl_opts = {
                    'outtmpl': os.path.join(output_dir, 'video.%(ext)s'),
                    'format': 'best[ext=mp4]/best',
                    'quiet': True,
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.download([url])

                # Εμφάνιση αποτελέσματος
                st.success("✅ Το βίντεο κατέβηκε με επιτυχία.")
                video_path = os.path.join(output_dir, 'video.mp4')
                if os.path.exists(video_path):
                    st.video(video_path)
                    st.info("⚙️ Η μετατροπή σε κείμενο θα ενεργοποιηθεί σύντομα.")
                else:
                    st.warning("Το βίντεο κατέβηκε με άλλο format.")

            except Exception as e:
                st.error(f"❌ Σφάλμα κατά το κατέβασμα: {str(e)}")

st.divider()
st.subheader("📝 Εναλλακτικά: Αν έχεις ήδη το κείμενο")

transcript = st.text_area("📋 Επικόλλησε εδώ το κείμενο από το βίντεο", height=300)

if transcript:
    lang = st.selectbox("🌍 Επίλεξε γλώσσα μετάφρασης", ["Ελληνικά", "Αγγλικά", "Ισπανικά", "Γαλλικά"])

    if st.button("🔄 Μετάφραση"):
        with st.spinner("Μετάφραση..."):
            prompt = f"Μετάφρασε το παρακάτω κείμενο στα {lang}:\n\n{transcript}"
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            st.subheader("🌐 Μετάφραση:")
            st.write(response.choices[0].message.content)

    if st.button("📝 Περίληψη"):
        with st.spinner("Δημιουργία περίληψης..."):
            prompt = f"Δώσε σύντομη περίληψη για το παρακάτω κείμενο:\n\n{transcript}"
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            st.subheader("📄 Περίληψη:")
            st.write(response.choices[0].message.content)
