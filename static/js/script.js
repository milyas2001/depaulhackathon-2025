let mediaRecorder;
let audioChunks = [];
let isRecording = false;

document.addEventListener('DOMContentLoaded', () => {
    const recordButton = document.getElementById('recordButton');
    const stopButton = document.getElementById('stopButton');
    const noteForm = document.getElementById('noteForm');
    const formattedNoteOutput = document.getElementById('formatted_note_output');
    const textInput = document.getElementById('text_input');
    const audioDataInput = document.getElementById('audio_data');

    if (recordButton) {
        recordButton.onclick = startRecording;
    }
    if (stopButton) {
        stopButton.onclick = stopRecording;
    }

    if (noteForm) {
        noteForm.onsubmit = async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            try {
                const response = await fetch('/process_audio', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const result = await response.text();
                document.getElementById('formatted_note_output').textContent = result;
            } catch (error) {
                console.error('Error:', error);
                document.getElementById('formatted_note_output').textContent = 'Error processing input: ' + error.message;
            }
        };
    }
});

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        
        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            const formData = new FormData();
            formData.append('audio_data', audioBlob, 'recording.wav');
            
            try {
                const response = await fetch('/process_audio', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const result = await response.text();
                document.getElementById('formatted_note_output').textContent = result;
            } catch (error) {
                console.error('Error:', error);
                document.getElementById('formatted_note_output').textContent = 'Error processing audio: ' + error.message;
            }
            
            // Reset for next recording
            audioChunks = [];
        };

        // Start recording
        mediaRecorder.start();
        isRecording = true;
        
        // Update UI
        document.getElementById('recordButton').disabled = true;
        document.getElementById('stopButton').disabled = false;
        document.getElementById('formatted_note_output').textContent = 'Recording...';
        
    } catch (error) {
        console.error('Error:', error);
        document.getElementById('formatted_note_output').textContent = 'Error accessing microphone: ' + error.message;
    }
}

function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        
        // Update UI
        document.getElementById('recordButton').disabled = false;
        document.getElementById('stopButton').disabled = true;
        document.getElementById('formatted_note_output').textContent = 'Processing audio...';
        
        // Stop all audio tracks
        mediaRecorder.stream.getTracks().forEach(track => track.stop());
    }
}

// Handle form submission for text input
document.getElementById('noteForm').onsubmit = async function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    try {
        const response = await fetch('/process_audio', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.text();
        document.getElementById('formatted_note_output').textContent = result;
    } catch (error) {
        console.error('Error:', error);
        document.getElementById('formatted_note_output').textContent = 'Error processing input: ' + error.message;
    }
}; 