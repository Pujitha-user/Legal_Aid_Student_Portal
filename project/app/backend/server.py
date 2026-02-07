from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
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
from bson import ObjectId

# Audio processing - FREE ALTERNATIVES
import whisper
import pyttsx3
import io
from langdetect import detect

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'test_database')]

# Create the main app
app = FastAPI(title="Legal Aid System", version="1.0.0")
api_router = APIRouter(prefix="/api")

# Audio storage directory
AUDIO_DIR = ROOT_DIR / "audio_files"
AUDIO_DIR.mkdir(exist_ok=True)

# Initialize models - load on demand
whisper_model = None

def get_whisper_model():
    """Lazy-load Whisper model on first use"""
    global whisper_model
    if whisper_model is None:
        try:
            logging.info("Loading Whisper model (first use - this may take a moment)...")
            whisper_model = whisper.load_model("base")
            logging.info("✓ Whisper model loaded successfully")
        except Exception as e:
            logging.error(f"Failed to load Whisper model: {e}")
            raise HTTPException(status_code=500, detail="Whisper model failed to load")
    return whisper_model

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

class Case(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    category: str
    status: str = "open"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    assigned_student_id: Optional[str] = None

class TTSRequest(BaseModel):
    text: str
    language: Optional[str] = "en"

class QueryRequest(BaseModel):
    query: str
    language: Optional[str] = "en"

# ============ LEGAL KNOWLEDGE BASE ============

CATEGORY_KEYWORDS = {
    "fir": ["fir", "police", "complaint", "theft", "crime", "report", "stolen", "attack", "assault", "murder", "robbery", "thana"],
    "rti": ["rti", "right to information", "information", "government", "public", "transparency", "disclosure"],
    "consumer": ["consumer", "complaint", "product", "defect", "quality", "refund", "warranty", "purchase"],
    "property": ["property", "land", "ownership", "deed", "tenancy", "lease", "rent", "boundary"],
    "marriage": ["marriage", "divorce", "alimony", "custody", "child", "maintenance", "dowry", "separation"],
    "employment": ["employment", "salary", "wage", "contract", "termination", "discrimination", "harassment", "leave"],
}

def classify_query(query_text):
    """Classify query into legal categories"""
    query_lower = query_text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in query_lower for keyword in keywords):
            return category
    return "general"

def get_response(category, language="en"):
    """Get legal aid response based on category and language"""
    
    responses = {
        "fir": {
            "en": "To file an FIR (First Information Report) with the police:\n1. Visit the nearest police station\n2. Provide written or oral complaint\n3. Police will record your statement\n4. You'll receive an FIR number\n5. Keep this number for reference in legal proceedings",
            "hi": "पुलिस के साथ एफआईआर (प्रथम सूचना रिपोर्ट) दर्ज करने के लिए:\n1. निकटतम पुलिस स्टेशन जाएं\n2. लिखित या मौखिक शिकायत दें\n3. पुलिस आपका बयान दर्ज करेगी\n4. आपको एफआईआर नंबर मिलेगा\n5. कानूनी कार्यवाही में इस नंबर को रखें",
        },
        "rti": {
            "en": "Right to Information (RTI) Act allows you to:\n1. Request government information\n2. File RTI application at the concerned office\n3. Pay applicable fees (usually ₹10)\n4. Response required within 30 days\n5. Appeal if information is denied",
            "hi": "सूचना का अधिकार (आरटीआई) अधिनियम आपको अनुमति देता है:\n1. सरकारी जानकारी का अनुरोध करें\n2. संबंधित कार्यालय में आरटीआई आवेदन दाखिल करें\n3. लागू शुल्क का भुगतान करें (आमतौर पर ₹10)\n4. 30 दिनों के भीतर प्रतिक्रिया आवश्यक है\n5. यदि जानकारी से इनकार किया जाए तो अपील करें",
        },
        "consumer": {
            "en": "Consumer Protection remedies:\n1. File complaint with District Consumer Commission\n2. Report to local consumer forum\n3. Provide purchase proof and defect details\n4. File within 2 years of purchase\n5. Compensation may include price refund + damages",
            "hi": "उपभोक्ता संरक्षण उपाय:\n1. जिला उपभोक्ता आयोग में शिकायत दर्ज करें\n2. स्थानीय उपभोक्ता मंच को रिपोर्ट करें\n3. खरीद प्रमाण और दोष विवरण प्रदान करें\n4. खरीद के 2 साल के भीतर फाइल करें\n5. मुआवजे में मूल्य की वापसी + हर्जाना शामिल हो सकता है",
        },
        "general": {
            "en": "For legal assistance:\n1. Consult with qualified legal advocate\n2. Legal aid available for poor citizens\n3. Contact state bar association\n4. Visit district courts for free services\n5. Document all relevant evidence",
            "hi": "कानूनी सहायता के लिए:\n1. योग्य कानूनी वकील से परामर्श लें\n2. गरीब नागरिकों के लिए कानूनी सहायता उपलब्ध है\n3. राज्य बार एसोसिएशन से संपर्क करें\n4. मुफ्त सेवाओं के लिए जिला अदालतों में जाएं\n5. सभी प्रासंगिक साक्ष्य दस्तावेज़ करें",
        }
    }
    
    return responses.get(category, {}).get(language, responses["general"]["en"])

