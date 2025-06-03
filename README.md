# Dental Notes Pro - AI-Powered Clinical Documentation

A modern web application that helps dental professionals create and manage clinical documentation through voice transcription and AI-powered note generation. Built for efficiency and accuracy in dental practice management.

## 🌟 Features

### Core Functionality
- **Voice-to-Text Transcription** - Real-time speech recognition using Web Speech API
- **AI-Powered Clinical Note Generation** - Professional clinical notes using Qwen3 30B model via OpenRouter
- **Patient Management System** - Complete patient registration, search, and management
- **Clinical Record Templates** - Standardized dental clinical note formatting
- **Copy to Clipboard** - One-click copying of generated clinical notes
- **Note History & Search** - View and search through patient clinical records

### User Experience
- **Beautiful Landing Page** - Modern design with typewriter animations
- **Loading Animations** - Beautiful loading screens during AI processing
- **Responsive Design** - Works seamlessly on desktop and mobile
- **Dark Theme UI** - Professional dark interface with Tailwind CSS
- **Real-time Updates** - Live transcription editing and processing

### Security & Authentication
- **Secure Login System** - Password hashing and session management
- **Dentist-specific Data** - Each dentist only sees their own patients
- **Session-based Security** - Secure cookie-based authentication
- **Data Privacy** - Patient data isolation and secure storage

## 🚀 Technologies Used

### Backend
- **Flask** - Python web framework
- **Redis** - High-performance database for sessions, patients, and notes
- **OpenRouter API** - Access to Qwen3 30B AI model for clinical note generation
- **Werkzeug** - Password hashing and security utilities

### Frontend
- **TailwindCSS** - Modern utility-first CSS framework
- **Vanilla JavaScript** - Client-side interactions and animations
- **Web Speech API** - Browser-based voice recognition
- **Responsive Design** - Mobile-first approach

### Deployment & Infrastructure
- **Vercel** - Serverless deployment platform
- **Redis Cloud** - Managed Redis database
- **Environment Variables** - Secure configuration management
- **Git Version Control** - GitHub repository management

## 📦 Project Structure

```
depaulhackathon-2025/
├── api/
│   ├── index.py              # Main Flask application (Vercel entry point)
│   └── requirements.txt      # Python dependencies for deployment
├── templates/
│   ├── index.html           # Landing page with animations
│   ├── login.html           # Authentication pages
│   ├── register.html        
│   ├── dashboard.html       # Dentist dashboard
│   ├── start_recording.html # Patient selection
│   ├── record.html          # Voice recording interface
│   ├── transcription.html   # Transcription editing
│   ├── clinicalrecord.html  # AI-generated clinical notes
│   ├── patients.html        # Patient management
│   └── patient_notes.html   # Patient history
├── static/
│   ├── css/                 # Stylesheets
│   └── js/                  # JavaScript files
├── data/                    # Local data storage structure
├── .vercel/                 # Vercel deployment configuration
├── vercel.json             # Vercel deployment settings
├── .vercelignore           # Files to ignore during deployment
├── requirements.txt        # Local development dependencies
└── README.md              # This file
```

## 🛠️ Setup Instructions

### Prerequisites
- Python 3.8+
- Redis instance (local or cloud)
- OpenRouter API key

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/milyas2001/depaulhackathon-2025.git
   cd depaulhackathon-2025
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables**
   Create a `.env` file with:
   ```env
   REDIS_URL=your_redis_connection_string
   OPENROUTER_API_KEY=your_openrouter_api_key
   SECRET_KEY=your_secret_key
   ```

5. **Run the application**
   ```bash
   cd api
   python index.py
   ```

6. **Access the application**
   Open http://localhost:8080 in your browser

### Deployment (Vercel)

1. **Connect to Vercel**
   - Link your GitHub repository to Vercel
   - Set environment variables in Vercel dashboard

2. **Environment Variables (Production)**
   ```
   REDIS_URL=your_production_redis_url
   OPENROUTER_API_KEY=your_openrouter_api_key
   SECRET_KEY=your_production_secret_key
   ```

3. **Deploy**
   - Push to main branch triggers automatic deployment
   - Vercel uses `api/index.py` as the entry point

## 🔧 Configuration

### OpenRouter Setup
1. Create account at [OpenRouter.ai](https://openrouter.ai)
2. Generate API key
3. Model used: `qwen/qwen3-30b-a3b:free` (30.5B parameters)

### Redis Setup
- **Local**: Install Redis server
- **Production**: Use Redis Cloud or similar managed service
- **Data Structure**: 
  - Dentists: `dentist:{id}`
  - Patients: `patient:{id}`
  - Notes: `note:{id}`
  - Sessions: `session:{id}`

## 💡 Usage Guide

### For Dental Professionals

1. **Registration/Login**
   - Create account or sign in
   - Secure password-based authentication

2. **Patient Management**
   - Add new patients with unique IDs
   - Search existing patients
   - View patient history

3. **Clinical Documentation**
   - Select patient
   - Record voice notes or type manually
   - Review and edit transcription
   - Generate AI clinical note
   - Copy and save final documentation

4. **Note Management**
   - View patient note history
   - Edit saved notes
   - Professional clinical formatting

## 🤖 AI Clinical Note Generation

### Model Details
- **Model**: Qwen3 30B A3B (30.5 billion parameters)
- **Provider**: OpenRouter
- **Capabilities**: 
  - Professional dental terminology conversion
  - Structured clinical note formatting
  - Template adherence
  - Medical notation accuracy

### Clinical Note Template
```
DENTAL CLINICAL NOTE
Date: [Date]
Time: [Time]
Patient Name: [Patient Name]
Dentist Name: [Dentist Name]

CLINICAL NOTES:
CHIEF COMPLAINT
CLINICAL FINDINGS
TREATMENT PROVIDED
MEDICATIONS
FOLLOW-UP

Note: Please verify all information above.
```

## 🔒 Security Features

- **Password Hashing**: Werkzeug secure password storage
- **Session Management**: Redis-based secure sessions
- **Data Isolation**: Dentist-specific data access
- **HTTPS Ready**: Secure deployment configuration
- **Input Validation**: Form validation and sanitization

## 🎨 UI/UX Features

- **Typewriter Animations**: Engaging landing page effects
- **Loading Screens**: Beautiful AI processing animations
- **Dark Theme**: Professional medical interface
- **Responsive Design**: Mobile and desktop optimized
- **Copy Functionality**: One-click note copying
- **Hover Effects**: Interactive UI elements

## 📊 Database Schema

### Redis Data Structure
```
dentist:{dentist_id} → {id, name, email, password_hash, created_at}
patient:{patient_id} → {id, name, dentist_id, created_at, last_visit, notes_count}
note:{note_id} → {id, content, transcription, timestamp, patient_id, dentist_id}
session:{session_id} → {session_data}
email_to_dentist:{email} → dentist_id
dentist:{dentist_id}:patients → Set of patient_ids
patient:{patient_id}:notes → Set of note_ids
```

## 🚀 Performance

- **Serverless Architecture**: Vercel edge functions
- **Redis Performance**: Sub-millisecond data access
- **AI Model**: 30B parameter model for high-quality generation
- **Frontend Optimization**: Minimal JavaScript, efficient CSS

## 📝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- OpenRouter for AI model access
- Vercel for hosting platform
- Redis for database technology
- TailwindCSS for styling framework

## 📞 Support

For support, email [your-email] or open an issue on GitHub.

---

**Built with ❤️ for dental professionals to streamline clinical documentation**
