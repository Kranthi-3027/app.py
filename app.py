# -------------------------------------------------
# LawLens 🔍  –  Document Summary & Chat   (app.py)
# -------------------------------------------------
import os, io, re, time, html, hashlib
from dotenv import load_dotenv

load_dotenv()

import streamlit as st
import PyPDF2, docx
from PIL import Image
import pytesseract
from langdetect import detect
import google.generativeai as genai   # ✅ updated
from gtts import gTTS


API_KEY = os.getenv("GEMINI_KEY")
genai.configure(api_key=API_KEY)

model = genai.GenerativeModel("gemini-2.5-flash-lite")  # ✅ updated


# ────────────────────────────────────────────────
# CONFIG & SESSION STATE
# ────────────────────────────────────────────────
OCR_API_KEY = os.getenv("OCR_API_KEY")


# Tesseract path
pytesseract.pytesseract.tesseract_cmd = os.getenv(
    "TESSERACT_PATH",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

st.set_page_config(page_title="LawLens", page_icon="🔍", layout="centered")

# Global style
st.markdown("""
<style>
html, body, [class*="css"] {
  font-family: "Noto Sans", "Noto Sans Telugu", "Noto Sans Devanagari", system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, "Noto Color Emoji", "Apple Color Emoji", "Segoe UI Emoji", sans-serif;
}
</style>
""", unsafe_allow_html=True)

DEFAULT_STATE = {
    "doc_text": "",
    "summary": "",
    "chat_history": [],
    "general_messages": [],
    "resp_lang": "Auto (match user)",
    "ocr_lang": "Auto",
    "last_user_input": ""
}
for k, v in DEFAULT_STATE.items():
    st.session_state.setdefault(k, v)

# Language options
LANG_OPTIONS = ["Auto (match user)", "English", "Telugu", "Hindi"]
LANG_CODE_MAP_TTS = {"English": "en", "Telugu": "te", "Hindi": "hi"}
LANG_CODE_MAP_OCR = {"English": "eng", "Telugu": "tel", "Hindi": "hin"}

def pick_language(user_text: str) -> str:
    pref = st.session_state.get("resp_lang", "Auto (match user)")
    if pref != "Auto (match user)":
        return pref
    try:
        code = detect(user_text or "")
        return {"te": "Telugu", "hi": "Hindi", "en": "English"}.get(code, "English")
    except Exception:
        return "English"

def pick_tts_code(lang_name: str) -> str:
    return LANG_CODE_MAP_TTS.get(lang_name, "en-IN")

def pick_ocr_code() -> str:
    pref = st.session_state.get("ocr_lang", "Auto")
    if pref == "Auto":
        return "eng"
    return LANG_CODE_MAP_OCR.get(pref, "eng")

# ────────────────────────────────────────────────
# AI: prompts with explicit language control
# ────────────────────────────────────────────────
def ask_lawlens(document_text=None, query=None, mode="summary"):
    desired_lang = pick_language((query or "") + " " + (document_text or ""))
    lang_clause = (
        f"Respond in {desired_lang}. "
        "If a legal term lacks a natural equivalent, keep the term in English and explain it in the chosen language."
    )

    if mode == "summary":
        prompt = f"""You are LawLens 🔍, a legal document explainer.
{lang_clause}
Simplify this document:
- Short summary
- Highlight obligations, risks, deadlines
- Flag red flags
- Explain consequences of non-compliance
- Define legal jargon simply

Document:
{document_text}
"""
    elif mode == "chat":
        prompt = f"""You are LawLens 🔍, a legal explainer assistant.
{lang_clause}
The user's document:
{document_text}

User question:
{query}

Tasks:
- Answer based ONLY on the document provided.
- Explain contents clearly.
- Note possible consequences.
- Suggest practical actions.
- Define referenced legal sections with examples.
- Do not provide information outside the scope of this document.
"""
    else:
        prompt = f"""You are LawLens 🔍, a legal literacy guide.
{lang_clause}
User's question:
{query}

Tasks:
- Provide clear, concise legal information.
- Use only the language specified.
- Step-by-step guidance in plain language.
- Use relatable examples.
- Avoid long, complex sentences.
- Cover business registration, notices, or legal sections.
- Friendly, educational tone.
"""

    # ✅ FIX: wrap configs inside generation_config
    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": 0.7,
            "max_output_tokens": 800
        }
    )

    return response.text

