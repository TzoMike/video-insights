import streamlit as st
import openai

st.set_page_config(page_title="Video Analyzer", layout="centered")

# === Ρύθμιση OpenAI API ===
openai.api_key = st.secrets["openai_api_key"]

# === UI ===
st.title("📹 AI Ανάλυση Βίντεο")
transcript = st.text_area("📋 Επικόλλησε εδώ το κείμενο από το βίντεο:", height=300)

if transcript:
    # Επιλογή γλώσσας
    lang = st.selectbox("🌍 Επίλεξε γλώσσα μετάφρασης", ["Ελληνικά", "Αγγλικά", "Ισπανικά", "Γαλλικά"])
    
    if st.button("🔄 Μετάφραση"):
        with st.spinner("Μετάφραση..."):
            translation_prompt = f"Μετάφρασε το παρακάτω κείμενο στα {lang}:\n\n{transcript}"
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": translation_prompt}]
            )
            translated = response.choices[0].message.content
            st.subheader("🌐 Μετάφραση:")
            st.write(translated)
    
    if st.button("📝 Περίληψη"):
        with st.spinner("Δημιουργία περίληψης..."):
            summary_prompt = f"Δώσε μια σύντομη και ξεκάθαρη περίληψη του εξής κειμένου:\n\n{transcript}"
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": summary_prompt}]
            )
            summary = response.choices[0].message.content
            st.subheader("📄 Περίληψη:")
            st.write(summary)
