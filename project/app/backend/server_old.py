from fastapi import FastAPI, APIRouter, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import random
from bson import ObjectId

# Language detection and TTS
import httpx
from langdetect import detect
import tempfile
import base64

# New AI imports
import whisper
import piper
import wave
import struct
import io
import openai
import torchaudio

try:
    import google.generativeai as genai
    GOOGLE_AI_AVAILABLE = True
except Exception as e:
    GOOGLE_AI_AVAILABLE = False
    genai = None
    logging.warning(f"google-generativeai not available: {str(e)[:100]}. Gemini API will not be available.")

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# AI API URLs and Keys
ai_api_url = os.environ.get('AI_API_URL')
openai_api_key = os.environ.get('OPENAI_API_KEY')
gemini_api_key = os.environ.get('GEMINI_API_KEY')

# Configure Gemini if key is available
if GOOGLE_AI_AVAILABLE and gemini_api_key and genai:
    try:
        genai.configure(api_key=gemini_api_key)
    except Exception as e:
        logging.warning(f"Failed to configure Gemini: {e}")
        GOOGLE_AI_AVAILABLE = False

# Create the main app
app = FastAPI(title="Legal Aid System", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Audio storage directory
AUDIO_DIR = ROOT_DIR / "audio_files"
AUDIO_DIR.mkdir(exist_ok=True)

# Lazy-load models to avoid startup issues
whisper_model = None
piper_tts = None

def get_whisper_model():
    global whisper_model
    if whisper_model is None:
        try:
            logging.info("Loading Whisper model...")
            whisper_model = whisper.load_model("small")
            logging.info("Whisper model loaded successfully")
        except Exception as e:
            logging.error(f"Failed to load Whisper model: {e}")
            whisper_model = None
    return whisper_model

def get_piper_tts():
    global piper_tts
    if piper_tts is None:
        try:
            logging.info("Loading Piper TTS model...")
            PIPER_MODELS_DIR = ROOT_DIR / "models"
            PIPER_MODELS_DIR.mkdir(exist_ok=True)
            piper_tts = piper.PiperVoice.load(PIPER_MODELS_DIR / "en_US-lessac-medium.onnx")
            logging.info("Piper TTS model loaded successfully")
        except Exception as e:
            logging.error(f"Failed to load Piper TTS model: {e}")
            piper_tts = None
    return piper_tts

# ============ MODELS ============

class StudentCreate(BaseModel):
    name: str
    email: str
    college: str
    skills: List[str] = []

class Student(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    college: str
    skills: List[str] = []
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class CaseCreate(BaseModel):
    title: str
    description: str
    category: str

class CaseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    assigned_student_id: Optional[str] = None

class Case(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    category: str
    status: str = "open"
    assigned_student_id: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class QueryCreate(BaseModel):
    query_text: str
    language: Optional[str] = None  # Optional override for language

class UserQuery(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query_text: str
    detected_language: str
    category: str
    response_text: str
    audio_id: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class DocumentCreate(BaseModel):
    doc_type: str  # FIR or RTI
    language: str = "en"
    case_id: Optional[str] = None
    details: dict = {}

class LegalDocument(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    doc_type: str
    content: str
    language: str
    case_id: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class TTSRequest(BaseModel):
    text: str
    language: Optional[str] = "en"

# ============ LEGAL KNOWLEDGE BASE ============

# Keywords for classification
CATEGORY_KEYWORDS = {
    "fir": ["fir", "police", "complaint", "theft", "crime", "report", "stolen", "attack", "assault", "murder", "robbery", "chori", "police station", "thana", "शिकायत", "पुलिस", "चोरी", "దొంగతనం", "పోలీసు"],
    "rti": ["rti", "right to information", "information", "government", "public", "transparency", "disclosure", "सूचना", "अधिकार", "సమాచారం", "హక్కు"],
    "consumer": ["consumer", "product", "defect", "refund", "warranty", "seller", "fraud", "cheated", "shop", "purchase", "उपभोक्ता", "वापसी", "వినియోగదారు", "రిఫండ్"],
    "labour": ["labour", "labor", "salary", "wages", "employer", "worker", "overtime", "termination", "fired", "job", "वेतन", "नौकरी", "मजदूर", "జీతం", "ఉద్యోగం", "కార్మికుడు"],
    "family": ["family", "divorce", "marriage", "custody", "domestic", "violence", "maintenance", "alimony", "husband", "wife", "तलाक", "विवाह", "విడాకులు", "పెళ్ళి", "భర్త", "భార్య"],
    "property": ["property", "land", "house", "tenant", "rent", "landlord", "ownership", "deed", "registration", "भूमि", "जमीन", "मकान", "భూమి", "ఇల్లు", "అద్దె"]
}

# Response templates for each category (multiple templates to avoid repetition)
RESPONSE_TEMPLATES = {
    "fir": {
        "en": [
            """📋 POLICE COMPLAINT / FIR GUIDANCE

🔹 Relevant Law: Indian Penal Code (IPC) & Code of Criminal Procedure (CrPC) Section 154

🔹 Key Information:
- An FIR (First Information Report) is the first step in reporting a cognizable offense
- Police MUST register your FIR - it's your legal right under Section 154 CrPC
- If police refuse, approach the Superintendent of Police (SP) or a Magistrate

🔹 Steps to File FIR:
1. Visit the nearest police station with jurisdiction over the incident location
2. Provide a written or oral complaint with all details (date, time, place, description)
3. Mention names/descriptions of suspects if known
4. Get the FIR copy - it's free and mandatory to provide
5. Note the FIR number for future reference

🔹 Documents Needed:
- ID proof (Aadhaar, Voter ID, etc.)
- Evidence if available (photos, CCTV footage, witnesses)
- Medical report (in case of physical harm)

🔹 Important: You can also file e-FIR online in many states for certain offenses.""",
            """📌 FIR FILING PROCEDURE

⚖️ Legal Basis: Section 154 of CrPC, Indian Penal Code

✅ Your Rights:
- Police cannot refuse to register a cognizable offense FIR
- Zero FIR can be filed at any police station regardless of jurisdiction
- You are entitled to a free copy of your FIR

📝 How to Proceed:
1. Go to the police station having jurisdiction
2. Submit a detailed written complaint describing the incident
3. Include when, where, what happened, and who was involved
4. Get acknowledgment and FIR number
5. Follow up regularly on investigation status

📋 Required Documents:
- Valid identity proof
- Any evidence (photographs, bills, records)
- Contact details of witnesses

⚠️ If Refused: File a complaint with the Superintendent of Police or approach the Judicial Magistrate under Section 156(3) CrPC.""",
            """🚔 REGISTERING A POLICE COMPLAINT

📖 Applicable Laws: CrPC Section 154, IPC relevant sections

🎯 What is FIR?
- First Information Report is the starting point of criminal proceedings
- Must be filed for cognizable offenses (serious crimes)
- Can be filed by victim or any person aware of the crime

📋 Process:
1. Visit jurisdictional police station
2. Give written/verbal statement of the incident
3. Include complete details: time, date, location, incident description
4. Identify suspects if possible
5. Collect FIR copy with registration number

📎 Supporting Documents:
- Photo ID (Aadhaar preferred)
- Evidence materials
- Medical examination report (if applicable)
- Witness contact information

💡 Online Option: Many states offer e-FIR services through their police websites."""
        ],
        "hi": [
            """📋 पुलिस शिकायत / एफआईआर मार्गदर्शन

🔹 संबंधित कानून: भारतीय दंड संहिता (IPC) और दंड प्रक्रिया संहिता (CrPC) धारा 154

🔹 महत्वपूर्ण जानकारी:
- एफआईआर (प्रथम सूचना रिपोर्ट) संज्ञेय अपराध की रिपोर्ट करने का पहला कदम है
- पुलिस को आपकी एफआईआर दर्ज करनी होगी - यह धारा 154 CrPC के तहत आपका कानूनी अधिकार है
- अगर पुलिस मना करे तो पुलिस अधीक्षक (SP) या मजिस्ट्रेट से संपर्क करें

🔹 एफआईआर दर्ज करने के चरण:
1. घटना स्थान के क्षेत्राधिकार वाले निकटतम थाने में जाएं
2. सभी विवरणों के साथ लिखित या मौखिक शिकायत दें
3. संदिग्धों के नाम/विवरण बताएं
4. एफआईआर की प्रति प्राप्त करें - यह मुफ्त और अनिवार्य है
5. भविष्य के संदर्भ के लिए एफआईआर नंबर नोट करें

🔹 आवश्यक दस्तावेज:
- पहचान प्रमाण (आधार, वोटर आईडी, आदि)
- साक्ष्य (फोटो, सीसीटीवी फुटेज, गवाह)""",
            """📌 एफआईआर दर्ज करने की प्रक्रिया

⚖️ कानूनी आधार: CrPC की धारा 154, भारतीय दंड संहिता

✅ आपके अधिकार:
- पुलिस संज्ञेय अपराध की एफआईआर दर्ज करने से मना नहीं कर सकती
- जीरो एफआईआर किसी भी थाने में दर्ज की जा सकती है
- आप अपनी एफआईआर की मुफ्त प्रति के हकदार हैं

📝 कैसे आगे बढ़ें:
1. क्षेत्राधिकार वाले थाने में जाएं
2. घटना का विस्तृत विवरण दें
3. कब, कहाँ, क्या हुआ और कौन शामिल था बताएं
4. पावती और एफआईआर नंबर प्राप्त करें
5. जांच की स्थिति पर नियमित अनुवर्ती कार्रवाई करें

📋 आवश्यक दस्तावेज:
- वैध पहचान प्रमाण
- कोई भी सबूत
- गवाहों के संपर्क विवरण"""
        ],
        "te": [
            """📋 పోలీసు ఫిర్యాదు / ఎఫ్‌ఐఆర్ మార్గదర్శకత్వం

🔹 సంబంధిత చట్టం: భారత శిక్షాస్మృతి (IPC) & క్రిమినల్ ప్రొసీజర్ కోడ్ (CrPC) సెక్షన్ 154

🔹 ముఖ్య సమాచారం:
- ఎఫ్‌ఐఆర్ (ఫస్ట్ ఇన్ఫర్మేషన్ రిపోర్ట్) కాగ్నిజబుల్ నేరాన్ని రిపోర్ట్ చేయడంలో మొదటి అడుగు
- పోలీసులు మీ ఎఫ్‌ఐఆర్‌ను తప్పనిసరిగా నమోదు చేయాలి - ఇది సెక్షన్ 154 CrPC ప్రకారం మీ చట్టబద్ధమైన హక్కు
- పోలీసులు నిరాకరిస్తే, పోలీసు సూపరింటెండెంట్ (SP) లేదా మేజిస్ట్రేట్‌ను సంప్రదించండి

🔹 ఎఫ్‌ఐఆర్ దాఖలు చేయడానికి దశలు:
1. సంఘటన స్థలంపై అధికార పరిధి ఉన్న సమీపంలోని పోలీస్ స్టేషన్‌కు వెళ్ళండి
2. అన్ని వివరాలతో వ్రాతపూర్వక లేదా మౌఖిక ఫిర్యాదు ఇవ్వండి
3. తెలిస్తే అనుమానితుల పేర్లు/వివరణలు చెప్పండి
4. ఎఫ్‌ఐఆర్ కాపీ పొందండి - ఇది ఉచితం మరియు తప్పనిసరి
5. భవిష్యత్ సూచన కోసం ఎఫ్‌ఐఆర్ నంబర్ నోట్ చేయండి"""
        ]
    },
    "rti": {
        "en": [
            """📋 RIGHT TO INFORMATION (RTI) GUIDANCE

🔹 Relevant Law: Right to Information Act, 2005

🔹 Key Information:
- RTI allows any Indian citizen to request information from public authorities
- Response must be provided within 30 days (48 hours for life/liberty matters)
- Fee: ₹10 for Central Government, varies for State Governments

🔹 Steps to File RTI:
1. Identify the Public Authority holding the information
2. Write application to the Public Information Officer (PIO)
3. Clearly state what information you need (be specific)
4. Pay the application fee (₹10 by postal order/DD/cash)
5. Send by post or submit in person

🔹 Application Format:
To: The Public Information Officer
[Department Name]
[Address]

Subject: Application under RTI Act, 2005

I, [Your Name], request the following information under RTI Act:
[List your questions clearly]

🔹 If No Response: File First Appeal to First Appellate Authority within 30 days.""",
            """📌 RTI APPLICATION PROCEDURE

⚖️ Legal Basis: RTI Act 2005

✅ Your Rights:
- Every citizen can seek information from government offices
- No reason needs to be given for seeking information
- Exemptions apply only for sensitive matters (Section 8)

📝 How to Apply:
1. Write "Application under RTI Act 2005" at the top
2. Address it to the Public Information Officer (PIO)
3. State your questions clearly and specifically
4. Attach fee of ₹10 (postal order/demand draft/court fee stamp)
5. Keep a copy for your records

📋 Key Points:
- Response deadline: 30 days
- BPL applicants are exempted from fees
- Life/liberty matters: 48 hours response time

⚠️ Appeals: First Appeal within 30 days, Second Appeal to Information Commission within 90 days."""
        ],
        "hi": [
            """📋 सूचना का अधिकार (RTI) मार्गदर्शन

🔹 संबंधित कानून: सूचना का अधिकार अधिनियम, 2005

🔹 महत्वपूर्ण जानकारी:
- RTI किसी भी भारतीय नागरिक को सार्वजनिक प्राधिकरणों से सूचना मांगने की अनुमति देता है
- 30 दिनों के भीतर जवाब देना अनिवार्य है (जीवन/स्वतंत्रता के मामलों में 48 घंटे)
- शुल्क: केंद्र सरकार के लिए ₹10

🔹 RTI दाखिल करने के चरण:
1. सूचना रखने वाले सार्वजनिक प्राधिकरण की पहचान करें
2. जन सूचना अधिकारी (PIO) को आवेदन लिखें
3. स्पष्ट रूप से बताएं कि आपको कौन सी जानकारी चाहिए
4. आवेदन शुल्क का भुगतान करें (₹10)
5. डाक से भेजें या व्यक्तिगत रूप से जमा करें

🔹 यदि कोई प्रतिक्रिया नहीं: 30 दिनों के भीतर प्रथम अपीलीय प्राधिकारी के पास प्रथम अपील दायर करें।"""
        ],
        "te": [
            """📋 సమాచార హక్కు (RTI) మార్గదర్శకత్వం

🔹 సంబంధిత చట్టం: సమాచార హక్కు చట్టం, 2005

🔹 ముఖ్య సమాచారం:
- RTI ఏ భారతీయ పౌరుడికైనా ప్రభుత్వ అధికారుల నుండి సమాచారం అభ్యర్థించే అధికారం ఇస్తుంది
- 30 రోజుల్లో ప్రతిస్పందన ఇవ్వాలి (జీవితం/స్వేచ్ఛ విషయాలకు 48 గంటలు)
- రుసుము: కేంద్ర ప్రభుత్వానికి ₹10

🔹 RTI దాఖలు చేయడానికి దశలు:
1. సమాచారం కలిగి ఉన్న ప్రభుత్వ సంస్థను గుర్తించండి
2. పబ్లిక్ ఇన్ఫర్మేషన్ ఆఫీసర్ (PIO)కు దరఖాస్తు రాయండి
3. మీకు ఏ సమాచారం కావాలో స్పష్టంగా చెప్పండి
4. దరఖాస్తు రుసుము చెల్లించండి (₹10)
5. పోస్ట్ ద్వారా పంపండి లేదా వ్యక్తిగతంగా సమర్పించండి"""
        ]
    },
    "consumer": {
        "en": [
            """📋 CONSUMER RIGHTS GUIDANCE

🔹 Relevant Law: Consumer Protection Act, 2019

🔹 Key Information:
- Covers goods, services, and e-commerce transactions
- File complaint within 2 years of the cause of action
- No lawyer required for consumer forum

🔹 Consumer Forums by Value:
- District Forum: Up to ₹1 Crore
- State Commission: ₹1 Crore to ₹10 Crore
- National Commission: Above ₹10 Crore

🔹 Steps to File Complaint:
1. Send a legal notice to the seller/company
2. If no resolution, prepare complaint with details
3. Attach bills, receipts, warranty cards, communication records
4. File at appropriate Consumer Forum
5. Pay nominal court fee

🔹 Your Rights:
- Right to Safety
- Right to Information
- Right to Choose
- Right to be Heard
- Right to Redressal
- Right to Consumer Education

🔹 Online: File at https://consumerhelpline.gov.in or call 1800-11-4000""",
            """📌 CONSUMER COMPLAINT PROCEDURE

⚖️ Legal Basis: Consumer Protection Act 2019

✅ Grounds for Complaint:
- Defective goods or deficient services
- Unfair trade practices
- Overcharging or hidden charges
- False advertising

📝 Steps:
1. First approach the seller/service provider with complaint
2. Keep written records of all communications
3. If unresolved, file complaint at Consumer Forum
4. Include: name/address of parties, facts, relief sought, evidence

📋 Required Documents:
- Purchase receipt/invoice
- Warranty/guarantee card
- Defective product photos
- Communication records with seller

💡 Tip: E-commerce complaints can be filed online through consumer helpline portal."""
        ],
        "hi": [
            """📋 उपभोक्ता अधिकार मार्गदर्शन

🔹 संबंधित कानून: उपभोक्ता संरक्षण अधिनियम, 2019

🔹 महत्वपूर्ण जानकारी:
- वस्तुओं, सेवाओं और ई-कॉमर्स लेनदेन को कवर करता है
- कारण की तारीख से 2 वर्ष के भीतर शिकायत दर्ज करें
- उपभोक्ता फोरम के लिए वकील की जरूरत नहीं

🔹 उपभोक्ता फोरम (मूल्य के अनुसार):
- जिला फोरम: ₹1 करोड़ तक
- राज्य आयोग: ₹1 करोड़ से ₹10 करोड़
- राष्ट्रीय आयोग: ₹10 करोड़ से ऊपर

🔹 शिकायत दर्ज करने के चरण:
1. विक्रेता/कंपनी को कानूनी नोटिस भेजें
2. यदि समाधान नहीं, विवरण के साथ शिकायत तैयार करें
3. बिल, रसीदें, वारंटी कार्ड संलग्न करें
4. उचित उपभोक्ता फोरम में दाखिल करें"""
        ],
        "te": [
            """📋 వినియోగదారు హక్కుల మార్గదర్శకత్వం

🔹 సంబంధిత చట్టం: వినియోగదారు రక్షణ చట్టం, 2019

🔹 ముఖ్య సమాచారం:
- వస్తువులు, సేవలు మరియు ఇ-కామర్స్ లావాదేవీలను కవర్ చేస్తుంది
- కారణ తేదీ నుండి 2 సంవత్సరాల్లోపు ఫిర్యాదు దాఖలు చేయండి
- వినియోగదారు ఫోరమ్‌కు లాయర్ అవసరం లేదు

🔹 వినియోగదారు ఫోరమ్‌లు:
- జిల్లా ఫోరమ్: ₹1 కోటి వరకు
- రాష్ట్ర కమిషన్: ₹1 కోటి నుండి ₹10 కోటి
- జాతీయ కమిషన్: ₹10 కోటి పైన

🔹 ఫిర్యాదు దాఖలు చేయడానికి దశలు:
1. విక్రేత/కంపెనీకి లీగల్ నోటీస్ పంపండి
2. పరిష్కారం లేకపోతే, వివరాలతో ఫిర్యాదు తయారు చేయండి
3. బిల్లులు, రసీదులు, వారంటీ కార్డులు జతచేయండి"""
        ]
    },
    "labour": {
        "en": [
            """📋 LABOUR LAW GUIDANCE

🔹 Relevant Laws:
- Payment of Wages Act, 1936
- Minimum Wages Act, 1948
- Industrial Disputes Act, 1947
- Employees' Provident Fund Act, 1952

🔹 Key Rights:
- Right to minimum wages as per state notification
- Right to timely payment (within 7 days of wage period)
- Right to safe working conditions
- Right to leave and holidays
- Right against wrongful termination

🔹 Steps for Wage-Related Issues:
1. Document all your work records and payment history
2. Write a formal complaint to employer
3. If no response, approach the Labour Commissioner
4. File complaint at Labour Court if needed

🔹 For Wrongful Termination:
1. Get termination letter or written communication
2. Check if notice period and dues are paid
3. File complaint with Labour Department
4. Approach Labour Court within time limit

🔹 Helpline: SHRAM helpline - 14434""",
            """📌 EMPLOYEE RIGHTS PROTECTION

⚖️ Applicable Laws: Labour Codes 2020, PF Act, ESI Act

✅ Your Entitlements:
- Minimum wages as per government notification
- PF and ESI benefits (for eligible establishments)
- Gratuity after 5 years of service
- Maternity benefits for women employees

📝 Complaint Process:
1. Maintain records of employment, salary slips, communications
2. Submit written grievance to HR/management
3. If unresolved, approach Labour Commissioner's office
4. File case in Labour Court/Industrial Tribunal

📋 Required Documents:
- Employment letter/contract
- Salary slips and bank statements
- Attendance records
- Any communication with employer

💡 Online: Register complaint on SHRAM portal (shramsuvidha.gov.in)"""
        ],
        "hi": [
            """📋 श्रम कानून मार्गदर्शन

🔹 संबंधित कानून:
- मजदूरी भुगतान अधिनियम, 1936
- न्यूनतम मजदूरी अधिनियम, 1948
- औद्योगिक विवाद अधिनियम, 1947

🔹 मुख्य अधिकार:
- राज्य अधिसूचना के अनुसार न्यूनतम मजदूरी का अधिकार
- समय पर भुगतान का अधिकार
- सुरक्षित कार्य स्थितियों का अधिकार
- छुट्टी और अवकाश का अधिकार

🔹 वेतन संबंधी मुद्दों के लिए चरण:
1. अपने सभी कार्य रिकॉर्ड और भुगतान इतिहास का दस्तावेज रखें
2. नियोक्ता को औपचारिक शिकायत लिखें
3. कोई प्रतिक्रिया नहीं मिलने पर श्रम आयुक्त से संपर्क करें

🔹 हेल्पलाइन: श्रम हेल्पलाइन - 14434"""
        ],
        "te": [
            """📋 కార్మిక చట్ట మార్గదర్శకత్వం

🔹 సంబంధిత చట్టాలు:
- వేతన చెల్లింపు చట్టం, 1936
- కనీస వేతన చట్టం, 1948
- పారిశ్రామిక వివాదాల చట్టం, 1947

🔹 ముఖ్య హక్కులు:
- రాష్ట్ర నోటిఫికేషన్ ప్రకారం కనీస వేతన హక్కు
- సకాలంలో చెల్లింపు హక్కు
- సురక్షితమైన పని పరిస్థితుల హక్కు
- సెలవు మరియు సెలవుల హక్కు

🔹 వేతన సమస్యల కోసం దశలు:
1. మీ పని రికార్డులు మరియు చెల్లింపు చరిత్రను డాక్యుమెంట్ చేయండి
2. యజమానికి అధికారిక ఫిర్యాదు రాయండి
3. స్పందన లేకపోతే, కార్మిక కమిషనర్‌ను సంప్రదించండి"""
        ]
    },
    "family": {
        "en": [
            """📋 FAMILY LAW GUIDANCE

🔹 Relevant Laws:
- Hindu Marriage Act, 1955
- Special Marriage Act, 1954
- Protection of Women from Domestic Violence Act, 2005
- Hindu Adoption and Maintenance Act, 1956

🔹 For Domestic Violence:
- File complaint at nearest police station or Women's Cell
- Approach Protection Officer in your district
- File application in Magistrate Court under DV Act
- Seek protection order, residence order, monetary relief

🔹 For Divorce:
- Mutual consent divorce (simpler, faster)
- Contested divorce (through court proceedings)
- Grounds: cruelty, desertion, adultery, mental disorder, etc.

🔹 For Maintenance:
- Wife can claim maintenance under Section 125 CrPC
- Children entitled to maintenance until 18 (or completion of education)
- Can be filed in Family Court or Magistrate Court

🔹 Helplines:
- Women Helpline: 181
- NCW Helpline: 7827-170-170""",
            """📌 DOMESTIC VIOLENCE & FAMILY DISPUTES

⚖️ Legal Protection: DV Act 2005, Section 498A IPC

✅ Immediate Help:
- Call Women Helpline 181 for emergency
- Contact nearest Police Station or Women's Cell
- Approach NGOs like Shakti Shalini, Jagori

📝 For Protection Order:
1. File complaint with Protection Officer or Service Provider
2. Submit application to Magistrate Court
3. Court can grant interim protection immediately
4. Final order within 60 days

📋 Relief Available:
- Protection Order (stop abuse)
- Residence Order (right to stay in shared household)
- Monetary Relief (compensation for injuries)
- Custody Order (for children)

💡 Free Legal Aid: Contact DLSA (District Legal Services Authority)"""
        ],
        "hi": [
            """📋 पारिवारिक कानून मार्गदर्शन

🔹 संबंधित कानून:
- हिंदू विवाह अधिनियम, 1955
- विशेष विवाह अधिनियम, 1954
- घरेलू हिंसा से महिलाओं का संरक्षण अधिनियम, 2005

🔹 घरेलू हिंसा के लिए:
- निकटतम पुलिस स्टेशन या महिला सेल में शिकायत दर्ज करें
- अपने जिले में संरक्षण अधिकारी से संपर्क करें
- DV अधिनियम के तहत मजिस्ट्रेट कोर्ट में आवेदन दायर करें

🔹 तलाक के लिए:
- आपसी सहमति से तलाक (सरल, तेज)
- विवादित तलाक (अदालती कार्यवाही के माध्यम से)

🔹 भरण-पोषण के लिए:
- पत्नी धारा 125 CrPC के तहत भरण-पोषण का दावा कर सकती है
- बच्चे 18 वर्ष तक भरण-पोषण के हकदार हैं

🔹 हेल्पलाइन:
- महिला हेल्पलाइन: 181
- NCW हेल्पलाइन: 7827-170-170"""
        ],
        "te": [
            """📋 కుటుంబ చట్ట మార్గదర్శకత్వం

🔹 సంబంధిత చట్టాలు:
- హిందూ వివాహ చట్టం, 1955
- ప్రత్యేక వివాహ చట్టం, 1954
- గృహ హింస నుండి మహిళల రక్షణ చట్టం, 2005

🔹 గృహ హింస కోసం:
- సమీపంలోని పోలీస్ స్టేషన్ లేదా మహిళా సెల్‌లో ఫిర్యాదు చేయండి
- మీ జిల్లాలో ప్రొటెక్షన్ ఆఫీసర్‌ను సంప్రదించండి
- DV చట్టం కింద మేజిస్ట్రేట్ కోర్టులో దరఖాస్తు దాఖలు చేయండి

🔹 విడాకుల కోసం:
- పరస్పర అంగీకార విడాకులు (సరళమైన, వేగవంతమైన)
- వివాదాస్పద విడాకులు (కోర్టు ప్రొసీడింగ్స్ ద్వారా)

🔹 హెల్ప్‌లైన్‌లు:
- మహిళా హెల్ప్‌లైన్: 181
- NCW హెల్ప్‌లైన్: 7827-170-170"""
        ]
    },
    "property": {
        "en": [
            """📋 PROPERTY LAW GUIDANCE

🔹 Relevant Laws:
- Transfer of Property Act, 1882
- Registration Act, 1908
- Specific Relief Act, 1963
- Rent Control Acts (State-specific)

🔹 For Property Disputes:
1. Verify property documents (sale deed, mutation records)
2. Check encumbrance certificate for any liens/charges
3. Approach civil court for title disputes
4. Revenue court for mutation/land record issues

🔹 For Tenant Issues:
- Check state Rent Control Act provisions
- Landlord cannot forcibly evict - need court order
- Fair rent determination through Rent Controller
- Notice periods as per state laws

🔹 For Property Registration:
- Pay stamp duty (varies by state)
- Register within 4 months of execution
- Presence of 2 witnesses required
- Get encumbrance certificate before purchase

🔹 Important Documents:
- Title deed / Sale deed
- Mutation records
- Encumbrance certificate
- Tax receipts
- Approved building plan""",
            """📌 LAND & PROPERTY DISPUTES

⚖️ Applicable Laws: Transfer of Property Act, Registration Act

✅ Before Buying Property:
- Verify seller's title through chain of documents
- Get encumbrance certificate (EC) for 30+ years
- Check approved layout and building plan
- Verify tax payments and utility bills

📝 For Illegal Possession:
1. Gather title documents proving ownership
2. Send legal notice to occupant
3. File civil suit for possession
4. Apply for interim injunction to prevent further damage

📋 For Boundary Disputes:
1. Get survey from Revenue Department
2. Mediation through local authorities
3. Civil suit if unresolved

💡 Free Legal Aid available at DLSA for property disputes."""
        ],
        "hi": [
            """📋 संपत्ति कानून मार्गदर्शन

🔹 संबंधित कानून:
- संपत्ति हस्तांतरण अधिनियम, 1882
- पंजीकरण अधिनियम, 1908
- विशिष्ट राहत अधिनियम, 1963

🔹 संपत्ति विवादों के लिए:
1. संपत्ति दस्तावेजों का सत्यापन करें (विक्रय पत्र, म्युटेशन रिकॉर्ड)
2. किसी भी लियन/प्रभार के लिए भारमुक्ति प्रमाणपत्र जांचें
3. स्वामित्व विवादों के लिए दीवानी अदालत में जाएं
4. म्युटेशन/भूमि रिकॉर्ड मुद्दों के लिए राजस्व न्यायालय

🔹 किरायेदार मुद्दों के लिए:
- राज्य किराया नियंत्रण अधिनियम प्रावधान देखें
- मकान मालिक जबरन बेदखल नहीं कर सकता

🔹 महत्वपूर्ण दस्तावेज:
- स्वामित्व पत्र / विक्रय पत्र
- म्युटेशन रिकॉर्ड
- भारमुक्ति प्रमाणपत्र
- कर रसीदें"""
        ],
        "te": [
            """📋 ఆస్తి చట్ట మార్గదర్శకత్వం

🔹 సంబంధిత చట్టాలు:
- ఆస్తి బదిలీ చట్టం, 1882
- రిజిస్ట్రేషన్ చట్టం, 1908
- నిర్దిష్ట ఉపశమన చట్టం, 1963

🔹 ఆస్తి వివాదాల కోసం:
1. ఆస్తి పత్రాలను ధృవీకరించండి (సేల్ డీడ్, మ్యుటేషన్ రికార్డులు)
2. ఏవైనా లైన్స్/ఛార్జీల కోసం ఎన్‌కంబరెన్స్ సర్టిఫికేట్ తనిఖీ చేయండి
3. టైటిల్ వివాదాల కోసం సివిల్ కోర్టుకు వెళ్ళండి
4. మ్యుటేషన్/భూమి రికార్డు సమస్యల కోసం రెవెన్యూ కోర్టు

🔹 అద్దెదారు సమస్యల కోసం:
- రాష్ట్ర అద్దె నియంత్రణ చట్ట నిబంధనలు చూడండి
- ఇంటి యజమాని బలవంతంగా ఖాళీ చేయించలేరు

🔹 ముఖ్యమైన పత్రాలు:
- టైటిల్ డీడ్ / సేల్ డీడ్
- మ్యుటేషన్ రికార్డులు
- ఎన్‌కంబరెన్స్ సర్టిఫికేట్"""
        ]
    },
    "general": {
        "en": [
            """📋 GENERAL LEGAL GUIDANCE

Thank you for your query. Based on your question, here is some general legal guidance:

🔹 Free Legal Aid:
- Contact DLSA (District Legal Services Authority) in your district
- Call NALSA helpline: 15100
- Eligible: Women, children, SC/ST, disabled, victims of trafficking

🔹 Common Legal Resources:
- e-Courts Services: https://ecourts.gov.in
- Legal Aid: https://nalsa.gov.in
- Consumer Helpline: 1800-11-4000
- Women Helpline: 181

🔹 For Specific Help:
Please provide more details about your legal issue so I can give you targeted guidance. You can mention:
- The nature of your problem (civil, criminal, family, property)
- Parties involved
- What relief you are seeking

Our system supports queries related to: FIR/Police complaints, RTI, Consumer issues, Labour disputes, Family matters, and Property issues.""",
            """📌 LEGAL ASSISTANCE INFORMATION

I understand you have a legal concern. Let me help you navigate the right path.

⚖️ Steps to Get Legal Help:
1. Identify the type of issue (criminal, civil, family, consumer, labour)
2. Gather relevant documents and evidence
3. Consult with a lawyer or visit Free Legal Aid Centre
4. File complaint/petition at appropriate forum

📋 Important Helplines:
- Police Emergency: 100
- Women Helpline: 181
- Child Helpline: 1098
- Consumer Helpline: 1800-11-4000
- Legal Aid: 15100

💡 For More Specific Guidance:
Please describe your issue in detail. Our system can help with:
- Police complaints (FIR)
- Right to Information (RTI)
- Consumer disputes
- Labour/employment issues
- Family matters (divorce, maintenance, domestic violence)
- Property disputes"""
        ],
        "hi": [
            """📋 सामान्य कानूनी मार्गदर्शन

आपकी क्वेरी के लिए धन्यवाद। आपके प्रश्न के आधार पर, यहां कुछ सामान्य कानूनी मार्गदर्शन है:

🔹 मुफ्त कानूनी सहायता:
- अपने जिले में DLSA (जिला कानूनी सेवा प्राधिकरण) से संपर्क करें
- NALSA हेल्पलाइन पर कॉल करें: 15100

🔹 सामान्य कानूनी संसाधन:
- ई-कोर्ट्स सेवाएं: https://ecourts.gov.in
- उपभोक्ता हेल्पलाइन: 1800-11-4000
- महिला हेल्पलाइन: 181

🔹 विशिष्ट सहायता के लिए:
कृपया अपने कानूनी मुद्दे के बारे में अधिक विवरण प्रदान करें।"""
        ],
        "te": [
            """📋 సాధారణ న్యాయ మార్గదర్శకత్వం

మీ ప్రశ్నకు ధన్యవాదాలు. మీ ప్రశ్న ఆధారంగా, ఇక్కడ కొన్ని సాధారణ న్యాయ మార్గదర్శకత్వం ఉంది:

🔹 ఉచిత న్యాయ సహాయం:
- మీ జిల్లాలో DLSA (జిల్లా న్యాయ సేవల ప్రాధికారం) ను సంప్రదించండి
- NALSA హెల్ప్‌లైన్: 15100

🔹 సాధారణ న్యాయ వనరులు:
- ఇ-కోర్ట్స్ సేవలు: https://ecourts.gov.in
- వినియోగదారు హెల్ప్‌లైన్: 1800-11-4000
- మహిళా హెల్ప్‌లైన్: 181

🔹 నిర్దిష్ట సహాయం కోసం:
దయచేసి మీ న్యాయ సమస్య గురించి మరిన్ని వివరాలు అందించండి."""
        ]
    }
}

# Document templates
FIR_TEMPLATES = {
    "en": """FIRST INFORMATION REPORT (FIR)
=====================================

To,
The Station House Officer
[Police Station Name]
[District, State]

Subject: Complaint for registration of FIR

Respected Sir/Madam,

I, {name}, aged {age} years, residing at {address}, hereby lodge this complaint for the registration of FIR regarding the following incident:

1. Date of Incident: {incident_date}
2. Time of Incident: {incident_time}
3. Place of Incident: {incident_place}

4. Description of Incident:
{incident_description}

5. Details of Accused (if known):
{accused_details}

6. List of Witnesses:
{witness_details}

7. Evidence/Documents attached:
{evidence_list}

I request you to kindly register this FIR and take necessary legal action against the accused person(s).

Date: {current_date}
Place: {place}

Yours faithfully,
{name}
Mobile: {mobile}
Email: {email}

[Signature of Complainant]""",
    "hi": """प्रथम सूचना रिपोर्ट (एफआईआर)
=====================================

सेवा में,
थाना प्रभारी
[थाने का नाम]
[जिला, राज्य]

विषय: एफआईआर दर्ज करने हेतु शिकायत

महोदय/महोदया,

मैं, {name}, आयु {age} वर्ष, निवासी {address}, निम्नलिखित घटना के संबंध में एफआईआर दर्ज करने हेतु यह शिकायत प्रस्तुत करता/करती हूं:

1. घटना की तारीख: {incident_date}
2. घटना का समय: {incident_time}
3. घटना का स्थान: {incident_place}

4. घटना का विवरण:
{incident_description}

5. आरोपी का विवरण (यदि ज्ञात हो):
{accused_details}

6. गवाहों की सूची:
{witness_details}

7. संलग्न साक्ष्य/दस्तावेज:
{evidence_list}

कृपया इस एफआईआर को दर्ज करें और आरोपी के विरुद्ध आवश्यक कानूनी कार्रवाई करें।

दिनांक: {current_date}
स्थान: {place}

भवदीय,
{name}
मोबाइल: {mobile}
ईमेल: {email}

[शिकायतकर्ता के हस्ताक्षर]""",
    "te": """ఫస్ట్ ఇన్ఫర్మేషన్ రిపోర్ట్ (ఎఫ్‌ఐఆర్)
=====================================

కు,
స్టేషన్ హౌస్ ఆఫీసర్
[పోలీస్ స్టేషన్ పేరు]
[జిల్లా, రాష్ట్రం]

సబ్జెక్ట్: ఎఫ్‌ఐఆర్ రిజిస్ట్రేషన్ కోసం ఫిర్యాదు

గౌరవనీయులైన సార్/మేడమ్,

నేను, {name}, వయస్సు {age} సంవత్సరాలు, {address} లో నివసిస్తున్నాను, ఈ క్రింది సంఘటనకు సంబంధించి ఎఫ్‌ఐఆర్ రిజిస్ట్రేషన్ కోసం ఈ ఫిర్యాదును దాఖలు చేస్తున్నాను:

1. సంఘటన తేదీ: {incident_date}
2. సంఘటన సమయం: {incident_time}
3. సంఘటన స్థలం: {incident_place}

4. సంఘటన వివరణ:
{incident_description}

5. నిందితుల వివరాలు (తెలిస్తే):
{accused_details}

6. సాక్షుల జాబితా:
{witness_details}

7. జతచేసిన సాక్ష్యాలు/పత్రాలు:
{evidence_list}

దయచేసి ఈ ఎఫ్‌ఐఆర్‌ను నమోదు చేసి నిందితులపై అవసరమైన చట్టపరమైన చర్య తీసుకోండి.

తేదీ: {current_date}
స్థలం: {place}

విధేయుడు,
{name}
మొబైల్: {mobile}
ఇమెయిల్: {email}

[ఫిర్యాదిదారు సంతకం]"""
}

RTI_TEMPLATES = {
    "en": """RIGHT TO INFORMATION APPLICATION
=====================================

To,
The Public Information Officer
{department_name}
{department_address}

Subject: Application under Right to Information Act, 2005

Respected Sir/Madam,

I, {name}, residing at {address}, hereby request the following information under the Right to Information Act, 2005:

1. {question_1}

2. {question_2}

3. {question_3}

Period for which information is sought: {period}

I am paying the prescribed fee of Rs. {fee}/- through {payment_mode}.

I request you to provide the above information within the stipulated time period of 30 days as per the RTI Act.

Date: {current_date}
Place: {place}

Yours faithfully,
{name}
Address: {address}
Mobile: {mobile}
Email: {email}

[Signature of Applicant]

Enclosures:
1. Copy of ID Proof
2. Fee payment proof ({payment_mode})""",
    "hi": """सूचना का अधिकार आवेदन
=====================================

सेवा में,
जन सूचना अधिकारी
{department_name}
{department_address}

विषय: सूचना का अधिकार अधिनियम, 2005 के तहत आवेदन

महोदय/महोदया,

मैं, {name}, निवासी {address}, सूचना का अधिकार अधिनियम, 2005 के तहत निम्नलिखित सूचना का अनुरोध करता/करती हूं:

1. {question_1}

2. {question_2}

3. {question_3}

सूचना की अवधि: {period}

मैं निर्धारित शुल्क रु. {fee}/- {payment_mode} के माध्यम से जमा कर रहा/रही हूं।

कृपया RTI अधिनियम के अनुसार 30 दिनों के भीतर उपरोक्त सूचना प्रदान करें।

दिनांक: {current_date}
स्थान: {place}

भवदीय,
{name}
पता: {address}
मोबाइल: {mobile}
ईमेल: {email}

[आवेदक के हस्ताक्षर]""",
    "te": """సమాచార హక్కు దరఖాస్తు
=====================================

కు,
పబ్లిక్ ఇన్ఫర్మేషన్ ఆఫీసర్
{department_name}
{department_address}

సబ్జెక్ట్: సమాచార హక్కు చట్టం, 2005 కింద దరఖాస్తు

గౌరవనీయులైన సార్/మేడమ్,

నేను, {name}, {address} లో నివసిస్తున్నాను, సమాచార హక్కు చట్టం, 2005 కింద ఈ క్రింది సమాచారాన్ని అభ్యర్థిస్తున్నాను:

1. {question_1}

2. {question_2}

3. {question_3}

సమాచారం అవసరమైన కాలం: {period}

నేను నిర్ణీత రుసుము రూ. {fee}/- {payment_mode} ద్వారా చెల్లిస్తున్నాను.

RTI చట్టం ప్రకారం 30 రోజుల్లోపు పై సమాచారాన్ని అందించమని అభ్యర్థిస్తున్నాను.

తేదీ: {current_date}
స్థలం: {place}

విధేయుడు,
{name}
చిరునామా: {address}
మొబైల్: {mobile}
ఇమెయిల్: {email}

[దరఖాస్తుదారు సంతకం]"""
}

# Sample data for seeding
SAMPLE_STUDENTS = [
    {"name": "Rahul Sharma", "email": "rahul.sharma@lawcollege.edu", "college": "National Law University, Delhi", "skills": ["Criminal Law", "RTI", "Legal Research"]},
    {"name": "Priya Patel", "email": "priya.patel@lawcollege.edu", "college": "Gujarat National Law University", "skills": ["Family Law", "Consumer Rights", "Mediation"]},
    {"name": "Arjun Reddy", "email": "arjun.reddy@lawcollege.edu", "college": "NALSAR University, Hyderabad", "skills": ["Property Law", "Corporate Law", "Drafting"]},
    {"name": "Sneha Gupta", "email": "sneha.gupta@lawcollege.edu", "college": "NLU, Jodhpur", "skills": ["Labour Law", "Human Rights", "PIL"]},
    {"name": "Vikram Singh", "email": "vikram.singh@lawcollege.edu", "college": "NLSIU, Bangalore", "skills": ["Constitutional Law", "FIR Drafting", "Litigation"]}
]

SAMPLE_CASES = [
    {"title": "Consumer Fraud - Online Purchase", "description": "Victim purchased electronic goods online but received counterfeit products. Seeking refund and compensation.", "category": "consumer"},
    {"title": "Domestic Violence Support", "description": "Woman seeking protection order against abusive spouse. Requires legal aid for DV Act proceedings.", "category": "family"},
    {"title": "Property Encroachment", "description": "Ancestral property being illegally occupied by neighbor. Need to file civil suit for possession.", "category": "property"},
    {"title": "Unpaid Wages Case", "description": "Factory workers not paid minimum wages for 3 months. Collective complaint against employer.", "category": "labour"},
    {"title": "RTI for Road Project", "description": "Citizen seeking information about delayed road construction project in locality.", "category": "rti"}
]

# ============ UTILITY FUNCTIONS ============

def detect_language(text: str) -> str:
    """Detect language of the input text."""
    try:
        lang = detect(text)
        if lang in ['hi', 'te']:
            return lang
        return 'en'  # Default to English
    except:
        return 'en'

def classify_query(text: str) -> str:
    """Classify the query into a legal category based on keywords."""
    text_lower = text.lower()
    
    # Count keyword matches for each category
    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in text_lower)
        scores[category] = score
    
    # Find category with highest score
    max_score = max(scores.values())
    if max_score > 0:
        for category, score in scores.items():
            if score == max_score:
                return category
    
    return 'general'

def get_response(category: str, language: str) -> str:
    """Get a randomized response for the given category and language."""
    templates = RESPONSE_TEMPLATES.get(category, RESPONSE_TEMPLATES['general'])
    lang_templates = templates.get(language, templates.get('en', []))
    
    if lang_templates:
        return random.choice(lang_templates)
    return RESPONSE_TEMPLATES['general']['en'][0]

# ============ API ROUTES ============

@api_router.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Legal Aid System API is running", "status": "healthy"}

# ----- QUERIES -----

@api_router.post("/queries", response_model=UserQuery)
async def process_query(query_input: QueryCreate):
    """Process a legal query and return response with audio."""
    # Detect language (or use provided override)
    detected_lang = query_input.language if query_input.language else detect_language(query_input.query_text)
    
    # Get response from AI API or OpenAI or Gemini or fallback
    response_text = None
    
    # Try OpenAI first
    if openai_api_key:
        try:
            client = openai.OpenAI(api_key=openai_api_key)
            system_prompt = """You are a legal aid assistant for Indian laws. Respond accurately, clearly, and helpfully. 
Provide structured, user-friendly answers based on Indian legal framework. 
If the query is in Hindi or Telugu, respond in the same language. 
Keep answers concise but comprehensive."""
            
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query_input.query_text}
                ],
                max_tokens=800,
                temperature=0.3
            )
            response_text = response.choices[0].message.content.strip()
            logging.info("Successfully used OpenAI API for query response")
        except Exception as e:
            logging.error(f"OpenAI error: {e}")
            response_text = None
    
    # Try Gemini if OpenAI failed
    if not response_text and GOOGLE_AI_AVAILABLE and gemini_api_key:
        try:
            model = genai.GenerativeModel('gemini-pro')
            system_prompt = """You are a legal aid assistant for Indian laws. Respond accurately, clearly, and helpfully. 
Provide structured, user-friendly answers based on Indian legal framework. 
If the query is in Hindi or Telugu, respond in the same language. 
Keep answers concise but comprehensive."""
            
            full_prompt = f"{system_prompt}\n\nQuery: {query_input.query_text}"
            response = model.generate_content(full_prompt)
            response_text = response.text.strip()
            logging.info("Successfully used Gemini API for query response")
        except Exception as e:
            logging.error(f"Gemini error: {e}")
            response_text = None
    
    # Try custom AI API if others failed
    if not response_text and ai_api_url:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(ai_api_url, json={"query": query_input.query_text, "language": detected_lang}, timeout=30.0)
                response_data = response.json()
                response_text = response_data.get("response", "Sorry, I couldn't generate a response at this time.")
                logging.info("Successfully used custom AI API for query response")
            except Exception as e:
                logging.error(f"AI API error: {e}")
    
    if not response_text:
        # Fallback to keyword-based
        category = classify_query(query_input.query_text)
        response_text = get_response(category, detected_lang)
        logging.info(f"Used fallback response for category: {category}")
    
    # Create query object
    query_obj = UserQuery(
        query_text=query_input.query_text,
        detected_language=detected_lang,
        category='ai_generated' if (openai_api_key or gemini_api_key or ai_api_url) else classify_query(query_input.query_text),
        response_text=response_text,
        audio_id=None  # No longer generating audio server-side
    )
    
    # Save to database
    doc = query_obj.model_dump()
    await db.user_queries.insert_one(doc)
    
    return query_obj

@api_router.get("/queries", response_model=List[UserQuery])
async def get_queries(limit: int = Query(default=50, le=100)):
    """Get all processed queries."""
    queries = await db.user_queries.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return queries

@api_router.get("/queries/{query_id}", response_model=UserQuery)
async def get_query(query_id: str):
    """Get a specific query by ID."""
    query = await db.user_queries.find_one({"id": query_id}, {"_id": 0})
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")
    return query

# ----- AUDIO -----

@api_router.get("/audio/{audio_id}")
async def get_audio(audio_id: str):
    """Get audio file by ID."""
    audio_path = AUDIO_DIR / f"{audio_id}.mp3"
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio not found")
    return FileResponse(str(audio_path), media_type="audio/mpeg")

# ----- STUDENTS -----

@api_router.post("/students", response_model=Student)
async def create_student(student_input: StudentCreate):
    """Create a new student."""
    student = Student(**student_input.model_dump())
    doc = student.model_dump()
    await db.students.insert_one(doc)
    return student

@api_router.get("/students", response_model=List[Student])
async def get_students():
    """Get all students."""
    students = await db.students.find({}, {"_id": 0}).to_list(100)
    return students

@api_router.get("/students/{student_id}", response_model=Student)
async def get_student(student_id: str):
    """Get a specific student."""
    student = await db.students.find_one({"id": student_id}, {"_id": 0})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student

@api_router.delete("/students/{student_id}")
async def delete_student(student_id: str):
    """Delete a student."""
    result = await db.students.delete_one({"id": student_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Student not found")
    return {"message": "Student deleted successfully"}

@api_router.get("/students/{student_id}/assigned-cases", response_model=List[Case])
async def get_student_cases(student_id: str):
    """Get cases assigned to a student."""
    cases = await db.cases.find({"assigned_student_id": student_id}, {"_id": 0}).to_list(100)
    return cases

# ----- CASES -----

@api_router.post("/cases", response_model=Case)
async def create_case(case_input: CaseCreate):
    """Create a new case."""
    case = Case(**case_input.model_dump())
    doc = case.model_dump()
    await db.cases.insert_one(doc)
    return case

@api_router.get("/cases", response_model=List[Case])
async def get_cases():
    """Get all cases."""
    cases = await db.cases.find({}, {"_id": 0}).to_list(100)
    return cases

@api_router.get("/cases/{case_id}", response_model=Case)
async def get_case(case_id: str):
    """Get a specific case."""
    case = await db.cases.find_one({"id": case_id}, {"_id": 0})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case

@api_router.patch("/cases/{case_id}", response_model=Case)
async def update_case(case_id: str, case_update: CaseUpdate):
    """Update a case."""
    update_data = {k: v for k, v in case_update.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")
    
    result = await db.cases.update_one({"id": case_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Case not found")
    
    case = await db.cases.find_one({"id": case_id}, {"_id": 0})
    return case

@api_router.delete("/cases/{case_id}")
async def delete_case(case_id: str):
    """Delete a case."""
    result = await db.cases.delete_one({"id": case_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Case not found")
    return {"message": "Case deleted successfully"}

# ----- DOCUMENTS -----

@api_router.post("/documents", response_model=LegalDocument)
async def generate_document(doc_input: DocumentCreate):
    """Generate a legal document (FIR or RTI)."""
    if doc_input.doc_type.upper() == "FIR":
        template = FIR_TEMPLATES.get(doc_input.language, FIR_TEMPLATES['en'])
    elif doc_input.doc_type.upper() == "RTI":
        template = RTI_TEMPLATES.get(doc_input.language, RTI_TEMPLATES['en'])
    else:
        raise HTTPException(status_code=400, detail="Invalid document type. Use FIR or RTI")
    
    # Fill template with provided details or placeholders
    details = doc_input.details
    content = template.format(
        name=details.get('name', '[Your Name]'),
        age=details.get('age', '[Age]'),
        address=details.get('address', '[Your Address]'),
        incident_date=details.get('incident_date', '[Date of Incident]'),
        incident_time=details.get('incident_time', '[Time of Incident]'),
        incident_place=details.get('incident_place', '[Place of Incident]'),
        incident_description=details.get('incident_description', '[Describe the incident in detail]'),
        accused_details=details.get('accused_details', '[Details of accused if known]'),
        witness_details=details.get('witness_details', '[Witness names and contacts]'),
        evidence_list=details.get('evidence_list', '[List of evidence/documents]'),
        current_date=details.get('current_date', datetime.now(timezone.utc).strftime('%Y-%m-%d')),
        place=details.get('place', '[Place]'),
        mobile=details.get('mobile', '[Mobile Number]'),
        email=details.get('email', '[Email Address]'),
        department_name=details.get('department_name', '[Department Name]'),
        department_address=details.get('department_address', '[Department Address]'),
        question_1=details.get('question_1', '[Question 1]'),
        question_2=details.get('question_2', '[Question 2]'),
        question_3=details.get('question_3', '[Question 3]'),
        period=details.get('period', '[Time Period]'),
        fee=details.get('fee', '10'),
        payment_mode=details.get('payment_mode', 'Postal Order')
    )
    
    # Create document
    doc = LegalDocument(
        doc_type=doc_input.doc_type.upper(),
        content=content,
        language=doc_input.language,
        case_id=doc_input.case_id
    )
    
    # Save to database
    await db.legal_documents.insert_one(doc.model_dump())
    
    return doc

@api_router.get("/documents", response_model=List[LegalDocument])
async def get_documents():
    """Get all generated documents."""
    docs = await db.legal_documents.find({}, {"_id": 0}).to_list(100)
    return docs

@api_router.get("/documents/{doc_id}", response_model=LegalDocument)
async def get_document(doc_id: str):
    """Get a specific document."""
    doc = await db.legal_documents.find_one({"id": doc_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

# ----- SEED DATA -----

@api_router.post("/seed")
async def seed_database():
    """Seed the database with sample data."""
    try:
        # Clear existing data
        await db.students.delete_many({})
        await db.cases.delete_many({})
        
        # Insert sample students
        student_ids = []
        for student_data in SAMPLE_STUDENTS:
            student = Student(**student_data)
            doc = student.model_dump()
            await db.students.insert_one(doc)
            student_ids.append(student.id)
        
        # Insert sample cases and assign some to students
        for i, case_data in enumerate(SAMPLE_CASES):
            case = Case(**case_data)
            # Assign some cases to students
            if i < len(student_ids):
                case.assigned_student_id = student_ids[i]
                case.status = "assigned"
            doc = case.model_dump()
            await db.cases.insert_one(doc)
        
        return {
            "message": "Database seeded successfully",
            "students_created": len(SAMPLE_STUDENTS),
            "cases_created": len(SAMPLE_CASES)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error seeding database: {str(e)}")

# ----- STATISTICS -----

@api_router.get("/stats")
async def get_statistics():
    """Get system statistics."""
    students_count = await db.students.count_documents({})
    cases_count = await db.cases.count_documents({})
    queries_count = await db.user_queries.count_documents({})
    documents_count = await db.legal_documents.count_documents({})
    
    # Cases by status
    open_cases = await db.cases.count_documents({"status": "open"})
    assigned_cases = await db.cases.count_documents({"status": "assigned"})
    closed_cases = await db.cases.count_documents({"status": "closed"})
    
    return {
        "total_students": students_count,
        "total_cases": cases_count,
        "total_queries": queries_count,
        "total_documents": documents_count,
        "cases_by_status": {
            "open": open_cases,
            "assigned": assigned_cases,
            "closed": closed_cases
        }
    }

# ----- VOICE AI ENDPOINTS -----

class SpeechRequest(BaseModel):
    text: str
    language: str  # "en", "hi", "te"

@api_router.post("/voice-to-text")
async def voice_to_text(audio_file: UploadFile = File(...)):
    """
    Process voice input using Whisper for Speech-to-Text.
    
    Accepts audio file upload (any format supported by torchaudio).
    Returns JSON: { "text": "<transcribed text>" }
    """
    try:
        whisper_model_instance = get_whisper_model()
        if whisper_model_instance is None:
            raise HTTPException(status_code=500, detail="Whisper model failed to load")
            
        # Save uploaded file temporarily
        input_path = AUDIO_DIR / f"input_{uuid.uuid4()}.{audio_file.filename.split('.')[-1] if '.' in audio_file.filename else 'webm'}"
        with open(input_path, "wb") as f:
            content = await audio_file.read()
            f.write(content)
        
        # Load audio with torchaudio for better format handling
        try:
            waveform, sample_rate = torchaudio.load(str(input_path))
        except Exception as load_error:
            logging.error(f"Failed to load audio file: {load_error}")
            # Fallback: try with whisper directly
            result = whisper_model_instance.transcribe(str(input_path), language=None)
            transcribed_text = result["text"].strip()
            input_path.unlink(missing_ok=True)
            return {"text": transcribed_text}
        
        # Resample to 16kHz if needed (Whisper expects 16kHz)
        if sample_rate != 16000:
            resampler = torchaudio.transforms.Resample(sample_rate, 16000)
            waveform = resampler(waveform)
        
        # Convert to numpy array
        audio_array = waveform.squeeze().numpy()
        
        # Transcribe using Whisper with numpy array
        result = whisper_model_instance.transcribe(audio_array, language=None)
        
        # Extract text
        transcribed_text = result["text"].strip()
        logging.info(f"Transcription result: '{transcribed_text}'")
        
        # Clean up
        input_path.unlink(missing_ok=True)
        
        return {"text": transcribed_text}
        
    except Exception as e:
        logging.error(f"Error processing voice: {e}")
        raise HTTPException(status_code=500, detail=f"Voice processing failed: {str(e)}")

@api_router.post("/text-to-speech")
async def text_to_speech(request: TTSRequest):
    """
    Generate speech from text using OpenAI TTS or Piper as fallback.

    Accepts JSON: { "text": "Hello world", "language": "en" }
    Returns audio file (mp3).
    """
    try:
        text = request.text
        language = getattr(request, 'language', 'en')

        if not text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")

        # Generate unique filename
        audio_filename = f"tts_{uuid.uuid4()}.mp3"
        output_path = AUDIO_DIR / audio_filename

        # Try OpenAI TTS first
        if openai_api_key:
            try:
                client = openai.OpenAI(api_key=openai_api_key)
                voice = "alloy"  # Default voice
                if language == "hi":
                    voice = "alloy"  # OpenAI doesn't have Hindi voices, use alloy
                elif language == "te":
                    voice = "alloy"  # Use alloy for Telugu too
                
                response = client.audio.speech.create(
                    model="tts-1",
                    voice=voice,
                    input=text
                )
                
                with open(str(output_path), "wb") as f:
                    f.write(response.content)
                
                return FileResponse(
                    path=output_path,
                    media_type="audio/mpeg",
                    filename="speech.mp3"
                )
            except Exception as e:
                logging.warning(f"OpenAI TTS failed: {e}")

        # Fallback to Piper TTS
        piper_tts_instance = get_piper_tts()
        if piper_tts_instance is None:
            raise HTTPException(status_code=500, detail="TTS models failed to load")
            
        with open(str(output_path), "wb") as wav_file:
            piper_tts_instance.synthesize(text, wav_file)

        # Return the audio file as streaming response
        return FileResponse(
            path=output_path,
            media_type="audio/wav",
            filename="speech.wav"
        )

    except Exception as e:
        logging.error(f"Error generating speech: {e}")
        raise HTTPException(status_code=500, detail=f"Speech generation failed: {str(e)}")

class VoiceQueryRequest(BaseModel):
    language: Optional[str] = None  # Optional language override

@api_router.post("/voice-query")
async def voice_query(audio_file: UploadFile = File(...), language: str = Form(None)):
    """
    Process voice input: transcribe, detect language, get AI answer.
    
    Accepts audio file and optional language override.
    Returns JSON: { "query_text": "...", "language": "en/hi/te", "answer": "..." }
    """
    try:
        whisper_model_instance = get_whisper_model()
        if whisper_model_instance is None:
            raise HTTPException(status_code=500, detail="Whisper model failed to load")
            
        # Step 1: Transcribe audio
        input_path = AUDIO_DIR / f"input_{uuid.uuid4()}.{audio_file.filename.split('.')[-1] if '.' in audio_file.filename else 'webm'}"
        with open(input_path, "wb") as f:
            content = await audio_file.read()
            f.write(content)
        
        # Load audio
        try:
            waveform, sample_rate = torchaudio.load(str(input_path))
        except Exception as load_error:
            logging.error(f"Failed to load audio file: {load_error}")
            result = whisper_model_instance.transcribe(str(input_path), language=None)
            transcribed_text = result["text"].strip()
        else:
            if sample_rate != 16000:
                resampler = torchaudio.transforms.Resample(sample_rate, 16000)
                waveform = resampler(waveform)
            audio_array = waveform.squeeze().numpy()
            result = whisper_model_instance.transcribe(audio_array, language=None)
            transcribed_text = result["text"].strip()
        
        logging.info(f"Transcription: '{transcribed_text}'")
        
        if not transcribed_text:
            return {"query_text": "", "language": "en", "answer": "No speech detected. Please try again."}
        
        # Step 2: Detect language
        detected_lang = language or detect(transcribed_text)
        if detected_lang not in ['en', 'hi', 'te']:
            detected_lang = 'en'  # Default to English
        
        logging.info(f"Detected language: {detected_lang}")
        
        # Step 3: Get AI answer
        answer = None
        system_prompt = """You are a legal aid assistant for Indian laws. Respond accurately, clearly, and helpfully. 
Provide structured, user-friendly answers based on Indian legal framework. 
If the query is in Hindi or Telugu, respond in the same language. 
Keep answers concise but comprehensive."""
        
        user_prompt = f"Query: {transcribed_text}\nLanguage: {detected_lang}"
        
        # Try OpenAI first
        if openai_api_key:
            try:
                client = openai.OpenAI(api_key=openai_api_key)
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=800,
                    temperature=0.3
                )
                answer = response.choices[0].message.content.strip()
                logging.info("Successfully used OpenAI API for voice query response")
            except Exception as e:
                logging.error(f"OpenAI error: {e}")
        
        # Try Gemini if OpenAI failed
        if not answer and GOOGLE_AI_AVAILABLE and gemini_api_key:
            try:
                model = genai.GenerativeModel('gemini-pro')
                full_prompt = f"{system_prompt}\n\n{user_prompt}"
                response = model.generate_content(full_prompt)
                answer = response.text.strip()
                logging.info("Successfully used Gemini API for voice query response")
            except Exception as e:
                logging.error(f"Gemini error: {e}")
        
        # Fallback to keyword-based
        if not answer:
            category = classify_query(transcribed_text)
            answer = get_response(category, detected_lang)
            logging.info(f"Used fallback response for voice query category: {category}")
        
        # Clean up
        input_path.unlink(missing_ok=True)
        
        return {
            "query_text": transcribed_text,
            "language": detected_lang,
            "answer": answer
        }
        
    except Exception as e:
        logging.error(f"Error in voice query: {e}")
        raise HTTPException(status_code=500, detail=f"Voice query processing failed: {str(e)}")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