# ============ HEALTH CHECK ============

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Legal Aid API running"}

@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}

# ============ VOICE ENDPOINTS ============

@api_router.post("/voice-to-text")
async def voice_to_text(audio_file: UploadFile = File(...)):
    """
    Transcribe audio to text using OpenAI Whisper (FREE)
    
    Returns: {"text": "transcribed text"}
    """
    try:
        whisper_model_instance = get_whisper_model()  # Lazy-load model
        
        # Save uploaded file temporarily
        input_path = AUDIO_DIR / f"input_{uuid.uuid4()}.{audio_file.filename.split('.')[-1] if '.' in audio_file.filename else 'webm'}"
        
        with open(input_path, "wb") as f:
            content = await audio_file.read()
            f.write(content)
        
        try:
            # Transcribe using Whisper
            result = whisper_model_instance.transcribe(str(input_path), language=None)
            transcribed_text = result["text"].strip()
            logging.info(f"✓ Transcribed: '{transcribed_text}'")
            
            return {"text": transcribed_text}
        finally:
            # Clean up
            input_path.unlink(missing_ok=True)
            
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Voice-to-text error: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@api_router.post("/text-to-speech")
async def text_to_speech(request: TTSRequest):
    """
    Generate speech from text using pyttsx3 (FREE, LOCAL)
    
    Returns: Audio file (WAV format)
    """
    try:
        text = request.text
        language = getattr(request, 'language', 'en')
        
        if not text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        # Initialize text-to-speech engine
        tts_engine = pyttsx3.init()
        tts_engine.setProperty('rate', 150)  # Speed
        tts_engine.setProperty('volume', 0.9)  # Volume
        
        # Generate unique filename
        audio_filename = f"tts_{uuid.uuid4()}.wav"
        output_path = AUDIO_DIR / audio_filename
        
        # Save to file
        tts_engine.save_to_file(text, str(output_path))
        tts_engine.runAndWait()
        
        logging.info(f"✓ Generated TTS: {len(text)} characters")
        
        return FileResponse(
            path=output_path,
            media_type="audio/wav",
            filename="speech.wav"
        )
    
    except Exception as e:
        logging.error(f"Text-to-speech error: {e}")
        raise HTTPException(status_code=500, detail=f"Speech generation failed: {str(e)}")

