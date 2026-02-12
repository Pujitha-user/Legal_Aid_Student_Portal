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

##  Project Structure
legal-aid-system/

│

├── frontend/ # React Application

├── backend/ # FastAPI Server

├── database/ # MongoDB Models & Config

├── docs/ # Documentation & Diagrams

└── README.md

---

## Setup Instructions

### Environment Configuration

The application requires environment variables to be configured before running. Follow these steps:

1. Navigate to the backend directory:
   ```bash
   cd project/app/backend
   ```

2. Create a `.env` file based on the `.env.example` template:
   ```bash
   cp .env.example .env
   ```

3. Edit the `.env` file and configure the required variables:
   - **MONGO_URL**: MongoDB connection string (Required)
   - **DB_NAME**: Database name for the application (Required)

   Example:
   ```
   MONGO_URL=mongodb://localhost:27017
   DB_NAME=legal_aid_db
   ```

4. **Important**: Never commit the `.env` file to version control as it may contain sensitive credentials. The `.env` file is already included in `.gitignore`.

### Running the Application

After configuring the environment variables, you can start the backend server:

```bash
cd project/app/backend
python app.py
```

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