# ────────────────────────────────────────────────
# Unicode-safe TTS button
# ────────────────────────────────────────────────
def clean_text(text: str) -> str:
    """
    Remove emojis, symbols, and other non-verbal characters from text.
    """
    # Regex pattern to remove emojis and symbols
    emoji_pattern = re.compile(
        "["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags
        u"\U00002700-\U000027BF"  # dingbats
        u"\U0001F900-\U0001F9FF"  # supplemental symbols
        u"\U00002600-\U000026FF"  # misc symbols
        u"\U00002B00-\U00002BFF"  # arrows
        "]+", flags=re.UNICODE
    )
    # Substitute emojis/symbols with nothing
    text = emoji_pattern.sub(r'', text)
    text = re.sub(r'(\*\*|__|\*|_|#+)', '', text)  # strip markdown
    return text.strip()

def clean_for_tts(text: str) -> str:
    """
    Clean text for TTS by removing emojis, symbols, and non-verbal characters.
    """
    return clean_text(text)

def tts_speak_toggle(text: str, lang_name: str):
    safe_text = clean_text(text)
    lang_code = pick_tts_code(lang_name)
    
    try:
        # Generate TTS audio using gTTS
        tts = gTTS(text=safe_text, lang=lang_code, slow=False)
        
        # Save to a temporary buffer
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        
        # Create a unique key for each audio widget
        audio_key = f"audio_{abs(hash(text + str(time.time()))) % 100000}"
        
        # Display audio player with download option
        st.audio(audio_buffer.getvalue(), format='audio/mp3')
        
    except Exception as e:
        st.error(f"TTS generation failed: {e}")
        st.info("Note: Ensure you have internet connection for gTTS to work.")


# ────────────────────────────────────────────────
# OCR HELPERS
# ────────────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=3600)
def ocr_image_bytes(img_bytes: bytes, lang_code: str) -> str:
    try:
        img = Image.open(io.BytesIO(img_bytes))
        txt = pytesseract.image_to_string(img, lang=lang_code).strip()
        return txt
    except Exception as e:
        return f"__OCR_ERROR__ {e}"

def hash_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def preprocess_pil(img: Image.Image) -> Image.Image:
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img

# ────────────────────────────────────────────────
# PDF / IMAGE / DOCX → TEXT
# ────────────────────────────────────────────────
def extract_text_from_pdf(uploaded_file) -> str:
    try:
        uploaded_file.seek(0)
        pdf = PyPDF2.PdfReader(uploaded_file)
        txt = "\n".join((p.extract_text() or "") for p in pdf.pages).strip()
        if len(txt) > 20:
            return txt
    except Exception as e:
        st.warning(f"PyPDF2 failed: {e}")

    lang_code = pick_ocr_code()
    try:
        uploaded_file.seek(0)
        import pdf2image
        images = pdf2image.convert_from_bytes(
            uploaded_file.read(),
            dpi=300,
            first_page=1,
            last_page=10
        )
        out = []
        bar = st.progress(0.0)
        for i, im in enumerate(images, 1):
            im = preprocess_pil(im)
            buf = io.BytesIO()
            im.save(buf, format="PNG")
            page_bytes = buf.getvalue()
            text = ocr_image_bytes(page_bytes, lang_code)
            if not text.startswith("__OCR_ERROR__"):
                out.append(text)
            bar.progress(i/len(images))
        bar.empty()
        combined = "\n".join(out).strip()
        if combined:
            return combined
    except Exception as e:
        st.info(f"pdf2image/OCR skipped: {e}")

    try:
        uploaded_file.seek(0)
        import fitz
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        out = []
        for p in doc[:5]:
            pix = p.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.open(io.BytesIO(pix.tobytes()))
            img = preprocess_pil(img)
            buff = io.BytesIO()
            img.save(buff, format="PNG")
            text = ocr_image_bytes(buff.getvalue(), lang_code)
            if not text.startswith("__OCR_ERROR__"):
                out.append(text)
        combined = "\n".join(out).strip()
        if combined:
            return combined
    except Exception as e:
        st.info(f"PyMuPDF OCR skipped: {e}")

    st.error("❌ Could not extract readable text from this PDF.")
    return ""

def extract_text_from_docx(f):
    try:
        return "\n".join(p.text for p in docx.Document(f).paragraphs).strip()
    except Exception as e:
        st.error(f"DOCX read error: {e}")
        return ""