@api_router.post("/voice-query")
async def voice_query(audio_file: UploadFile = File(...), language: str = Form(None)):
    """
    Complete voice query: transcribe audio, detect language, get AI response
    
    Returns: {"query_text": "...", "language": "en/hi", "answer": "..."}
    """
    try:
        whisper_model_instance = get_whisper_model()  # Lazy-load model
        
        # Step 1: Save and transcribe audio
        input_path = AUDIO_DIR / f"input_{uuid.uuid4()}.{audio_file.filename.split('.')[-1] if '.' in audio_file.filename else 'webm'}"
        
        with open(input_path, "wb") as f:
            content = await audio_file.read()
            f.write(content)
        
        try:
            # Transcribe
            result = whisper_model_instance.transcribe(str(input_path), language=None)
            transcribed_text = result["text"].strip()
            logging.info(f"✓ Transcribed: '{transcribed_text}'")
            
            if not transcribed_text:
                return {
                    "query_text": "",
                    "language": "en",
                    "answer": "No speech detected. Please try again."
                }
            
            # Step 2: Detect language
            detected_lang = language or detect(transcribed_text)
            if detected_lang not in ['en', 'hi', 'te']:
                detected_lang = 'en'
            
            logging.info(f"✓ Detected language: {detected_lang}")
            
            # Step 3: Get AI response
            category = classify_query(transcribed_text)
            answer = get_response(category, detected_lang)
            logging.info(f"✓ Category: {category}, Language: {detected_lang}")
            
            return {
                "query_text": transcribed_text,
                "language": detected_lang,
                "answer": answer
            }
        
        finally:
            # Clean up
            input_path.unlink(missing_ok=True)
    
    except Exception as e:
        logging.error(f"Voice query error: {e}")
        raise HTTPException(status_code=500, detail=f"Voice query failed: {str(e)}")

@api_router.post("/text-query")
async def text_query(request: QueryRequest):
    """
    Process text query and return legal aid response
    
    Returns: {"answer": "..."}
    """
    try:
        query_text = request.query.strip()
        language = request.language or 'en'
        
        if not query_text:
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        # Classify and get response
        category = classify_query(query_text)
        answer = get_response(category, language)
        
        return {"answer": answer}
    
    except Exception as e:
        logging.error(f"Text query error: {e}")
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")

# ============ QUERIES (Frontend Compatible) ============

class UserQueryCreate(BaseModel):
    query_text: str
    language: Optional[str] = "en"

