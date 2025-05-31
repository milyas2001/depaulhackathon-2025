from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_session import Session
import os
from dotenv import load_dotenv
import uuid
from datetime import datetime
import logging
import sys
import json
import traceback
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import re

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management
app.config['SESSION_TYPE'] = 'filesystem'  # Enable server-side session storage
app.config['SESSION_FILE_DIR'] = 'flask_session'
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours
Session(app)  # Initialize Flask-Session

# Load environment variables
load_dotenv()

# Global variables for lazy loading
model = None
tokenizer = None

def load_model_if_needed():
    """Lazy loading of the model only when needed"""
    global model, tokenizer
    if model is None or tokenizer is None:
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch
            
            logger.info("Starting DeepSeek model loading process...")
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Using device: {device}")
            
            # Use a smaller model for better performance
            model_name = "deepseek-ai/deepseek-coder-1.3b-instruct"
            logger.info(f"Attempting to load model: {model_name}")
            
            logger.info("Loading tokenizer...")
            tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
            logger.info("Tokenizer loaded successfully")
            
            logger.info("Loading model...")
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16,
                trust_remote_code=True,
                device_map="auto",
                load_in_8bit=True
            )
            logger.info("Model loaded successfully!")
            return True
        except Exception as e:
            logger.error(f"Error loading DeepSeek model: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return False
    return True

def preprocess_transcription(transcription):
    """Clean and structure the transcription text."""
    # Convert to lowercase for processing
    text = transcription.lower().strip()
    
    # Initialize structured data
    info = {
        'tooth_number': None,
        'symptoms': set(),  # Using set to avoid duplicates
        'findings': set(),
        'procedures': set(),
        'treatment_plan': set(),
        'location': set()
    }
    
    # Extract tooth number
    tooth_matches = re.findall(r'(?:tooth|number|#)\s*#?\s*(\d{1,2})', text)
    if tooth_matches:
        info['tooth_number'] = tooth_matches[0]
    
    # Extract symptoms
    if 'pain' in text:
        if 'severe' in text:
            info['symptoms'].add('severe pain')
        elif 'moderate' in text:
            info['symptoms'].add('moderate pain')
        else:
            info['symptoms'].add('pain')
    if 'sensitivity' in text:
        info['symptoms'].add('sensitivity')
    if 'discomfort' in text:
        info['symptoms'].add('discomfort')
            
    # Extract findings
    if 'cavity' in text:
        if 'deep' in text:
            info['findings'].add('deep carious lesion')
        else:
            info['findings'].add('carious lesion')
    if 'decay' in text:
        info['findings'].add('dental caries')
    if 'infection' in text:
        info['findings'].add('periapical infection')
            
    # Extract procedures/recommendations
    if 'root canal' in text:
        info['treatment_plan'].add('endodontic therapy')
    if 'drill' in text:
        info['procedures'].add('caries removal and preparation')
    if 'fill' in text:
        info['procedures'].add('composite restoration')
    if 'clean' in text:
        info['procedures'].add('debridement')
        
    # Convert sets to sorted lists for consistent output
    return {k: sorted(v) if isinstance(v, set) else v for k, v in info.items()}

def generate_clinical_note(transcription, patient_name):
    """Generate a clinical note using structured information."""
    try:
        # Process the transcription
        info = preprocess_transcription(transcription)
        
        # Build the note components
        tooth_desc = f"tooth #{info['tooth_number']}" if info['tooth_number'] else "the affected tooth"
        
        # Symptoms description
        symptoms = ', '.join(info['symptoms']) if info['symptoms'] else "dental concerns"
        
        # Clinical findings
        findings = ', '.join(info['findings']) if info['findings'] else "clinical findings warranting treatment"
        
        # Treatment description
        procedures = info['procedures']
        treatment_plan = info['treatment_plan']
        
        # Construct the clinical note with proper medical terminology and flow
        note_parts = []
        
        # Chief complaint and presentation
        note_parts.append(f"Patient presented with {symptoms} affecting {tooth_desc}.")
        
        # Clinical examination
        if info['findings']:
            note_parts.append(f"Clinical examination revealed {findings}.")
        
        # Treatment performed/planned
        if procedures:
            note_parts.append(f"Treatment performed included {', '.join(procedures)}.")
        if treatment_plan:
            note_parts.append(f"The recommended treatment plan comprises {', '.join(treatment_plan)}.")
            
        # Add clinical protocols and instructions with more specific details
        note_parts.append("All procedures were performed under local anesthesia following standard clinical protocols.")
        
        # Add specific post-operative instructions based on procedures
        if 'endodontic therapy' in treatment_plan or 'caries removal' in procedures:
            note_parts.append("Post-operative instructions emphasized temporary crown care, avoiding mastication on the treated tooth, and maintaining meticulous oral hygiene.")
        else:
            note_parts.append("Post-operative instructions emphasized maintaining optimal oral hygiene and following the prescribed care regimen.")
            
        note_parts.append("Patient was advised to monitor for any persistent pain, swelling, or unusual symptoms and contact the office immediately if concerns arise.")
        note_parts.append("A follow-up appointment will be scheduled to evaluate healing progress and ensure treatment efficacy.")
        
        # Combine into final note
        note = ' '.join(note_parts)
        
        # Add header
        current_date = datetime.now().strftime("%B %d, %Y")
        current_time = datetime.now().strftime("%I:%M %p")
        header = f"""DENTAL CLINICAL NOTE
Date: {current_date}
Time: {current_time}
Patient: {patient_name}

"""
        
        final_note = header + note + "\n\nNote: This clinical note was generated from voice transcription. Please verify all information for accuracy."
        logger.info(f"Generated clinical note: {final_note}")
        
        return final_note
    except Exception as e:
        logger.error(f"Error generating clinical note: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return None

# Initialize session data structure
def init_session():
    if 'patients' not in session:
        session['patients'] = {}
    if 'recent_patients' not in session:
        session['recent_patients'] = []

# Create data directory if it doesn't exist
DATA_DIR = Path('data')
DATA_DIR.mkdir(exist_ok=True)
NOTES_DIR = DATA_DIR / 'notes'
NOTES_DIR.mkdir(exist_ok=True)
PATIENTS_DIR = DATA_DIR / 'patients'
PATIENTS_DIR.mkdir(exist_ok=True)

def save_note_to_file(note, patient_id):
    """Save note to a JSON file."""
    note_id = note['id']
    patient_dir = NOTES_DIR / patient_id
    patient_dir.mkdir(exist_ok=True)
    
    note_file = patient_dir / f"{note_id}.json"
    with open(note_file, 'w') as f:
        json.dump(note, f, default=str)
    
    # Update patient's note list
    patient_file = PATIENTS_DIR / f"{patient_id}.json"
    try:
        with open(patient_file, 'r') as f:
            patient_data = json.load(f)
    except FileNotFoundError:
        patient_data = {'notes': []}
    
    patient_data['notes'].append(note_id)
    patient_data['last_visit'] = str(datetime.now())
    
    with open(patient_file, 'w') as f:
        json.dump(patient_data, f, default=str)

def get_patient_notes(patient_id):
    """Retrieve all notes for a patient."""
    try:
        logger.info(f"Retrieving notes for patient {patient_id}")
        patient_dir = NOTES_DIR / patient_id
        notes = []
        
        if patient_dir.exists():
            logger.info(f"Found patient directory: {patient_dir}")
            for note_file in patient_dir.glob('*.json'):
                try:
                    logger.info(f"Reading note file: {note_file}")
                    with open(note_file, 'r') as f:
                        note = json.load(f)
                        notes.append(note)
                except Exception as e:
                    logger.error(f"Error reading note file {note_file}: {str(e)}")
                    continue
        else:
            logger.warning(f"No directory found for patient {patient_id}")
        
        sorted_notes = sorted(notes, key=lambda x: x['timestamp'], reverse=True)
        logger.info(f"Retrieved {len(sorted_notes)} notes for patient {patient_id}")
        return sorted_notes
    except Exception as e:
        logger.error(f"Error in get_patient_notes for patient {patient_id}: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return []

@app.route('/')
def index():
    init_session()
    return render_template('home.html')

@app.route('/dashboard')
def dashboard():
    init_session()
    
    # Get dentist name from query parameter if available
    dentist_name = request.args.get('name')
    if dentist_name:
        session['dentist_name'] = dentist_name
    
    return render_template('dashboard.html', 
                         recent_patients=session.get('recent_patients', []),
                         dentist_name=session.get('dentist_name', 'Doctor'))

@app.route('/start-recording', methods=['POST', 'GET'])
def start_recording():
    if request.method == 'GET':
        patient_id = request.args.get('patient_id')
        if patient_id and patient_id in session.get('patients', {}):
            patient = session['patients'][patient_id]
            session['current_patient'] = patient
            return redirect(url_for('record'))
        return redirect(url_for('index'))

    patient_name = request.form.get('patient_name')
    patient_id = request.form.get('patient_id')
    
    if patient_name and patient_id:
        # Store patient information
        patients = session.get('patients', {})
        
        # Check if ID already exists for a different patient
        if patient_id in patients and patients[patient_id]['name'] != patient_name:
            return "Error: This ID is already assigned to another patient", 400
            
        # Update or create patient entry
        if patient_id not in patients:
            patients[patient_id] = {
                'name': patient_name,
                'id': patient_id,
                'notes': [],
                'last_visit': datetime.now()
            }
        
        session['patients'] = patients
        session['current_patient'] = patients[patient_id]
        
        # Update recent patients list
        recent_patients = session.get('recent_patients', [])
        patient_entry = {'name': patient_name, 'id': patient_id}
        if patient_entry not in recent_patients:
            recent_patients.insert(0, patient_entry)
            recent_patients = recent_patients[:5]  # Keep only last 5 patients
            session['recent_patients'] = recent_patients
            
        return redirect(url_for('record'))
    return redirect(url_for('index'))

@app.route('/record')
def record():
    current_patient = session.get('current_patient')
    if not current_patient:
        return redirect(url_for('index'))
    return render_template('record.html', patient=current_patient)

@app.route('/transcription')
def transcription():
    current_patient = session.get('current_patient')
    if not current_patient:
        return redirect(url_for('index'))
    return render_template('transcription.html', patient=current_patient)

@app.route('/clinical-record')
def clinical_record():
    try:
        current_patient = session.get('current_patient')
        current_note_data = session.get('current_note_data')
        
        if not current_patient:
            logger.error("No patient selected")
            return redirect(url_for('index'))
            
        # If we have transcription data, generate a clinical note
        if current_note_data and current_note_data.get('transcription'):
            transcription = current_note_data['transcription']
            clinical_record = generate_clinical_note(transcription, current_patient.get('name', 'Patient'))
            
            if not clinical_record:
                logger.warning("LLM failed, falling back to basic template...")
                current_date = datetime.now().strftime("%B %d, %Y")
                current_time = datetime.now().strftime("%I:%M %p")
                
                clinical_record = f"""DENTAL CLINICAL NOTE
Date: {current_date}
Time: {current_time}
Patient: {current_patient.get('name', 'Patient')}

CLINICAL NOTES:
{transcription}

Note: This clinical note was generated from voice transcription.
Please verify all information for accuracy."""
            
            return render_template('clinicalrecord.html', 
                                patient=current_patient,
                                clinical_record=clinical_record)
        
        return redirect(url_for('index'))
        
    except Exception as e:
        logger.error(f"Error in clinical_record: {str(e)}")
        return redirect(url_for('index'))

@app.route('/get-recent-patients')
def get_recent_patients():
    recent_patients = session.get('recent_patients', [])
    return jsonify(recent_patients)

@app.route('/patients')
def patients():
    all_patients = session.get('patients', {})
    return render_template('patients.html', patients=all_patients)

@app.route('/search-patients')
def search_patients():
    query = request.args.get('q', '').lower()
    if not query:
        return jsonify([])
    
    patients = session.get('patients', {})
    results = []
    
    for patient_id, patient in patients.items():
        # Search in both name and ID
        if (query in patient['name'].lower() or 
            query in patient['id'].lower()):
            results.append(patient)
    
    return jsonify(results)

@app.route('/save-note', methods=['POST'])
def save_note():
    try:
        logger.info("=== Starting note save process ===")
        
        # Get current patient and note data
        current_patient = session.get('current_patient')
        current_note_data = session.get('current_note_data')
        
        logger.info(f"Current patient from session: {current_patient}")
        logger.info(f"Current note data from session: {current_note_data}")
        
        if not current_patient:
            logger.error("No patient selected")
            return jsonify({'error': 'No patient selected'}), 400

        # Get the content from the request
        content = request.json.get('content')
        logger.info(f"Received content to save: {content}")
        
        if not content:
            logger.error("No content provided")
            return jsonify({'error': 'No content provided'}), 400

        patient_id = current_patient['id']
        
        # Create the note
        note = {
            'id': str(uuid.uuid4()),
            'content': content,
            'transcription': current_note_data.get('transcription', '') if current_note_data else '',
            'timestamp': str(datetime.now()),
            'patient_id': patient_id,
            'patient_name': current_patient.get('name')
        }
        
        # Save note to file system
        try:
            save_note_to_file(note, patient_id)
            logger.info(f"Successfully saved note to file system for patient {current_patient['name']}")
        except Exception as e:
            logger.error(f"Error saving note to file system: {str(e)}")
            return jsonify({'error': 'Failed to save note'}), 500

        # Also keep in session for immediate access
        if 'patients' not in session:
            session['patients'] = {}
        if patient_id not in session['patients']:
            session['patients'][patient_id] = {
                'name': current_patient['name'],
                'id': patient_id,
                'notes': [],
                'last_visit': datetime.now()
            }
        
        session['patients'][patient_id]['notes'].append(note)
        session.modified = True

        # Clear the current note data from session
        session.pop('current_note_data', None)

        return jsonify({
            'success': True,
            'note_id': note['id'],
            'patient_id': patient_id
        })
        
    except Exception as e:
        logger.error(f"Error in save_note: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@app.route('/patient/<patient_id>')
def patient_notes(patient_id):
    try:
        # Get notes from file system
        notes = get_patient_notes(patient_id)
        
        # Get patient info from session
        patient = session.get('patients', {}).get(patient_id, {
            'id': patient_id,
            'name': 'Unknown Patient',
            'notes': notes
        })
        
        # Update notes from file system
        patient['notes'] = notes
        
        return render_template('patient_notes.html', patient=patient)
    except Exception as e:
        logger.error(f"Error retrieving patient notes: {str(e)}")
        return redirect(url_for('patients'))

@app.route('/view-note/<note_id>')
def view_note(note_id):
    try:
        logger.info(f"Viewing note with ID: {note_id}")
        
        # First try to find which patient this note belongs to
        for patient_dir in NOTES_DIR.iterdir():
            if not patient_dir.is_dir():
                continue
                
            note_file = patient_dir / f"{note_id}.json"
            if note_file.exists():
                try:
                    # Found the note file, read it
                    with open(note_file, 'r') as f:
                        note = json.load(f)
                        
                    # Get patient info
                    patient_id = patient_dir.name
                    patient_file = PATIENTS_DIR / f"{patient_id}.json"
                    
                    if patient_file.exists():
                        with open(patient_file, 'r') as f:
                            patient = json.load(f)
                    else:
                        # Fallback patient info if file doesn't exist
                        patient = {
                            'id': patient_id,
                            'name': note.get('patient_name', 'Unknown Patient')
                        }
                    
                    # Store in session for the clinical record view
                    session['current_patient'] = patient
                    session['current_note_data'] = {
                        'transcription': note.get('transcription', ''),
                        'clinical_record': note.get('content', '')
                    }
                    
                    return render_template('clinicalrecord.html',
                                        patient=patient,
                                        clinical_record=note.get('content', ''))
                except Exception as e:
                    logger.error(f"Error reading note file {note_file}: {str(e)}")
                    
        logger.error(f"Note with ID {note_id} not found")
        return redirect(url_for('patients'))
        
    except Exception as e:
        logger.error(f"Error in view_note: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return redirect(url_for('patients'))

@app.route('/get-current-patient')
def get_current_patient():
    current_patient = session.get('current_patient')
    if not current_patient:
        return jsonify({'error': 'No patient selected'}), 404
    return jsonify(current_patient)

def process_correction(text, previous_text=None):
    """
    Process corrections in the transcription intelligently.
    """
    if not model:
        return text
        
    try:
        # If this is the first transcription, no correction needed
        if not previous_text:
            return text
            
        prompt = f"""You are an expert dental assistant processing voice transcriptions.
        
        Previous transcription:
        {previous_text}
        
        New input (may contain corrections):
        {text}
        
        Task: If the new input contains corrections to the previous transcription (like changing tooth numbers, procedures, etc.),
        apply those corrections to create an updated, corrected version. If it's new information, append it properly.
        
        Rules:
        1. If you hear "sorry", "correction", "I meant", "not this tooth", etc., interpret it as a correction
        2. Replace the corrected information in the original text
        3. Don't include the correction statement itself in the final text
        4. Maintain proper dental terminology
        5. Keep the context and flow of the note
        
        Return only the corrected/updated text without any explanations.
        """
        
        response = model(prompt)
        if response:
            return response.strip()
        return text
            
    except Exception as e:
        print(f"Error in correction processing: {str(e)}")
        return text

@app.route('/save-transcription', methods=['POST'])
def save_transcription():
    try:
        logger.info("\n=== Starting transcription save process ===")
        data = request.get_json()
        transcription = data.get('transcription', '')
        
        logger.info(f"Received transcription: {transcription}")
        
        if not transcription:
            logger.error("No transcription provided")
            return jsonify({'error': 'No transcription provided'}), 400

        current_patient = session.get('current_patient')
        logger.info(f"Current patient from session: {current_patient}")
        
        if not current_patient:
            logger.error("No patient selected")
            return jsonify({'error': 'No patient selected'}), 400

        # Process the transcription to add punctuation
        processed_transcription = process_speech_text(transcription)
        logger.info(f"Processed transcription: {processed_transcription}")

        # Store the processed transcription in session
        note_data = {
            'transcription': processed_transcription,
            'timestamp': datetime.now().isoformat(),
            'patient_name': current_patient.get('name'),
            'patient_id': current_patient.get('id'),
            'status': 'transcribed'
        }
        
        logger.info("Storing transcription data in session...")
        logger.info(f"Note data being stored: {note_data}")
        session['current_note_data'] = note_data
        session.modified = True
        
        # Verify the data was stored
        stored_data = session.get('current_note_data')
        logger.info(f"Verified stored note data: {stored_data}")
        
        logger.info("=== Completed transcription save process ===")
        
        return jsonify({
            'status': 'success',
            'message': 'Transcription saved successfully',
            'processed_text': processed_transcription
        })
    except Exception as e:
        logger.error(f"Error saving transcription: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@app.route('/generate-clinical-record')
def generate_clinical_record():
    try:
        logger.info("=== Starting clinical record generation ===")
        current_patient = session.get('current_patient')
        current_note_data = session.get('current_note_data')
        
        logger.info(f"Retrieved current patient from session: {current_patient}")
        logger.info(f"Retrieved note data from session: {current_note_data}")
        
        if not current_patient:
            logger.error("No patient selected")
            return redirect(url_for('index'))
            
        if not current_note_data or not current_note_data.get('transcription'):
            logger.error("No transcription data found")
            logger.error(f"Current note data state: {current_note_data}")
            return redirect(url_for('transcription'))
        
        transcription = current_note_data['transcription']
        logger.info(f"Found transcription to process: {transcription}")
        
        # Generate the clinical note using our preprocessing and structured generation
        clinical_record = generate_clinical_note(transcription, current_patient.get('name', 'Patient'))
        
        if clinical_record:
            # Store the generated note
            current_note_data['clinical_record'] = clinical_record
            current_note_data['status'] = 'processed'
            session['current_note_data'] = current_note_data
            session.modified = True
            logger.info("Clinical record saved to session")
        else:
            logger.error("Failed to generate clinical note")
            return redirect(url_for('transcription'))
        
        logger.info("=== Completed clinical record generation ===")
        return render_template('clinicalrecord.html', 
                            patient=current_patient,
                            clinical_record=clinical_record)
        
    except Exception as e:
        logger.error(f"Error in generate_clinical_record: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return redirect(url_for('transcription'))

def process_speech_text(text):
    """Process speech text to add proper punctuation and formatting."""
    # Clean up the text
    text = text.strip()
    
    # Add periods after common sentence endings
    common_endings = [
        'patient', 'treatment', 'cavity', 'procedure', 'tooth', 
        'examination', 'recommended', 'performed', 'completed', 'noted',
        'observed', 'found', 'present', 'visible', 'detected'
    ]
    
    # Split into potential sentences
    words = text.split()
    processed_words = []
    
    for i, word in enumerate(words):
        processed_words.append(word)
        
        # Add period if this word is a common ending and next word starts with capital
        if (i < len(words) - 1 and 
            word.lower() in common_endings and 
            words[i + 1][0].isupper()):
            processed_words[-1] = word + "."
        
        # Add comma after tooth numbers
        if (re.match(r'#?\d{1,2}$', word) and 
            i < len(words) - 1 and 
            not words[i + 1].startswith('#')):
            processed_words[-1] = word + ","
        
        # Add comma after certain phrases
        if word.lower() in ['however', 'additionally', 'furthermore', 'moreover']:
            processed_words[-1] = word + ","
    
    # Join words back together
    text = ' '.join(processed_words)
    
    # Add final period if missing
    if not text.endswith(('.', '!', '?')):
        text += '.'
    
    # Fix common speech patterns
    text = re.sub(r'\band\s+and\s+', ' and ', text)
    text = re.sub(r'\bum\s+', '', text)
    text = re.sub(r'\buh\s+', '', text)
    text = re.sub(r'\s+', ' ', text)  # Remove extra spaces
    
    return text

@app.route('/process_transcription', methods=['POST'])
def process_transcription():
    try:
        logger.info("\n=== Starting transcription processing ===")
        data = request.get_json()
        transcription = data.get('transcription', '')
        
        logger.info(f"Received transcription: {transcription}")
        
        if not transcription:
            logger.error("No transcription provided")
            return jsonify({'error': 'No transcription provided'}), 400

        current_patient = session.get('current_patient')
        logger.info(f"Current patient from session: {current_patient}")
        
        if not current_patient:
            logger.error("No patient selected")
            return jsonify({'error': 'No patient selected'}), 400

        # Process the transcription to add punctuation
        processed_transcription = process_speech_text(transcription)
        logger.info(f"Processed transcription: {processed_transcription}")

        # Store the processed transcription in session
        note_data = {
            'transcription': processed_transcription,
            'timestamp': datetime.now().isoformat(),
            'patient_name': current_patient.get('name'),
            'patient_id': current_patient.get('id'),
            'status': 'transcribed'
        }
        
        logger.info("Storing transcription data in session...")
        session['current_note_data'] = note_data
        session.modified = True
        
        logger.info("=== Completed transcription processing ===")
        
        return jsonify({
            'status': 'success',
            'message': 'Transcription processed successfully',
            'processed_text': processed_transcription
        })
    except Exception as e:
        logger.error(f"Error in process_transcription: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting Flask app...")
    print("Please access the application at: http://127.0.0.1:5010")
    app.run(host='127.0.0.1', port=5010, debug=True) 