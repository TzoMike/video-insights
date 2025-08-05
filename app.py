import streamlit as st
import os
import tempfile
import logging
from datetime import datetime
import json
import re
from typing import Dict, List, Optional, Tuple

# Third-party imports
try:
    from pytubefix import YouTube
    import pytubefix
except ImportError:
    st.error("Please install pytubefix: pip install pytubefix")
    st.stop()

try:
    from pydub import AudioSegment
    from pydub.utils import which
except ImportError:
    st.error("Please install pydub: pip install pydub")
    st.stop()

try:
    import openai
except ImportError:
    st.error("Please install openai: pip install openai")
    st.stop()

try:
    from googletrans import Translator
except ImportError:
    st.error("Please install googletrans: pip install googletrans==4.0.0rc1")
    st.stop()

try:
    from fpdf import FPDF
except ImportError:
    st.error("Please install fpdf2: pip install fpdf2")
    st.stop()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supported languages for translation
SUPPORTED_LANGUAGES = {
    'Greek': 'el',
    'English': 'en',
    'French': 'fr',
    'Spanish': 'es',
    'German': 'de',
    'Hindi': 'hi',
    'Chinese (Simplified)': 'zh-cn',
    'Russian': 'ru',
    'Dutch': 'nl',
    'Arabic': 'ar'
}