@api_router.post("/queries")
async def create_query(query_input: UserQueryCreate):
    """
    Frontend-compatible endpoint: Create and respond to legal query
    
    Returns: {"id": "...", "query_text": "...", "category": "...", "response_text": "..."}
    """
    try:
        query_text = query_input.query_text.strip()
        language = query_input.language or 'en'
        
        if not query_text:
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        # Classify and get response
        category = classify_query(query_text)
        answer = get_response(category, language)
        
        # Create query document in database
        query_doc = {
            "id": str(uuid.uuid4()),
            "query_text": query_text,
            "detected_language": language,
            "category": category,
            "response_text": answer,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.queries.insert_one(query_doc)
        logging.info(f"✓ Query created: {category}")
        
        return query_doc
    
    except Exception as e:
        logging.error(f"Query creation error: {e}")
        raise HTTPException(status_code=500, detail=f"Query creation failed: {str(e)}")

# ============ DOCUMENTS ============

class LegalDocumentCreate(BaseModel):
    doc_type: str  # "FIR" or "RTI"
    language: str = "en"
    details: dict

def generate_fir_document(details: dict, language: str = "en") -> str:
    """Generate FIR (First Information Report) document"""
    
    if language == "hi":
        template = f"""
प्रथम सूचना रिपोर्ट (एफ.आई.आर.)
First Information Report (FIR)
════════════════════════════════════════════════════════════════

रिपोर्ट दिनांक / Report Date: {details.get('current_date', '')}
स्थान / Place: {details.get('place', '')}

विवरण / DETAILS:
────────────────────────────────────────────────────────────────

शिकायतकर्ता का नाम / Complainant Name: {details.get('name', '')}
आयु / Age: {details.get('age', '')}
पता / Address: {details.get('address', '')}
मोबाइल / Mobile: {details.get('mobile', '')}
ईमेल / Email: {details.get('email', '')}

घटना की तारीख / Incident Date: {details.get('incident_date', '')}
घटना का समय / Incident Time: {details.get('incident_time', '')}
घटना का स्थान / Incident Place: {details.get('incident_place', '')}

घटना का विवरण / Incident Description:
{details.get('incident_description', '')}

आरोपित का विवरण / Accused Details:
{details.get('accused_details', '')}

साक्षी का विवरण / Witness Details:
{details.get('witness_details', '')}

साक्ष्य की सूची / Evidence List:
{details.get('evidence_list', '')}

════════════════════════════════════════════════════════════════
यह एफ.आई.आर. पुलिस स्टेशन में दर्ज की जाएगी।
This FIR will be filed with the Police Station.
"""
    else:
        template = f"""
FIRST INFORMATION REPORT (FIR)
════════════════════════════════════════════════════════════════

Report Date: {details.get('current_date', '')}
Place: {details.get('place', '')}

DETAILS:
────────────────────────────────────────────────────────────────

Complainant Name: {details.get('name', '')}
Age: {details.get('age', '')}
Address: {details.get('address', '')}
Mobile: {details.get('mobile', '')}
Email: {details.get('email', '')}

Incident Date: {details.get('incident_date', '')}
Incident Time: {details.get('incident_time', '')}
Incident Place: {details.get('incident_place', '')}

Incident Description:
{details.get('incident_description', '')}

Accused Details:
{details.get('accused_details', '')}

Witness Details:
{details.get('witness_details', '')}

Evidence List:
{details.get('evidence_list', '')}

════════════════════════════════════════════════════════════════
This FIR will be filed with the Police Station.
Complainant Signature: ___________________
Date: ___________________
"""
    return template.strip()

def generate_rti_document(details: dict, language: str = "en") -> str:
    """Generate RTI (Right to Information) Application"""
    
    if language == "hi":
        template = f"""
सूचना का अधिकार आवेदन / RIGHT TO INFORMATION (RTI) APPLICATION
════════════════════════════════════════════════════════════════

आवेदन दिनांक / Application Date: {details.get('current_date', '')}

आवेदनकर्ता का विवरण / APPLICANT DETAILS:
────────────────────────────────────────────────────────────────

नाम / Name: {details.get('name', '')}
पता / Address: {details.get('address', '')}
मोबाइल / Mobile: {details.get('mobile', '')}
ईमेल / Email: {details.get('email', '')}

प्रश्न / QUESTIONS:
────────────────────────────────────────────────────────────────

प्रश्न 1 / Question 1: {details.get('question_1', '')}

प्रश्न 2 / Question 2: {details.get('question_2', '')}

प्रश्न 3 / Question 3: {details.get('question_3', '')}

सूचना की समयावधि / Period: {details.get('period', '')}

विभाग का नाम / Department Name: {details.get('department_name', '')}
विभाग का पता / Department Address: {details.get('department_address', '')}

आवेदन शुल्क / Application Fee: ₹ {details.get('fee', '10')}
भुगतान माध्यम / Payment Mode: {details.get('payment_mode', 'Postal Order')}

════════════════════════════════════════════════════════════════
आवेदनकर्ता के हस्ताक्षर / Applicant Signature: ___________________
दिनांक / Date: ___________________

नोट: यह आवेदन संबंधित सरकारी विभाग में जमा किया जाएगा।
Note: This application will be submitted to the concerned government department.
"""
    else:
        template = f"""
RIGHT TO INFORMATION (RTI) APPLICATION
════════════════════════════════════════════════════════════════

Application Date: {details.get('current_date', '')}

APPLICANT DETAILS:
────────────────────────────────────────────────────────────────

Name: {details.get('name', '')}
Address: {details.get('address', '')}
Mobile: {details.get('mobile', '')}
Email: {details.get('email', '')}

QUESTIONS:
────────────────────────────────────────────────────────────────

Question 1: {details.get('question_1', '')}

Question 2: {details.get('question_2', '')}

Question 3: {details.get('question_3', '')}

Period: {details.get('period', '')}

Department Name: {details.get('department_name', '')}
Department Address: {details.get('department_address', '')}

Application Fee: ₹ {details.get('fee', '10')}
Payment Mode: {details.get('payment_mode', 'Postal Order')}

════════════════════════════════════════════════════════════════
Applicant Signature: ___________________
Date: ___________________

Note: This application will be submitted to the concerned government department.
"""
    return template.strip()

@api_router.post("/documents")
async def create_document(doc_input: LegalDocumentCreate):
    """
    Generate legal documents (FIR or RTI)
    
    Returns: {"id": "...", "doc_type": "...", "content": "..."}
    """
    try:
        doc_type = doc_input.doc_type.upper()
        language = doc_input.language or 'en'
        details = doc_input.details
        
        if doc_type not in ['FIR', 'RTI']:
            raise HTTPException(status_code=400, detail="Invalid document type. Use 'FIR' or 'RTI'")
        
        # Generate document content
        if doc_type == 'FIR':
            content = generate_fir_document(details, language)
        else:  # RTI
            content = generate_rti_document(details, language)
        
        # Save to database
        doc_record = {
            "id": str(uuid.uuid4()),
            "doc_type": doc_type,
            "language": language,
            "content": content,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.documents.insert_one(doc_record)
        logging.info(f"✓ Document generated: {doc_type}")
        
        return doc_record
    
    except Exception as e:
        logging.error(f"Document generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Document generation failed: {str(e)}")

# ============ STUDENTS ============

@api_router.post("/students", response_model=Student)
async def create_student(student_input: StudentCreate):
    """Create a new student"""
    student = Student(**student_input.model_dump())
    doc = student.model_dump()
    await db.students.insert_one(doc)
    return student

@api_router.get("/students", response_model=List[Student])
async def get_students():
    """Get all students"""
    students = await db.students.find({}, {"_id": 0}).to_list(100)
    return students

@api_router.get("/students/{student_id}", response_model=Student)
async def get_student(student_id: str):
    """Get a specific student"""
    student = await db.students.find_one({"id": student_id}, {"_id": 0})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student

@api_router.delete("/students/{student_id}")
async def delete_student(student_id: str):
    """Delete a student"""
    result = await db.students.delete_one({"id": student_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Student not found")
    return {"message": "Student deleted successfully"}

@api_router.get("/students/{student_id}/assigned-cases", response_model=List[Case])
async def get_student_cases(student_id: str):
    """Get cases assigned to a student"""
    cases = await db.cases.find({"assigned_student_id": student_id}, {"_id": 0}).to_list(100)
    return cases

# ============ CASES ============

@api_router.post("/cases", response_model=Case)
async def create_case(case_input: CaseCreate):
    """Create a new case"""
    case = Case(**case_input.model_dump())
    doc = case.model_dump()
    await db.cases.insert_one(doc)
    return case

@api_router.get("/cases", response_model=List[Case])
async def get_cases():
    """Get all cases"""
    cases = await db.cases.find({}, {"_id": 0}).to_list(100)
    return cases

@api_router.get("/cases/{case_id}", response_model=Case)
async def get_case(case_id: str):
    """Get a specific case"""
    case = await db.cases.find_one({"id": case_id}, {"_id": 0})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case

@api_router.patch("/cases/{case_id}", response_model=Case)
async def update_case(case_id: str, case_update: CaseUpdate):
    """Update a case"""
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
    """Delete a case"""
    result = await db.cases.delete_one({"id": case_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Case not found")
    return {"message": "Case deleted successfully"}

# Include the router
app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Shutdown event - disabled for now to debug startup issues
# @app.on_event("shutdown")
# async def shutdown_db_client():
#     try:
#         client.close()
#         logging.info("Database connection closed")
#     except Exception as e:
#         logging.error(f"Error closing database: {e}")
