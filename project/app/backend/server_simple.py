from fastapi import FastAPI, APIRouter, HTTPException
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

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ CATEGORY CLASSIFICATION ============

CATEGORY_KEYWORDS = {
    "fir": ["fir", "police", "complaint", "theft", "crime"],
    "rti": ["rti", "right to information", "government", "public"],
    "consumer": ["consumer", "complaint", "product", "defect", "refund"],
    "property": ["property", "land", "ownership", "deed", "tenancy"],
    "marriage": ["marriage", "divorce", "alimony", "custody"],
    "employment": ["employment", "salary", "wage", "contract"],
}

def classify_query(query_text):
    """Classify query into legal categories"""
    query_lower = query_text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in query_lower for keyword in keywords):
            return category
    return "general"

RESPONSES = {
    "fir": {
        "en": "To file an FIR (First Information Report):\n1. Visit nearest police station\n2. Provide your complaint\n3. Police will record and give you an FIR number\n4. Keep the number for legal proceedings",
        "hi": "एफआईआर दर्ज करने के लिए:\n1. निकटतम पुलिस स्टेशन जाएं\n2. अपनी शिकायत दें\n3. पुलिस एफआईआर नंबर देगी\n4. कानूनी कार्यवाही के लिए संरक्षित रखें",
    },
    "rti": {
        "en": "RTI (Right to Information) Process:\n1. File RTI application at concerned office\n2. Pay applicable fees (usually ₹10)\n3. Response required within 30 days\n4. Appeal if information is denied",
        "hi": "आरटीआई (सूचना का अधिकार):\n1. संबंधित कार्यालय में आवेदन करें\n2. शुल्क का भुगतान करें (₹10)\n3. 30 दिनों में जवाब\n4. इनकार पर अपील करें",
    },
    "consumer": {
        "en": "Consumer Protection:\n1. File complaint with Consumer Commission\n2. Provide purchase proof\n3. Describe the defect\n4. Get compensation + refund",
        "hi": "उपभोक्ता संरक्षण:\n1. उपभोक्ता आयोग में शिकायत करें\n2. खरीद प्रमाण प्रदान करें\n3. समस्या का विवरण दें\n4. मुआवजा + वापसी पाएं",
    },
    "general": {
        "en": "For legal help:\n1. Consult a qualified lawyer\n2. Legal aid available for poor citizens\n3. Contact state bar association\n4. Document all evidence",
        "hi": "कानूनी मदद के लिए:\n1. योग्य वकील से मिलें\n2. गरीब नागरिकों के लिए कानूनी सहायता\n3. राज्य बार एसोसिएशन से संपर्क करें\n4. सभी साक्ष्य दस्तावेज़ करें",
    }
}

def get_response(category, language="en"):
    """Get legal response based on category and language"""
    return RESPONSES.get(category, {}).get(language, RESPONSES["general"]["en"])

# ============ MODELS ============

class UserQueryCreate(BaseModel):
    query_text: str
    language: Optional[str] = "en"

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

# ============ ENDPOINTS ============

@app.get("/")
async def root():
    return {"message": "Legal Aid API Running"}

@api_router.get("/health")
async def health_check():
    """Health check"""
    return {"status": "healthy"}

@api_router.post("/queries")
async def create_query(query_input: UserQueryCreate):
    """Create and respond to legal query"""
    try:
        query_text = query_input.query_text.strip()
        language = query_input.language or 'en'
        
        if not query_text:
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        category = classify_query(query_text)
        answer = get_response(category, language)
        
        query_doc = {
            "id": str(uuid.uuid4()),
            "query_text": query_text,
            "detected_language": language,
            "category": category,
            "response_text": answer,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.queries.insert_one(query_doc)
        logger.info(f"✓ Query created: {category}")
        
        return query_doc
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/queries/{query_id}")
async def get_query(query_id: str):
    """Get a query by ID"""
    try:
        query = await db.queries.find_one({"id": query_id})
        if not query:
            raise HTTPException(status_code=404, detail="Query not found")
        query.pop("_id", None)
        return query
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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

@api_router.post("/cases", response_model=dict)
async def create_case(case_input: CaseCreate):
    """Create a new case"""
    case_doc = {
        "id": str(uuid.uuid4()),
        **case_input.model_dump(),
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.cases.insert_one(case_doc)
    case_doc.pop("_id", None)
    return case_doc

# Include router
app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("✓ Application initialized successfully")
