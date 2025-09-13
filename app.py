# -------------------------------------------------
# Multi-Sector Document Analysis App (Enhanced UI, Readable Text)
# -------------------------------------------------
import os, io, re, time, html, hashlib, base64
from dotenv import load_dotenv
load_dotenv()
import time
import base64
import streamlit as st
import PyPDF2, docx
from PIL import Image
import pytesseract
from langdetect import detect
import google.generativeai as genai
from gtts import gTTS
# -------------------------------------------------
# 2-second splash gate (now with Base64 image encoding for reliability and
#                        corrected size)
# -------------------------------------------------
import base64


# -------------------------------------------------
# API / Models
# -------------------------------------------------
API_KEY = os.getenv("GEMINI_KEY", "")
genai.configure(api_key=API_KEY)
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
model = genai.GenerativeModel(MODEL_NAME)
vision_model = genai.GenerativeModel(MODEL_NAME)

# -------------------------------------------------
# App Config (wide layout looks better with new UI)
# -------------------------------------------------
st.set_page_config(
    page_title="Document Analysis Hub",
    page_icon="🔍",
    layout="wide"
)

# -------------------------------------------------
# State Defaults
# -------------------------------------------------
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
    "last_user_input": "",
    "_render_flag": False
}
for k, v in DEFAULT_STATE.items():
    st.session_state.setdefault(k, v)

# -------------------------------------------------
# Languages / Sectors
# -------------------------------------------------
LANGUAGES = {
    "English": "🇺🇸",
    "हिंदी": "🇮🇳",
    "తెలుగు": "🇮🇳",
    "اردو": "🇵🇰",
    "മലയാളം": "🇮🇳"
}
SECTORS = {
    "Law": {"emoji": "⚖️", "symbol": "§"},
    "Medical": {"emoji": "🏥", "symbol": "+"},
    "Agriculture": {"emoji": "🌾", "symbol": "🚜"},
    "Credit": {"emoji": "💳", "symbol": "₹"}  
}


LANG_CODE_MAP_TTS = {
    "English": "en", "हिंदी": "hi", "తెలుగు": "te", "اردو": "ur", "മലയാളം": "ml"
}
LANG_CODE_MAP_OCR = {
    "English": "eng", "हिंदी": "hin", "తెలుగు": "tel", "اردو": "urd", "മലയാളം": "mal"
}

SECTOR_LABELS = {
    "English": {
        "Law": "Law",
        "Medical": "Medical",
        "Agriculture": "Agriculture",
        "Credilens": "Credilens"
    },
    "हिंदी": {
        "Law": "कानून",
        "Medical": "चिकित्सा",
        "Agriculture": "कृषि",
        "Credilens": "क्रेडिलेंस"
    },
    "తెలుగు": {
        "Law": "చట్టం",
        "Medical": "వైద్యం",
        "Agriculture": "వ్యవసాయం",
        "Credilens": "క్రెడిలెన్స్"
    },
    "اردو": {
        "Law": "قانون",
        "Medical": "طبی",
        "Agriculture": "زراعت",
        "Credilens": "کریڈیلینس"
    },
    "മലയാളം": {
        "Law": "നിയമം",
        "Medical": "വൈദ്യശാസ്ത്രം",
        "Agriculture": "കൃഷി",
        "Credilens": "ക്രെഡിലൻസ്"
    },
}

def sector_label(name: str) -> str:
    lang = st.session_state.get("selected_language", "English")
    return SECTOR_LABELS.get(lang, SECTOR_LABELS["English"]).get(name, name)

