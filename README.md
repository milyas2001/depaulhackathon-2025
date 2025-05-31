# Dental Documentation Assistant

A web application that helps dental professionals create and manage clinical documentation through voice and text input.

## Features

- Voice-to-text transcription
- AI-powered clinical note generation using DeepSeek
- Patient management system
- Note history and search
- Real-time transcription editing
- Professional clinical formatting

## Technologies Used

- Flask - Web framework
- DeepSeek - AI model for clinical note generation
- Web Speech API - Voice recognition
- SQLite - Data storage
- TailwindCSS - Styling

## Setup Instructions

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the application:
   ```bash
   python app.py
   ```
5. Access the application at http://localhost:5010

## Usage

1. Enter patient information or select from recent patients
2. Start recording or enter notes manually
3. Review and edit the transcription
4. Generate and review the clinical note
5. Save the final documentation

## Note Generation

The application uses DeepSeek's AI model to convert informal dental notes into professional clinical documentation. The model is trained to:

- Use proper dental terminology
- Structure notes in a clinical format
- Include relevant patient information
- Highlight procedures and findings
- Add appropriate follow-up recommendations

## Security and Privacy

- All data is stored locally
- No external API calls for note processing
- Patient information is session-based
- Secure password protection

## Directory Structure

- `/app.py` - Main application file
- `/static/` - Static files (JS, CSS)
- `/templates/` - HTML templates
- `/data/` - Local data storage
  - `/notes/` - Patient notes
  - `/patients/` - Patient information
- `/flask_session/` - Server-side session storage

## Data Storage

Notes and patient data are stored locally in the following locations:
- Patient notes: `/data/notes/<patient_id>/<note_id>.json`
- Patient information: `/data/patients/<patient_id>.json`

## Dependencies

- Flask - Web framework
- Flask-Session - Server-side session management
- GPT4All - Local AI model for note generation
- CTTransformers - Transformer models for local inference

## Project Structure

-   `app.py`: Main Flask application file.
-   `templates/`: Contains HTML templates.
    -   `index.html`: Main page of the application.
-   `static/`: Contains static files.
    -   `css/style.css`: Styles for the application.
    -   `js/script.js`: JavaScript for client-side interactions (e.g., audio recording).
-   `requirements.txt`: Python dependencies.
-   `README.md`: This file.

## TODO / Future Enhancements

-   Implement actual speech-to-text functionality (e.g., using Web Speech API, or a cloud service like Google Speech-to-Text, Azure Speech, etc.).
-   Develop the core NLP logic in `convert_to_formal_note` function in `app.py` to accurately parse dental shorthand and generate SOAP notes or progress notes.
-   Add user authentication if handling sensitive patient data.
-   Improve UI/UX.
-   Database integration for storing notes.
