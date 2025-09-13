# -------------------------------------------------
# Multi-Sector Document Analysis App (app.py)
# -------------------------------------------------
import os, io, re, time, html, hashlib
from dotenv import load_dotenv

load_dotenv()

import streamlit as st
import PyPDF2, docx
from PIL import Image
import pytesseract
from langdetect import detect
import google.generativeai as genai
from gtts import gTTS

API_KEY = os.getenv("GEMINI_KEY")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash-lite")

# ────────────────────────────────────────────────
# CONFIG & SESSION STATE
# ────────────────────────────────────────────────
OCR_API_KEY = os.getenv("OCR_API_KEY")

pytesseract.pytesseract.tesseract_cmd = os.getenv(
    "TESSERACT_PATH",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

st.set_page_config(page_title="Document Analysis Hub", page_icon="🔍", layout="centered")

# Global style
st.markdown("""
<style>
html, body, [class*="css"] {
  font-family: "Noto Sans", "Noto Sans Telugu", "Noto Sans Devanagari", system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, "Noto Color Emoji", "Apple Color Emoji", "Segoe UI Emoji", sans-serif;
}
.big-button {
    font-size: 20px !important;
    padding: 20px !important;
    margin: 10px 0 !important;
    text-align: center !important;
    border-radius: 10px !important;
}
.sector-button {
    font-size: 48px !important;
    padding: 30px !important;
    margin: 15px !important;
    text-align: center !important;
    border-radius: 15px !important;
}
</style>
""", unsafe_allow_html=True)

# Initialize session state
DEFAULT_STATE = {
    "language_selected": False,
    "sector_selected": False,
    "selected_language": "",
    "selected_sector": "",
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

# Language and sector configurations
LANGUAGES = {
    "English": "🇺🇸",
    "हिंदी": "🇮🇳", 
    "తెలుగు": "🇮🇳",
    "اردو": "🇵🇰"
}

SECTORS = {
    "Law": {"emoji": "⚖️", "symbol": "§"},
    "Medical": {"emoji": "🏥", "symbol": "+"},
    "Agriculture": {"emoji": "🌾", "symbol": "🚜"}
}

LANG_CODE_MAP_TTS = {"English": "en", "हिंदी": "hi", "తెలుగు": "te", "اردو": "ur"}
LANG_CODE_MAP_OCR = {"English": "eng", "हिंदी": "hin", "తెలుగు": "tel", "اردو": "urd"}

# UI Translations
UI_TRANSLATIONS = {
    "English": {
        "select_language": "🌍 Select Your Language",
        "choose_language": "Choose your preferred language to continue",
        "choose_sector": "Choose Your Sector",
        "selected_language": "Selected Language",
        "legal_docs": "Legal documents & consultation",
        "medical_reports": "Medical reports & analysis", 
        "agro_reports": "Agricultural reports & guidance",
        "back_language": "← Back to Language Selection",
        "settings": "⚙️ Settings",
        "change_lang_sector": "🔄 Change Language/Sector",
        "current": "Current",
        "upload_analyze": "Upload & Analyze",
        "document": "Document",
        "upload_files": "Upload PDF, DOCX, TXT, JPG, PNG (≤200 MB)",
        "load_sample": "📝 Load sample",
        "sample_tip": "Use sample if you don't have a file handy.",
        "analysis_summary": "📑 Analysis Summary",
        "ask_questions": "💬 Ask Questions About This Document",
        "ask_question_doc": "Ask a question about the document…",
        "general_help": "🧭 General",
        "help": "Help",
        "ask_general": "Ask any general questions about",
        "ask_question_general": "Ask any",
        "question": "question…",
        "disclaimer": "⚠️ **Disclaimer:**",
        "disclaimer_text": "is an AI tool and may make mistakes. Always consult a qualified",
        "disclaimer_end": "professional for critical matters.",
        "language": "🌍 Language",
        "sector": "📊 Sector",
        "extracting": "Extracting text…",
        "generating": "Generating analysis…",
        "thinking": "Thinking...",
        "no_text": "No readable text found in the uploaded file."
    },
    "हिंदी": {
        "select_language": "🌍 अपनी भाषा चुनें",
        "choose_language": "जारी रखने के लिए अपनी पसंदीदा भाषा चुनें",
        "choose_sector": "अपना क्षेत्र चुनें",
        "selected_language": "चयनित भाषा",
        "legal_docs": "कानूनी दस्तावेज़ और परामर्श",
        "medical_reports": "चिकित्सा रिपोर्ट और विश्लेषण",
        "agro_reports": "कृषि रिपोर्ट और मार्गदर्शन",
        "back_language": "← भाषा चयन पर वापस जाएं",
        "settings": "⚙️ सेटिंग्स",
        "change_lang_sector": "🔄 भाषा/क्षेत्र बदलें",
        "current": "वर्तमान",
        "upload_analyze": "अपलोड और विश्लेषण करें",
        "document": "दस्तावेज़",
        "upload_files": "PDF, DOCX, TXT, JPG, PNG अपलोड करें (≤200 MB)",
        "load_sample": "📝 नमूना लोड करें",
        "sample_tip": "यदि आपके पास फ़ाइल नहीं है तो नमूना उपयोग करें।",
        "analysis_summary": "📑 विश्लेषण सारांश",
        "ask_questions": "💬 इस दस्तावेज़ के बारे में प्रश्न पूछें",
        "ask_question_doc": "दस्तावेज़ के बारे में प्रश्न पूछें…",
        "general_help": "🧭 सामान्य",
        "help": "सहायता",
        "ask_general": "के बारे में कोई भी सामान्य प्रश्न पूछें",
        "ask_question_general": "कोई भी",
        "question": "प्रश्न पूछें…",
        "disclaimer": "⚠️ **अस्वीकरण:**",
        "disclaimer_text": "एक AI उपकरण है और गलतियाँ हो सकती हैं। हमेशा योग्य",
        "disclaimer_end": "पेशेवर से महत्वपूर्ण मामलों के लिए सलाह लें।",
        "language": "🌍 भाषा",
        "sector": "📊 क्षेत्र",
        "extracting": "टेक्स्ट निकाला जा रहा है…",
        "generating": "विश्लेषण तैयार किया जा रहा है…",
        "thinking": "सोच रहे हैं...",
        "no_text": "अपलोड की गई फ़ाइल में कोई पठनीय टेक्स्ट नहीं मिला।"
    },
    "తెలుగు": {
        "select_language": "🌍 మీ భాషను ఎంచుకోండి",
        "choose_language": "కొనసాగించడానికి మీ ప్రాధాన్య భాషను ఎంచుకోండి",
        "choose_sector": "మీ రంగాన్ని ఎంచుకోండి",
        "selected_language": "ఎంచుకున్న భాష",
        "legal_docs": "చట్టపరమైన పత్రాలు & సలహా",
        "medical_reports": "వైద్య నివేదికలు & విశ్లేషణ",
        "agro_reports": "వ్యవసాయ నివేదికలు & మార్గదర్శకత్వం",
        "back_language": "← భాష ఎంపికకు తిరిగి వెళ్ళు",
        "settings": "⚙️ సెట్టింగ్‌లు",
        "change_lang_sector": "🔄 భాష/రంగం మార్చు",
        "current": "ప్రస్తుత",
        "upload_analyze": "అప్‌లోడ్ & విశ్లేషించు",
        "document": "పత్రం",
        "upload_files": "PDF, DOCX, TXT, JPG, PNG అప్‌లోడ్ చేయండి (≤200 MB)",
        "load_sample": "📝 నమూనా లోడ్ చేయండి",
        "sample_tip": "మీ వద్ద ఫైల్ లేకపోతే నమూనాను ఉపయోగించండి.",
        "analysis_summary": "📑 విశ్లేషణ సారాంశం",
        "ask_questions": "💬 ఈ పత్రం గురించి ప్రశ్నలు అడగండి",
        "ask_question_doc": "పత్రం గురించి ప్రశ్న అడగండి…",
        "general_help": "🧭 సాధారణ",
        "help": "సహాయం",
        "ask_general": "గురించి ఏవైనా సాధారణ ప్రశ్నలు అడగండి",
        "ask_question_general": "ఏదైనా",
        "question": "ప్రశ్న అడగండి…",
        "disclaimer": "⚠️ **నిరాకరణ:**",
        "disclaimer_text": "ఒక AI సాధనం మరియు తప్పులు జరుగవచ్చు. ఎల్లప్పుడూ అర్హత కలిగిన",
        "disclaimer_end": "నిపుణుడిని కీలక విషయాల కోసం సంప్రదించండి।",
        "language": "🌍 భాష",
        "sector": "📊 రంగం",
        "extracting": "టెక్స్ట్ వెలికితీస్తున్నాం…",
        "generating": "విశ్లేషణ రూపొందిస్తున్నాం…",
        "thinking": "ఆలోచిస్తున్నాం...",
        "no_text": "అప్‌లోడ్ చేసిన ఫైల్‌లో చదవగలిగే టెక్స్ట్ కనుగొనబడలేదు."
    },
    "اردو": {
        "select_language": "🌍 اپنی زبان منتخب کریں",
        "choose_language": "جاری رکھنے کے لیے اپنی پسندیدہ زبان منتخب کریں",
        "choose_sector": "اپنا شعبہ منتخب کریں",
        "selected_language": "منتخب کردہ زبان",
        "legal_docs": "قانونی دستاویزات اور مشاورت",
        "medical_reports": "طبی رپورٹس اور تجزیہ",
        "agro_reports": "زرعی رپورٹس اور رہنمائی",
        "back_language": "← زبان کے انتخاب پر واپس جائیں",
        "settings": "⚙️ ترتیبات",
        "change_lang_sector": "🔄 زبان/شعبہ تبدیل کریں",
        "current": "موجودہ",
        "upload_analyze": "اپ لوڈ اور تجزیہ کریں",
        "document": "دستاویز",
        "upload_files": "PDF, DOCX, TXT, JPG, PNG اپ لوڈ کریں (≤200 MB)",
        "load_sample": "📝 نمونہ لوڈ کریں",
        "sample_tip": "اگر آپ کے پاس فائل نہیں ہے تو نمونہ استعمال کریں۔",
        "analysis_summary": "📑 تجزیہ خلاصہ",
        "ask_questions": "💬 اس دستاویز کے بارے میں سوالات پوچھیں",
        "ask_question_doc": "دستاویز کے بارے میں سوال پوچھیں…",
        "general_help": "🧭 عام",
        "help": "مدد",
        "ask_general": "کے بارے میں کوئی بھی عام سوالات پوچھیں",
        "ask_question_general": "کوئی بھی",
        "question": "سوال پوچھیں…",
        "disclaimer": "⚠️ **دستبرداری:**",
        "disclaimer_text": "ایک AI ٹول ہے اور غلطیاں ہو سکتی ہیں۔ ہمیشہ اہل",
        "disclaimer_end": "پیشہ ور سے اہم معاملات کے لیے مشورہ لیں۔",
        "language": "🌍 زبان",
        "sector": "📊 شعبہ",
        "extracting": "ٹیکسٹ نکالا جا رہا ہے…",
        "generating": "تجزیہ تیار کیا جا رہا ہے…",
        "thinking": "سوچ رہے ہیں...",
        "no_text": "اپ لوڈ شدہ فائل میں پڑھنے کے قابل ٹیکسٹ نہیں ملا۔"
    }
}

def get_text(key):
    """Get translated text based on selected language"""
    lang = st.session_state.get("selected_language", "English")
    return UI_TRANSLATIONS.get(lang, UI_TRANSLATIONS["English"]).get(key, key)

def pick_language(user_text: str) -> str:
    pref = st.session_state.get("selected_language", "English")
    return pref

def pick_tts_code(lang_name: str) -> str:
    return LANG_CODE_MAP_TTS.get(lang_name, "en")

def pick_ocr_code() -> str:
    pref = st.session_state.get("selected_language", "English")
    return LANG_CODE_MAP_OCR.get(pref, "eng")

# ────────────────────────────────────────────────
# AI FUNCTIONS (UPDATED FOR SECTOR RESTRICTION)
# ────────────────────────────────────────────────
def get_sector_prompt(sector, mode="summary"):
    prompts = {
        "Law": {
            "summary": "You are LawLens ⚖️, a legal document explainer. ONLY analyze legal documents, contracts, agreements, laws, regulations, court cases, and legal matters.",
            "chat": "You are LawLens ⚖️, a legal assistant. ONLY answer questions about legal documents, legal terms, laws, regulations, and legal procedures.",
            "general": "You are LawLens ⚖️, a legal guide. ONLY provide legal information, legal advice, law explanations, legal procedures, and legal guidance."
        },
        "Medical": {
            "summary": "You are MedLens 🏥, a medical document explainer. ONLY analyze medical reports, test results, prescriptions, medical records, health documents, and medical matters.",
            "chat": "You are MedLens 🏥, a medical assistant. ONLY answer questions about medical documents, medical terminology, health conditions, treatments, and medical procedures.",
            "general": "You are MedLens 🏥, a medical guide. ONLY provide medical information, health advice, medical explanations, disease information, and health guidance."
        },
        "Agriculture": {
            "summary": "You are AgroLens 🌾, an agricultural document explainer. ONLY analyze agricultural reports, soil tests, crop data, farming documents, weather reports, and agricultural matters.",
            "chat": "You are AgroLens 🌾, an agricultural assistant. ONLY answer questions about farming documents, agricultural terms, crops, soil, weather, and farming procedures.",
            "general": "You are AgroLens 🌾, an agricultural guide. ONLY provide farming information, agricultural advice, crop guidance, soil management, and farming techniques."
        }
    }
    return prompts.get(sector, prompts["Law"]).get(mode, prompts["Law"]["summary"])

def ask_ai(document_text=None, query=None, mode="summary"):
    sector = st.session_state.selected_sector
    language = st.session_state.selected_language
    
    # Check for critical medical keywords across all sectors
    critical_medical_keywords = [
        # English
        "emergency", "urgent", "critical", "severe", "chest pain", "heart attack", 
        "stroke", "bleeding", "unconscious", "poisoning", "overdose", "suicide",
        "difficulty breathing", "allergic reaction", "seizure", "trauma", "fracture",
        "high fever", "blood pressure", "diabetes", "insulin", "medication error",
        "swelling", "rash", "infection", "wound", "burn", "accident", "injury",
        
        # Hindi
        "आपातकाल", "तत्काल", "गंभीर", "सीने में दर्द", "दिल का दौरा", "खून बहना",
        "बेहोश", "जहर", "सांस लेने में कठिनाई", "एलर्जी", "बुखार", "रक्तचाप", "मधुमेह",
        "सूजन", "संक्रमण", "घाव", "जलना", "चोट",
        
        # Telugu
        "అత్యవసర", "తక్షణ", "తీవ్రమైన", "ఛాతీ నొప్పి", "గుండెపోటు", "రక్తస్రావం",
        "అపస్మారక", "విషం", "శ్వాస తీసుకోవడంలో ఇబ్బంది", "అలెర్జీ", "జ్వరం", "రక్తపోటు",
        "మధుమేహం", "వాపు", "ఇన్ఫెక్షన్", "గాయం", "కాలిన గాయం", "దెబ్బ",
        
        # Urdu
        "ہنگامی", "فوری", "شدید", "سینے میں درد", "دل کا دورہ", "خون بہنا",
        "بے ہوش", "زہر", "سانس لینے میں دشواری", "الرجی", "بخار", "بلڈ پریشر",
        "ذیابیطس", "سوجن", "انفیکشن", "زخم", "جلنا", "چوٹ"
    ]
    
    # Check if query contains critical medical terms
    is_medical_emergency = False
    if query:
        query_lower = query.lower()
        is_medical_emergency = any(keyword.lower() in query_lower for keyword in critical_medical_keywords)
    
    # If it's a medical emergency, override sector restrictions
    if is_medical_emergency and sector != "Medical":
        emergency_prompt = f"""
        🚨 MEDICAL EMERGENCY OVERRIDE 🚨
        
        You are now temporarily acting as MedLens 🏥 because this appears to be a critical medical query that could involve immediate harm.
        
        RESPOND IMMEDIATELY in {language} with:
        1. **EMERGENCY WARNING**: If this is a life-threatening situation, contact emergency services immediately
        2. **BASIC GUIDANCE**: Provide essential first aid or immediate steps
        3. **SEEK PROFESSIONAL HELP**: Strongly advise to consult medical professionals
        4. **DISCLAIMER**: Emphasize this is emergency guidance only, not professional medical advice
        
        User's critical medical query: {query}
        Document context (if any): {document_text or "No document provided"}
        
        Respond with urgency and care, prioritizing user safety.
        """
        
        response = model.generate_content(
            emergency_prompt,
            generation_config={
                "temperature": 0.3,  # Lower temperature for more precise emergency response
                "max_output_tokens": 1000
            }
        )
        
        # Add emergency warning header
        emergency_response = f"""
        🚨 **MEDICAL EMERGENCY RESPONSE** 🚨
        *(Sector restriction overridden for potential medical emergency)*
        
        {response.text}
        
        ⚠️ **CRITICAL**: If this is a life-threatening emergency, contact emergency services (108/102 in India, 911 in US, etc.) IMMEDIATELY.
        """
        
        return emergency_response
    
    # Regular sector-specific responses
    if sector != "Medical":
        sector_restriction = f"""
        CRITICAL: You MUST only provide {sector.lower()}-related information. 
        - If the user asks about other topics (law, medicine, agriculture) outside your {sector.lower()} specialty, respond: "मुझे खुशी होगी कि मैं केवल {sector.lower()} से संबंधित प्रश्नों का उत्तर दे सकूं। कृपया अन्य विषयों के लिए उपयुक्त सेक्शन में जाएं।" (in the selected language)
        - REFUSE to answer non-{sector.lower()} questions completely.
        - Stay strictly within {sector.lower()} domain.
        - EXCEPTION: If you detect a potential medical emergency, you may provide basic safety guidance.
        """
    else:
        sector_restriction = f"You are in the Medical sector. Provide comprehensive medical guidance and information."
    
    lang_clause = f"Respond ONLY in {language}. All text, labels, headings, and content must be completely in {language}. Do not mix languages."
    base_prompt = get_sector_prompt(sector, mode)
    
    if mode == "summary":
        prompt = f"""{base_prompt}
{lang_clause}
{sector_restriction}

Analyze this {sector.lower()} document in {language}:
- Provide summary completely in {language}
- Key findings/obligations in {language} 
- Important dates/recommendations in {language}
- Risk factors/indicators in {language}
- All headings and labels in {language}

Document:
{document_text}
"""
    elif mode == "chat":
        prompt = f"""{base_prompt}
{lang_clause}
{sector_restriction}

Document context:
{document_text}

User question: {query}

IMPORTANT: 
1. Only answer if this question is related to {sector.lower()}
2. If not related to {sector.lower()}, respond in {language}: "I can only help with {sector.lower()}-related questions about your document."
3. Answer completely in {language}
4. EXCEPTION: For potential medical emergencies, provide basic safety guidance regardless of sector.
"""
    else:
        prompt = f"""{base_prompt}
{lang_clause}
{sector_restriction}

User question: {query}

IMPORTANT: 
1. Only answer {sector.lower()}-related questions
2. If question is about other topics, respond in {language}: "I specialize only in {sector.lower()}. Please switch to the appropriate sector for other topics."
3. Provide answer completely in {language}
4. EXCEPTION: For potential medical emergencies, provide basic safety guidance regardless of sector.
"""

    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": 0.7,
            "max_output_tokens": 800
        }
    )
    return response.text