# -------------------------------------------------
# UI Translations (keys used throughout the app)
# -------------------------------------------------
UI_TRANSLATIONS = {
    "English": {
        "select_language": "🌍 Select Your Language",
        "choose_language": "Choose your preferred language to continue",
        "choose_sector": "Choose Your Sector",
        "selected_language": "Selected Language",
        "back_language": "← Back to Language Selection",
        "settings": "⚙️ Settings",
        "change_lang_sector": "🔄 Change Language/Sector",
        "current": "Current",
        "uploader_any": "Upload ANY file type (📄 Documents + 🖼️ Images)",
        "sample_doc_btn": "📝 Load sample {sector} document",
        "sample_try": "Try sample data if there is no file ready",
        "extracting": "Extracting text…",
        "generating": "Generating analysis…",
        "thinking": "Thinking...",
        "no_text": "No readable text found in the uploaded file.",
        "analyzing_image": "🔍 Analyzing image...",
        "image_analysis_header": "🖼️ Image Analysis",
        "uploaded_image_caption": "Uploaded {sector} Image",
        "extracting_image_text": "Extracting text from image...",
        "enhanced_title_suffix": " Lens – Enhanced AI Analysis",

        # === Info per sector ===
        "info_law": "🌍 Language: {lang_flag} {lang} | ⚖️ Sector: All Document Types Analysis",
        "info_medical": "🌍 Language: {lang_flag} {lang} | 🏥 Sector: Medical Analysis + Emergency Help + Image Diagnosis",
        "info_agri": "🌍 Language: {lang_flag} {lang} | 🌾 Sector: Agricultural Analysis + Crop Image Recognition",
        "info_credilens": "🌍 Language: {lang_flag} {lang} | 💳 Sector: Credit & Finance Analysis",

        # === Tabs ===
        "tab_doc": "📄 Enhanced {sector} Analysis",
        "tab_gen": "🧭 General {sector} Help",

        # === Headers ===
        "enhanced_analysis_header": "📊 Enhanced {sector} Analysis",
        "chat_about_analysis": "💬 Ask Questions About This Analysis",
        "chat_placeholder": "Ask any question about this analysis...",
        "examples_try": "Try asking:",
        "gen_help_header": "🧭 General {sector} Help & Consultation",
        "gen_help_caption": "Ask any {sector_lower}-related questions — here to help!",
        "gen_chat_placeholder": "Ask any {sector_lower} question...",
        "examples_caption": "Example questions:",

        # === Features ===
        "enhanced_features_title": "🚀 Features:",
        "features_med_1": "🚨 Emergency medical response",
        "features_med_2": "🖼️ Medical image analysis",
        "features_med_3": "🩺 Injury/disease detection",
        "features_agri_1": "🌱 Crop disease detection",
        "features_agri_2": "🐛 Pest identification",
        "features_agri_3": "📊 Soil analysis from images",
        "features_law_1": "📄 ALL document types",
        "features_law_2": "⚖️ Legal analysis",
        "features_law_3": "🔍 Comprehensive review",
        "features_credit_1": "💰 Credit risk assessment",
        "features_credit_2": "📊 Loan eligibility analysis",
        "features_credit_3": "🏦 Financial document review",

        # === Disclaimers ===
        "disclaimer_block_header": "⚠️ Disclaimer:",
        "disclaimer_med": "- Medical: For emergencies, call 108/102 (India)",
        "disclaimer_law": "- Legal: Consult qualified legal professionals for important matters",
        "disclaimer_agri": "- Agricultural: Recommendations are general—consider local conditions",
        "disclaimer_credilens": "- Finance: Analysis is AI-generated. Verify with certified financial experts",
        "disclaimer_footer": "- Always verify critical information with qualified professionals",

        # === Misc ===
        "document": "Document",
        "analysis_summary": "📑 Analysis Summary"
    },
    "हिंदी": {
    "select_language": "🌍 अपनी भाषा चुनें",
    "choose_language": "जारी रखने के लिए अपनी पसंदीदा भाषा चुनें",
    "choose_sector": "अपना क्षेत्र चुनें",
    "selected_language": "चयनित भाषा",
    "back_language": "← भाषा चयन पर वापस",
    "settings": "⚙️ सेटिंग्स",
    "change_lang_sector": "🔄 भाषा/क्षेत्र बदलें",
    "current": "वर्तमान",
    "uploader_any": "किसी भी फ़ाइल प्रकार को अपलोड करें (📄 दस्तावेज़ + 🖼️ छवियाँ)",
    "sample_doc_btn": "📝 नमूना {sector} दस्तावेज़ लोड करें",
    "sample_try": "यदि फ़ाइल तैयार नहीं है तो नमूना आज़माएँ",
    "extracting": "पाठ निकाला जा रहा है…",
    "generating": "विश्लेषण बनाया जा रहा है…",
    "thinking": "सोच रहा है...",
    "no_text": "अपलोड की गई फ़ाइल में पढ़ने योग्य पाठ नहीं मिला।",
    "analyzing_image": "🔍 छवि का विश्लेषण हो रहा है...",
    "image_analysis_header": "🖼️ छवि विश्लेषण",
    "uploaded_image_caption": "अपलोड की गई {sector} छवि",
    "extracting_image_text": "छवि से पाठ निकाला जा रहा है...",
    "enhanced_title_suffix": " लेंस – उन्नत AI विश्लेषण",

    "info_law": "🌍 भाषा: {lang_flag} {lang} | ⚖️ क्षेत्र: सभी दस्तावेज़ प्रकार विश्लेषण",
    "info_medical": "🌍 भाषा: {lang_flag} {lang} | 🏥 क्षेत्र: चिकित्सा विश्लेषण + आपातकालीन सहायता + छवि निदान",
    "info_agri": "🌍 भाषा: {lang_flag} {lang} | 🌾 क्षेत्र: कृषि विश्लेषण + फसल छवि पहचान",
    "info_credilens": "🌍 भाषा: {lang_flag} {lang} | 💳 क्षेत्र: क्रेडिट विश्लेषण + धोखाधड़ी पहचान + वित्तीय रिपोर्टिंग",

    "tab_doc": "📄 उन्नत {sector} विश्लेषण",
    "tab_gen": "🧭 सामान्य {sector} सहायता",
    "enhanced_analysis_header": "📊 उन्नत {sector} विश्लेषण",
    "chat_about_analysis": "💬 इस विश्लेषण के बारे में प्रश्न पूछें",
    "chat_placeholder": "इस विश्लेषण के बारे में कोई भी प्रश्न पूछें...",
    "examples_try": "कोशिश करें पूछने की:",
    "gen_help_header": "🧭 सामान्य {sector} सहायता और परामर्श",
    "gen_help_caption": "किसी भी {sector_lower}-संबंधित प्रश्न पूछें — मदद के लिए तैयार!",
    "gen_chat_placeholder": "कोई भी {sector_lower} प्रश्न पूछें...",
    "examples_caption": "उदाहरण प्रश्न:",

    "enhanced_features_title": "🚀 विशेषताएँ:",
    "features_med_1": "🚨 आपातकालीन चिकित्सा प्रतिक्रिया",
    "features_med_2": "🖼️ चिकित्सा छवि विश्लेषण",
    "features_med_3": "🩺 चोट/रोग पहचान",
    "features_agri_1": "🌱 फसल रोग पहचान",
    "features_agri_2": "🐛 कीट पहचान",
    "features_agri_3": "📊 छवियों से मिट्टी विश्लेषण",
    "features_law_1": "📄 सभी दस्तावेज़ प्रकार",
    "features_law_2": "⚖️ कानूनी विश्लेषण",
    "features_law_3": "🔍 व्यापक समीक्षा",
    "features_credit_1": "💳 क्रेडिट रिपोर्ट विश्लेषण",
    "features_credit_2": "⚠️ धोखाधड़ी और जोखिम पहचान",
    "features_credit_3": "📊 वित्तीय रिपोर्टिंग और परामर्श",

    "disclaimer_block_header": "⚠️ अस्वीकरण:",
    "disclaimer_med": "- चिकित्सा: आपातस्थिति में 108/102 कॉल करें (भारत)",
    "disclaimer_law": "- कानूनी: महत्वपूर्ण मामलों में योग्य विधि विशेषज्ञ से परामर्श करें",
    "disclaimer_agri": "- कृषि: सिफारिशें सामान्य हैं—स्थानीय परिस्थितियों पर विचार करें",
    "disclaimer_credilens": "- क्रेडिट/वित्तीय: किसी भी निर्णय से पहले योग्य वित्तीय सलाहकार से परामर्श करें",
    "disclaimer_footer": "- महत्वपूर्ण जानकारी को हमेशा योग्य विशेषज्ञों से सत्यापित करें",

    "document": "दस्तावेज़",
    "analysis_summary": "📑 विश्लेषण सारांश"
  },
    "తెలుగు": {
    "select_language": "🌍 మీ భాషను ఎంచుకోండి",
    "choose_language": "కొనసాగేందుకు మీకు నచ్చిన భాషను ఎంచుకోండి",
    "choose_sector": "మీ విభాగాన్ని ఎంచుకోండి",
    "selected_language": "ఎంచుకున్న భాష",
    "back_language": "← భాష ఎంపికకు వెనక్కి",
    "settings": "⚙️ అమరికలు",
    "change_lang_sector": "🔄 భాష/విభాగం మార్చండి",
    "current": "ప్రస్తుతము",
    "uploader_any": "ఏ ఫైల్ రకమైనా అప్లోడ్ చేయండి (📄 పత్రాలు + 🖼️ చిత్రాలు)",
    "sample_doc_btn": "📝 నమూనా {sector} పత్రాన్ని లోడ్ చేయండి",
    "sample_try": "ఫైళ్లు సిద్ధంగా లేకపోతే నమూనా ప్రయత్నించండి",
    "extracting": "పాఠ్యాన్ని వెలికితీస్తున్నాం…",
    "generating": "విశ్లేషణను సృష్టిస్తున్నాం…",
    "thinking": "ఆలోచిస్తున్నాను...",
    "no_text": "ఈ ఫైల్‌లో చదవగలిగే పాఠ్యం కనిపించలేదు.",
    "analyzing_image": "🔍 చిత్రాన్ని విశ్లేషిస్తున్నాం...",
    "image_analysis_header": "🖼️ చిత్రం విశ్లేషణ",
    "uploaded_image_caption": "అప్లోడ్ చేసిన {sector} చిత్రం",
    "extracting_image_text": "చిత్రం నుండి పాఠ్యాన్ని వెలికితీస్తున్నాం...",
    "enhanced_title_suffix": " లెన్స్ – అధునాతన AI విశ్లేషణ",

    "info_law": "🌍 భాష: {lang_flag} {lang} | ⚖️ విభాగం: అన్ని పత్రాల విశ్లేషణ",
    "info_medical": "🌍 భాష: {lang_flag} {lang} | 🏥 విభాగం: వైద్య విశ్లేషణ + అత్యవసర సహాయం + చిత్రం నిర్ధారణ",
    "info_agri": "🌍 భాష: {lang_flag} {lang} | 🌾 విభాగం: వ్యవసాయ విశ్లేషణ + పంట చిత్రం గుర్తింపు",
    "info_credilens": "🌍 భాష: {lang_flag} {lang} | 💳 విభాగం: క్రెడిట్ విశ్లేషణ + మోసం గుర్తింపు + ఆర్థిక నివేదికలు",

    "tab_doc": "📄 అధునాతన {sector} విశ్లేషణ",
    "tab_gen": "🧭 సాధారణ {sector} సహాయం",
    "enhanced_analysis_header": "📊 అధునాతన {sector} విశ్లేషణ",
    "chat_about_analysis": "💬 ఈ విశ్లేషణ గురించి ప్రశ్నలు అడగండి",
    "chat_placeholder": "ఈ విశ్లేషణ గురించి ఏదైనా ప్రశ్న అడగండి...",
    "examples_try": "ఇలా అడగండి:",
    "gen_help_header": "🧭 సాధారణ {sector} సహాయం & సలహా",
    "gen_help_caption": "ఏదైనా {sector_lower} సంబంధిత ప్రశ్నలు అడగండి — సహాయం కోసం సిద్ధంగా ఉన్నాము!",
    "gen_chat_placeholder": "ఏదైనా {sector_lower} ప్రశ్న అడగండి...",
    "examples_caption": "ఉదాహరణ ప్రశ్నలు:",

    "enhanced_features_title": "🚀 లక్షణాలు:",
    "features_med_1": "🚨 అత్యవసర వైద్య స్పందన",
    "features_med_2": "🖼️ వైద్య చిత్రం విశ్లేషణ",
    "features_med_3": "🩺 గాయం/వ్యాధి గుర్తింపు",
    "features_agri_1": "🌱 పంట రోగాల గుర్తింపు",
    "features_agri_2": "🐛 కీటకాలను గుర్తించడం",
    "features_agri_3": "📊 చిత్రాల నుండి మట్టి విశ్లేషణ",
    "features_law_1": "📄 అన్ని పత్రాల రకాలు",
    "features_law_2": "⚖️ చట్ట విశ్లేషణ",
    "features_law_3": "🔍 సమగ్ర సమీక్ష",
    "features_credit_1": "💳 క్రెడిట్ రిపోర్ట్ విశ్లేషణ",
    "features_credit_2": "⚠️ మోసపూరిత లావాదేవీల గుర్తింపు",
    "features_credit_3": "📊 ఆర్థిక నివేదికలు మరియు సలహా",

    "disclaimer_block_header": "⚠️ గమనిక:",
    "disclaimer_med": "- వైద్యం: అత్యవసరానికి 108/102 కాల్ చేయండి (భారతదేశం)",
    "disclaimer_law": "- చట్టం: ముఖ్య విషయాలకు న్యాయ నిపుణులను సంప్రదించండి",
    "disclaimer_agri": "- వ్యవసాయం: సిఫారసులు సాధారణం — స్థానిక పరిస్థితులను పరిగణించండి",
    "disclaimer_credilens": "- క్రెడిట్/ఫైనాన్స్: ఏ నిర్ణయం తీసుకునే ముందు ఆర్థిక నిపుణులను సంప్రదించండి",
    "disclaimer_footer": "- ముఖ్య సమాచారాన్ని ఎల్లప్పుడూ అర్హులైన నిపుణులతో ధృవీకరించండి",

    "document": "పత్రం",
    "analysis_summary": "📑 విశ్లేషణ సారాంశం"
},
    "اردو": {
    "select_language": "🌍 اپنی زبان منتخب کریں",
    "choose_language": "جاری رکھنے کے لیے اپنی پسند کی زبان منتخب کریں",
    "choose_sector": "اپنا شعبہ منتخب کریں",
    "selected_language": "منتخب کردہ زبان",
    "back_language": "← زبان کے انتخاب پر واپس جائیں",
    "settings": "⚙️ ترتیبات",
    "change_lang_sector": "🔄 زبان/شعبہ تبدیل کریں",
    "current": "موجودہ",
    "uploader_any": "کسی بھی فائل کی قسم اپ لوڈ کریں (📄 دستاویزات + 🖼️ تصاویر)",
    "sample_doc_btn": "📝 نمونہ {sector} دستاویز لوڈ کریں",
    "sample_try": "اگر فائل دستیاب نہیں ہے تو نمونہ آزمائیں",
    "extracting": "متن نکالا جا رہا ہے…",
    "generating": "تجزیہ تیار کیا جا رہا ہے…",
    "thinking": "سوچا جا رہا ہے...",
    "no_text": "اپ لوڈ کی گئی فائل میں پڑھنے کے قابل متن نہیں ملا۔",
    "analyzing_image": "🔍 تصویر کا تجزیہ ہو رہا ہے...",
    "image_analysis_header": "🖼️ تصویر کا تجزیہ",
    "uploaded_image_caption": "اپ لوڈ کی گئی {sector} تصویر",
    "extracting_image_text": "تصویر سے متن نکالا جا رہا ہے...",
    "enhanced_title_suffix": " لینس – جدید AI تجزیہ",

    "info_law": "🌍 زبان: {lang_flag} {lang} | ⚖️ شعبہ: تمام دستاویزی اقسام کا تجزیہ",
    "info_medical": "🌍 زبان: {lang_flag} {lang} | 🏥 شعبہ: طبی تجزیہ + ہنگامی مدد + تصویر کی تشخیص",
    "info_agri": "🌍 زبان: {lang_flag} {lang} | 🌾 شعبہ: زرعی تجزیہ + فصل کی تصویر کی شناخت",
    "info_ct": "🌍 زبان: {lang_flag} {lang} | 💳 شعبہ: کریڈٹ تجزیہ + دھوکہ دہی کی شناخت + مالی رپورٹنگ",

    "tab_doc": "📄 جدید {sector} تجزیہ",
    "tab_gen": "🧭 عمومی {sector} مدد",
    "enhanced_analysis_header": "📊 جدید {sector} تجزیہ",
    "chat_about_analysis": "💬 اس تجزیہ کے بارے میں سوالات پوچھیں",
    "chat_placeholder": "اس تجزیہ کے بارے میں کوئی بھی سوال پوچھیں...",
    "examples_try": "پوچھ کر دیکھیں:",
    "gen_help_header": "🧭 عمومی {sector} مدد اور مشاورت",
    "gen_help_caption": "کسی بھی {sector_lower} سے متعلق سوالات پوچھیں — مدد کے لیے موجود!",
    "gen_chat_placeholder": "کوئی بھی {sector_lower} سوال پوچھیں...",
    "examples_caption": "مثالی سوالات:",

    "enhanced_features_title": "🚀 جدید خصوصیات:",
    "features_med_1": "🚨 ہنگامی طبی ردِعمل",
    "features_med_2": "🖼️ طبی تصویر کا تجزیہ",
    "features_med_3": "🩺 چوٹ/بیماری کی شناخت",
    "features_agri_1": "🌱 فصل کی بیماری کی شناخت",
    "features_agri_2": "🐛 کیڑوں کی شناخت",
    "features_agri_3": "📊 تصاویر سے مٹی کا تجزیہ",
    "features_law_1": "📄 تمام دستاویزاتی اقسام",
    "features_law_2": "⚖️ قانونی تجزیہ",
    "features_law_3": "🔍 جامع جائزہ",
    "features_credit_1": "💳 کریڈٹ رپورٹ تجزیہ",
    "features_credit_2": "⚠️ دھوکہ دہی اور رسک کی شناخت",
    "features_credit_3": "📊 مالی رپورٹنگ اور مشاورت",

    "disclaimer_block_header": "⚠️ انتباہ:",
    "disclaimer_med": "- طبی: ہنگامی صورت میں 108/102 پر کال کریں (بھارت)",
    "disclaimer_law": "- قانونی: اہم معاملات میں مستند قانونی ماہر سے رجوع کریں",
    "disclaimer_agri": "- زرعی: سفارشات عمومی ہیں — مقامی حالات کو مدنظر رکھیں",
    "disclaimer_credit": "- کریڈٹ/مالی: کسی بھی فیصلے سے پہلے مستند مالی مشیر سے رجوع کریں",
    "disclaimer_footer": "- اہم معلومات ہمیشہ مستند ماہرین سے تصدیق کریں",

    "document": "دستاویز",
    "analysis_summary": "📑 تجزیہ کا خلاصہ"
},
    "മലയാളം": {
        "select_language": "🌍 ഭാഷ തിരഞ്ഞെടുക്കുക",
        "choose_language": "തുടരാൻ ഇഷ്ടമുള്ള ഭാഷ തിരഞ്ഞെടുക്കുക",
        "choose_sector": "വിഭാഗം തിരഞ്ഞെടുക്കുക",
        "selected_language": "തിരഞ്ഞെടുത്ത ഭാഷ",
        "back_language": "← ഭാഷ തിരഞ്ഞെടുപ്പിലേക്ക് മടങ്ങുക",
        "settings": "⚙️ ക്രമീകരണങ്ങൾ",
        "change_lang_sector": "🔄 ഭാഷ/വിഭാഗം മാറ്റുക",
        "current": "നിലവിൽ",
        "uploader_any": "ഏത് ഫയൽ തരം വേണമെങ്കിലും അപ്‌ലോഡ് ചെയ്യുക (📄 രേഖകൾ + 🖼️ ചിത്രങ്ങൾ)",
        "sample_doc_btn": "📝 സാമ്പിൾ {sector} രേഖ ലോഡ് ചെയ്യുക",
        "sample_try": "ഫയൽ ഇല്ലെങ്കിൽ സാമ്പിൾ പരീക്ഷിക്കുക",
        "extracting": "ടെക്സ്റ്റ് എടുത്തുകൊണ്ടിരിക്കുന്നു…",
        "generating": "വിശകലനം സൃഷ്ടിക്കുന്നു…",
        "thinking": "ചിന്തിക്കുന്നു...",
        "no_text": "അപ്‌ലോഡ് ചെയ്ത ഫയലിൽ വായിക്കാൻ പറ്റുന്ന ടെക്സ്റ്റ് കണ്ടെത്താനായില്ല.",
        "analyzing_image": "🔍 ചിത്രം വിശകലനം ചെയ്യുന്നു...",
        "image_analysis_header": "🖼️ ചിത്രം വിശകലനം",
        "uploaded_image_caption": "അപ്‌ലോഡ് ചെയ്ത {sector} ചിത്രം",
        "extracting_image_text": "ചിത്രത്തിൽ നിന്ന് ടെക്സ്റ്റ് എടുത്തുകൊണ്ടിരിക്കുന്നു...",
        "enhanced_title_suffix": " ലെൻസ് – ഉയർന്ന നിലവാരമുള്ള AI വിശകലനം",

        "info_law": "🌍 ഭാഷ: {lang_flag} {lang} | ⚖️ വിഭാഗം: എല്ലാ രേഖകളുടെയും വിശകലനം",
        "info_medical": "🌍 ഭാഷ: {lang_flag} {lang} | 🏥 വിഭാഗം: മെഡിക്കൽ വിശകലനം + അടിയന്തര സഹായം + ചിത്രം നിർണയം",
        "info_agri": "🌍 ഭാഷ: {lang_flag} {lang} | 🌾 വിഭാഗം: കാർഷിക വിശകലനം + വിള ചിത്ര തിരിച്ചറിയൽ",
        "info_credit": "🌍 ഭാഷ: {lang_flag} {lang} | 💳 വിഭാഗം: സാമ്പത്തിക വിശകലനം + ക്രെഡിറ്റ് റിപ്പോർട്ട് + അപകട മൂല്യനിർണയം",

        "tab_doc": "📄 ഉയർന്ന നിലവാരമുള്ള {sector} വിശകലനം",
        "tab_gen": "🧭 പൊതുവായ {sector} സഹായം",
        "enhanced_analysis_header": "📊 ഉയർന്ന നിലവാരമുള്ള {sector} വിശകലനം",

        "chat_about_analysis": "💬 ഈ വിശകലനത്തെ കുറിച്ച് ചോദ്യങ്ങൾ ചോദിക്കുക",
        "chat_placeholder": "ഈ വിശകലനത്തെ കുറിച്ച് ഏതെങ്കിലും ചോദ്യമുണ്ടോ...",
        "examples_try": "ഇങ്ങനെ ചോദിക്കുക:",

        "gen_help_header": "🧭 പൊതുവായ {sector} സഹായവും നിർദേശവും",
        "gen_help_caption": "{sector_lower} സംബന്ധമായ ഏതെങ്കിലും ചോദ്യങ്ങൾ ചോദിക്കുക — സഹായത്തിനായി തയ്യാറാണ്!",
        "gen_chat_placeholder": "ഏതെങ്കിലും {sector_lower} ചോദ്യം ചോദിക്കുക...",
        "examples_caption": "ഉദാഹരണ ചോദ്യങ്ങൾ:",

        "enhanced_features_title": "🚀 വിശേഷഗുണങ്ങൾ:",
        "features_med_1": "🚨 അടിയന്തിര മെഡിക്കൽ പ്രതികരണം",
        "features_med_2": "🖼️ മെഡിക്കൽ ചിത്ര വിശകലനം",
        "features_med_3": "🩺 പരിക്ക്/രോഗം തിരിച്ചറിയൽ",

        "features_agri_1": "🌱 വിള രോഗം തിരിച്ചറിയൽ",
        "features_agri_2": "🐛 കീടം തിരിച്ചറിയൽ",
        "features_agri_3": "📊 ചിത്രങ്ങളിൽ നിന്ന് മണ്ണ് വിശകലനം",

        "features_law_1": "📄 എല്ലാ രേഖാ തരം",
        "features_law_2": "⚖️ നിയമ വിശകലനം",
        "features_law_3": "🔍 സമഗ്ര അവലോകനം",

        "features_credit_1": "💳 ക്രെഡിറ്റ് സ്കോർ വിശകലനം",
        "features_credit_2": "📊 വായ്പ/കടം അപകട മൂല്യനിർണയം",
        "features_credit_3": "🔍 സാമ്പത്തിക രേഖാ പരിശോധന",

        "disclaimer_block_header": "⚠️ അറിയിപ്പ്:",
        "disclaimer_med": "- മെഡിക്കൽ: അടിയന്തിരാവസ്ഥയിൽ 108/102 വിളിക്കൂ (ഇന്ത്യ)",
        "disclaimer_law": "- നിയമം: പ്രധാന കാര്യങ്ങൾക്ക് യോഗ്യനായ നിയമ വിദഗ്ധനോട് ചേക്കൂറുക",
        "disclaimer_agri": "- കാർഷികം: നിർദേശങ്ങൾ പൊതുവായതാണ് — പ്രാദേശിക സാഹചര്യങ്ങൾ പരിഗണിക്കുക",
        "disclaimer_credit": "- സാമ്പത്തികം: പ്രധാന സാമ്പത്തിക തീരുമാനങ്ങൾക്ക് അംഗീകൃത വിദഗ്ധരെ ആശ്രയിക്കുക",
        "disclaimer_footer": "- പ്രധാന വിവരങ്ങൾ എപ്പോഴും യോഗ്യനായ വിദഗ്ധരുമായി സ്ഥിരീകരിക്കുക",

        "document": "രേഖ",
        "analysis_summary": "📑 വിശകലന സംഗ്രഹം"
    },

}

