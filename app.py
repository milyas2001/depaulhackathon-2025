from flask import Flask, render_template, request, jsonify
import os
import whisper
import tempfile
import soundfile as sf
import numpy as np
from scipy import signal
from transformers import pipeline
from ctransformers import AutoModelForCausalLM

app = Flask(__name__)

# Load Whisper model globally (using base model for faster startup)
whisper_model = whisper.load_model("base")

# Initialize the LLM for clinical note generation
def initialize_llm():
    try:
        # Using Llama-2-7b-chat model with medical knowledge
        llm = AutoModelForCausalLM.from_pretrained(
            "TheBloke/Llama-2-7B-Chat-GGML",
            model_file="llama-2-7b-chat.ggmlv3.q4_0.bin",
            model_type="llama",
            max_new_tokens=512,
            context_length=2048,
            temperature=0.7
        )
        return llm
    except Exception as e:
        print(f"Error loading LLM: {str(e)}")
        return None

llm = initialize_llm()

def generate_clinical_note(input_text):
    """
    Uses LLM to generate a detailed clinical note from the input text.
    """
    try:
        # Prompt engineering for clinical note generation
        prompt = f"""You are a dental documentation assistant. Convert the following informal dental notes into a formal, detailed clinical note.
        Use proper dental terminology and maintain a professional tone.
        
        Format the note with these sections:
        1. DENTAL CLINICAL NOTE with current date
        2. PROCEDURE TYPE (identify from the input)
        3. CLINICAL NARRATIVE (detailed paragraph about the procedure)
        4. ASSESSMENT (clinical evaluation)
        5. PLAN AND RECOMMENDATIONS (comprehensive paragraph)
        
        Input notes:
        {input_text}
        
        Generate a formal clinical note:"""

        # Generate response using the LLM
        if llm:
            response = llm(prompt)
            return response
        else:
            # Fallback to template-based generation if LLM fails
            return fallback_generate_note(input_text)

    except Exception as e:
        print(f"Error generating clinical note: {str(e)}")
        return fallback_generate_note(input_text)

def fallback_generate_note(input_text):
    """
    Fallback template-based note generation if LLM fails.
    """
    # Extract procedure type and details
    procedure_type = "Dental Procedure"  # Default
    if "extraction" in input_text.lower():
        procedure_type = "Tooth Extraction"
    elif "root canal" in input_text.lower():
        procedure_type = "Root Canal Treatment"
    elif "filling" in input_text.lower():
        procedure_type = "Dental Restoration"
    elif "cleaning" in input_text.lower():
        procedure_type = "Dental Prophylaxis"
    
    # Format the note with detailed procedure description
    note = f"""DENTAL CLINICAL NOTE
Date: {os.popen('date').read().strip()}

PROCEDURE TYPE: {procedure_type}

CLINICAL NARRATIVE:
{elaborate_procedure(input_text)}

ASSESSMENT:
Clinical evaluation completed. Patient's condition and procedure outcomes were assessed.

PLAN AND RECOMMENDATIONS:
Patient was provided with comprehensive post-operative instructions for optimal recovery. A follow-up appointment will be scheduled as appropriate for the procedure performed. Necessary medications were prescribed based on the treatment requirements. The patient was thoroughly informed about potential post-procedure symptoms and advised to contact our office immediately if experiencing any concerning symptoms or complications. All questions were addressed, and written instructions were provided for home care management.

Note: This clinical documentation was generated from provider input and formatted according to standard clinical documentation practices."""

    return note

def elaborate_procedure(input_text):
    """
    Elaborates on the procedure details based on the input text.
    Converts shorthand notes into detailed clinical narrative.
    """
    # Convert common shorthand terms
    text = input_text.lower()
    
    if "extraction" in text:
        details = []
        
        # Anesthesia details
        if "lidocaine" in text or "lido" in text:
            details.append("Local anesthesia was administered using 2% Lidocaine with 1:100,000 epinephrine.")
        
        # Extraction details
        if "partial bony" in text:
            details.append("The extraction was identified as a partial bony removal, requiring careful management of bone and soft tissue.")
        
        # Mucoperiosteal flap
        if "mucoperi" in text or "flap" in text:
            details.append("A mucoperiosteal flap was carefully elevated to access the surgical site.")
        
        # Irrigation
        if "irrigat" in text:
            details.append("The socket was thoroughly irrigated to ensure removal of any debris.")
            
        # Additional details from input
        details.append(f"Additional procedure notes: {input_text}")
        
        # Combine all details into a coherent paragraph
        return " ".join(details)
    
    # For other types of procedures, return the original text with basic formatting
    return f"The following procedure was performed: {input_text}"

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
                        print(f"Transcribed text: {transcribed_text}")  # Debug log
                        
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
    app.run(debug=True, host='0.0.0.0', port=5004) 