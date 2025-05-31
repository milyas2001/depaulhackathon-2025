document.addEventListener('DOMContentLoaded', () => {
    const patientIdInput = document.getElementById('patientId');
    const startGenerationButton = document.getElementById('startGenerationButton');
    const stopGenerationButton = document.getElementById('stopGenerationButton');
    const transcribedTextOutput = document.getElementById('transcribedTextOutput');
    const templateInput = document.getElementById('templateInput');
    const generateRefurbishedButton = document.getElementById('generateRefurbishedButton');
    const refurbishedNoteOutput = document.getElementById('refurbishedNoteOutput');

    let mediaRecorder;
    let audioChunks = [];
    let recognition; // For Web Speech API
    let isRecording = false;

    // Check for browser speech recognition support
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        recognition.onresult = (event) => {
            let interimTranscript = '';
            let finalTranscript = transcribedTextOutput.innerHTML === 'Speak to see your notes here...' ? '' : transcribedTextOutput.innerHTML;
            // Keep existing newlines if any when appending new text
            if (finalTranscript.length > 0 && !finalTranscript.endsWith('\n')) {
                finalTranscript += ' '; // Add space if not ending with newline and has content
            }

            for (let i = event.resultIndex; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                    finalTranscript += event.results[i][0].transcript + '\n'; // Add newline after each final segment
                } else {
                    interimTranscript += event.results[i][0].transcript;
                }
            }
            transcribedTextOutput.innerHTML = finalTranscript + '<i style="color:grey">' + interimTranscript + '</i>';
        };

        recognition.onerror = (event) => {
            console.error('Speech recognition error', event.error);
            transcribedTextOutput.innerHTML += `<p style="color:red;">Error during transcription: ${event.error}</p>`;
            stopActualRecording(); // Ensure recording stops on error
        };

        recognition.onend = () => {
            if(isRecording) { // If it ended unexpectedly and we are supposed to be recording, restart it
                console.log("Speech recognition service disconnected, restarting...");
                recognition.start();
            }
        };

    } else {
        console.warn('Speech Recognition API not supported in this browser.');
        startGenerationButton.disabled = true;
        startGenerationButton.textContent = 'Browser Not Supported';
        transcribedTextOutput.textContent = 'Live transcription is not supported by your browser. You can still type notes manually.';
    }

    function startActualRecording() {
        if (recognition && !isRecording) {
            transcribedTextOutput.innerHTML = transcribedTextOutput.innerHTML === 'Speak to see your notes here...' ? '' : transcribedTextOutput.innerHTML; // Clear placeholder only if it exists
            recognition.start();
            isRecording = true;
            startGenerationButton.disabled = true;
            stopGenerationButton.disabled = false;
            console.log("Voice note generation started.");
        }
        // Fallback or alternative recording mechanism (e.g., MediaRecorder for sending audio to backend) can be added here
        // For now, focusing on Web Speech API for real-time client-side transcription
    }

    function stopActualRecording() {
        if (recognition && isRecording) {
            recognition.stop();
            isRecording = false;
            startGenerationButton.disabled = false;
            stopGenerationButton.disabled = true;
            console.log("Voice note generation stopped.");
            // Remove any lingering interim transcript styling
            transcribedTextOutput.innerHTML = transcribedTextOutput.innerHTML.replace(/<i style="color:grey">.*?<\/i>/g, '');
        }
    }

    if (startGenerationButton) {
        startGenerationButton.onclick = () => {
            if (!patientIdInput.value.trim()) {
                alert("Please enter a Patient ID before starting note generation.");
                patientIdInput.focus();
                return;
            }
            startActualRecording();
        };
    }

    if (stopGenerationButton) {
        stopGenerationButton.onclick = () => {
            stopActualRecording();
        };
    }

    if (generateRefurbishedButton) {
        generateRefurbishedButton.onclick = async () => {
            const patientId = patientIdInput.value.trim();
            const transcribedText = transcribedTextOutput.innerText; // Use innerText to get clean text
            const templateText = templateInput.value;

            if (!transcribedText || transcribedText === 'Speak to see your notes here...') {
                alert("Please generate some notes before refurbishing.");
                return;
            }
            if (!templateText) {
                alert("Please provide a template for refurbishment.");
                templateInput.focus();
                return;
            }

            refurbishedNoteOutput.textContent = 'Refurbishing notes...';

            try {
                const response = await fetch('/refurbish', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ 
                        patient_id: patientId, // Sending patient ID as well
                        transcribed_text: transcribedText,
                        template_text: templateText 
                    })
                });
                const data = await response.json();
                if (response.ok) {
                    refurbishedNoteOutput.textContent = data.refurbished_note;
                } else {
                    refurbishedNoteOutput.textContent = `Error: ${data.error || 'Could not refurbish notes.'}`;
                }
            } catch (error) {
                console.error('Error refurbishing notes:', error);
                refurbishedNoteOutput.textContent = 'An error occurred while refurbishing notes.';
            }
        };
    }
}); 