def get_text(key: str) -> str:
    lang = st.session_state.get("selected_language", "English")
    return UI_TRANSLATIONS.get(lang, UI_TRANSLATIONS["English"]).get(key, UI_TRANSLATIONS["English"].get(key, key))

def pick_tts_code(lang_name: str) -> str:
    return LANG_CODE_MAP_TTS.get(lang_name, "en")

def pick_ocr_code() -> str:
    pref = st.session_state.get("selected_language", "English")
    return LANG_CODE_MAP_OCR.get(pref, "eng")

# -------------------------------------------------
# Sector-aware Color Palettes + Accessible, Colorful CSS
# -------------------------------------------------
PALETTES = {
    "Law": {
        "brand": "#7C3AED", 
        "brand2": "#75AED7", 
        "bg1": "#EDE9FE", 
        "bg2": "#CFFAFE"
    },
    "Medical": {
        "brand": "#10B981", 
        "brand2": "#06B6D4", 
        "bg1": "#D1FAE5", 
        "bg2": "#60CCD5"
    },
    "Agriculture": {
        "brand": "#16A34A", 
        "brand2": "#F59E0B", 
        "bg1": "#DCFCE7", 
        "bg2": "#FEF3C7"
    },
    "Credit": {   # 💳 CrediLens sector
        "brand": "#4261A2",   # strong financial blue
        "brand2": "#9333EA",  # secondary purple
        "bg1": "#DBEAFE",     # light blue background
        "bg2": "#E9D5FF"      # light purple background
    }
}

