from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv
import os
import logging
from pathlib import Path
import uuid
from datetime import datetime, timezone
import whisper
import pyttsx3
from langdetect import detect
from pymongo import MongoClient
from bson import ObjectId
import json
import io

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return super().default(obj)

# Setup
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

app = Flask(__name__)
CORS(app)

# MongoDB setup
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
mongo_client = MongoClient(mongo_url)
db = mongo_client[os.environ.get('DB_NAME', 'test_database')]

# Audio directory
AUDIO_DIR = ROOT_DIR / "audio_files"
AUDIO_DIR.mkdir(exist_ok=True)

# Models (lazy load)
whisper_model = None

def get_whisper_model():
    global whisper_model
    if whisper_model is None:
        logging.info("Loading Whisper model...")
        whisper_model = whisper.load_model("base")
        logging.info("✓ Whisper model loaded")
    return whisper_model

# Legal knowledge base
CATEGORY_KEYWORDS = {
    "fir": ["fir", "police", "complaint", "theft", "crime", "report", "stolen"],
    "rti": ["rti", "right to information", "information", "government", "public"],
    "consumer": ["consumer", "complaint", "product", "defect", "refund"],
    "property": ["property", "land", "ownership", "deed", "tenancy", "lease"],
    "marriage": ["marriage", "divorce", "alimony", "custody", "child"],
    "employment": ["employment", "salary", "wage", "contract", "termination"],
}

def classify_query(query_text):
    query_lower = query_text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in query_lower for keyword in keywords):
            return category
    return "general"

def get_response(category, language="en"):
    responses = {
        "fir": {
            "en": "To file an FIR (First Information Report) with the police:\n1. Visit the nearest police station\n2. Provide written or oral complaint\n3. Police will record your statement\n4. You'll receive an FIR number\n5. Keep this number for reference in legal proceedings",
            "hi": "पुलिस के साथ एफआईआर (प्रथम सूचना रिपोर्ट) दर्ज करने के लिए:\n1. निकटतम पुलिस स्टेशन जाएं\n2. लिखित या मौखिक शिकायत दें\n3. पुलिस आपका बयान दर्ज करेगी\n4. आपको एफआईआर नंबर मिलेगा\n5. कानूनी कार्यवाही में इस नंबर को रखें",
        },
        "rti": {
            "en": "Right to Information (RTI) Act allows you to:\n1. Request government information\n2. File RTI application at the concerned office\n3. Pay applicable fees (usually ₹10)\n4. Response required within 30 days\n5. Appeal if information is denied",
            "hi": "सूचना का अधिकार (आरटीआई) अधिनियम आपको अनुमति देता है:\n1. सरकारी जानकारी का अनुरोध करें\n2. संबंधित कार्यालय में आरटीआई आवेदन दाखिल करें\n3. लागू शुल्क का भुगतान करें (आमतौर पर ₹10)\n4. 30 दिनों के भीतर प्रतिक्रिया आवश्यक है\n5. यदि जानकारी से इनकार किया जाए तो अपील करें",
        },
        "general": {
            "en": "For legal assistance:\n1. Consult with qualified legal advocate\n2. Legal aid available for poor citizens\n3. Contact state bar association\n4. Visit district courts for free services\n5. Document all relevant evidence",
            "hi": "कानूनी सहायता के लिए:\n1. योग्य कानूनी वकील से परामर्श लें\n2. गरीब नागरिकों के लिए कानूनी सहायता उपलब्ध है\n3. राज्य बार एसोसिएशन से संपर्क करें\n4. मुफ्त सेवाओं के लिए जिला अदालतों में जाएं\n5. सभी प्रासंगिक साक्ष्य दस्तावेज़ करें",
        }
    }
    return responses.get(category, {}).get(language, responses["general"]["en"])

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ ROUTES ============

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()})