# ────────────────────────────────────────────────
# TTS FUNCTIONS
# ────────────────────────────────────────────────
def clean_text(text: str) -> str:
    emoji_pattern = re.compile(
        "["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF"
        u"\U0001F1E0-\U0001F1FF"
        u"\U00002700-\U000027BF"
        u"\U0001F900-\U0001F9FF"
        u"\U00002600-\U000026FF"
        u"\U00002B00-\U00002BFF"
        "]+", flags=re.UNICODE
    )
    text = emoji_pattern.sub(r'', text)
    text = re.sub(r'(\*\*|__|\*|_|#+)', '', text)
    return text.strip()

def tts_speak_toggle(text: str, lang_name: str):
    safe_text = clean_text(text)
    lang_code = pick_tts_code(lang_name)
    
    try:
        tts = gTTS(text=safe_text, lang=lang_code, slow=False)
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        st.audio(audio_buffer.getvalue(), format='audio/mp3')
    except Exception as e:
        st.error(f"TTS generation failed: {e}")

# ────────────────────────────────────────────────
# OCR FUNCTIONS
# ────────────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=3600)
def ocr_image_bytes(img_bytes: bytes, lang_code: str) -> str:
    try:
        img = Image.open(io.BytesIO(img_bytes))
        txt = pytesseract.image_to_string(img, lang=lang_code).strip()
        return txt
    except Exception as e:
        return f"__OCR_ERROR__ {e}"