active_sector = st.session_state.get("selected_sector", "Law")
pal = PALETTES.get(active_sector, PALETTES["Law"])

# Accessible, high-contrast CSS (UI-only)
st.markdown(f"""
<style>
/* Force readable light scheme and strong foreground */
html {{ color-scheme: light; }}
:root {{
  --brand: {pal["brand"]};
  --brand-2: {pal["brand2"]};
  --bg-grad-1: {pal["bg1"]};
  --bg-grad-2: {pal["bg2"]};
  --text: #0F172A;              /* Dark slate for high contrast */
  --text-weak: #334155;
  --surface: #ffffff;
  --border: #E5E7EB;
}}
/* Background stays colorful but subtle */
.stApp {{
  background:
    radial-gradient(1200px 600px at 10% 0%, var(--bg-grad-1), transparent 60%),
    radial-gradient(1000px 500px at 100% 10%, var(--bg-grad-2), transparent 60%),
    linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
}}
/* GLOBAL TYPOGRAPHY: remove transparent gradient text and ensure solid color */
html, body, [class*="css"] {{
  font-family: "Inter","Poppins","Noto Sans","Noto Sans Telugu","Noto Sans Devanagari","Noto Sans Malayalam",
               system-ui,-apple-system,Segoe UI,Roboto,"Helvetica Neue",Arial,"Noto Color Emoji","Apple Color Emoji","Segoe UI Emoji",sans-serif !important;
  color: var(--text);
}}
h1, h2, h3, h4, h5, h6 {{
  color: var(--text) !important;     /* critical: readable headings */
  font-weight: 700;
  letter-spacing: -0.01em;
  text-shadow: none;
}}
/* Optional: subtle underline accent instead of gradient-filled text */
.h-accent {{ position: relative; }}
.h-accent:after {{
  content: "";
  position: absolute; left: 0; bottom: -6px; height: 4px; width: 80px;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--brand), var(--brand-2));
}}
/* BUTTONS: keep vibrant gradients */
div.stButton > button {{
  background: linear-gradient(135deg, var(--brand), var(--brand-2));
  color: #fff !important;
  border: none; border-radius: 14px;
  padding: 0.9rem 1.1rem;
  box-shadow: 0 8px 24px rgba(0,0,0,.12);
  transition: transform .15s ease, box-shadow .15s ease, filter .2s ease;
}}
div.stButton > button:hover {{
  transform: translateY(-1px);
  box-shadow: 0 12px 30px rgba(0,0,0,.18);
  filter: brightness(1.03);
}}
/* TABS: readable default + white on selected */
.stTabs [role="tablist"] {{ gap: 8px; }}
.stTabs [role="tablist"] button {{
  background: #fff; color: var(--text);
  border-radius: 12px; border: 1px solid var(--border);
  padding: .6rem 1rem;
}}
.stTabs [role="tab"][aria-selected="true"] {{
  background: linear-gradient(135deg, var(--brand), var(--brand-2));
  color: #fff !important; border-color: transparent !important;
}}
/* INFO/WARNING banners: high-contrast text on soft surface */
.stAlert > div {{
  background: #ffffff;          /* solid surface for legibility */
  border-left: 6px solid var(--brand);
  border-radius: 12px;
  color: var(--text) !important;
}}
/* FILE UPLOADER: lighten the dropzone and labels */
[data-testid="stFileUploader"] > section {{
  background: #FFFFFF; border: 1px dashed var(--border) !important;
  border-radius: 14px;
}}
[data-testid="stFileUploader"] * {{ color: var(--text) !important; }}
/* TEXT INPUTS / AREAS: clear borders and readable placeholders */
.stTextInput > div > div input,
.stTextArea > div > textarea {{
  color: var(--text) !important;
  border-radius: 12px; border: 1px solid var(--border);
  transition: border-color .2s ease, box-shadow .2s ease;
}}
.stTextInput > div > div input::placeholder,
.stTextArea > div > textarea::placeholder {{ color: var(--text-weak) !important; opacity: 1; }}
.stTextInput > div > div input:focus,
.stTextArea > div > textarea:focus {{
  border-color: var(--brand);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--brand) 25%, transparent);
}}
/* IMAGES/CARDS: soft elevation */
img {{ border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,.08); }}
.kpi-card {{
  padding: 1rem 1.25rem; background: #ffffff;
  border: 1px solid var(--border); border-radius: 14px;
  box-shadow: 0 10px 24px rgba(0,0,0,.05);
}}
/* BADGES/CHIPS */
.badge {{
  display: inline-block; padding: .25rem .6rem; border-radius: 999px;
  color: #fff; background: linear-gradient(135deg, var(--brand), var(--brand-2));
  font-size: .8rem;
}}
/* Separate sections subtly */
.hr-soft {{ margin: .8rem 0 1rem 0; border: none; height: 1px;
  background: linear-gradient(90deg, transparent, #e5e7eb, transparent); }}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# OCR / Tesseract
# -------------------------------------------------
pytesseract.pytesseract.tesseract_cmd = os.getenv(
    "TESSERACT_PATH",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

# -------------------------------------------------
# AI Helpers
# -------------------------------------------------
def analyze_image_with_ai(image_bytes: bytes, sector: str, language: str, query: str | None = None) -> str:
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    image_part = {"mime_type": "image/jpeg", "data": image_base64}
    if sector == "Medical":
        if query and any(k in (query or "").lower() for k in ["emergency","urgent","injury","bleeding","pain","burn","wound"]):
            prompt = f"""
🚨 MEDICAL IMAGE ANALYSIS - EMERGENCY MODE 🚨
Respond immediately in {language} with:
1) Emergency assessment 2) Visual observations 3) Immediate actions 4) Emergency services 5) First aid 6) When to seek care
User query: {query or "Analyze this medical image"}
"""
        else:
            prompt = f"You are MedLens. Analyze this medical image in {language}: observations, possible conditions, actions, and when to seek help."
    elif sector == "Agriculture":
        prompt = f"You are AgroLens. Analyze this agricultural image in {language}: identification, problems, solutions, and prevention."
    else:
        prompt = f"You are LawLens. Analyze this legal document image in {language}: doc type, key elements/clauses, and next steps."
    try:
        response = vision_model.generate_content([prompt, image_part])
        return response.text
    except Exception as e:
        return f"Error analyzing image: {str(e)}"

def get_sector_prompt(sector: str, mode: str = "summary") -> str:
    prompts = {
        "Law": {
            "summary": "You are LawLens ⚖️, a legal document explainer. Analyze ALL types of documents.",
            "chat": "You are LawLens ⚖️, a legal assistant. Answer questions about ANY documents and legal matters.",
            "general": "You are LawLens ⚖️, a legal guide. Provide legal information and procedures."
        },
        "Medical": {
            "summary": "You are MedLens 🏥, a medical document explainer. ONLY analyze medical documents.",
            "chat": "You are MedLens 🏥, a medical assistant. ONLY answer medical questions.",
            "general": "You are MedLens 🏥, a medical guide. ONLY provide medical information."
        },
        "Agriculture": {
            "summary": "You are AgroLens 🌾, an agricultural document explainer. ONLY analyze agricultural documents.",
            "chat": "You are AgroLens 🌾, an agricultural assistant. ONLY answer agriculture questions.",
            "general": "You are AgroLens 🌾, an agricultural guide. ONLY provide farming information."
        },
        "Credit": {  # 💳 CrediLens sector
            "summary": "You are CrediLens 💳, a financial/credit document explainer. ONLY analyze finance and credit-related documents.",
            "chat": "You are CrediLens 💳, a financial assistant. ONLY answer questions about loans, credit, banking, and finance.",
            "general": "You are CrediLens 💳, a finance guide. Provide financial literacy, credit tips, and money management information."
        }
    }
    return prompts.get(sector, prompts["Law"]).get(mode, prompts["Law"]["summary"])


def ask_ai(document_text: str | None = None, query: str | None = None, mode: str = "summary", image_bytes: bytes | None = None) -> str:
    sector = st.session_state.selected_sector
    language = st.session_state.selected_language

    # ✅ Always fall back to stored doc_text
    if not document_text:
        document_text = st.session_state.get("doc_text", "")

    if image_bytes:
        return analyze_image_with_ai(image_bytes, sector, language, query)

    critical_medical_keywords = [
        "emergency","urgent","critical","severe","chest pain","heart attack","stroke","bleeding","unconscious",
        "poisoning","overdose","suicide","difficulty breathing","allergic reaction","seizure","trauma","fracture",
        "high fever","blood pressure","diabetes","insulin","medication error","swelling","rash","infection","wound",
        "burn","accident","injury","broken bone","cut","deep wound","heavy bleeding","choking","anaphylaxis","cardiac",
        "respiratory","faint"
    ]
    is_medical_emergency = any(k in (query or "").lower() for k in critical_medical_keywords)

    if is_medical_emergency:
        emergency_prompt = f"""