def extract_text_from_image(f):
    try:
        img = Image.open(f)
        img = preprocess_pil(img)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        lang_code = pick_ocr_code()
        txt = ocr_image_bytes(buf.getvalue(), lang_code)
        if txt and not txt.startswith("__OCR_ERROR__"):
            return txt
        if txt.startswith("__OCR_ERROR__"):
            st.error(txt.replace("__OCR_ERROR__", "OCR error:"))
    except Exception as e:
        st.error(f"OCR image error: {e}")
    return ""

def extract_text(file):
    if not file:
        return ""
    ext = file.name.lower().split(".")[-1]
    if ext == "pdf":
        return extract_text_from_pdf(file)
    elif ext == "docx":
        return extract_text_from_docx(file)
    elif ext in ("jpg", "jpeg", "png"):
        return extract_text_from_image(file)
    elif ext == "txt":
        return file.read().decode("utf-8", errors="ignore")
    else:
        st.error("Unsupported file type")
        return ""

# ────────────────────────────────────────────────
# UI
# ────────────────────────────────────────────────
st.title("🔍 LawLens – Document Summary & Chat")

with st.sidebar:
    st.subheader("Preferences")
    st.session_state.resp_lang = st.selectbox(
        "Response language",
        LANG_OPTIONS,
        index=LANG_OPTIONS.index(st.session_state.resp_lang)
    )
    st.session_state.ocr_lang = st.selectbox(
        "OCR language (for scanned PDFs/images)",
        ["Auto", "English", "Telugu", "Hindi"],
        index=["Auto", "English", "Telugu", "Hindi"].index(st.session_state.ocr_lang)
    )
    st.caption("Tip: Set OCR language to improve accuracy for scanned docs.")

tab_doc, tab_gen = st.tabs(["📄 Document Summary & Chat", "🧭 General Legal Help"])

with tab_doc:
    st.header("📄 Upload & Analyze Document / Image")
    up = st.file_uploader(
        "PDF, DOCX, TXT, JPG, PNG (≤200 MB)",
        type=["pdf", "docx", "txt", "jpg", "jpeg", "png"]
    )

    colA, colB = st.columns(2)
    with colA:
        sample_btn = st.button("Load sample text contract")
    with colB:
        st.caption("Use sample if you don't have a file handy.")

    if sample_btn and not up:
        sample_text = """Service Agreement between Alpha Pvt Ltd and Beta Traders.
Parties agree to monthly deliveries by the 5th. Late delivery incurs 2% of invoice per week.
Either party may terminate with 30 days notice. Disputes: Hyderabad jurisdiction."""
        st.session_state.doc_text = sample_text
        with st.spinner("Generating summary…"):
            st.session_state.summary = ask_lawlens(document_text=sample_text, mode="summary")

    if up:
        with st.spinner("Extracting text…"):
            text = extract_text(up)
        if text:
            st.session_state.doc_text = text
            with st.spinner("Generating summary…"):
                st.session_state.summary = ask_lawlens(document_text=text, mode="summary")
        else:
            st.warning("No readable text found.")

    if st.session_state.summary:
        st.subheader("📑 Summary")
        st.write(st.session_state.summary)
        tts_speak_toggle(st.session_state.summary, pick_language(st.session_state.summary))

        st.divider()
        st.subheader("💬 Ask about this document")

        for m in st.session_state.chat_history:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])
                if m["role"] == "assistant":
                    tts_speak_toggle(m["content"], pick_language(m["content"]))

        q = st.chat_input("Ask a question…")
        if q:
            st.session_state.last_user_input = q
            st.session_state.chat_history.append({"role": "user", "content": q})
            ans = ask_lawlens(document_text=st.session_state.doc_text, query=q, mode="chat")
            st.session_state.chat_history.append({"role": "assistant", "content": ans})
            st.rerun()

with tab_gen:
    st.header("🧭 General Legal Help")
    for m in st.session_state.general_messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            if m["role"] == "assistant":
                tts_speak_toggle(m["content"], pick_language(m["content"]))

    q2 = st.chat_input("Ask any legal question…")
    if q2:
        st.session_state.last_user_input = q2
        st.session_state.general_messages.append({"role": "user", "content": q2})
        ans2 = ask_lawlens(query=q2, mode="general")
        st.session_state.general_messages.append({"role": "assistant", "content": ans2})
        st.rerun()

st.markdown("""---
⚠️ **Disclaimer:** LawLens is an AI tool and may make mistakes.
Always consult a qualified legal professional for critical matters.
""")
