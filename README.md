# An Intelligent Legal Aid and Information Retrieval System for Public Assistance

##  Overview

An AI-powered legal assistance platform designed to provide simplified legal guidance, multilingual interaction, and automated sample legal document generation for students and the general public.

The system integrates Artificial Intelligence, Natural Language Processing (NLP), Voice Technologies, and a Student/User Portal to improve legal accessibility and awareness.

---

##  Key Features

-  AI-based Legal Query Processing
-  Voice Input & Text-to-Speech Output
-  Multilingual Support (English, Hindi, Telugu)
-  Automated Legal Document Generation (FIR, RTA, Complaints)
-  Student/User Portal with Query History
-  Secure MongoDB Data Storage
-  FastAPI Backend with React Frontend

---

##  System Architecture

User → Frontend (React.js) → Backend API (FastAPI) → AI Processing Engine → Database (MongoDB) → Response (Text + Voice)

---

##  Tech Stack

### Frontend
- React.js
- Tailwind CSS
- JavaScript (ES6+)
- Axios
- Web Speech API

### Backend
- Python 3.10+
- FastAPI
- Flask
- Pydantic
- HTTPX

### AI & NLP
- OpenAI GPT (Legal reasoning)
- Whisper (Speech-to-Text)
- Language Detection Models

### Database
- MongoDB

---

## 🔐 Security & Environment Variables

This application uses environment variables to manage sensitive configuration. **Never commit your `.env` file to version control.**

### Setup Environment Variables

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your actual credentials:
   ```bash
   # MongoDB Configuration
   MONGO_URL=mongodb://localhost:27017
   DB_NAME=your_database_name

   # AI API Keys (Optional)
   OPENAI_API_KEY=sk-your-actual-openai-key
   GEMINI_API_KEY=your-actual-gemini-key
   AI_API_URL=https://your-ai-api-url.com

   # CORS Configuration
   CORS_ORIGINS=http://localhost:3000,http://localhost:8000
   ```

3. **Important Security Notes:**
   - ✅ The `.env` file is already in `.gitignore` and will not be committed
   - ✅ Use strong, unique API keys for production environments
   - ✅ Rotate API keys regularly
   - ✅ Never share your `.env` file or commit it to the repository
   - ✅ Use different credentials for development and production

### Required Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `MONGO_URL` | Yes | MongoDB connection string | `mongodb://localhost:27017` |
| `DB_NAME` | Yes | Database name | `legal_aid_db` |
| `OPENAI_API_KEY` | No | OpenAI API key for AI features | `your-openai-key-here` |
| `GEMINI_API_KEY` | No | Google Gemini API key | `your-gemini-key-here` |
| `AI_API_URL` | No | Custom AI API endpoint | `https://api.example.com` |
| `CORS_ORIGINS` | No | Allowed CORS origins (comma-separated) | `http://localhost:3000` |

---

##  Project Structure
legal-aid-system/

│

├── frontend/ # React Application

├── backend/ # FastAPI Server

├── database/ # MongoDB Models & Config

├── docs/ # Documentation & Diagrams

└── README.md

---

##  Sample Use Case – FIR/RTA Generation

1. User selects "Generate FIR/RTA"
2. Enters incident details
3. AI processes the input
4. Structured FIR/RTA template is generated
5. User can copy or download the document

---

##  Security Measures

- Environment Variables for API keys
- Input Validation using Pydantic
- CORS Configuration
- Secure MongoDB Connection

---

##  Disclaimer

This system generates **sample legal documents for guidance purposes only**.  
The generated documents are not legally binding and must be verified before official submission.

---

##  Future Scope

- Advocate Consultation Integration
- Government API Integration
- Mobile Application Version
- OCR-based Document Upload
- Expanded Regional Language Support

---

##  License

This project is developed for academic and research purposes.



