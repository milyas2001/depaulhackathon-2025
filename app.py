from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_session import Session
import openai
import os
from dotenv import load_dotenv
import uuid
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management
app.config['SESSION_TYPE'] = 'filesystem'  # Enable server-side session storage
Session(app)  # Initialize Flask-Session

# Load environment variables
load_dotenv()

# Configure OpenAI - will be None if not configured
openai.api_key = os.getenv('OPENAI_API_KEY')

# Initialize session data structure
def init_session():
    if 'patients' not in session:
        session['patients'] = {}
    if 'recent_patients' not in session:
        session['recent_patients'] = []

@app.route('/')
def index():
    init_session()
    return render_template('dashboard.html', recent_patients=session.get('recent_patients', []))

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
    current_patient = session.get('current_patient')
    current_note = session.get('current_note')
    current_note_data = session.get('current_note_data')
    
    if not current_patient:
        return redirect(url_for('index'))
        
    # If we're viewing an existing note, use that
    if current_note:
        return render_template('clinicalrecord.html', 
                             patient=current_patient, 
                             note=current_note,
                             clinical_record=current_note.get('content'))
    
    # If we're creating a new note, use the current note data
    if current_note_data:
        return render_template('clinicalrecord.html', 
                             patient=current_patient,
                             clinical_record=current_note_data.get('clinical_record'))
    
    return redirect(url_for('index'))

@app.route('/get-recent-patients')
def get_recent_patients():
    recent_patients = session.get('recent_patients', [])
    return jsonify(recent_patients)

@app.route('/patients')
def patients():
    all_patients = session.get('patients', {})
    return render_template('patients.html', patients=all_patients)

@app.route('/process_transcription', methods=['POST'])
def process_transcription():
    data = request.get_json()
    transcription = data.get('transcription', '')
    current_patient = session.get('current_patient')
    
    if not current_patient:
        return jsonify({'error': 'No patient selected'}), 400
        
    if not transcription:
        return jsonify({'error': 'No transcription provided'}), 400

    # Convert transcription to clinical record format using actual patient name
    clinical_record = convert_to_clinical_record(transcription, current_patient.get('name', 'Patient'))
    
    # Store both transcription and clinical record in session
    note_data = {
        'transcription': transcription,
        'clinical_record': clinical_record,
        'timestamp': datetime.now().isoformat(),
        'patient_name': current_patient.get('name')
    }
    session['current_note_data'] = note_data
    session.modified = True
    
    return jsonify({
        'status': 'success',
        'clinical_record': clinical_record,
        'transcription': transcription  # Send back the transcription for verification
    })

def convert_to_clinical_record(transcription, patient_name):
    """
    Convert the transcription into a formal clinical record format.
    If OpenAI is configured, it will use the API. Otherwise, it will use a template.
    """
    if openai.api_key:
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a dental professional assistant helping to format clinical notes."},
                    {"role": "user", "content": f"""
                    Convert the following dental notes for patient {patient_name} into a formal clinical record using SOAP format.
                    Use the exact transcription content in your response, do not make up or assume additional information.
                    
                    Transcription: {transcription}
                    
                    Format the response as:
                    SUBJECTIVE:
                    [Use the exact transcription: {transcription}]
                    
                    OBJECTIVE:
                    Clinical examination documented based on transcribed notes.
                    
                    ASSESSMENT:
                    Assessment based on provided transcription.
                    
                    PLAN:
                    - Follow-up as needed
                    - Patient education provided
                    - Treatment plan discussed with patient
                    """}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error using OpenAI API: {e}")
            return create_template_record(transcription, patient_name)
    else:
        return create_template_record(transcription, patient_name)

def create_template_record(transcription, patient_name):
    """Create a basic formatted record using a template."""
    return f"""SUBJECTIVE:
Patient {patient_name} reports: {transcription}

OBJECTIVE:
Clinical examination documented based on transcribed notes.

ASSESSMENT:
Assessment based on transcription: {transcription}

PLAN:
- Follow-up as needed
- Patient education provided to {patient_name}
- Treatment plan discussed with patient"""

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
    current_patient = session.get('current_patient')
    current_note_data = session.get('current_note_data')
    
    if not current_patient:
        return jsonify({'error': 'No patient selected'}), 400
    
    content = request.json.get('content')
    if not content:
        return jsonify({'error': 'No content provided'}), 400
    
    # Create a new note with all the data
    note = {
        'id': str(uuid.uuid4()),
        'content': content,
        'transcription': current_note_data.get('transcription', '') if current_note_data else '',
        'timestamp': datetime.now(),
        'patient_id': current_patient['id']
    }
    
    # Get a fresh copy of patients from session
    patients = dict(session.get('patients', {}))
    
    if current_patient['id'] in patients:
        if 'notes' not in patients[current_patient['id']]:
            patients[current_patient['id']]['notes'] = []
            
        # Add the new note
        patients[current_patient['id']]['notes'].append(note)
        patients[current_patient['id']]['last_visit'] = note['timestamp']
        
        # Update session
        session['patients'] = patients
        session['current_patient'] = patients[current_patient['id']]
        # Clear the current note data since we've saved it
        session.pop('current_note_data', None)
        session.modified = True
        
        return jsonify({
            'success': True,
            'note_id': note['id'],
            'patient_id': current_patient['id']
        })
    
    return jsonify({'error': 'Patient not found'}), 404

@app.route('/patient/<patient_id>')
def patient_notes(patient_id):
    patients = session.get('patients', {})
    if patient_id not in patients:
        return redirect(url_for('patients'))
    
    patient = patients[patient_id]
    return render_template('patient_notes.html', patient=patient)

@app.route('/view-note/<note_id>')
def view_note(note_id):
    patients = session.get('patients', {})
    for patient in patients.values():
        for note in patient.get('notes', []):
            if note['id'] == note_id:
                session['current_patient'] = patient
                session['current_note'] = note
                return redirect(url_for('clinical_record'))
    return redirect(url_for('patients'))

@app.route('/get-current-patient')
def get_current_patient():
    current_patient = session.get('current_patient')
    if not current_patient:
        return jsonify({'error': 'No patient selected'}), 404
    return jsonify(current_patient)

if __name__ == '__main__':
    app.run(debug=True) 