class VideoProcessor:
    def __init__(self):
        self.translator = Translator()
        
    def validate_url(self, url: str) -> Tuple[bool, str]:
        """Validate if the URL is from supported platforms"""
        youtube_pattern = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
        instagram_pattern = r'(https?://)?(www\.)?instagram\.com/'
        facebook_pattern = r'(https?://)?(www\.)?facebook\.com/'
        tiktok_pattern = r'(https?://)?(www\.)?tiktok\.com/'
        
        if re.search(youtube_pattern, url, re.IGNORECASE):
            return True, "youtube"
        elif re.search(instagram_pattern, url, re.IGNORECASE):
            return False, "Instagram downloads not supported in this demo (requires different API)"
        elif re.search(facebook_pattern, url, re.IGNORECASE):
            return False, "Facebook downloads not supported in this demo (requires different API)"
        elif re.search(tiktok_pattern, url, re.IGNORECASE):
            return False, "TikTok downloads not supported in this demo (requires different API)"
        else:
            return False, "Unsupported URL format"
    
    def download_youtube_audio(self, url: str, output_path: str) -> Tuple[bool, str, Dict]:
        """Download YouTube video and extract audio with fallback methods"""
        try:
            logger.info(f"Downloading YouTube video: {url}")
            
            # Method 1: Try with pytubefix (more stable than pytube)
            try:
                yt = YouTube(url)
                
                # Get video info safely
                video_info = {
                    'title': getattr(yt, 'title', 'Unknown Title'),
                    'length': getattr(yt, 'length', 0),
                    'views': getattr(yt, 'views', 0),
                    'author': getattr(yt, 'author', 'Unknown Author')
                }
                
                # Try different stream selection strategies
                audio_stream = None
                
                # Strategy 1: Audio-only streams
                try:
                    audio_streams = yt.streams.filter(only_audio=True)
                    if audio_streams:
                        audio_stream = audio_streams.first()
                except:
                    pass
                
                # Strategy 2: Progressive streams (contain both audio and video)
                if not audio_stream:
                    try:
                        progressive_streams = yt.streams.filter(progressive=True, file_extension='mp4')
                        if progressive_streams:
                            audio_stream = progressive_streams.order_by('resolution').asc().first()
                    except:
                        pass
                
                # Strategy 3: Any available stream
                if not audio_stream:
                    try:
                        all_streams = yt.streams.filter(file_extension='mp4')
                        if all_streams:
                            audio_stream = all_streams.first()
                    except:
                        pass
                
                if not audio_stream:
                    return False, "No compatible streams found. This video may be restricted or unavailable.", {}
                
                # Download the stream
                logger.info(f"Downloading stream: {audio_stream}")
                temp_file = audio_stream.download(
                    output_path=output_path, 
                    filename="temp_video.mp4"
                )
                
            except Exception as e1:
                logger.error(f"pytubefix download failed: {str(e1)}")
                return False, f"Download failed: {str(e1)}. This video may be age-restricted, private, or region-blocked.", {}
            
            # Convert to MP3 using pydub
            try:
                logger.info("Converting to MP3 format...")
                
                # Load the downloaded file
                audio = AudioSegment.from_file(temp_file)
                
                # Create MP3 file path
                mp3_file = os.path.join(output_path, "audio.mp3")
                
                # Export with optimized settings for transcription
                audio.export(
                    mp3_file, 
                    format="mp3", 
                    bitrate="128k",
                    parameters=["-ac", "1", "-ar", "16000"]  # Mono, 16kHz (optimal for Whisper)
                )
                
                # Clean up original file
                if os.path.exists(temp_file) and temp_file != mp3_file:
                    try:
                        os.remove(temp_file)
                    except:
                        pass  # Don't fail if cleanup fails
                
                # Verify the MP3 file was created successfully
                if os.path.exists(mp3_file) and os.path.getsize(mp3_file) > 1000:  # At least 1KB
                    logger.info(f"Audio successfully extracted to: {mp3_file}")
                    return True, mp3_file, video_info
                else:
                    return False, "Generated audio file is empty or corrupted", {}
                    
            except Exception as conv_error:
                logger.error(f"Audio conversion failed: {str(conv_error)}")
                return False, f"Audio conversion failed: {str(conv_error)}. The downloaded file may be corrupted.", {}
            
        except Exception as e:
            logger.error(f"Unexpected error in download_youtube_audio: {str(e)}")
            return False, f"Unexpected error: {str(e)}", {}
    
    def transcribe_audio(self, audio_path: str, openai_api_key: str) -> Tuple[bool, str]:
        """Transcribe audio using OpenAI Whisper"""
        try:
            logger.info(f"Transcribing audio: {audio_path}")
            
            # Set OpenAI API key
            openai.api_key = openai_api_key
            
            # Open and transcribe audio file
            with open(audio_path, "rb") as audio_file:
                transcript = openai.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
            
            logger.info("Transcription completed successfully")
            return True, transcript
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {str(e)}")
            return False, f"Transcription failed: {str(e)}"
    
    def create_summary(self, text: str, max_length: int = 300) -> str:
        """Create a simple summary by taking first N characters"""
        if len(text) <= max_length:
            return text
        
        # Find the last complete sentence within the limit
        truncated = text[:max_length]
        last_period = truncated.rfind('.')
        last_exclamation = truncated.rfind('!')
        last_question = truncated.rfind('?')
        
        last_sentence_end = max(last_period, last_exclamation, last_question)
        
        if last_sentence_end > 0:
            return text[:last_sentence_end + 1]
        else:
            return text[:max_length] + "..."
    
    def translate_text(self, text: str, target_language: str) -> Tuple[bool, str]:
        """Translate text to target language"""
        try:
            logger.info(f"Translating text to: {target_language}")
            
            # Skip translation if target language is English and text appears to be English
            if target_language == 'en':
                detected = self.translator.detect(text)
                if detected.lang == 'en':
                    return True, text
            
            result = self.translator.translate(text, dest=target_language)
            logger.info("Translation completed successfully")
            return True, result.text
            
        except Exception as e:
            logger.error(f"Error translating text: {str(e)}")
            return False, f"Translation failed: {str(e)}"
    
    def generate_pdf_report(self, data: Dict, output_path: str) -> Tuple[bool, str]:
        """Generate PDF report with all processed data"""
        try:
            logger.info("Generating PDF report")
            
            class PDF(FPDF):
                def header(self):
                    self.set_font('Arial', 'B', 15)
                    self.cell(0, 10, 'Video Content Analysis Report', 0, 1, 'C')
                    self.ln(10)
                
                def footer(self):
                    self.set_y(-15)
                    self.set_font('Arial', 'I', 8)
                    self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
            
            pdf = PDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            
            # Video Information
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(0, 10, "Video Information", 0, 1)
            pdf.set_font("Arial", size=10)
            
            if 'video_info' in data and data['video_info']:
                info = data['video_info']
                pdf.cell(0, 8, f"Title: {info.get('title', 'N/A')}", 0, 1)
                pdf.cell(0, 8, f"Author: {info.get('author', 'N/A')}", 0, 1)
                pdf.cell(0, 8, f"Duration: {info.get('length', 'N/A')} seconds", 0, 1)
                pdf.cell(0, 8, f"Views: {info.get('views', 'N/A')}", 0, 1)
            
            pdf.ln(5)
            
            # Summary
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(0, 10, "Summary", 0, 1)
            pdf.set_font("Arial", size=10)
            
            summary_text = data.get('summary', 'No summary available')
            # Handle Unicode characters
            try:
                pdf.multi_cell(0, 8, summary_text.encode('latin-1', 'replace').decode('latin-1'))
            except:
                pdf.multi_cell(0, 8, "Summary contains special characters that cannot be displayed in PDF")
            
            pdf.ln(5)
            
            # Translation
            if 'translation' in data and data['translation']:
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(0, 10, f"Translation ({data.get('target_language', 'Unknown')})", 0, 1)
                pdf.set_font("Arial", size=10)
                
                try:
                    pdf.multi_cell(0, 8, data['translation'].encode('latin-1', 'replace').decode('latin-1'))
                except:
                    pdf.multi_cell(0, 8, "Translation contains special characters that cannot be displayed in PDF")
                
                pdf.ln(5)
            
            # Full Transcript
            pdf.add_page()
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(0, 10, "Full Transcript", 0, 1)
            pdf.set_font("Arial", size=9)
            
            transcript_text = data.get('transcript', 'No transcript available')
            try:
                pdf.multi_cell(0, 6, transcript_text.encode('latin-1', 'replace').decode('latin-1'))
            except:
                pdf.multi_cell(0, 6, "Transcript contains special characters that cannot be displayed in PDF")
            
            # Save PDF
            pdf_path = os.path.join(output_path, f"video_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
            pdf.output(pdf_path)
            
            logger.info(f"PDF report generated: {pdf_path}")
            return True, pdf_path
            
        except Exception as e:
            logger.error(f"Error generating PDF: {str(e)}")
            return False, f"PDF generation failed: {str(e)}"

# Streamlit App
def main():
    st.set_page_config(
        page_title="Video Content Processor",
        page_icon="🎥",
        layout="wide"
    )
    
    st.title("🎥 Video Content Processor")
    st.markdown("Extract, transcribe, summarize, and translate content from YouTube videos")
    
    # Initialize session state
    if 'favorites' not in st.session_state:
        st.session_state.favorites = []
    
    # Initialize processor
    processor = VideoProcessor()
    
    # Get OpenAI API key from Streamlit secrets
    try:
        openai_api_key = st.secrets["OPENAI_API_KEY"]
    except KeyError:
        st.error("🔑 OpenAI API key not found in secrets. Please add OPENAI_API_KEY to your Streamlit secrets.")
        st.info("Go to your Streamlit Cloud app settings → Secrets and add: OPENAI_API_KEY = \"your-api-key-here\"")
        st.stop()
    
    # Sidebar for settings
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # Show API key status
        st.success("🔑 OpenAI API Key: Loaded from secrets")
        
        # Language selection
        target_language = st.selectbox(
            "Translation Language",
            options=list(SUPPORTED_LANGUAGES.keys()),
            index=1  # Default to English
        )
        
        st.markdown("---")
        st.markdown("### 📚 Supported Platforms")
        st.markdown("- ✅ YouTube")
        st.markdown("- ❌ Instagram (API required)")
        st.markdown("- ❌ Facebook (API required)")
        st.markdown("- ❌ TikTok (API required)")
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("🔗 Video URL Input")
        
        # URL input
        video_url = st.text_input(
            "Paste your video URL here:",
            placeholder="https://www.youtube.com/watch?v=..."
        )
        
        # Process button
        process_button = st.button("🚀 Process Video", type="primary")
        
        if process_button and video_url:
            
            # Validate URL
            is_valid, platform_or_error = processor.validate_url(video_url)
            
            if not is_valid:
                st.error(f"❌ {platform_or_error}")
                return
            
            # Processing steps
            with st.spinner("Processing video..."):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Step 1: Download and extract audio
                status_text.text("⏬ Downloading video and extracting audio...")
                progress_bar.progress(20)
                
                with tempfile.TemporaryDirectory() as temp_dir:
                    success, audio_path_or_error, video_info = processor.download_youtube_audio(
                        video_url, temp_dir
                    )
                    
                    if not success:
                        st.error(f"❌ {audio_path_or_error}")
                        return
                    
                    # Step 2: Transcribe audio
                    status_text.text("🎤 Transcribing audio...")
                    progress_bar.progress(40)
                    
                    success, transcript_or_error = processor.transcribe_audio(
                        audio_path_or_error, openai_api_key
                    )
                    
                    if not success:
                        st.error(f"❌ {transcript_or_error}")
                        return
                    
                    # Step 3: Create summary
                    status_text.text("📝 Creating summary...")
                    progress_bar.progress(60)
                    
                    summary = processor.create_summary(transcript_or_error)
                    
                    # Step 4: Translate content
                    status_text.text("🌐 Translating content...")
                    progress_bar.progress(80)
                    
                    target_lang_code = SUPPORTED_LANGUAGES[target_language]
                    success, translation_or_error = processor.translate_text(
                        transcript_or_error, target_lang_code
                    )
                    
                    if not success:
                        st.warning(f"⚠️ Translation failed: {translation_or_error}")
                        translation_or_error = "Translation not available"
                    
                    # Step 5: Generate PDF
                    status_text.text("📄 Generating PDF report...")
                    progress_bar.progress(90)
                    
                    report_data = {
                        'video_info': video_info,
                        'transcript': transcript_or_error,
                        'summary': summary,
                        'translation': translation_or_error if success else None,
                        'target_language': target_language
                    }
                    
                    pdf_success, pdf_path_or_error = processor.generate_pdf_report(
                        report_data, temp_dir
                    )
                    
                    progress_bar.progress(100)
                    status_text.text("✅ Processing complete!")
                    
                    # Display results
                    st.success("🎉 Video processed successfully!")
                    
                    # Video Information
                    if video_info:
                        st.subheader("📹 Video Information")
                        info_col1, info_col2 = st.columns(2)
                        with info_col1:
                            st.write(f"**Title:** {video_info.get('title', 'N/A')}")
                            st.write(f"**Author:** {video_info.get('author', 'N/A')}")
                        with info_col2:
                            st.write(f"**Duration:** {video_info.get('length', 'N/A')} seconds")
                            st.write(f"**Views:** {video_info.get('views', 'N/A'):,}")
                    
                    # Summary
                    st.subheader("📝 Summary")
                    st.write(summary)
                    
                    # Translation
                    if success and translation_or_error:
                        st.subheader(f"🌐 Translation ({target_language})")
                        st.write(translation_or_error)
                    
                    # Full Transcript
                    with st.expander("📄 Full Transcript", expanded=False):
                        st.text_area("Transcript", transcript_or_error, height=300)
                    
                    # PDF Download
                    if pdf_success:
                        with open(pdf_path_or_error, "rb") as pdf_file:
                            st.download_button(
                                label="📥 Download PDF Report",
                                data=pdf_file.read(),
                                file_name=f"video_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                                mime="application/pdf"
                            )
                    else:
                        st.error(f"❌ PDF generation failed: {pdf_path_or_error}")
                    
                    # Save to favorites
                    if st.button("⭐ Save to Favorites"):
                        favorite_item = {
                            'url': video_url,
                            'title': video_info.get('title', 'Untitled'),
                            'summary': summary,
                            'translation': translation_or_error if success else None,
                            'target_language': target_language,
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        st.session_state.favorites.append(favorite_item)
                        st.success("✅ Added to favorites!")
    
    with col2:
        st.header("⭐ Favorites")
        
        if st.session_state.favorites:
            for i, favorite in enumerate(reversed(st.session_state.favorites)):
                with st.expander(f"📹 {favorite['title'][:30]}...", expanded=False):
                    st.write(f"**URL:** {favorite['url']}")
                    st.write(f"**Added:** {favorite['timestamp']}")
                    st.write(f"**Summary:** {favorite['summary'][:100]}...")
                    if favorite['translation']:
                        st.write(f"**Translation ({favorite['target_language']}):** {favorite['translation'][:100]}...")
                    
                    if st.button(f"🗑️ Remove", key=f"remove_{len(st.session_state.favorites)-1-i}"):
                        st.session_state.favorites.pop(len(st.session_state.favorites)-1-i)
                        st.rerun()
        else:
            st.info("No favorites saved yet. Process a video and save it to favorites!")
        
        # Clear all favorites
        if st.session_state.favorites and st.button("🗑️ Clear All Favorites"):
            st.session_state.favorites = []
            st.rerun()

if __name__ == "__main__":
    main()
