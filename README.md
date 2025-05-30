# Dental Documentation Assistant

This web application listens to shorthand, informal, or dialect-based voice input from a dentist and converts it into a formal, professional dental clinical note.

## Features

-   Voice input recording (requires browser permission for microphone)
-   Text input for notes
-   Conversion of informal notes to formal clinical documentation (placeholder logic)

## Setup and Running

1.  **Clone the repository (if you haven't already):**
    ```bash
    git clone <repository-url>
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
