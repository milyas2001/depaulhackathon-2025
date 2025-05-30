from flask import Flask, render_template, request, jsonify
import os
import whisper
import tempfile
import soundfile as sf
import numpy as np
from scipy import signal
from llm_handler import DentalNoteGenerator

app = Flask(__name__)

# Load Whisper model globally (using base model for faster startup)
whisper_model = whisper.load_model("base")

# Initialize the LLM note generator lazily
note_generator = None

def get_note_generator():
    global note_generator
    if note_generator is None:
        note_generator = DentalNoteGenerator()
    return note_generator

def generate_clinical_note(input_text):
    """
    Generate a clinical note using the LLM. Falls back to template if LLM fails.
    """
    try:
        # Try generating with LLM first
        generator = get_note_generator()
        if generator.is_available():
            llm_note = generator.generate_note(input_text)
            if llm_note:
                return llm_note

        # Fallback to template-based generation
        return fallback_generate_note(input_text)

    except Exception as e:
        print(f"Error in note generation: {str(e)}")
        return fallback_generate_note(input_text)

def fallback_generate_note(input_text):
    """
    Template-based note generation as fallback
    """
    try:
        note = f"""DENTAL CLINICAL NOTE
Date: {os.popen('date').read().strip()}

PROCEDURE TYPE:
{'Tooth Extraction' if 'extract' in input_text.lower() else 'Dental Procedure'}

CLINICAL NARRATIVE:
{input_text}

ASSESSMENT:
Clinical evaluation completed. Patient's condition and procedure outcomes were assessed.

PLAN AND RECOMMENDATIONS:
Patient was provided with comprehensive post-operative instructions for optimal recovery. A follow-up appointment will be scheduled as appropriate for the procedure performed. Necessary medications were prescribed based on the treatment requirements. The patient was thoroughly informed about potential post-procedure symptoms and advised to contact our office immediately if experiencing any concerning symptoms or complications."""

        return note
    except Exception as e:
        return f"Error generating note: {str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

def preprocess_audio(audio_path):
    """
    Preprocess audio file to improve transcription quality:
    1. Normalize audio
    2. Apply noise reduction
    3. Apply bandpass filter to focus on speech frequencies
    """
    try:
        # Read audio file
        audio, sr = sf.read(audio_path)
        
        # Convert to mono if stereo
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)
        
        # Normalize audio
        audio = audio / np.max(np.abs(audio))
        
        # Apply bandpass filter (focus on speech frequencies: 100-8000 Hz)
        nyquist = sr / 2
        low = 100 / nyquist
        high = 8000 / nyquist
        b, a = signal.butter(4, [low, high], btype='band')
        audio = signal.filtfilt(b, a, audio)
        
        # Save preprocessed audio
        preprocessed_path = audio_path + '_processed.wav'
        sf.write(preprocessed_path, audio, sr)
        return preprocessed_path
    except Exception as e:
        print(f"Error preprocessing audio: {str(e)}")
        return audio_path

@app.route('/process_audio', methods=['POST'])
def process_audio():
    try:
        if request.method == 'POST':
            # Check for text input first
            dentist_input_text = request.form.get('text_input')
            if dentist_input_text and dentist_input_text.strip():
                return generate_clinical_note(dentist_input_text)

            # Check for audio file
            audio_data = request.files.get('audio_data')
            if audio_data:
                # Create a temporary file to save the audio
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_audio:
                    audio_data.save(temp_audio.name)
                    
                    try:
                        # Preprocess the audio
                        processed_audio_path = preprocess_audio(temp_audio.name)
                        
                        # Transcribe the processed audio using Whisper
                        result = whisper_model.transcribe(
                            processed_audio_path,
                            language="en",
                            fp16=False,
                            initial_prompt="This is a dental examination note. Please transcribe clearly and accurately."
                        )
                        
                        # Get the transcribed text
                        transcribed_text = result["text"].strip()
                        print(f"Transcribed text: {transcribed_text}")
                        
                        if not transcribed_text:
                            return "No speech detected in the audio. Please try again.", 400
                        
                        # Generate clinical note from transcribed text
                        formal_note = generate_clinical_note(transcribed_text)
                        
                        # Clean up temporary files
                        os.unlink(temp_audio.name)
                        if processed_audio_path != temp_audio.name:
                            os.unlink(processed_audio_path)
                        
                        return formal_note
                        
                    except Exception as e:
                        print(f"Error processing audio: {str(e)}")
                        os.unlink(temp_audio.name)
                        if 'processed_audio_path' in locals() and processed_audio_path != temp_audio.name:
                            os.unlink(processed_audio_path)
                        return f"Error processing audio: {str(e)}", 500
            
            return "No input received. Please provide either text or audio input.", 400
            
    except Exception as e:
        print(f"Error in process_audio: {str(e)}")
        return f"Error processing your request: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005, debug=False) 