@app.route('/api/queries', methods=['POST'])
def create_query():
    """Create and respond to legal query"""
    try:
        data = request.get_json()
        query_text = data.get('query_text', '').strip()
        language = data.get('language', 'en')
        
        if not query_text:
            return jsonify({"error": "Query cannot be empty"}), 400
        
        # Classify and get response
        category = classify_query(query_text)
        answer = get_response(category, language)
        
        # Save to database
        query_doc = {
            "id": str(uuid.uuid4()),
            "query_text": query_text,
            "detected_language": language,
            "category": category,
            "response_text": answer,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        db.queries.insert_one(query_doc)
        logger.info(f"✓ Query created: {category}")
        
        # Convert to dict to avoid ObjectId serialization issue
        response_doc = dict(query_doc)
        response_doc.pop('_id', None)
        
        return jsonify(response_doc), 201
    
    except Exception as e:
        logger.error(f"Query error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/documents', methods=['POST'])
def create_document():
    """Generate legal document"""
    try:
        data = request.get_json()
        doc_type = data.get('doc_type', 'FIR').upper()
        language = data.get('language', 'en')
        details = data.get('details', {})
        
        # Generate document content
        if doc_type == 'FIR':
            content = f"""
FIR (First Information Report)
Date: {datetime.now().strftime('%Y-%m-%d')}

Details:
{json.dumps(details, indent=2)}

Instructions:
1. Provide this form to the nearest police station
2. Fill in all required information accurately
3. Keep a copy for your records
4. Note down the FIR number provided by police
"""
        elif doc_type == 'RTI':
            content = f"""
RTI (Right to Information) Application
Date: {datetime.now().strftime('%Y-%m-%d')}

Information Requested:
{json.dumps(details, indent=2)}

Instructions:
1. Submit to the concerned government office
2. Pay the prescribed fee (usually ₹10)
3. Keep the receipt and acknowledgment
4. Follow up within 30 days if no response
"""
        else:
            content = f"Document Type: {doc_type}\n\nDetails:\n{json.dumps(details, indent=2)}"
        
        # Save to database
        doc_id = str(uuid.uuid4())
        doc = {
            "id": doc_id,
            "doc_type": doc_type,
            "language": language,
            "content": content,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        db.documents.insert_one(doc)
        logger.info(f"✓ Document created: {doc_type}")
        
        # Prepare response - remove _id field
        response = dict(doc)
        response.pop('_id', None)
        
        return jsonify(response), 201
    
    except Exception as e:
        logger.error(f"Document error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/voice-to-text', methods=['POST'])
def voice_to_text():
    """Transcribe audio to text"""
    try:
        if 'audio_file' not in request.files:
            return jsonify({"error": "No audio file provided"}), 400
        
        audio_file = request.files['audio_file']
        whisper_model_instance = get_whisper_model()
        
        # Save temporarily
        temp_path = AUDIO_DIR / f"input_{uuid.uuid4()}.webm"
        audio_file.save(str(temp_path))
        
        try:
            # Transcribe
            result = whisper_model_instance.transcribe(str(temp_path), language=None)
            transcribed_text = result["text"].strip()
            logger.info(f"✓ Transcribed: {transcribed_text}")
            
            return jsonify({"text": transcribed_text}), 200
        finally:
            temp_path.unlink(missing_ok=True)
    
    except Exception as e:
        logger.error(f"Voice-to-text error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/text-to-speech', methods=['POST'])
def text_to_speech():
    """Generate speech from text"""
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        language = data.get('language', 'en')
        
        if not text:
            return jsonify({"error": "Text cannot be empty"}), 400
        
        # Generate audio
        tts_engine = pyttsx3.init()
        tts_engine.setProperty('rate', 150)
        tts_engine.setProperty('volume', 0.9)
        
        audio_filename = f"tts_{uuid.uuid4()}.wav"
        output_path = AUDIO_DIR / audio_filename
        
        tts_engine.save_to_file(text, str(output_path))
        tts_engine.runAndWait()
        
        logger.info(f"✓ Generated TTS: {len(text)} characters")
        
        return send_file(str(output_path), mimetype="audio/wav", as_attachment=True, download_name="speech.wav")
    
    except Exception as e:
        logger.error(f"TTS error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/voice-query', methods=['POST'])
def voice_query():
    """Complete voice query: transcribe, classify, respond"""
    try:
        if 'audio_file' not in request.files:
            return jsonify({"error": "No audio file provided"}), 400
        
        audio_file = request.files['audio_file']
        language = request.form.get('language', None)
        
        whisper_model_instance = get_whisper_model()
        
        # Save temporarily
        temp_path = AUDIO_DIR / f"input_{uuid.uuid4()}.webm"
        audio_file.save(str(temp_path))
        
        try:
            # Transcribe
            result = whisper_model_instance.transcribe(str(temp_path), language=None)
            transcribed_text = result["text"].strip()
            
            if not transcribed_text:
                return jsonify({
                    "query_text": "",
                    "language": "en",
                    "answer": "No speech detected. Please try again."
                }), 200
            
            # Detect language
            detected_lang = language or detect(transcribed_text)
            if detected_lang not in ['en', 'hi', 'te']:
                detected_lang = 'en'
            
            # Get response
            category = classify_query(transcribed_text)
            answer = get_response(category, detected_lang)
            
            logger.info(f"✓ Voice query: {category} in {detected_lang}")
            
            return jsonify({
                "query_text": transcribed_text,
                "language": detected_lang,
                "answer": answer
            }), 200
        
        finally:
            temp_path.unlink(missing_ok=True)
    
    except Exception as e:
        logger.error(f"Voice query error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/queries/<query_id>', methods=['GET'])
def get_query(query_id):
    """Get query by ID"""
    try:
        query = db.queries.find_one({"id": query_id})
        if not query:
            return jsonify({"error": "Query not found"}), 404
        
        # Remove MongoDB's _id field
        query.pop('_id', None)
        return jsonify(query), 200
    
    except Exception as e:
        logger.error(f"Get query error: {e}")
        return jsonify({"error": str(e)}), 500

# ============ STUDENTS ============

@app.route('/api/students', methods=['POST'])
def create_student():
    """Create a new student"""
    try:
        data = request.get_json()
        student = {
            "id": str(uuid.uuid4()),
            "name": data.get('name', ''),
            "email": data.get('email', ''),
            "college": data.get('college', ''),
            "skills": data.get('skills', []),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        db.students.insert_one(student)
        logger.info(f"✓ Student created: {student['name']}")
        
        response = dict(student)
        response.pop('_id', None)
        return jsonify(response), 201
    
    except Exception as e:
        logger.error(f"Student creation error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/students', methods=['GET'])
def get_students():
    """Get all students"""
    try:
        students = list(db.students.find({}, {"_id": 0}))
        return jsonify(students), 200
    
    except Exception as e:
        logger.error(f"Get students error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/students/<student_id>', methods=['GET'])
def get_student(student_id):
    """Get a specific student"""
    try:
        student = db.students.find_one({"id": student_id}, {"_id": 0})
        if not student:
            return jsonify({"error": "Student not found"}), 404
        
        return jsonify(student), 200
    
    except Exception as e:
        logger.error(f"Get student error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/students/<student_id>', methods=['DELETE'])
def delete_student(student_id):
    """Delete a student"""
    try:
        result = db.students.delete_one({"id": student_id})
        if result.deleted_count == 0:
            return jsonify({"error": "Student not found"}), 404
        
        logger.info(f"✓ Student deleted: {student_id}")
        return jsonify({"message": "Student deleted successfully"}), 200
    
    except Exception as e:
        logger.error(f"Delete student error: {e}")
        return jsonify({"error": str(e)}), 500

# ============ CASES ============

@app.route('/api/cases', methods=['POST'])
def create_case():
    """Create a new case"""
    try:
        data = request.get_json()
        case = {
            "id": str(uuid.uuid4()),
            "title": data.get('title', ''),
            "description": data.get('description', ''),
            "category": data.get('category', 'general'),
            "status": data.get('status', 'open'),
            "assigned_student_id": data.get('assigned_student_id', None),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        db.cases.insert_one(case)
        logger.info(f"✓ Case created: {case['title']}")
        
        response = dict(case)
        response.pop('_id', None)
        return jsonify(response), 201
    
    except Exception as e:
        logger.error(f"Case creation error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/cases', methods=['GET'])
def get_cases():
    """Get all cases"""
    try:
        cases = list(db.cases.find({}, {"_id": 0}))
        return jsonify(cases), 200
    
    except Exception as e:
        logger.error(f"Get cases error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/cases/<case_id>', methods=['GET'])
def get_case(case_id):
    """Get a specific case"""
    try:
        case = db.cases.find_one({"id": case_id}, {"_id": 0})
        if not case:
            return jsonify({"error": "Case not found"}), 404
        
        return jsonify(case), 200
    
    except Exception as e:
        logger.error(f"Get case error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/cases/<case_id>', methods=['PATCH', 'PUT'])
def update_case(case_id):
    """Update a case"""
    try:
        data = request.get_json()
        update_data = {k: v for k, v in data.items() if v is not None}
        
        if not update_data:
            return jsonify({"error": "No update data provided"}), 400
        
        result = db.cases.update_one({"id": case_id}, {"$set": update_data})
        if result.matched_count == 0:
            return jsonify({"error": "Case not found"}), 404
        
        case = db.cases.find_one({"id": case_id}, {"_id": 0})
        logger.info(f"✓ Case updated: {case_id}")
        return jsonify(case), 200
    
    except Exception as e:
        logger.error(f"Update case error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/cases/<case_id>', methods=['DELETE'])
def delete_case(case_id):
    """Delete a case"""
    try:
        result = db.cases.delete_one({"id": case_id})
        if result.deleted_count == 0:
            return jsonify({"error": "Case not found"}), 404
        
        logger.info(f"✓ Case deleted: {case_id}")
        return jsonify({"message": "Case deleted successfully"}), 200
    
    except Exception as e:
        logger.error(f"Delete case error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/students/<student_id>/assigned-cases', methods=['GET'])
def get_student_cases(student_id):
    """Get cases assigned to a student"""
    try:
        cases = list(db.cases.find({"assigned_student_id": student_id}, {"_id": 0}))
        return jsonify(cases), 200
    
    except Exception as e:
        logger.error(f"Get student cases error: {e}")
        return jsonify({"error": str(e)}), 500

# ============ SEED DATA ============

@app.route('/api/seed', methods=['POST'])
def seed_data():
    """Load sample data into the database"""
    try:
        # Clear existing data
        db.students.delete_many({})
        db.cases.delete_many({})
        
        # Sample students
        sample_students = [
            {
                "id": str(uuid.uuid4()),
                "name": "Rajesh Kumar",
                "email": "rajesh@college.edu",
                "college": "Delhi University Law College",
                "skills": ["Constitutional Law", "Criminal Law"],
                "created_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Priya Singh",
                "email": "priya@college.edu",
                "college": "Mumbai Law School",
                "skills": ["Consumer Rights", "Property Law"],
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        ]
        
        # Sample cases
        sample_cases = [
            {
                "id": str(uuid.uuid4()),
                "title": "Property Dispute - Boundary Issue",
                "description": "Two neighbors in dispute over boundary line",
                "category": "property",
                "status": "open",
                "assigned_student_id": None,
                "created_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "title": "Consumer Complaint - Defective Product",
                "description": "Customer received defective appliance",
                "category": "consumer",
                "status": "open",
                "assigned_student_id": None,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        ]
        
        db.students.insert_many(sample_students)
        db.cases.insert_many(sample_cases)
        
        logger.info(f"✓ Seeded {len(sample_students)} students and {len(sample_cases)} cases")
        return jsonify({
            "message": "Sample data loaded successfully",
            "students": len(sample_students),
            "cases": len(sample_cases)
        }), 201
    
    except Exception as e:
        logger.error(f"Seed data error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    logger.info("Starting Legal Aid System Server...")
    logger.info("Models will load on first use to avoid startup delays")
    logger.info("Server running at http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=False, threaded=True)