🚨 MEDICAL EMERGENCY OVERRIDE 🚨
Respond in {language} with warning, basic guidance, when to seek help, and disclaimer.
User query: {query}
Document context: {document_text or "No document provided"}
"""
        response = model.generate_content(emergency_prompt, generation_config={"temperature": 0.3, "max_output_tokens": 1000})
        return f"🚨 MEDICAL EMERGENCY RESPONSE 🚨\n{response.text}\n\n⚠️ If life-threatening, contact emergency services (108/102 in India, 911 in US) immediately."

    if sector == "Law":
        sector_restriction = "You are in the Law sector. You can analyze and help with ANY type of document needing legal review."
    elif sector != "Medical":
        sector_restriction = f"CRITICAL: Provide only {sector.lower()}-related information."
    else:
        sector_restriction = "Provide comprehensive medical guidance and information."

    lang_clause = f"Respond ONLY in {language}."
    base_prompt = get_sector_prompt(sector, mode)

    if mode == "summary":
        prompt = f"""{base_prompt}
{lang_clause}
{sector_restriction}
Analyze this document in {language}:
- Summary
- Key findings/obligations
- Important dates/recommendations
- Risks
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
"""
    else:
        prompt = f"""{base_prompt}
{lang_clause}
{sector_restriction}
User question: {query}
"""
    response = model.generate_content(prompt, generation_config={"temperature": 0.7, "max_output_tokens": 800})
    return response.text

# -------------------------------------------------
# TTS
# -------------------------------------------------
def clean_text(text: str) -> str:
    emoji_pattern = re.compile(
        "[" +
        u"\U0001F600-\U0001F64F" +
        u"\U0001F300-\U0001F5FF" +
        u"\U0001F680-\U0001F6FF" +
        u"\U0001F1E0-\U0001F1FF" +
        u"\U00002700-\U000027BF" +
        u"\U0001F900-\U0001F9FF" +
        u"\U00002600-\U000026FF" +
        u"\U00002B00-\U00002BFF" +
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

# -------------------------------------------------
# OCR
# -------------------------------------------------
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

# -------------------------------------------------
# Extraction
# -------------------------------------------------
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
    st.error(get_text("no_text"))
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

# -------------------------------------------------
# Examples
# -------------------------------------------------
EXAMPLE_DOC_Q = {
    "Law": {
        "English": ["Is this contract valid?", "What are my rights?", "What should I be careful about?"],
        "हिंदी": ["क्या यह अनुबंध वैध है?", "मेरे अधिकार क्या हैं?", "मुझे किस बात का ध्यान रखना चाहिए?"],
        "తెలుగు": ["ఈ ఒప్పందం చెల్లుబాటుగా ఉందా?", "నా హక్కులు ఏమిటి?", "నేను ఏ విషయాల్లో జాగ్రత్తగా ఉండాలి?"],
        "اردو": ["کیا یہ معاہدہ درست ہے؟", "میرے حقوق کیا ہیں؟", "مجھے کن باتوں کا خیال رکھنا چاہیے؟"],
        "മലയാളം": ["ഈ കരാർ സാധുവാണോ?", "എന്റെ അവകാശങ്ങൾ എന്തൊക്കെ?", "എന്തിൽ ജാഗ്രത വേണം?"],
    },
    "Medical": {
        "English": ["Is this an emergency?", "What treatment is recommended?", "How serious is this condition?"],
        "हिंदी": ["क्या यह आपातस्थिति है?", "कौन-सा उपचार सुझाव है?", "यह स्थिति कितनी गंभीर है?"],
        "తెలుగు": ["ఇది అత్యవసరమా?", "ఏ చికిత్సను సూచిస్తారు?", "ఈ పరిస్థితి ఎంత తీవ్రం?"],
        "اردو": ["کیا یہ ایمرجنسی ہے؟", "کون سا علاج تجویز ہے؟", "یہ حالت کتنی سنگین ہے؟"],
        "മലയാളം": ["ഇത് അടിയന്തരാവസ്ഥയാണോ?", "ഏത് ചികിത്സയാണ് ശുപാർശ?", "ഈ അവസ്ഥ എത്ര ഗൗരവമാണെന്?"],
    },
    "Agriculture": {
        "English": ["What disease is this?", "How do I treat this crop issue?", "When should I harvest?"],
        "हिंदी": ["यह कौन-सी बीमारी है?", "इस फसल समस्या का इलाज कैसे करें?", "कटाई कब करनी चाहिए?"],
        "తెలుగు": ["ఇది ఏ వ్యాధి?", "ఈ పంట సమస్యను ఎలా పరిష్కరించాలి?", "పంటను ఎప్పుడు కోయాలి?"],
        "اردو": ["یہ کون سی بیماری ہے؟", "اس فصل کے مسئلے کا علاج کیسے پہچانیں؟", "کٹائی کب کروں؟"],
        "മലയാളം": ["ഇത് ഏത് രോഗമാണ്?", "ഈ വിള പ്രശ്നം എങ്ങനെ പരിഹരിക്കാം?", "എപ്പോൾ കൊയ്ത്ത് നടത്തണം?"],
    },
    "Credit": {  # 💳 CrediLens sector
        "English": ["What is my credit score?", "Is this loan agreement safe?", "How do I reduce debt faster?"],
        "हिंदी": ["मेरा क्रेडिट स्कोर क्या है?", "क्या यह ऋण अनुबंध सुरक्षित है?", "मैं कर्ज जल्दी कैसे घटा सकता हूँ?"],
        "తెలుగు": ["నా క్రెడిట్ స్కోర్ ఎంత?", "ఈ రుణ ఒప్పందం సురక్షితమా?", "నేను అప్పును వేగంగా ఎలా తగ్గించగలను?"],
        "اردو": ["میرا کریڈٹ اسکور کیا ہے؟", "کیا یہ قرض کا معاہدہ محفوظ ہے؟", "میں قرض جلدی کیسے کم کروں؟"],
        "മലയാളം": ["എന്റെ ക്രെഡിറ്റ് സ്കോർ എന്താണ്?", "ഈ വായ്പാ കരാർ സുരക്ഷിതമാണോ?", "ഞാൻ കടം വേഗത്തിൽ എങ്ങനെ കുറയ്ക്കാം?"],
    }
}

EXAMPLE_GEN_Q = {
    "Law": {
        "English": ["What makes a contract valid?", "Tenant rights in India?", "Breaking a lease early—implications?"],
        "हिंदी": ["एक अनुबंध वैध कैसे होता है?", "भारत में किरायेदार के अधिकार?", "लीज पहले तोड़ने पर प्रभाव?"],
        "తెలుగు": ["ఒప్పందం చెల్లుబాటు కావడానికి ఏమి అవసరం?", "భారతదేశంలో కిరాయిదారు హక్కులు?", "లీజ్‌ను ముందే రద్దు చేస్తే ఏమవుతుంది?"],
        "اردو": ["کن چیزوں سے معاہدہ درست ہوتا ہے؟", "بھارت میں کرایہ دار کے حقوق؟", "لیز جلد ختم کرنے کے اثرات؟"],
        "മലയാളം": ["ഒരു കരാർ സാധുവാകാൻ എന്താണ് ആവശ്യം?", "ഇന്ത്യയിലെ കിറായക്കാർക്ക് അവകാശങ്ങൾ?", "ലീസ് നേരത്തെ റദ്ദാക്കൽ—ഫലങ്ങൾ?"],
    },
    "Medical": {
        "English": ["I have chest pain—what should I do?", "BP is 150/95; is this dangerous?", "I burned my hand—first aid?"],
        "हिंदी": ["सीने में दर्द है—क्या करूं?", "BP 150/95 है; क्या यह खतरनाक है?", "हाथ जल गया—प्राथमिक उपचार?"],
        "తెలుగు": ["నాకు ఛాతి నొప్పి—ఏం చేయాలి?", "రక్తపోటు 150/95—ఇది ప్రమాదకరమా?", "చేతి కాలింది—ఫస్ట్ ఎయిడ్?"],
        "اردو": ["سینے میں درد ہے—کیا کروں؟", "BP 150/95 ہے؛ کیا یہ خطرناک है؟", "ہاتھ جل گیا—ابتدائی طبی امداد؟"],
        "മലയാളം": ["എനിക്ക് നെഞ്ചുവേദന—എന്ത് ചെയ്യണം?", "BP 150/95—ഇത് അപകടമാണോ?", "കൈ ചുട്ടുപോയി—ഫസ്റ്റ് എയ്ഡ്?"],
    },
    "Agriculture": {
        "English": ["Tomato leaves are yellow—cause?", "How to identify pest damage?", "Best time to plant corn?"],
        "हिंदी": ["टमाटर के पत्ते पीले—कारण?", "कीट नुकसान कैसे पहचानें?", "मक्का बोने का सही समय?"],
        "తెలుగు": ["టమోటా ఆకులు పసుపు—కారణం?", "కీటకాల నష్టం ఎలా గుర్తించాలి?", "మొక్కజొన్న ఎప్పుడు నాటాలి?"],
        "اردو": ["یہ کون سی بیماری ہے؟", "کیڑوں کا نقصان کیسے پہچانیں?", "مکئی کب لگائیں؟"],
        "മലയാളം": ["തക്കാളി ഇലകൾ മഞ്ഞ—കാരണം?", "കീടനാശം എങ്ങനെ തിരിച്ചറിയാം?", "മക്ക ചോളം വിതയ്ക്കാൻ മികച്ച സമയം?"],
    },
    "Credit": {  # 💳 CrediLens sector
        "English": ["How to improve my credit score?", "Is taking multiple loans risky?", "Best way to manage EMI payments?"],
        "हिंदी": ["क्रेडिट स्कोर कैसे बढ़ाऊं?", "क्या कई ऋण लेना जोखिम भरा है?", "ईएमआई भुगतान प्रबंधन का सबसे अच्छा तरीका?"],
        "తెలుగు": ["క్రెడిట్ స్కోర్‌ను ఎలా మెరుగుపరుచుకోవాలి?", "అనేక రుణాలు తీసుకోవడం ప్రమాదకరమా?", "EMI చెల్లింపులను నిర్వహించడానికి ఉత్తమ మార్గం ఏంటి?"],
        "اردو": ["کریڈٹ اسکور کیسے بہتر کروں؟", "کیا ایک سے زیادہ قرض لینا خطرناک ہے؟", "ای ایم آئی ادائیگی کا بہترین طریقہ کیا ہے؟"],
        "മലയാളം": ["ക്രെഡിറ്റ് സ്കോർ എങ്ങനെ മെച്ചപ്പെടുത്താം?", "ഒരു പിടി വായ്പകൾ എടുക്കുന്നത് അപകടമാണോ?", "EMI പണമടവ് നിയന്ത്രിക്കാൻ മികച്ച വഴി?"],
    }
}


# -------------------------------------------------
# Language Selection
# -------------------------------------------------
def show_language_selection():
    if st.session_state.get('_render_flag', False):
        return
    st.session_state['_render_flag'] = True

    st.markdown(f"<h1 style='text-align:center;'>{get_text('select_language')}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center; font-size:18px; margin-bottom:24px;'>{get_text('choose_language')}</p>", unsafe_allow_html=True)
    st.markdown("<hr class='hr-soft'/>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"{LANGUAGES['English']} English", key="final_eng", use_container_width=True):
            st.session_state.selected_language = "English"; st.session_state.language_selected = True; st.session_state['_render_flag'] = False; st.rerun()
        if st.button(f"{LANGUAGES['తెలుగు']} తెలుగు", key="final_tel", use_container_width=True):
            st.session_state.selected_language = "తెలుగు"; st.session_state.language_selected = True; st.session_state['_render_flag'] = False; st.rerun()
        if st.button(f"{LANGUAGES['മലയാളം']} മലയാളം", key="final_mal", use_container_width=True):
            st.session_state.selected_language = "മലയാളം"; st.session_state.language_selected = True; st.session_state['_render_flag'] = False; st.rerun()
    with col2:
        if st.button(f"{LANGUAGES['हिंदी']} हिंदी", key="final_hin", use_container_width=True):
            st.session_state.selected_language = "हिंदी"; st.session_state.language_selected = True; st.session_state['_render_flag'] = False; st.rerun()
        if st.button(f"{LANGUAGES['اردو']} اردو", key="final_urd", use_container_width=True):
            st.session_state.selected_language = "اردو"; st.session_state.language_selected = True; st.session_state['_render_flag'] = False; st.rerun()

# -------------------------------------------------
# Sector Selection
# -------------------------------------------------
def show_sector_selection():
    st.markdown(f"<h1 style='text-align:center;'>{get_text('choose_sector')}</h1>", unsafe_allow_html=True)
    st.markdown(
        f"<p style='text-align:center; font-size:18px; margin-bottom:20px;'>{get_text('selected_language')}: "
        f"{LANGUAGES[st.session_state.selected_language]} {st.session_state.selected_language}</p>",
        unsafe_allow_html=True
    )
    st.markdown("<hr class='hr-soft'/>", unsafe_allow_html=True)

    # 4 columns instead of 3
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("<div style='text-align:center; font-size:64px; margin: 10px 0;'>⚖️</div>", unsafe_allow_html=True)
        if st.button(sector_label("Law"), key="law_btn", use_container_width=True):
            st.session_state.selected_sector = "Law"; st.session_state.sector_selected = True; st.rerun()
        st.caption(get_text("features_law_1"))

    with col2:
        st.markdown("<div style='text-align:center; font-size:64px; margin: 10px 0;'>🏥</div>", unsafe_allow_html=True)
        if st.button(sector_label("Medical"), key="med_btn", use_container_width=True):
            st.session_state.selected_sector = "Medical"; st.session_state.sector_selected = True; st.rerun()
        st.caption(get_text("features_med_2"))

    with col3:
        st.markdown("<div style='text-align:center; font-size:64px; margin: 10px 0;'>🌾</div>", unsafe_allow_html=True)
        if st.button(sector_label("Agriculture"), key="agr_btn", use_container_width=True):
            st.session_state.selected_sector = "Agriculture"; st.session_state.sector_selected = True; st.rerun()
        st.caption(get_text("features_agri_1"))

    with col4:
        st.markdown("<div style='text-align:center; font-size:64px; margin: 10px 0;'>📊</div>", unsafe_allow_html=True)
        if st.button(sector_label("Credit"), key="cred_btn", use_container_width=True):
            st.session_state.selected_sector = "Credit"; st.session_state.sector_selected = True; st.rerun()
        st.caption(get_text("features_credit_1"))

    st.markdown("<br/>", unsafe_allow_html=True)
    if st.button(get_text("back_language"), use_container_width=True):
        for k in list(st.session_state.keys()):
            if k in DEFAULT_STATE:
                st.session_state[k] = DEFAULT_STATE[k]
        st.session_state['_render_flag'] = False
        st.rerun()
# -------------------------------------------------
# Main App
# -------------------------------------------------
def show_main_app():
    sector_info = SECTORS[st.session_state.selected_sector]
    st.title(f"{sector_info['emoji']} {sector_label(st.session_state.selected_sector)}{get_text('enhanced_title_suffix')}")

    lang = st.session_state.selected_language
    info_map = {
        "Law": get_text("info_law"),
        "Medical": get_text("info_medical"),
        "Agriculture": get_text("info_agri"),
        "Credit": get_text("info_credit")  # ✅ Added CrediLens
    }
    st.info(info_map[st.session_state.selected_sector].format(lang_flag=LANGUAGES[lang], lang=lang))

    # Sidebar
    with st.sidebar:
        st.subheader(get_text("settings"))
        if st.button(get_text("change_lang_sector"), use_container_width=True):
            for k in list(st.session_state.keys()):
                if k in DEFAULT_STATE:
                    st.session_state[k] = DEFAULT_STATE[k]
            st.session_state['_render_flag'] = False
            st.rerun()

        st.markdown("---")
        st.caption(f"{get_text('current')}: {lang} → {sector_label(st.session_state.selected_sector)}")
        st.markdown(f"### {get_text('enhanced_features_title')}")

        if st.session_state.selected_sector == "Medical":
            st.markdown(f"- {get_text('features_med_1')}")
            st.markdown(f"- {get_text('features_med_2')}")
            st.markdown(f"- {get_text('features_med_3')}")
        elif st.session_state.selected_sector == "Agriculture":
            st.markdown(f"- {get_text('features_agri_1')}")
            st.markdown(f"- {get_text('features_agri_2')}")
            st.markdown(f"- {get_text('features_agri_3')}")
        elif st.session_state.selected_sector == "Credit":  # ✅ New Sector
            st.markdown(f"- {get_text('features_credit_1')}")
            st.markdown(f"- {get_text('features_credit_2')}")
            st.markdown(f"- {get_text('features_credit_3')}")
        else:
            st.markdown(f"- {get_text('features_law_1')}")
            st.markdown(f"- {get_text('features_law_2')}")
            st.markdown(f"- {get_text('features_law_3')}")

    tab_doc, tab_gen = st.tabs([
        get_text("tab_doc").format(sector=sector_label(st.session_state.selected_sector)),
        get_text("tab_gen").format(sector=sector_label(st.session_state.selected_sector))
    ])


    # Document/Image Analysis
    with tab_doc:
        st.header(get_text("tab_doc").format(sector=sector_label(st.session_state.selected_sector)))
        with st.container():
            up = st.file_uploader(get_text("uploader_any"),
                                  type=["pdf", "docx", "txt", "jpg", "jpeg", "png"],
                                  help=get_text("uploader_any"))
            st.markdown("<div class='hr-soft'></div>", unsafe_allow_html=True)
            colA, colB = st.columns([1, 2])
            with colA:
                sample_btn = st.button(get_text("sample_doc_btn").format(sector=sector_label(st.session_state.selected_sector)))
            with colB:
                st.caption(get_text("sample_try"))

        if sample_btn and not up:
            samples = {
                "Law": """RENTAL AGREEMENT

