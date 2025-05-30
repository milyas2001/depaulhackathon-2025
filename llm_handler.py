from ctransformers import AutoModelForCausalLM
import os
from datetime import datetime

class DentalNoteGenerator:
    def __init__(self):
        try:
            # Initialize the model with ctransformers
            self.model = AutoModelForCausalLM.from_pretrained(
                "TheBloke/Llama-2-7B-Chat-GGML",
                model_file="llama-2-7b-chat.ggmlv3.q4_0.bin",
                model_type="llama",
                max_new_tokens=512,
                context_length=2048,
                temperature=0.7
            )
            print("LLM initialized successfully!")
        except Exception as e:
            print(f"Error initializing LLM: {str(e)}")
            self.model = None

    def generate_note(self, input_text):
        """
        Generate a clinical note from the input text using the LLM.
        """
        if not self.model:
            return None

        current_date = datetime.now().strftime("%B %d, %Y")
        
        prompt = f"""<s>[INST]You are a dental documentation assistant. Convert the following informal dental notes into a formal, detailed clinical note.
        Use proper dental terminology and maintain a professional tone.

        Guidelines:
        - Expand abbreviations into full medical terms
        - Include all procedural details mentioned
        - Add standard clinical phrases where appropriate
        - Maintain chronological order of events
        - Use proper dental notation for tooth numbers
        - Include any mentioned measurements or quantities
        
        Input notes:
        {input_text}

        Generate a formal clinical note with the following format:

        DENTAL CLINICAL NOTE
        Date: {current_date}

        PROCEDURE TYPE:
        [Main procedure identified from the notes]

        CLINICAL NARRATIVE:
        [Detailed paragraph describing the procedure, including all steps, materials used, and observations]

        ASSESSMENT:
        [Clinical evaluation and current status]

        PLAN AND RECOMMENDATIONS:
        [Comprehensive paragraph about follow-up care, instructions, and recommendations][/INST]
        </s>"""

        try:
            # Generate the note
            generated_text = self.model(prompt)
            
            # Extract the relevant part (after the prompt)
            note_start = generated_text.find("DENTAL CLINICAL NOTE")
            if note_start != -1:
                return generated_text[note_start:]
            return generated_text
            
        except Exception as e:
            print(f"Error generating note: {str(e)}")
            return None

    def is_available(self):
        """
        Check if the LLM is properly initialized and available.
        """
        return self.model is not None 