def preprocess_pil(img: Image.Image) -> Image.Image:
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img

# ────────────────────────────────────────────────
# TEXT EXTRACTION FUNCTIONS
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
        images = pdf2image.convert_from_bytes(uploaded_file.read(), dpi=300, first_page=1, last_page=10)
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
# LANGUAGE SELECTION PAGE
# ────────────────────────────────────────────────
def show_language_selection():
    st.markdown("<h1 style='text-align: center; color: #1f77b4;'>🌍 Select Your Language</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 18px; margin-bottom: 40px;'>Choose your preferred language to continue</p>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button(f"{LANGUAGES['English']} English", key="eng", use_container_width=True, help="Select English"):
            st.session_state.selected_language = "English"
            st.session_state.language_selected = True
            st.rerun()
            
        if st.button(f"{LANGUAGES['తెలుగు']} తెలుగు", key="tel", use_container_width=True, help="Select Telugu"):
            st.session_state.selected_language = "తెలుగు"
            st.session_state.language_selected = True
            st.rerun()
    
    with col2:
        if st.button(f"{LANGUAGES['हिंदी']} हिंदी", key="hin", use_container_width=True, help="Select Hindi"):
            st.session_state.selected_language = "हिंदी"
            st.session_state.language_selected = True
            st.rerun()
            
        if st.button(f"{LANGUAGES['اردو']} اردو", key="urd", use_container_width=True, help="Select Urdu"):
            st.session_state.selected_language = "اردو"
            st.session_state.language_selected = True
            st.rerun()

# ────────────────────────────────────────────────
# SECTOR SELECTION PAGE
# ────────────────────────────────────────────────
def show_sector_selection():
    st.markdown(f"<h1 style='text-align: center; color: #1f77b4;'>{get_text('choose_sector')}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; font-size: 18px; margin-bottom: 40px;'>{get_text('selected_language')}: {LANGUAGES[st.session_state.selected_language]} {st.session_state.selected_language}</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("<div style='text-align: center; font-size: 64px; margin: 20px 0;'>⚖️</div>", unsafe_allow_html=True)
        if st.button("Law", key="law_btn", use_container_width=True, help="Legal document analysis"):
            st.session_state.selected_sector = "Law"
            st.session_state.sector_selected = True
            st.rerun()
        st.markdown(f"<p style='text-align: center; font-size: 14px; color: #666;'>{get_text('legal_docs')}</p>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("<div style='text-align: center; font-size: 64px; margin: 20px 0;'>🏥</div>", unsafe_allow_html=True)
        if st.button("Medical", key="med_btn", use_container_width=True, help="Medical document analysis"):
            st.session_state.selected_sector = "Medical"
            st.session_state.sector_selected = True
            st.rerun()
        st.markdown(f"<p style='text-align: center; font-size: 14px; color: #666;'>{get_text('medical_reports')}</p>", unsafe_allow_html=True)
    
    with col3:
        st.markdown("<div style='text-align: center; font-size: 64px; margin: 20px 0;'>🌾</div>", unsafe_allow_html=True)
        if st.button("Agriculture", key="agr_btn", use_container_width=True, help="Agricultural document analysis"):
            st.session_state.selected_sector = "Agriculture"
            st.session_state.sector_selected = True
            st.rerun()
        st.markdown(f"<p style='text-align: center; font-size: 14px; color: #666;'>{get_text('agro_reports')}</p>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button(get_text("back_language"), use_container_width=True):
        st.session_state.language_selected = False
        st.session_state.selected_language = ""
        st.rerun()

# ────────────────────────────────────────────────
# MAIN APPLICATION
# ────────────────────────────────────────────────
def show_main_app():
    sector_info = SECTORS[st.session_state.selected_sector]
    st.title(f"{sector_info['emoji']} {st.session_state.selected_sector}Lens – {get_text('upload_analyze')} & Chat")
    
    # Language indicator
    st.info(f"{get_text('language')}: {LANGUAGES[st.session_state.selected_language]} {st.session_state.selected_language} | {get_text('sector')}: {sector_info['emoji']} {st.session_state.selected_sector}")
    
    # Settings in sidebar
    with st.sidebar:
        st.subheader(get_text("settings"))
        if st.button(get_text("change_lang_sector"), use_container_width=True):
            # Reset all states - FIXED
            st.session_state.language_selected = False
            st.session_state.sector_selected = False
            st.session_state.selected_language = ""
            st.session_state.selected_sector = ""
            st.session_state.doc_text = ""
            st.session_state.summary = ""
            st.session_state.chat_history = []        # ✅ Must be list
            st.session_state.general_messages = []    # ✅ Must be list
            st.rerun()
        
        st.markdown("---")
        st.caption(f"{get_text('current')}: {st.session_state.selected_language} → {st.session_state.selected_sector}")
    
    # Main tabs
    tab_doc, tab_gen = st.tabs([f"📄 {st.session_state.selected_sector} {get_text('upload_analyze')}", f"{get_text('general_help')} {st.session_state.selected_sector} {get_text('help')}"])
    
    with tab_doc:
        st.header(f"📄 {get_text('upload_analyze')} {st.session_state.selected_sector} {get_text('document')}")
        up = st.file_uploader(
            get_text("upload_files"),
            type=["pdf", "docx", "txt", "jpg", "jpeg", "png"]
        )
        
        # Sample button
        colA, colB = st.columns(2)
        with colA:
            sample_btn = st.button(f"{get_text('load_sample')} {st.session_state.selected_sector.lower()} {get_text('document')}")
        with colB:
            st.caption(get_text("sample_tip"))
        
        # Sample text based on sector
        if sample_btn and not up:
            samples = {
                "Law": "Service Agreement between Alpha Pvt Ltd and Beta Traders. Parties agree to monthly deliveries by the 5th. Late delivery incurs 2% of invoice per week. Either party may terminate with 30 days notice. Disputes: Hyderabad jurisdiction.",
                "Medical": "Patient: John Doe. Blood Pressure: 140/90 mmHg (elevated). Glucose: 180 mg/dL (high). Cholesterol: 250 mg/dL. Recommendation: Start antihypertensive medication. Follow low-sodium diet. Recheck in 4 weeks.",
                "Agriculture": "Soil Report - Field A: pH 6.8, Nitrogen 45 ppm (low), Phosphorus 25 ppm (adequate), Potassium 180 ppm (high). Crop: Wheat. Recommendation: Apply 120 kg/ha Urea. Expected yield: 4.2 tons/ha. Next soil test: 6 months."
            }
            st.session_state.doc_text = samples[st.session_state.selected_sector]
            with st.spinner(get_text("generating")):
                st.session_state.summary = ask_ai(document_text=st.session_state.doc_text, mode="summary")
        
        if up:
            with st.spinner(get_text("extracting")):
                text = extract_text(up)
            if text:
                st.session_state.doc_text = text
                with st.spinner(get_text("generating")):
                    st.session_state.summary = ask_ai(document_text=text, mode="summary")
            else:
                st.warning(get_text("no_text"))
        
        if st.session_state.summary:
            st.subheader(get_text("analysis_summary"))
            st.write(st.session_state.summary)
            tts_speak_toggle(st.session_state.summary, st.session_state.selected_language)
            
            st.divider()
            st.subheader(get_text("ask_questions"))
            
            # Chat history
            for m in st.session_state.chat_history:
                with st.chat_message(m["role"]):
                    st.markdown(m["content"])
                    if m["role"] == "assistant":
                        tts_speak_toggle(m["content"], st.session_state.selected_language)
            
            # Chat input
            q = st.chat_input(get_text("ask_question_doc"))
            if q:
                st.session_state.chat_history.append({"role": "user", "content": q})
                with st.spinner(get_text("thinking")):
                    ans = ask_ai(document_text=st.session_state.doc_text, query=q, mode="chat")
                st.session_state.chat_history.append({"role": "assistant", "content": ans})
                st.rerun()
    
    with tab_gen:
        st.header(f"{get_text('general_help')} {st.session_state.selected_sector} {get_text('help')}")
        st.caption(f"{get_text('ask_general')} {st.session_state.selected_sector.lower()}")
        
        # General chat history
        for m in st.session_state.general_messages:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])
                if m["role"] == "assistant":
                    tts_speak_toggle(m["content"], st.session_state.selected_language)
        
        # General chat input
        q2 = st.chat_input(f"{get_text('ask_question_general')} {st.session_state.selected_sector.lower()} {get_text('question')}")
        if q2:
            st.session_state.general_messages.append({"role": "user", "content": q2})
            with st.spinner(get_text("thinking")):
                ans2 = ask_ai(query=q2, mode="general")
            st.session_state.general_messages.append({"role": "assistant", "content": ans2})
            st.rerun()
    
    # Disclaimer
    st.markdown(f"""---
{get_text("disclaimer")} {st.session_state.selected_sector}Lens {get_text("disclaimer_text")} {st.session_state.selected_sector.lower()} {get_text("disclaimer_end")}
""")

# ────────────────────────────────────────────────
# MAIN APP LOGIC
# ────────────────────────────────────────────────
def main():
    if not st.session_state.language_selected:
        show_language_selection()
    elif not st.session_state.sector_selected:
        show_sector_selection()
    else:
        show_main_app()

if __name__ == "__main__":
    main()
# -------------------------------------------------
# Multi-Sector Document Analysis App (app.py)
# -------------------------------------------------
import os, io, re, time, html, hashlib
from dotenv import load_dotenv

load_dotenv()

import streamlit as st
import PyPDF2, docx
from PIL import Image
import pytesseract
from langdetect import detect
import google.generativeai as genai
from gtts import gTTS

API_KEY = os.getenv("GEMINI_KEY")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash-lite")

# ────────────────────────────────────────────────
# CONFIG & SESSION STATE
# ────────────────────────────────────────────────
OCR_API_KEY = os.getenv("OCR_API_KEY")

pytesseract.pytesseract.tesseract_cmd = os.getenv(
    "TESSERACT_PATH",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

st.set_page_config(page_title="Document Analysis Hub", page_icon="🔍", layout="centered")

# Global style
st.markdown("""
<style>
html, body, [class*="css"] {
  font-family: "Noto Sans", "Noto Sans Telugu", "Noto Sans Devanagari", system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, "Noto Color Emoji", "Apple Color Emoji", "Segoe UI Emoji", sans-serif;
}
.big-button {
    font-size: 20px !important;
    padding: 20px !important;
    margin: 10px 0 !important;
    text-align: center !important;
    border-radius: 10px !important;
}
.sector-button {
    font-size: 48px !important;
    padding: 30px !important;
    margin: 15px !important;
    text-align: center !important;
    border-radius: 15px !important;
}
</style>
""", unsafe_allow_html=True)

# Initialize session state
DEFAULT_STATE = {
    "language_selected": False,
    "sector_selected": False,
    "selected_language": "",
    "selected_sector": "",
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

# Language and sector configurations
LANGUAGES = {
    "English": "🇺🇸",
    "हिंदी": "🇮🇳", 
    "తెలుగు": "🇮🇳",
    "اردو": "🇵🇰"
}

SECTORS = {
    "Law": {"emoji": "⚖️", "symbol": "§"},
    "Medical": {"emoji": "🏥", "symbol": "+"},
    "Agriculture": {"emoji": "🌾", "symbol": "🚜"}
}

LANG_CODE_MAP_TTS = {"English": "en", "हिंदी": "hi", "తెలుగు": "te", "اردو": "ur"}
LANG_CODE_MAP_OCR = {"English": "eng", "हिंदी": "hin", "తెలుగు": "tel", "اردو": "urd"}

# UI Translations
UI_TRANSLATIONS = {
    "English": {
        "select_language": "🌍 Select Your Language",
        "choose_language": "Choose your preferred language to continue",
        "choose_sector": "Choose Your Sector",
        "selected_language": "Selected Language",
        "legal_docs": "Legal documents & consultation",
        "medical_reports": "Medical reports & analysis", 
        "agro_reports": "Agricultural reports & guidance",
        "back_language": "← Back to Language Selection",
        "settings": "⚙️ Settings",
        "change_lang_sector": "🔄 Change Language/Sector",
        "current": "Current",
        "upload_analyze": "Upload & Analyze",
        "document": "Document",
        "upload_files": "Upload PDF, DOCX, TXT, JPG, PNG (≤200 MB)",
        "load_sample": "📝 Load sample",
        "sample_tip": "Use sample if you don't have a file handy.",
        "analysis_summary": "📑 Analysis Summary",
        "ask_questions": "💬 Ask Questions About This Document",
        "ask_question_doc": "Ask a question about the document…",
        "general_help": "🧭 General",
        "help": "Help",
        "ask_general": "Ask any general questions about",
        "ask_question_general": "Ask any",
        "question": "question…",
        "disclaimer": "⚠️ **Disclaimer:**",
        "disclaimer_text": "is an AI tool and may make mistakes. Always consult a qualified",
        "disclaimer_end": "professional for critical matters.",
        "language": "🌍 Language",
        "sector": "📊 Sector",
        "extracting": "Extracting text…",
        "generating": "Generating analysis…",
        "thinking": "Thinking...",
        "no_text": "No readable text found in the uploaded file."
    },
    "हिंदी": {
        "select_language": "🌍 अपनी भाषा चुनें",
        "choose_language": "जारी रखने के लिए अपनी पसंदीदा भाषा चुनें",
        "choose_sector": "अपना क्षेत्र चुनें",
        "selected_language": "चयनित भाषा",
        "legal_docs": "कानूनी दस्तावेज़ और परामर्श",
        "medical_reports": "चिकित्सा रिपोर्ट और विश्लेषण",
        "agro_reports": "कृषि रिपोर्ट और मार्गदर्शन",
        "back_language": "← भाषा चयन पर वापस जाएं",
        "settings": "⚙️ सेटिंग्स",
        "change_lang_sector": "🔄 भाषा/क्षेत्र बदलें",
        "current": "वर्तमान",
        "upload_analyze": "अपलोड और विश्लेषण करें",
        "document": "दस्तावेज़",
        "upload_files": "PDF, DOCX, TXT, JPG, PNG अपलोड करें (≤200 MB)",
        "load_sample": "📝 नमूना लोड करें",
        "sample_tip": "यदि आपके पास फ़ाइल नहीं है तो नमूना उपयोग करें।",
        "analysis_summary": "📑 विश्लेषण सारांश",
        "ask_questions": "💬 इस दस्तावेज़ के बारे में प्रश्न पूछें",
        "ask_question_doc": "दस्तावेज़ के बारे में प्रश्न पूछें…",
        "general_help": "🧭 सामान्य",
        "help": "सहायता",
        "ask_general": "के बारे में कोई भी सामान्य प्रश्न पूछें",
        "ask_question_general": "कोई भी",
        "question": "प्रश्न पूछें…",
        "disclaimer": "⚠️ **अस्वीकरण:**",
        "disclaimer_text": "एक AI उपकरण है और गलतियाँ हो सकती हैं। हमेशा योग्य",
        "disclaimer_end": "पेशेवर से महत्वपूर्ण मामलों के लिए सलाह लें।",
        "language": "🌍 भाषा",
        "sector": "📊 क्षेत्र",
        "extracting": "टेक्स्ट निकाला जा रहा है…",
        "generating": "विश्लेषण तैयार किया जा रहा है…",
        "thinking": "सोच रहे हैं...",
        "no_text": "अपलोड की गई फ़ाइल में कोई पठनीय टेक्स्ट नहीं मिला।"
    },
    "తెలుగు": {
        "select_language": "🌍 మీ భాషను ఎంచుకోండి",
        "choose_language": "కొనసాగించడానికి మీ ప్రాధాన్య భాషను ఎంచుకోండి",
        "choose_sector": "మీ రంగాన్ని ఎంచుకోండి",
        "selected_language": "ఎంచుకున్న భాష",
        "legal_docs": "చట్టపరమైన పత్రాలు & సలహా",
        "medical_reports": "వైద్య నివేదికలు & విశ్లేషణ",
        "agro_reports": "వ్యవసాయ నివేదికలు & మార్గదర్శకత్వం",
        "back_language": "← భాష ఎంపికకు తిరిగి వెళ్ళు",
        "settings": "⚙️ సెట్టింగ్‌లు",
        "change_lang_sector": "🔄 భాష/రంగం మార్చు",
        "current": "ప్రస్తుత",
        "upload_analyze": "అప్‌లోడ్ & విశ్లేషించు",
        "document": "పత్రం",
        "upload_files": "PDF, DOCX, TXT, JPG, PNG అప్‌లోడ్ చేయండి (≤200 MB)",
        "load_sample": "📝 నమూనా లోడ్ చేయండి",
        "sample_tip": "మీ వద్ద ఫైల్ లేకపోతే నమూనాను ఉపయోగించండి.",
        "analysis_summary": "📑 విశ్లేషణ సారాంశం",
        "ask_questions": "💬 ఈ పత్రం గురించి ప్రశ్నలు అడగండి",
        "ask_question_doc": "పత్రం గురించి ప్రశ్న అడగండి…",
        "general_help": "🧭 సాధారణ",
        "help": "సహాయం",
        "ask_general": "గురించి ఏవైనా సాధారణ ప్రశ్నలు అడగండి",
        "ask_question_general": "ఏదైనా",
        "question": "ప్రశ్న అడగండి…",
        "disclaimer": "⚠️ **నిరాకరణ:**",
        "disclaimer_text": "ఒక AI సాధనం మరియు తప్పులు జరుగవచ్చు. ఎల్లప్పుడూ అర్హత కలిగిన",
        "disclaimer_end": "నిపుణుడిని కీలక విషయాల కోసం సంప్రదించండి।",
        "language": "🌍 భాష",
        "sector": "📊 రంగం",
        "extracting": "టెక్స్ట్ వెలికితీస్తున్నాం…",
        "generating": "విశ్లేషణ రూపొందిస్తున్నాం…",
        "thinking": "ఆలోచిస్తున్నాం...",
        "no_text": "అప్‌లోడ్ చేసిన ఫైల్‌లో చదవగలిగే టెక్స్ట్ కనుగొనబడలేదు."
    },
    "اردو": {
        "select_language": "🌍 اپنی زبان منتخب کریں",
        "choose_language": "جاری رکھنے کے لیے اپنی پسندیدہ زبان منتخب کریں",
        "choose_sector": "اپنا شعبہ منتخب کریں",
        "selected_language": "منتخب کردہ زبان",
        "legal_docs": "قانونی دستاویزات اور مشاورت",
        "medical_reports": "طبی رپورٹس اور تجزیہ",
        "agro_reports": "زرعی رپورٹس اور رہنمائی",
        "back_language": "← زبان کے انتخاب پر واپس جائیں",
        "settings": "⚙️ ترتیبات",
        "change_lang_sector": "🔄 زبان/شعبہ تبدیل کریں",
        "current": "موجودہ",
        "upload_analyze": "اپ لوڈ اور تجزیہ کریں",
        "document": "دستاویز",
        "upload_files": "PDF, DOCX, TXT, JPG, PNG اپ لوڈ کریں (≤200 MB)",
        "load_sample": "📝 نمونہ لوڈ کریں",
        "sample_tip": "اگر آپ کے پاس فائل نہیں ہے تو نمونہ استعمال کریں۔",
        "analysis_summary": "📑 تجزیہ خلاصہ",
        "ask_questions": "💬 اس دستاویز کے بارے میں سوالات پوچھیں",
        "ask_question_doc": "دستاویز کے بارے میں سوال پوچھیں…",
        "general_help": "🧭 عام",
        "help": "مدد",
        "ask_general": "کے بارے میں کوئی بھی عام سوالات پوچھیں",
        "ask_question_general": "کوئی بھی",
        "question": "سوال پوچھیں…",
        "disclaimer": "⚠️ **دستبرداری:**",
        "disclaimer_text": "ایک AI ٹول ہے اور غلطیاں ہو سکتی ہیں۔ ہمیشہ اہل",
        "disclaimer_end": "پیشہ ور سے اہم معاملات کے لیے مشورہ لیں۔",
        "language": "🌍 زبان",
        "sector": "📊 شعبہ",
        "extracting": "ٹیکسٹ نکالا جا رہا ہے…",
        "generating": "تجزیہ تیار کیا جا رہا ہے…",
        "thinking": "سوچ رہے ہیں...",
        "no_text": "اپ لوڈ شدہ فائل میں پڑھنے کے قابل ٹیکسٹ نہیں ملا۔"
    }
}

def get_text(key):
    """Get translated text based on selected language"""
    lang = st.session_state.get("selected_language", "English")
    return UI_TRANSLATIONS.get(lang, UI_TRANSLATIONS["English"]).get(key, key)

def pick_language(user_text: str) -> str:
    pref = st.session_state.get("selected_language", "English")
    return pref

def pick_tts_code(lang_name: str) -> str:
    return LANG_CODE_MAP_TTS.get(lang_name, "en")

def pick_ocr_code() -> str:
    pref = st.session_state.get("selected_language", "English")
    return LANG_CODE_MAP_OCR.get(pref, "eng")

# ────────────────────────────────────────────────
# AI FUNCTIONS (UPDATED FOR SECTOR RESTRICTION)
# ────────────────────────────────────────────────
def get_sector_prompt(sector, mode="summary"):
    prompts = {
        "Law": {
            "summary": "You are LawLens ⚖️, a legal document explainer. ONLY analyze legal documents, contracts, agreements, laws, regulations, court cases, and legal matters.",
            "chat": "You are LawLens ⚖️, a legal assistant. ONLY answer questions about legal documents, legal terms, laws, regulations, and legal procedures.",
            "general": "You are LawLens ⚖️, a legal guide. ONLY provide legal information, legal advice, law explanations, legal procedures, and legal guidance."
        },
        "Medical": {
            "summary": "You are MedLens 🏥, a medical document explainer. ONLY analyze medical reports, test results, prescriptions, medical records, health documents, and medical matters.",
            "chat": "You are MedLens 🏥, a medical assistant. ONLY answer questions about medical documents, medical terminology, health conditions, treatments, and medical procedures.",
            "general": "You are MedLens 🏥, a medical guide. ONLY provide medical information, health advice, medical explanations, disease information, and health guidance."
        },
        "Agriculture": {
            "summary": "You are AgroLens 🌾, an agricultural document explainer. ONLY analyze agricultural reports, soil tests, crop data, farming documents, weather reports, and agricultural matters.",
            "chat": "You are AgroLens 🌾, an agricultural assistant. ONLY answer questions about farming documents, agricultural terms, crops, soil, weather, and farming procedures.",
            "general": "You are AgroLens 🌾, an agricultural guide. ONLY provide farming information, agricultural advice, crop guidance, soil management, and farming techniques."
        }
    }
    return prompts.get(sector, prompts["Law"]).get(mode, prompts["Law"]["summary"])

def ask_ai(document_text=None, query=None, mode="summary"):
    sector = st.session_state.selected_sector
    language = st.session_state.selected_language
    
    # Check for critical medical keywords across all sectors
    critical_medical_keywords = [
        # English
        "emergency", "urgent", "critical", "severe", "chest pain", "heart attack", 
        "stroke", "bleeding", "unconscious", "poisoning", "overdose", "suicide",
        "difficulty breathing", "allergic reaction", "seizure", "trauma", "fracture",
        "high fever", "blood pressure", "diabetes", "insulin", "medication error",
        "swelling", "rash", "infection", "wound", "burn", "accident", "injury",
        
        # Hindi
        "आपातकाल", "तत्काल", "गंभीर", "सीने में दर्द", "दिल का दौरा", "खून बहना",
        "बेहोश", "जहर", "सांस लेने में कठिनाई", "एलर्जी", "बुखार", "रक्तचाप", "मधुमेह",
        "सूजन", "संक्रमण", "घाव", "जलना", "चोट",
        
        # Telugu
        "అత్యవసర", "తక్షణ", "తీవ్రమైన", "ఛాతీ నొప్పి", "గుండెపోటు", "రక్తస్రావం",
        "అపస్మారక", "విషం", "శ్వాస తీసుకోవడంలో ఇబ్బంది", "అలెర్జీ", "జ్వరం", "రక్తపోటు",
        "మధుమేహం", "వాపు", "ఇన్ఫెక్షన్", "గాయం", "కాలిన గాయం", "దెబ్బ",
        
        # Urdu
        "ہنگامی", "فوری", "شدید", "سینے میں درد", "دل کا دورہ", "خون بہنا",
        "بے ہوش", "زہر", "سانس لینے میں دشواری", "الرجی", "بخار", "بلڈ پریشر",
        "ذیابیطس", "سوجن", "انفیکشن", "زخم", "جلنا", "چوٹ"
    ]
    
    # Check if query contains critical medical terms
    is_medical_emergency = False
    if query:
        query_lower = query.lower()
        is_medical_emergency = any(keyword.lower() in query_lower for keyword in critical_medical_keywords)
    
    # If it's a medical emergency, override sector restrictions
    if is_medical_emergency and sector != "Medical":
        emergency_prompt = f"""
        🚨 MEDICAL EMERGENCY OVERRIDE 🚨
        
        You are now temporarily acting as MedLens 🏥 because this appears to be a critical medical query that could involve immediate harm.
        
        RESPOND IMMEDIATELY in {language} with:
        1. **EMERGENCY WARNING**: If this is a life-threatening situation, contact emergency services immediately
        2. **BASIC GUIDANCE**: Provide essential first aid or immediate steps
        3. **SEEK PROFESSIONAL HELP**: Strongly advise to consult medical professionals
        4. **DISCLAIMER**: Emphasize this is emergency guidance only, not professional medical advice
        
        User's critical medical query: {query}
        Document context (if any): {document_text or "No document provided"}
        
        Respond with urgency and care, prioritizing user safety.
        """
        
        response = model.generate_content(
            emergency_prompt,
            generation_config={
                "temperature": 0.3,  # Lower temperature for more precise emergency response
                "max_output_tokens": 1000
            }
        )
        
        # Add emergency warning header
        emergency_response = f"""
        🚨 **MEDICAL EMERGENCY RESPONSE** 🚨
        *(Sector restriction overridden for potential medical emergency)*
        
        {response.text}
        
        ⚠️ **CRITICAL**: If this is a life-threatening emergency, contact emergency services (108/102 in India, 911 in US, etc.) IMMEDIATELY.
        """
        
        return emergency_response
    
    # Regular sector-specific responses
    if sector != "Medical":
        sector_restriction = f"""
        CRITICAL: You MUST only provide {sector.lower()}-related information. 
        - If the user asks about other topics (law, medicine, agriculture) outside your {sector.lower()} specialty, respond: "मुझे खुशी होगी कि मैं केवल {sector.lower()} से संबंधित प्रश्नों का उत्तर दे सकूं। कृपया अन्य विषयों के लिए उपयुक्त सेक्शन में जाएं।" (in the selected language)
        - REFUSE to answer non-{sector.lower()} questions completely.
        - Stay strictly within {sector.lower()} domain.
        - EXCEPTION: If you detect a potential medical emergency, you may provide basic safety guidance.
        """
    else:
        sector_restriction = f"You are in the Medical sector. Provide comprehensive medical guidance and information."
    
    lang_clause = f"Respond ONLY in {language}. All text, labels, headings, and content must be completely in {language}. Do not mix languages."
    base_prompt = get_sector_prompt(sector, mode)
    
    if mode == "summary":
        prompt = f"""{base_prompt}
{lang_clause}
{sector_restriction}

Analyze this {sector.lower()} document in {language}:
- Provide summary completely in {language}
- Key findings/obligations in {language} 
- Important dates/recommendations in {language}
- Risk factors/indicators in {language}
- All headings and labels in {language}

Document:
{document_text}
"""
    elif mode == "chat":
        prompt = f"""{base_prompt}
{lang_clause}
{sector_restriction}

Document context:
{document_text}

User question: {query}

IMPORTANT: 
1. Only answer if this question is related to {sector.lower()}
2. If not related to {sector.lower()}, respond in {language}: "I can only help with {sector.lower()}-related questions about your document."
3. Answer completely in {language}
4. EXCEPTION: For potential medical emergencies, provide basic safety guidance regardless of sector.
"""
    else:
        prompt = f"""{base_prompt}
{lang_clause}
{sector_restriction}

User question: {query}

IMPORTANT: 
1. Only answer {sector.lower()}-related questions
2. If question is about other topics, respond in {language}: "I specialize only in {sector.lower()}. Please switch to the appropriate sector for other topics."
3. Provide answer completely in {language}
4. EXCEPTION: For potential medical emergencies, provide basic safety guidance regardless of sector.
"""

    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": 0.7,
            "max_output_tokens": 800
        }
    )
    return response.text

# ────────────────────────────────────────────────
# TTS FUNCTIONS
# ────────────────────────────────────────────────
def clean_text(text: str) -> str:
    emoji_pattern = re.compile(
        "["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF"
        u"\U0001F1E0-\U0001F1FF"
        u"\U00002700-\U000027BF"
        u"\U0001F900-\U0001F9FF"
        u"\U00002600-\U000026FF"
        u"\U00002B00-\U00002BFF"
        "]+", flags=re.UNICODE
    )
    text = emoji_pattern.sub(r'', text)
    text = re.sub(r'(\*\*|__|\*|_|#+)', '', text)
    return text.strip()

def tts_speak_toggle(text: str, lang_name: str):
    safe_text = clean_text(text)
    lang_code = pick_tts_code(lang_name)
    
    try:
        tts = gTTS(text=safe_text, lang=lang_code, slow=False)
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        st.audio(audio_buffer.getvalue(), format='audio/mp3')
    except Exception as e:
        st.error(f"TTS generation failed: {e}")

# ────────────────────────────────────────────────
# OCR FUNCTIONS
# ────────────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=3600)
def ocr_image_bytes(img_bytes: bytes, lang_code: str) -> str:
    try:
        img = Image.open(io.BytesIO(img_bytes))
        txt = pytesseract.image_to_string(img, lang=lang_code).strip()
        return txt
    except Exception as e:
        return f"__OCR_ERROR__ {e}"

def preprocess_pil(img: Image.Image) -> Image.Image:
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img

# ────────────────────────────────────────────────
# TEXT EXTRACTION FUNCTIONS
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
        images = pdf2image.convert_from_bytes(uploaded_file.read(), dpi=300, first_page=1, last_page=10)
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
# LANGUAGE SELECTION PAGE
# ────────────────────────────────────────────────
def show_language_selection():
    st.markdown("<h1 style='text-align: center; color: #1f77b4;'>🌍 Select Your Language</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 18px; margin-bottom: 40px;'>Choose your preferred language to continue</p>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button(f"{LANGUAGES['English']} English", key="eng", use_container_width=True, help="Select English"):
            st.session_state.selected_language = "English"
            st.session_state.language_selected = True
            st.rerun()
            
        if st.button(f"{LANGUAGES['తెలుగు']} తెలుగు", key="tel", use_container_width=True, help="Select Telugu"):
            st.session_state.selected_language = "తెలుగు"
            st.session_state.language_selected = True
            st.rerun()
    
    with col2:
        if st.button(f"{LANGUAGES['हिंदी']} हिंदी", key="hin", use_container_width=True, help="Select Hindi"):
            st.session_state.selected_language = "हिंदी"
            st.session_state.language_selected = True
            st.rerun()
            
        if st.button(f"{LANGUAGES['اردو']} اردو", key="urd", use_container_width=True, help="Select Urdu"):
            st.session_state.selected_language = "اردو"
            st.session_state.language_selected = True
            st.rerun()

# ────────────────────────────────────────────────
# SECTOR SELECTION PAGE
# ────────────────────────────────────────────────
def show_sector_selection():
    st.markdown(f"<h1 style='text-align: center; color: #1f77b4;'>{get_text('choose_sector')}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; font-size: 18px; margin-bottom: 40px;'>{get_text('selected_language')}: {LANGUAGES[st.session_state.selected_language]} {st.session_state.selected_language}</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("<div style='text-align: center; font-size: 64px; margin: 20px 0;'>⚖️</div>", unsafe_allow_html=True)
        if st.button("Law", key="law_btn", use_container_width=True, help="Legal document analysis"):
            st.session_state.selected_sector = "Law"
            st.session_state.sector_selected = True
            st.rerun()
        st.markdown(f"<p style='text-align: center; font-size: 14px; color: #666;'>{get_text('legal_docs')}</p>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("<div style='text-align: center; font-size: 64px; margin: 20px 0;'>🏥</div>", unsafe_allow_html=True)
        if st.button("Medical", key="med_btn", use_container_width=True, help="Medical document analysis"):
            st.session_state.selected_sector = "Medical"
            st.session_state.sector_selected = True
            st.rerun()
        st.markdown(f"<p style='text-align: center; font-size: 14px; color: #666;'>{get_text('medical_reports')}</p>", unsafe_allow_html=True)
    
    with col3:
        st.markdown("<div style='text-align: center; font-size: 64px; margin: 20px 0;'>🌾</div>", unsafe_allow_html=True)
        if st.button("Agriculture", key="agr_btn", use_container_width=True, help="Agricultural document analysis"):
            st.session_state.selected_sector = "Agriculture"
            st.session_state.sector_selected = True
            st.rerun()
        st.markdown(f"<p style='text-align: center; font-size: 14px; color: #666;'>{get_text('agro_reports')}</p>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button(get_text("back_language"), use_container_width=True):
        st.session_state.language_selected = False
        st.session_state.selected_language = ""
        st.rerun()

# ────────────────────────────────────────────────
# MAIN APPLICATION
# ────────────────────────────────────────────────
def show_main_app():
    sector_info = SECTORS[st.session_state.selected_sector]
    st.title(f"{sector_info['emoji']} {st.session_state.selected_sector}Lens – {get_text('upload_analyze')} & Chat")
    
    # Language indicator
    st.info(f"{get_text('language')}: {LANGUAGES[st.session_state.selected_language]} {st.session_state.selected_language} | {get_text('sector')}: {sector_info['emoji']} {st.session_state.selected_sector}")
    
    # Settings in sidebar
    with st.sidebar:
        st.subheader(get_text("settings"))
        if st.button(get_text("change_lang_sector"), use_container_width=True):
            # Reset all states - FIXED
            st.session_state.language_selected = False
            st.session_state.sector_selected = False
            st.session_state.selected_language = ""
            st.session_state.selected_sector = ""
            st.session_state.doc_text = ""
            st.session_state.summary = ""
            st.session_state.chat_history = []        # ✅ Must be list
            st.session_state.general_messages = []    # ✅ Must be list
            st.rerun()
        
        st.markdown("---")
        st.caption(f"{get_text('current')}: {st.session_state.selected_language} → {st.session_state.selected_sector}")
    
    # Main tabs
    tab_doc, tab_gen = st.tabs([f"📄 {st.session_state.selected_sector} {get_text('upload_analyze')}", f"{get_text('general_help')} {st.session_state.selected_sector} {get_text('help')}"])
    
    with tab_doc:
        st.header(f"📄 {get_text('upload_analyze')} {st.session_state.selected_sector} {get_text('document')}")
        up = st.file_uploader(
            get_text("upload_files"),
            type=["pdf", "docx", "txt", "jpg", "jpeg", "png"]
        )
        
        # Sample button
        colA, colB = st.columns(2)
        with colA:
            sample_btn = st.button(f"{get_text('load_sample')} {st.session_state.selected_sector.lower()} {get_text('document')}")
        with colB:
            st.caption(get_text("sample_tip"))
        
        # Sample text based on sector
        if sample_btn and not up:
            samples = {
                "Law": "Service Agreement between Alpha Pvt Ltd and Beta Traders. Parties agree to monthly deliveries by the 5th. Late delivery incurs 2% of invoice per week. Either party may terminate with 30 days notice. Disputes: Hyderabad jurisdiction.",
                "Medical": "Patient: John Doe. Blood Pressure: 140/90 mmHg (elevated). Glucose: 180 mg/dL (high). Cholesterol: 250 mg/dL. Recommendation: Start antihypertensive medication. Follow low-sodium diet. Recheck in 4 weeks.",
                "Agriculture": "Soil Report - Field A: pH 6.8, Nitrogen 45 ppm (low), Phosphorus 25 ppm (adequate), Potassium 180 ppm (high). Crop: Wheat. Recommendation: Apply 120 kg/ha Urea. Expected yield: 4.2 tons/ha. Next soil test: 6 months."
            }
            st.session_state.doc_text = samples[st.session_state.selected_sector]
            with st.spinner(get_text("generating")):
                st.session_state.summary = ask_ai(document_text=st.session_state.doc_text, mode="summary")
        
        if up:
            with st.spinner(get_text("extracting")):
                text = extract_text(up)
            if text:
                st.session_state.doc_text = text
                with st.spinner(get_text("generating")):
                    st.session_state.summary = ask_ai(document_text=text, mode="summary")
            else:
                st.warning(get_text("no_text"))
        
        if st.session_state.summary:
            st.subheader(get_text("analysis_summary"))
            st.write(st.session_state.summary)
            tts_speak_toggle(st.session_state.summary, st.session_state.selected_language)
            
            st.divider()
            st.subheader(get_text("ask_questions"))
            
            # Chat history
            for m in st.session_state.chat_history:
                with st.chat_message(m["role"]):
                    st.markdown(m["content"])
                    if m["role"] == "assistant":
                        tts_speak_toggle(m["content"], st.session_state.selected_language)
            
            # Chat input
            q = st.chat_input(get_text("ask_question_doc"))
            if q:
                st.session_state.chat_history.append({"role": "user", "content": q})
                with st.spinner(get_text("thinking")):
                    ans = ask_ai(document_text=st.session_state.doc_text, query=q, mode="chat")
                st.session_state.chat_history.append({"role": "assistant", "content": ans})
                st.rerun()
    
    with tab_gen:
        st.header(f"{get_text('general_help')} {st.session_state.selected_sector} {get_text('help')}")
        st.caption(f"{get_text('ask_general')} {st.session_state.selected_sector.lower()}")
        
        # General chat history
        for m in st.session_state.general_messages:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])
                if m["role"] == "assistant":
                    tts_speak_toggle(m["content"], st.session_state.selected_language)
        
        # General chat input
        q2 = st.chat_input(f"{get_text('ask_question_general')} {st.session_state.selected_sector.lower()} {get_text('question')}")
        if q2:
            st.session_state.general_messages.append({"role": "user", "content": q2})
            with st.spinner(get_text("thinking")):
                ans2 = ask_ai(query=q2, mode="general")
            st.session_state.general_messages.append({"role": "assistant", "content": ans2})
            st.rerun()
    
    # Disclaimer
    st.markdown(f"""---
{get_text("disclaimer")} {st.session_state.selected_sector}Lens {get_text("disclaimer_text")} {st.session_state.selected_sector.lower()} {get_text("disclaimer_end")}
""")

# ────────────────────────────────────────────────
# MAIN APP LOGIC
# ────────────────────────────────────────────────
def main():
    if not st.session_state.language_selected:
        show_language_selection()
    elif not st.session_state.sector_selected:
        show_sector_selection()
    else:
        show_main_app()

if __name__ == "__main__":
    main()