Landlord: John Smith
Tenant: Mary Johnson
Property: 123 Main St, Apartment 2B
Rent: $1,200/month
Security Deposit: $1,200
Lease Term: 12 months

Terms:
1. Rent due on 1st of each month
2. Late fee: $50 after 5 days
3. No pets allowed
4. Tenant responsible for utilities
5. 30-day notice required for termination
""",
                "Medical": """MEDICAL REPORT

Patient: John Doe, Age 45

Vital Signs:
- Blood Pressure: 145/92 mmHg (HIGH)
- Heart Rate: 85 bpm
- Temperature: 98.6°F
- Weight: 185 lbs

Lab Results:
- Blood Glucose: 165 mg/dL (HIGH)
- Cholesterol: 240 mg/dL (HIGH)
- HbA1c: 7.2% (ELEVATED)

Diagnosis: Type 2 Diabetes, Hypertension

Recommendations:
1. Start Metformin 500mg twice daily
2. Blood pressure medication
3. Low carb diet
4. Exercise 30 min daily
5. Follow-up in 4 weeks
""",
                "Agriculture": """SOIL ANALYSIS REPORT

Farm: Green Valley Farm, Field Section A
Date: March 20, 2024
Crop: Wheat (Winter Variety)

Soil Test Results:
- pH Level: 6.2 (Slightly Acidic)
- Nitrogen (N): 35 ppm (LOW)
- Phosphorus (P): 18 ppm (ADEQUATE)
- Potassium (K): 165 ppm (HIGH)
- Organic Matter: 2.8%
- Soil Type: Clay Loam

