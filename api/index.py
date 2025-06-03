from flask import Flask, render_template, jsonify, request, redirect, url_for, make_response
import os
import uuid
from datetime import datetime, timedelta
import logging
import sys
import json
import traceback
import re
import requests # For OpenRouter
# from dotenv import load_dotenv # Not needed on Vercel
import secrets

# For Redis
import redis
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables from .env for local development
# load_dotenv() # Not needed on Vercel

app = Flask(__name__,
            template_folder='../templates',
            static_folder='../static')

# Configure secret key
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24))

# Simplified Redis connection setup
redis_client = None
redis_url = os.environ.get('REDIS_URL')

if redis_url:
    try:
        logger.info("Attempting to connect to Redis...")
        redis_client = redis.Redis.from_url(redis_url)
        redis_client.ping()  # Test connection
        logger.info("Successfully connected to Redis")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {str(e)}")
        redis_client = None
else:
    logger.warning("REDIS_URL not found in environment variables")

# Custom session management instead of Flask-Session
def get_session_id():
    """Get or create session ID from cookies"""
    session_id = request.cookies.get('session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
    return session_id

def get_session_data(session_id):
    """Get session data from Redis or return empty dict"""
    if not redis_client:
        return {}
    try:
        session_data = redis_client.get(f"session:{session_id}")
        if session_data:
            return json.loads(session_data)
    except Exception as e:
        logger.error(f"Error getting session data: {str(e)}")
    return {}

def save_session_data(session_id, data):
    """Save session data to Redis"""
    if not redis_client:
        return False
    try:
        redis_client.set(f"session:{session_id}", json.dumps(data), ex=86400)  # 24 hour expiry
        return True
    except Exception as e:
        logger.error(f"Error saving session data: {str(e)}")
        return False

def get_session():
    """Get current session data"""
    session_id = get_session_id()
    return get_session_data(session_id)

def update_session(data):
    """Update session data and ensure cookie is set"""
    session_id = get_session_id()
    current_data = get_session_data(session_id)
    current_data.update(data)
    if save_session_data(session_id, current_data):
        # Set session cookie in response if not already set
        if not request.cookies.get('session_id'):
            response = make_response()
            response.set_cookie('session_id', session_id, max_age=86400, httponly=True)
            return session_id, response
    return session_id, None

# OpenRouter API Key
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')
if not OPENROUTER_API_KEY:
    logger.warning("OPENROUTER_API_KEY not found in environment variables")

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        dentist_id = request.cookies.get('dentist_id')
        if not dentist_id or not get_dentist_from_kv(dentist_id):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Database functions
def get_dentist_from_kv(dentist_id):
    if not redis_client:
        return None
    
    dentist_data = redis_client.get(f"dentist:{dentist_id}")
    if not dentist_data:
        return None
    
    try:
        return json.loads(dentist_data)
    except:
        return None

def save_dentist_to_kv(dentist_data):
    if not redis_client:
        return False
    
    try:
        redis_client.set(f"dentist:{dentist_data['id']}", json.dumps(dentist_data))
        return True
    except Exception as e:
        logger.error(f"Error saving dentist to KV: {str(e)}")
        return False

def get_patient_from_kv(patient_id, dentist_id=None):
    if not redis_client:
        return None
    
    patient_data = redis_client.get(f"patient:{patient_id}")
    if not patient_data:
        return None
    
    try:
        patient = json.loads(patient_data)
        # If dentist_id is provided, ensure patient belongs to this dentist
        if dentist_id and patient.get('dentist_id') != dentist_id:
            return None
        return patient
    except:
        return None

def save_patient_to_kv(patient_data):
    if not redis_client:
        return False
    
    try:
        redis_client.set(f"patient:{patient_data['id']}", json.dumps(patient_data))
        # Add to dentist's patient list
        dentist_id = patient_data.get('dentist_id')
        if dentist_id:
            redis_client.sadd(f"dentist:{dentist_id}:patients", patient_data['id'])
        return True
    except Exception as e:
        logger.error(f"Error saving patient to KV: {str(e)}")
        return False

def get_note_from_kv(note_id):
    if not redis_client:
        return None
    
    note_data = redis_client.get(f"note:{note_id}")
    if not note_data:
        return None
    
    try:
        return json.loads(note_data)
    except:
        return None

def save_note_to_kv(note_data):
    if not redis_client:
        return False
    
    try:
        redis_client.set(f"note:{note_data['id']}", json.dumps(note_data))
        # Add to patient's note list
        patient_id = note_data.get('patient_id')
        if patient_id:
            redis_client.sadd(f"patient:{patient_id}:notes", note_data['id'])
        return True
    except Exception as e:
        logger.error(f"Error saving note to KV: {str(e)}")
        return False

def get_patient_notes_from_kv(patient_id):
    if not redis_client:
        return []
    
    try:
        note_ids = redis_client.smembers(f"patient:{patient_id}:notes")
        notes = []
        for note_id in note_ids:
            note_id_str = note_id.decode('utf-8') if isinstance(note_id, bytes) else note_id
            note = get_note_from_kv(note_id_str)
            if note:
                notes.append(note)
        return notes
    except Exception as e:
        logger.error(f"Error getting patient notes from KV: {str(e)}")
        return []

def get_dentist_patients(dentist_id):
    if not redis_client:
        return []
    
    try:
        patient_ids = redis_client.smembers(f"dentist:{dentist_id}:patients")
        patients = []
        for patient_id in patient_ids:
            patient_id_str = patient_id.decode('utf-8') if isinstance(patient_id, bytes) else patient_id
            patient = get_patient_from_kv(patient_id_str)
            if patient:
                patients.append(patient)
        return patients
    except Exception as e:
        logger.error(f"Error getting dentist patients from KV: {str(e)}")
        return []

def delete_patient_from_kv(patient_id, dentist_id):
    """Deletes a patient and all their associated notes from Redis."""
    if not redis_client:
        logger.error("Redis client not available for deleting patient.")
        return False
    
    try:
        # Ensure patient belongs to the dentist
        patient = get_patient_from_kv(patient_id, dentist_id)
        if not patient:
            logger.warning(f"Attempt to delete patient {patient_id} not belonging to dentist {dentist_id} or patient not found.")
            return False

        logger.info(f"Starting deletion for patient {patient_id} belonging to dentist {dentist_id}")
        
        # 1. Get all notes associated with the patient
        note_ids = redis_client.smembers(f"patient:{patient_id}:notes")
        
        # 2. Delete each note individually
        for note_id_bytes in note_ids:
            note_id = note_id_bytes.decode('utf-8') if isinstance(note_id_bytes, bytes) else note_id_bytes
            logger.info(f"Deleting note {note_id} for patient {patient_id}")
            redis_client.delete(f"note:{note_id}")
        
        # 3. Delete the patient's notes set
        redis_client.delete(f"patient:{patient_id}:notes")
        
        # 4. Remove patient from dentist's patient list
        redis_client.srem(f"dentist:{dentist_id}:patients", patient_id)
        logger.info(f"Removed patient {patient_id} from dentist {dentist_id}'s patient list")
        
        # 5. Delete the patient record itself
        redis_client.delete(f"patient:{patient_id}")
        logger.info(f"Deleted patient record {patient_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error deleting patient from KV: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def is_patient_id_unique(patient_id):
    """Check if a patient ID is unique across the entire system."""
    if not redis_client:
        logger.error("Redis client not available for checking patient ID uniqueness")
        return False
    
    try:
        # Check if any patient with this ID exists
        existing_patient = redis_client.get(f"patient:{patient_id}")
        return existing_patient is None
    except Exception as e:
        logger.error(f"Error checking patient ID uniqueness: {str(e)}")
        return False

def validate_patient_id_format(patient_id):
    """Validate patient ID format and return error message if invalid."""
    if not patient_id:
        return "Patient ID is required"
    
    patient_id = patient_id.strip()
    
    if len(patient_id) < 3:
        return "Patient ID must be at least 3 characters long"
    
    if len(patient_id) > 50:
        return "Patient ID must be 50 characters or less"
    
    # Allow alphanumeric, hyphens, and underscores
    if not re.match(r'^[a-zA-Z0-9_-]+$', patient_id):
        return "Patient ID can only contain letters, numbers, hyphens, and underscores"
    
    return None  # No validation errors

def process_speech_text(text):
    text = text.strip()
    common_endings = ['patient', 'treatment', 'cavity', 'procedure', 'tooth', 'examination', 'recommended', 'performed', 'completed', 'noted', 'observed', 'found', 'present', 'visible', 'detected']
    words = text.split()
    processed_words = []
    for i, word in enumerate(words):
        processed_words.append(word)
        if (i < len(words) - 1 and word.lower() in common_endings and words[i + 1][0].isupper()):
            processed_words[-1] = word + "."
        if (re.match(r'#?\d{1,2}$', word) and i < len(words) - 1 and not words[i + 1].startswith('#')):
            processed_words[-1] = word + ","
        if word.lower() in ['however', 'additionally', 'furthermore', 'moreover']:
            processed_words[-1] = word + ","
    text = ' '.join(processed_words)
    if not text.endswith(('.', '!', '?')): text += '.'
    text = re.sub(r'\band\s+and\s+', ' and ', text)
    text = re.sub(r'\bum\s+', '', text)
    text = re.sub(r'\buh\s+', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text

def generate_clinical_note(transcription, patient_name):
    """Generate a clinical note using Qwen3 8B through OpenRouter."""
    try:
        logger.info(f"Starting clinical note generation for patient: {patient_name}")
        logger.info(f"Transcription length: {len(transcription)}")
        
        if not OPENROUTER_API_KEY:
            logger.error("OpenRouter API key not found in environment variables")
            return generate_basic_note(transcription, patient_name)

        # Get dentist name from current dentist
        dentist_id = request.cookies.get('dentist_id')
        dentist_name = 'Doctor'
        if dentist_id:
            dentist = get_dentist_from_kv(dentist_id)
            if dentist:
                dentist_name = dentist.get('name', 'Doctor')

        # Get current timestamp for the clinical note
        current_time = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        logger.info(f"Using timestamp: {current_time}")

        prompt = f"""Task: Convert an informal dental transcription into a formal dental clinical note that follows the exact template and style provided below.

TEMPLATE TO FOLLOW:
---
DENTAL CLINICAL NOTE
Date: [Date]
Time: [Time]
Patient Name: [Patient Name]
Dentist Name: [Dentist Name]

CLINICAL NOTES:
CHIEF COMPLAINT  
[Patient's main complaint and reason for visit]

CLINICAL FINDINGS  
[Detailed clinical observations, tooth conditions, and diagnostic findings]

TREATMENT PROVIDED  
[Specific treatments, procedures, and interventions performed]

MEDICATIONS  
[Prescribed medications with dosages and instructions]

FOLLOW-UP  
[Follow-up instructions and recommendations]

Note: Please verify all information above.
---

INSTRUCTIONS:
1. Use the EXACT template format shown above
2. Convert the informal transcription into professional dental terminology
3. Organize information into the specified sections
4. Use proper dental notation (tooth numbers, procedures)
5. If information for a section is missing from the transcription, write "None documented" for that section
6. Do NOT use ** or any asterisk formatting
7. Keep the professional, clinical tone throughout
8. Fix any typos or informal language from the transcription
9. Include specific details about tooth numbers, procedures, and findings

Date: {current_time.split(' at ')[0]}
Time: {current_time.split(' at ')[1]}
Patient Name: {patient_name}
Dentist Name: {dentist_name}

Transcription to convert:
{transcription}

Generate the clinical note following the exact template format above."""

        logger.info(f"Preparing OpenRouter API call for patient: {patient_name}")
        logger.info(f"Using model: qwen/qwen3-30b-a3b:free")
        logger.info(f"Prompt length: {len(prompt)}")
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://depaulhackathon-2025.vercel.app/",
            "X-Title": "Dental Notes Pro",
            "X-Model": "qwen/qwen3-30b-a3b:free"
        }
        
        data = {
            "model": "qwen/qwen3-30b-a3b:free",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1000,
            "temperature": 0.7,
            "stream": False,
            "top_p": 0.9,
            "frequency_penalty": 0.1
        }
        
        logger.info("Sending request to OpenRouter API...")
        logger.info(f"Request headers: {headers}")
        logger.info(f"Request data keys: {list(data.keys())}")
        
        # Set a timeout for the request to prevent hanging
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30  # Increased timeout to 30 seconds
        )
        
        logger.info(f"OpenRouter API response status: {response.status_code}")
        logger.info(f"OpenRouter API response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                logger.info(f"OpenRouter API response structure: {list(result.keys()) if result else 'None'}")
                
                if result and "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"]
                    logger.info("Successfully received response from OpenRouter")
                    logger.info(f"Generated note length: {len(content)} characters")
                    logger.info(f"Generated note preview: {content[:200]}...")
                    return content
                else:
                    logger.error("OpenRouter API returned invalid response structure")
                    logger.error(f"Full response: {result}")
                    raise Exception("Invalid API response structure")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse OpenRouter response as JSON: {str(e)}")
                logger.error(f"Raw response text: {response.text}")
                raise Exception("Invalid JSON response from OpenRouter")
        elif response.status_code == 401:
            logger.error("OpenRouter API authentication failed - invalid API key")
            raise Exception("OpenRouter API authentication failed")
        elif response.status_code == 429:
            logger.error("OpenRouter API rate limit exceeded")
            raise Exception("Rate limit exceeded - please try again later")
        else:
            error_msg = f"OpenRouter API error: {response.status_code}"
            try:
                error_data = response.json()
                if 'error' in error_data:
                    error_msg += f" - {error_data['error']}"
                elif 'message' in error_data:
                    error_msg += f" - {error_data['message']}"
                logger.error(f"OpenRouter API error details: {error_data}")
            except:
                error_msg += f" - {response.text}"
                logger.error(f"OpenRouter API error text: {response.text}")
            
            raise Exception(error_msg)
        
    except requests.exceptions.Timeout:
        logger.error("OpenRouter API request timed out after 30 seconds")
        raise Exception("API request timed out - please try again")
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error calling OpenRouter API: {str(e)}")
        raise Exception("Network error - please check your connection")
    except Exception as e:
        logger.error(f"Error generating clinical note: {str(e)}")
        logger.error(traceback.format_exc())
        raise Exception(f"Error generating note: {str(e)}")

def enhance_fallback_note(basic_note, transcription):
    """Extract key information from transcription to enhance a basic note template"""
    try:
        # Extract tooth numbers mentioned
        tooth_pattern = r'#?\s*(\d{1,2})'
        tooth_matches = re.findall(tooth_pattern, transcription)
        teeth_mentioned = list(set(tooth_matches))
        
        # Extract potential symptoms
        symptom_words = ['pain', 'ache', 'sensitivity', 'discomfort', 'swelling', 'bleeding']
        symptoms = [word for word in symptom_words if word in transcription.lower()]
        
        # Extract potential medications
        med_words = ['ibuprofen', 'antibiotics', 'painkillers', 'painkiller', 'medication', 'tylenol', 'advil']
        meds = [word for word in med_words if word in transcription.lower()]
        
        # Extract numbers that might be frequencies/durations (e.g., "2 weeks", "3 times")
        number_pattern = r'(\d+)\s*(day|days|week|weeks|time|times|hour|hours)'
        time_matches = re.findall(number_pattern, transcription.lower())
        
        # Enhance the basic note
        enhanced_note = basic_note
        
        # Add teeth if found
        if teeth_mentioned:
            teeth_str = ", ".join([f"#{t}" for t in teeth_mentioned])
            enhanced_note = enhanced_note.replace("CLINICAL FINDINGS:\nNone documented.", 
                                                f"CLINICAL FINDINGS:\nExamination of tooth {teeth_str}.")
        
        # Add symptoms if found
        if symptoms:
            symptoms_str = ", ".join(symptoms)
            if "None documented" in enhanced_note.split("CHIEF COMPLAINT:")[1].split("CLINICAL FINDINGS:")[0]:
                enhanced_note = enhanced_note.replace("CHIEF COMPLAINT:\nNone documented.", 
                                                    f"CHIEF COMPLAINT:\nPatient presented with {symptoms_str}.")
        
        # Add meds if found
        if meds:
            meds_str = ", ".join(meds)
            enhanced_note = enhanced_note.replace("MEDICATIONS:\nNone documented.",
                                                f"MEDICATIONS:\n{meds_str.title()} recommended.")
        
        # Add follow-up if time periods found
        if time_matches:
            time_str = ", ".join([f"{num} {unit}" for num, unit in time_matches])
            enhanced_note = enhanced_note.replace("FOLLOW-UP:\nNone documented.",
                                                f"FOLLOW-UP:\nRecommended follow-up in {time_str}.")
        
        return enhanced_note
    except Exception as e:
        logger.error(f"Error enhancing fallback note: {str(e)}")
        return basic_note

def generate_basic_note(transcription, patient_name):
    """Generate a basic clinical note template."""
    return f"""CHIEF COMPLAINT:
None documented.

CLINICAL FINDINGS:
None documented.

TREATMENT PROVIDED:
None documented.

MEDICATIONS:
None documented.

FOLLOW-UP:
None documented.

Note: This clinical note was generated with AI assistance. Please verify all information for accuracy."""

def init_session():
    """Initialize session data with defaults"""
    session_data = get_session()
    
    # Set defaults if not present
    if 'patients' not in session_data:
        session_data['patients'] = {}
    if 'recent_patients' not in session_data:
        session_data['recent_patients'] = []
    if 'current_patient' not in session_data:
        session_data['current_patient'] = None
    if 'current_note_data' not in session_data:
        session_data['current_note_data'] = None
    if 'dentist_name' not in session_data:
        session_data['dentist_name'] = 'Doctor'
    
    # Update session with defaults
    session_id, session_response = update_session(session_data)
    return session_data, session_id

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            return render_template('login.html', error="Please enter both email and password")
        
        if redis_client:
            dentist_id = redis_client.get(f"email_to_dentist:{email}")
            if not dentist_id:
                return render_template('login.html', error="Invalid email or password")
            
            dentist_id = dentist_id.decode('utf-8') if isinstance(dentist_id, bytes) else dentist_id
            dentist = get_dentist_from_kv(dentist_id)
            
            if not dentist or not check_password_hash(dentist['password_hash'], password):
                return render_template('login.html', error="Invalid email or password")
            
            response = make_response(redirect(url_for('dashboard')))
            response.set_cookie('dentist_id', dentist_id, max_age=86400*30)  # 30 days
            return response
        else:
            return render_template('login.html', error="Database not available")
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not name or not email or not password:
            return render_template('register.html', error="Please fill all fields")
        
        if redis_client:
            if redis_client.get(f"email_to_dentist:{email}"):
                return render_template('register.html', error="Email already registered")
            
            dentist_id = str(uuid.uuid4())
            dentist_data = {
                'id': dentist_id,
                'name': name,
                'email': email,
                'password_hash': generate_password_hash(password),
                'created_at': datetime.now().isoformat()
            }
            
            if save_dentist_to_kv(dentist_data):
                redis_client.set(f"email_to_dentist:{email}", dentist_id)
                response = make_response(redirect(url_for('dashboard')))
                response.set_cookie('dentist_id', dentist_id, max_age=86400*30)  # 30 days
                return response
            else:
                return render_template('register.html', error="Registration failed")
        else:
            return render_template('register.html', error="Database not available")
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    response = make_response(redirect(url_for('login')))
    response.delete_cookie('dentist_id')
    return response

# Application routes
@app.route('/')
def home():
    dentist_id = request.cookies.get('dentist_id')
    if dentist_id and get_dentist_from_kv(dentist_id):
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/api/health')
def health_check():
    return jsonify({"status": "ok"})

@app.route('/dashboard')
@login_required
def dashboard():
    dentist_id = request.cookies.get('dentist_id')
    dentist = get_dentist_from_kv(dentist_id)
    
    recent_patients = get_dentist_patients(dentist_id)[:5]  # Get 5 most recent patients
    
    return render_template('dashboard.html', 
                          dentist=dentist,
                          recent_patients=recent_patients)

@app.route('/start-recording', methods=['POST', 'GET'])
@login_required
def start_recording():
    try:
        dentist_id = request.cookies.get('dentist_id')
        logger.info(f"Start recording accessed by dentist: {dentist_id}")
        
        if request.method == 'POST':
            logger.info("Processing POST request to start-recording")
            
            # Log all form data for debugging
            logger.info(f"All form data: {request.form}")
            
            patient_id = request.form.get('patient_id')
            new_patient_name = request.form.get('new_patient_name')
            new_patient_id = request.form.get('new_patient_id')
            
            logger.info(f"Form data - patient_id: {patient_id}, new_patient_name: {new_patient_name}, new_patient_id: {new_patient_id}")
            
            if not patient_id and not new_patient_name:
                logger.warning("No patient selected or new patient name provided")
                return redirect(url_for('start_recording', error="Please select a patient or enter a new patient name"))
            
            if new_patient_name:
                if not new_patient_id:
                    logger.warning("New patient ID not provided")
                    return redirect(url_for('start_recording', error="Please provide both patient name and ID for new patients"))
                
                logger.info(f"Creating new patient: {new_patient_name} with ID: {new_patient_id}")
                
                # Validate patient ID format
                new_patient_id = new_patient_id.strip()
                format_error = validate_patient_id_format(new_patient_id)
                if format_error:
                    logger.warning(f"Invalid patient ID format: {new_patient_id} - {format_error}")
                    return redirect(url_for('start_recording', error=format_error))
                
                # Check if patient ID is unique across the entire system
                if not is_patient_id_unique(new_patient_id):
                    logger.warning(f"Patient ID {new_patient_id} already exists")
                    return redirect(url_for('start_recording', error=f"Patient ID '{new_patient_id}' already exists. Please choose a different ID."))
                
                # Check if patient with same name already exists for this dentist
                existing_patients = get_dentist_patients(dentist_id)
                if any(p['name'].lower() == new_patient_name.lower() for p in existing_patients):
                    logger.warning(f"Patient with name {new_patient_name} already exists")
                    return redirect(url_for('start_recording', error=f"A patient named '{new_patient_name}' already exists. Please use a different name or select the existing patient."))
                
                # Use the provided patient ID
                patient_id = new_patient_id
                logger.info(f"Using provided patient_id: {patient_id}")
                
                patient_data = {
                    'id': patient_id,
                    'name': new_patient_name.strip(),
                    'dentist_id': dentist_id,
                    'created_at': datetime.now().isoformat(),
                    'last_visit': datetime.now().isoformat(),
                    'notes_count': 0
                }
                
                logger.info(f"Attempting to save patient: {patient_data}")
                if not save_patient_to_kv(patient_data):
                    logger.error("Failed to save new patient to KV")
                    return redirect(url_for('start_recording', error="Failed to create new patient"))
                logger.info(f"Successfully saved new patient with ID: {patient_id}")
            
            # Validate patient_id exists and belongs to dentist
            if patient_id:
                logger.info(f"Attempting to get patient {patient_id} for dentist {dentist_id}")
                patient = get_patient_from_kv(patient_id, dentist_id)
                if not patient:
                    logger.error(f"Patient {patient_id} not found or not accessible by dentist {dentist_id}")
                    return redirect(url_for('start_recording', error="Invalid patient selected"))
                
                logger.info(f"Successfully found patient: {patient.get('name')}, redirecting to record/{patient_id}")
                response = make_response(redirect(url_for('record', patient_id=patient_id)))
                return response
        
        # GET request - show patient selection form
        logger.info("Processing GET request to start-recording")
        patients = get_dentist_patients(dentist_id)
        logger.info(f"Found {len(patients)} patients for dentist {dentist_id}")
        error = request.args.get('error')
        
        # Check if a specific patient_id is provided in the URL (for existing patient selection)
        selected_patient_id = request.args.get('patient_id')
        if selected_patient_id:
            # Auto-select this patient and redirect to recording
            patient = get_patient_from_kv(selected_patient_id, dentist_id)
            if patient:
                logger.info(f"Auto-selecting patient {selected_patient_id} for recording")
                response = make_response(redirect(url_for('record', patient_id=selected_patient_id)))
                return response
            else:
                error = "Invalid patient selected"
        
        # Check if "new" parameter is present to focus on creating a new patient
        focus_new_patient = request.args.get('new') == 'true'
        
        return render_template('start_recording.html', 
                              patients=patients,
                              error=error,
                              focus_new_patient=focus_new_patient)
                              
    except Exception as e:
        logger.error(f"Error in start_recording route: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return redirect(url_for('dashboard', error="An error occurred while starting recording"))

@app.route('/record/<patient_id>')
@login_required
def record(patient_id):
    dentist_id = request.cookies.get('dentist_id')
    patient = get_patient_from_kv(patient_id, dentist_id)
    
    if not patient:
        return redirect(url_for('start_recording', error="Invalid patient selected"))
    
    return render_template('record.html', patient=patient)

@app.route('/transcription/<patient_id>', methods=['GET', 'POST'])
@login_required
def transcription_page(patient_id):
    dentist_id = request.cookies.get('dentist_id')
    patient = get_patient_from_kv(patient_id, dentist_id)
    
    if not patient:
        logger.warning(f"Patient {patient_id} not found for dentist {dentist_id}")
        return redirect(url_for('start_recording', error="Invalid patient selected"))
    
    if request.method == 'POST':
        logger.info(f"POST request received for transcription page, patient: {patient_id}")
        transcription = request.form.get('transcription')
        logger.info(f"Transcription received: {transcription[:100]}..." if transcription else "No transcription received")
        
        if not transcription:
            logger.warning("No transcription provided in POST request")
            return render_template('transcription.html', patient=patient, error="No transcription provided")
        
        processed_transcription = process_speech_text(transcription)
        logger.info(f"Processed transcription: {processed_transcription[:100]}...")
        
        # Store transcription in session
        session_data = get_session()
        session_data['pending_transcription'] = processed_transcription
        session_data['pending_patient_id'] = patient_id
        session_id, session_response = update_session(session_data)
        logger.info(f"Stored transcription in session for patient {patient_id}")
        
        # Explicitly set show_loading=True in the redirect
        redirect_url = url_for('generate_clinical_record_route', patient_id=patient_id, show_loading=True)
        logger.info(f"Redirecting to: {redirect_url} with show_loading=True")
        
        # Create response with session cookie if needed
        if session_response:
            response = make_response(redirect(redirect_url))
            response.set_cookie('session_id', session_id, max_age=86400, httponly=True)
            return response
        
        return redirect(redirect_url)
    
    logger.info(f"GET request for transcription page, patient: {patient_id}")
    return render_template('transcription.html', patient=patient)

@app.route('/patients')
@login_required
def patients_page():
    dentist_id = request.cookies.get('dentist_id')
    patients = get_dentist_patients(dentist_id)
    
    return render_template('patients.html', patients=patients)

@app.route('/search-patients')
@login_required
def search_patients():
    dentist_id = request.cookies.get('dentist_id')
    query = request.args.get('q', '').lower().strip()
    
    if not query: 
        return jsonify([])
    
    patients = get_dentist_patients(dentist_id)
    results = []
    
    for patient in patients:
        # Search by name (partial match)
        name_match = query in patient['name'].lower()
        
        # Search by patient ID (partial match from beginning or full match)
        id_match = (query in patient['id'].lower() or 
                   patient['id'].lower().startswith(query) or
                   query in patient['id'][:8].lower())  # Search in short ID too
        
        if name_match or id_match:
            # Add search relevance score
            patient_result = patient.copy()
            if patient['name'].lower().startswith(query):
                patient_result['relevance'] = 3  # Exact name match
            elif name_match:
                patient_result['relevance'] = 2  # Partial name match
            elif id_match:
                patient_result['relevance'] = 1  # ID match
            else:
                patient_result['relevance'] = 0
            
            results.append(patient_result)
    
    # Sort by relevance (highest first)
    results.sort(key=lambda x: x.get('relevance', 0), reverse=True)
    
    # Return top 10 results
    return jsonify(results[:10])

@app.route('/save-note', methods=['POST'])
@login_required
def save_note():
    try:
        dentist_id = request.cookies.get('dentist_id')
        logger.info(f"Save note request from dentist: {dentist_id}")
        
        # Log the incoming data for debugging
        request_data = request.get_json()
        logger.info(f"Received save-note data: {request_data}")
        
        if not request_data:
            logger.error("No JSON data received in save-note request")
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Log each field individually for debugging
        patient_id = request_data.get('patient_id')
        content = request_data.get('content')
        transcription = request_data.get('transcription', '')
        
        logger.info(f"DETAILED FIELD ANALYSIS:")
        logger.info(f"- patient_id: {repr(patient_id)} (type: {type(patient_id)})")
        logger.info(f"- content length: {len(content) if content else 0} (type: {type(content)})")
        logger.info(f"- transcription length: {len(transcription) if transcription else 0} (type: {type(transcription)})")
        logger.info(f"- patient_id is None: {patient_id is None}")
        logger.info(f"- patient_id is empty string: {patient_id == ''}")
        logger.info(f"- patient_id truthiness: {bool(patient_id)}")
        
        logger.info(f"Parsed data - patient_id: {patient_id}, content_length: {len(content) if content else 0}, transcription_length: {len(transcription) if transcription else 0}")
        
        if not patient_id:
            logger.error("Missing patient_id in save-note request")
            return jsonify({'error': 'Missing patient_id'}), 400
        
        if not content:
            logger.error("Missing content in save-note request")
            return jsonify({'error': 'Missing content (clinical record text)'}), 400
        
        patient = get_patient_from_kv(patient_id, dentist_id)
        if not patient:
            logger.error(f"Invalid patient {patient_id} for dentist {dentist_id}")
            return jsonify({'error': 'Invalid patient'}), 400
        
        note_id = str(uuid.uuid4())
        note_data = {
            'id': note_id,
            'content': content,
            'transcription': transcription,
            'timestamp': datetime.now().isoformat(),
            'patient_id': patient_id,
            'dentist_id': dentist_id,
            'patient_name': patient.get('name')
        }
        
        logger.info(f"Attempting to save note with ID: {note_id}")
        if not save_note_to_kv(note_data):
            logger.error(f"Failed to save note {note_id} to Redis")
            return jsonify({'error': 'Failed to save note to database'}), 500
        
        # Update patient last visit
        patient['last_visit'] = datetime.now().isoformat()
        patient['notes_count'] = patient.get('notes_count', 0) + 1
        save_patient_to_kv(patient)
        logger.info(f"Updated patient {patient_id} last visit and note count")
        
        logger.info(f"Successfully saved note {note_id} for patient {patient_id}")
        return jsonify({'success': True, 'note_id': note_id, 'patient_id': patient_id})
        
    except Exception as e:
        logger.error(f"Error in save_note: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/patient/<patient_id>')
@login_required
def patient_notes_page(patient_id):
    dentist_id = request.cookies.get('dentist_id')
    patient = get_patient_from_kv(patient_id, dentist_id)
    
    if not patient:
        return redirect(url_for('patients_page'))
    
    notes = get_patient_notes_from_kv(patient_id)
    patient_data = patient.copy()
    patient_data['notes'] = notes
    
    return render_template('patient_notes.html', patient=patient_data)

@app.route('/view-note/<note_id>')
@login_required
def view_note_page(note_id):
    dentist_id = request.cookies.get('dentist_id')
    note = get_note_from_kv(note_id)
    
    if not note or note.get('dentist_id') != dentist_id:
        return redirect(url_for('patients_page'))
    
    patient = get_patient_from_kv(note.get('patient_id'), dentist_id)
    if not patient:
        return redirect(url_for('patients_page'))
    
    return render_template('clinicalrecord.html',
                        patient=patient,
                        clinical_record=note.get('content', ''),
                        transcription=note.get('transcription', ''),
                        view_only=True)

@app.route('/generate-clinical-record/<patient_id>')
@login_required
def generate_clinical_record_route(patient_id):
    dentist_id = request.cookies.get('dentist_id')
    patient = get_patient_from_kv(patient_id, dentist_id)
    
    if not patient:
        return redirect(url_for('start_recording'))
    
    # Try to get transcription from session first, then from URL parameter
    session_data = get_session()
    transcription = session_data.get('pending_transcription')
    
    # If not in session, check URL parameter (for backward compatibility)
    if not transcription:
        transcription = request.args.get('transcription')
    
    # Clear session data after retrieval
    if transcription and session_data.get('pending_patient_id') == patient_id:
        session_data.pop('pending_transcription', None)
        session_data.pop('pending_patient_id', None)
        session_id, session_response = update_session(session_data)
        logger.info(f"Retrieved and cleared transcription from session for patient {patient_id}")
    
    if not transcription:
        logger.warning(f"No transcription found for patient {patient_id}, redirecting back to transcription page")
        return redirect(url_for('transcription_page', patient_id=patient_id))
    
    # Always show loading when coming from transcription page
    show_loading = True
    logger.info(f"Showing loading screen for patient {patient_id} with transcription length: {len(transcription)}")
    
    # Create response with session cookie if needed
    response = make_response(render_template('clinicalrecord.html', 
                                          patient=patient,
                                          clinical_record="",
                                          transcription=transcription,
                                          show_loading=show_loading))
    
    if session_response:
        response.set_cookie('session_id', session_id, max_age=86400, httponly=True)
    
    return response

@app.route('/api/generate-note', methods=['POST'])
@login_required
def api_generate_note():
    try:
        dentist_id = request.cookies.get('dentist_id')
        if not dentist_id:
            logger.error("No dentist_id in cookies for generate-note request")
            return jsonify({'error': 'Authentication required'}), 401
            
        data = request.get_json()
        if not data:
            logger.error("No JSON data provided to generate-note endpoint")
            return jsonify({'error': 'No JSON data provided'}), 400
            
        patient_id = data.get('patient_id')
        transcription = data.get('transcription')
        
        logger.info(f"Generate note request - dentist: {dentist_id}, patient: {patient_id}")
        
        if not patient_id:
            logger.error("Missing patient_id in generate-note request")
            return jsonify({'error': 'Missing patient_id'}), 400
        if not transcription:
            logger.error("Missing transcription in generate-note request")
            return jsonify({'error': 'Missing transcription'}), 400
        
        patient = get_patient_from_kv(patient_id, dentist_id)
        if not patient:
            logger.error(f"Invalid patient {patient_id} for dentist {dentist_id}")
            return jsonify({'error': 'Invalid patient or permission denied'}), 403
        
        logger.info(f"Generating clinical note for patient {patient_id} with transcription length: {len(transcription)}")
        
        try:
            generated_clinical_record = generate_clinical_note(transcription, patient.get('name', 'Patient'))
            
            if not generated_clinical_record:
                logger.error("generate_clinical_note returned empty result")
                return jsonify({'error': 'Failed to generate clinical note - no content generated'}), 500
            
            logger.info(f"Successfully generated clinical note, length: {len(generated_clinical_record)}")
            return jsonify({
                'success': True, 
                'clinical_record': generated_clinical_record,
                'patient_id': patient_id,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as generation_error:
            logger.error(f"Error in generate_clinical_note function: {str(generation_error)}")
            logger.error(f"Generation error traceback: {traceback.format_exc()}")
            
            # Return more specific error information
            error_message = str(generation_error)
            if "OpenRouter API error" in error_message:
                return jsonify({'error': f'AI service error: {error_message}'}), 503
            elif "timeout" in error_message.lower():
                return jsonify({'error': 'Request timed out - please try again'}), 504
            elif "authentication" in error_message.lower():
                return jsonify({'error': 'AI service authentication failed'}), 503
            else:
                return jsonify({'error': f'Clinical note generation failed: {error_message}'}), 500
            
    except Exception as e:
        logger.error(f"Unexpected error in api_generate_note: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/delete-patient/<patient_id>', methods=['DELETE'])
@login_required
def delete_patient_route(patient_id):
    try:
        dentist_id = request.cookies.get('dentist_id')
        if not dentist_id:
            logger.error("Delete patient request without dentist_id in cookies")
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        # Verify patient exists first
        patient = get_patient_from_kv(patient_id, dentist_id)
        if not patient:
            logger.warning(f"Attempt to delete non-existent patient {patient_id} for dentist {dentist_id}")
            return jsonify({
                'success': False, 
                'error': 'Patient not found or you do not have permission to delete it'
            }), 404
        
        # Log the patient details for debugging
        patient_name = patient.get('name', 'Unknown')
        logger.info(f"Attempting to delete patient '{patient_name}' (ID: {patient_id}) for dentist {dentist_id}")
        
        # Perform the deletion
        deletion_success = delete_patient_from_kv(patient_id, dentist_id)
        
        if deletion_success:
            logger.info(f"Successfully deleted patient '{patient_name}' (ID: {patient_id}) for dentist {dentist_id}")
            return jsonify({
                'success': True, 
                'message': 'Patient deleted successfully',
                'patient_id': patient_id,
                'patient_name': patient_name
            }), 200
        else:
            logger.error(f"Database operation failed when deleting patient {patient_id} for dentist {dentist_id}")
            return jsonify({
                'success': False, 
                'error': 'Database error while deleting patient'
            }), 500
    except Exception as e:
        error_details = str(e)
        logger.error(f"Exception when deleting patient {patient_id}: {error_details}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False, 
            'error': 'An unexpected error occurred',
            'details': error_details
        }), 500

# Test route for Redis connection
@app.route('/api/redis-test')
def redis_test():
    result = {
        'redis_url_exists': bool(redis_url),
        'redis_connected': False
    }
    
    if redis_client:
        try:
            test_key = 'redis_test_key'
            test_value = f'test_value_{datetime.now().isoformat()}'
            redis_client.set(test_key, test_value)
            retrieved = redis_client.get(test_key)
            
            if retrieved:
                result['redis_connected'] = True
                result['test_value'] = retrieved.decode('utf-8') if isinstance(retrieved, bytes) else retrieved
            
            redis_client.delete(test_key)
        except Exception as e:
            result['error'] = str(e)
    
    return jsonify(result)

# This is needed for Vercel. The actual app is 'app' above.
# When Vercel runs this, it imports 'app' from this file.
# The if __name__ == '__main__': block is for local execution.
if __name__ == '__main__':
    logger.info("Starting Flask app for local development...")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=True) 