# Dentist Note Transcriber Web Application

This web application is designed for dentists to transcribe voice notes into text in real-time. It allows for the input of patient IDs and refines the notes based on user-provided templates.

## User Flow

1.  **Landing Page:**
    *   Modern and visually appealing landing page.
    *   Title: "Every Dentist's Top Choice for Note Generation."
    *   Prominent button: "Start Note-Taking."

2.  **Note Generation Page:**
    *   Accessed by clicking the button on the landing page.
    *   Input field for Patient ID.
    *   "Start Note Generation" button to activate voice recording.

3.  **Voice Transcription (Client-Side with Web Speech API - Initial Implementation):**
    *   Utilizes the browser's Web Speech API for real-time voice-to-text.
    *   Displays transcribed text as the dentist speaks.
    *   *Future Enhancement: Integrate robust open-source tools like Mozilla DeepSpeech or Kaldi for server-side processing if higher accuracy or more control is needed.*

4.  **Completion of Transcription:**
    *   Dentist stops speaking (or clicks "Stop Note Generation").
    *   Transcribed text is clearly visible and editable.

5.  **Note Refinement:**
    *   "Template" box for dentists to enter a sample note format.
    *   "Generate Refurbished Notes" button.

6.  **Refurbishment Process (Placeholder):**
    *   The application will send the transcribed text and the template to a backend endpoint.
    *   *Future Enhancement: Integrate an external open-source model (e.g., a fine-tuned version of GPT, BERT, or other NLP models) to summarize and format the transcribed notes based on the provided template.*
    *   Displays the refurbished notes.

## Technical Details

*   **Frontend:** HTML, CSS, JavaScript
*   **Backend:** Python (Flask)
*   **Real-time Transcription (Initial):** Web Speech API (browser-dependent)
*   **Note Refinement Model (Future):** Open-source NLP models (e.g., GPT-2, BERT, T5, etc. via libraries like Hugging Face Transformers).

## Setup and Running

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd <repository-directory>
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the Flask application:**
    ```bash
    python app.py
    ```

5.  Open your web browser and go to `http://127.0.0.1:5000/`.

## Project Structure

-   `app.py`: Main Flask application file with routes.
-   `templates/`:
    -   `landing.html`: The landing page.
    -   `note_generation.html`: The page for taking notes.
-   `static/`:
    -   `css/style.css`: CSS styles for the application.
    -   `js/`:
        -   `landing.js`: JavaScript for the landing page.
        -   `note_taking.js`: JavaScript for the note generation page (handles Web Speech API, form submissions).
-   `requirements.txt`: Python dependencies (currently just Flask).
-   `README.md`: This file.

## Key Features Implemented (Initial Version)

*   Landing page with navigation to the note-taking page.
*   Note generation page with Patient ID input.
*   Client-side real-time voice transcription using the Web Speech API (browser-dependent).
*   Ability to manually edit transcribed text.
*   Input for a note template.
*   Placeholder functionality for "Refurbish Notes" which sends data to a backend endpoint.

## Future Enhancements & TODOs

*   **Robust Speech-to-Text:**
    *   Implement server-side speech-to-text using Mozilla DeepSpeech, Kaldi, or a similar open-source engine for better accuracy, less browser dependency, and handling of larger audio files/streams.
    *   This will involve sending audio data (e.g., recorded via `MediaRecorder` API) to the backend.
*   **Note Refinement AI Model Integration:**
    *   Integrate a suitable open-source NLP model (e.g., from Hugging Face Transformers library) into the `/refurbish` backend endpoint.
    *   This model will need to be capable of understanding the context of the transcribed dental notes and reformatting/summarizing them according to the user-provided template (e.g., extracting information for SOAP notes).
*   **Data Persistence:** Store patient notes and templates (e.g., in a database).
*   **Security and Compliance:** Thoroughly address data protection regulations (HIPAA if applicable in target regions) for patient information. This includes secure data transmission, storage, and access controls.
*   **Error Handling and UI/UX Improvements:** Enhance error messages, loading states, and overall user experience.
*   **User Authentication:** If required for data security and user-specific templates.
*   **Testing:** Comprehensive usability testing with dentists.
*   **Deployment:** Prepare for scalable deployment.