Recommendations:
1. Apply 120 kg/ha Urea (Nitrogen)
2. Add lime to increase pH to 6.5–7.0
3. Expected yield: 4.5 tons/ha
4. Irrigation needed: 400 mm during growing season
5. Next soil test: 6 months
""",
"Credit": """CREDIT REPORT

Name: Jane Williams
DOB: 12/05/1987
PAN: ABCPW1234X
Credit Score: 742 (Good)

Credit Accounts:
- Credit Card: HDFC Bank, Limit ₹2,00,000, Current Balance ₹45,000
- Personal Loan: SBI Bank, ₹3,50,000, EMI ₹10,500/month, On-time
- Home Loan: ICICI Bank, ₹28,00,000, Tenure: 15 years, EMI ₹25,000/month

Payment History:
- Last 24 months: 23 On-time, 1 Delayed (5 days)

Current Status:
- No defaults
- Low credit utilization (22%)

Recommendations:
1. Keep utilization below 30%
2. Avoid multiple new loan applications
3. Maintain consistent EMI payments
"""

            }
            st.session_state.doc_text = samples[st.session_state.selected_sector]
            with st.spinner(get_text("generating")):
                st.session_state.summary = ask_ai(document_text=st.session_state.doc_text, mode="summary")

        if up:
            file_extension = up.name.lower().split(".")[-1]
            if file_extension in ("jpg", "jpeg", "png"):
                st.subheader(get_text("image_analysis_header"))
                image = Image.open(up)
                st.image(image, caption=get_text("uploaded_image_caption").format(sector=sector_label(st.session_state.selected_sector)), use_column_width=True)

                img_byte_array = io.BytesIO()
                image.save(img_byte_array, format='JPEG')
                image_bytes = img_byte_array.getvalue()

                with st.spinner(get_text("analyzing_image")):
                    st.session_state.summary = ask_ai(mode="summary", image_bytes=image_bytes)

                with st.spinner(get_text("extracting_image_text")):
                    ocr_text = extract_text_from_image(up)
                    if ocr_text:
                        st.session_state.doc_text = ocr_text
                        st.subheader(get_text("analysis_summary"))
                        st.text_area(get_text("document"), ocr_text, height=150)
            else:
                with st.spinner(get_text("extracting")):
                    text = extract_text(up)
                if text:
                    st.session_state.doc_text = text
                    with st.spinner(get_text("generating")):
                        st.session_state.summary = ask_ai(document_text=text, mode="summary")
                else:
                    st.warning(get_text("no_text"))

        if st.session_state.summary:
            st.subheader(get_text("enhanced_analysis_header").format(sector=sector_label(st.session_state.selected_sector)))
            st.write(st.session_state.summary)
            tts_speak_toggle(st.session_state.summary, st.session_state.selected_language)

            st.divider()
            st.subheader(get_text("chat_about_analysis"))

            for m in st.session_state.chat_history:
                with st.chat_message(m["role"]):
                    st.markdown(m["content"])
                    if m["role"] == "assistant":
                        tts_speak_toggle(m["content"], st.session_state.selected_language)

            try_examples = EXAMPLE_DOC_Q.get(st.session_state.selected_sector, {}).get(st.session_state.selected_language, [])
            if try_examples:
                st.caption(f"{get_text('examples_try')} {' • '.join(try_examples)}")

            q = st.chat_input(get_text("chat_placeholder"))
            if q:
                st.session_state.chat_history.append({"role": "user", "content": q})
                with st.spinner(get_text("thinking")):
                    ans = ask_ai(document_text=st.session_state.doc_text, query=q, mode="chat", image_bytes=None)
                st.session_state.chat_history.append({"role": "assistant", "content": ans})
                st.rerun()

    # General Q&A
    with tab_gen:
        st.header(get_text("gen_help_header").format(sector=sector_label(st.session_state.selected_sector)))
        st.caption(get_text("gen_help_caption").format(sector_lower=sector_label(st.session_state.selected_sector).lower()))

        for m in st.session_state.general_messages:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])
                if m["role"] == "assistant":
                    tts_speak_toggle(m["content"], st.session_state.selected_language)

        try_examples2 = EXAMPLE_GEN_Q.get(st.session_state.selected_sector, {}).get(st.session_state.selected_language, [])
        if try_examples2:
            st.caption(f"{get_text('examples_caption')} {' • '.join(try_examples2)}")

        q2 = st.chat_input(get_text("gen_chat_placeholder").format(sector_lower=sector_label(st.session_state.selected_sector).lower()))
        if q2:
            st.session_state.general_messages.append({"role": "user", "content": q2})
            with st.spinner(get_text("thinking")):
                ans2 = ask_ai(query=q2, mode="general")
            st.session_state.general_messages.append({"role": "assistant", "content": ans2})
            st.rerun()

    # Disclaimer
lines = ["---", get_text("disclaimer_block_header")]

sector = st.session_state.selected_sector

if sector == "Medical":
    lines.append(get_text("disclaimer_med"))
elif sector == "Law":
    lines.append(get_text("disclaimer_law"))
elif sector == "Agriculture":
    lines.append(get_text("disclaimer_agri"))
elif sector == "CrediLens":
    lines.append(get_text("disclaimer_credilens"))

lines.append(get_text("disclaimer_footer"))

st.markdown("\n".join(lines))


# -------------------------------------------------
# Main
# -------------------------------------------------
def main():
    if not st.session_state.language_selected:
        st.session_state.pop('_render_flag', None)
        show_language_selection()
    elif not st.session_state.sector_selected:
        st.session_state.pop('_render_flag', None)
        show_sector_selection()
    else:
        st.session_state.pop('_render_flag', None)
        show_main_app()

if __name__ == "__main__":
    main()


