let mediaRecorder;
let audioChunks = [];

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
        noteForm.onsubmit = async function(event) {
            event.preventDefault();
            formattedNoteOutput.textContent = 'Processing...';
            const formData = new FormData(noteForm);
            let response;

            try {
                response = await fetch('/process_audio', {
                    method: 'POST',
                    body: formData
                });

                if (response.ok) {
                    const resultText = await response.text();
                    formattedNoteOutput.textContent = resultText;
                } else {
                    formattedNoteOutput.textContent = `Error: ${response.status} ${await response.text()}`;
                }
            } catch (error) {
                console.error('Error submitting form:', error);
                formattedNoteOutput.textContent = 'Error processing your request. Please try again.';
            }
        };
    }
});

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        mediaRecorder.start();

        audioChunks = []; // Reset chunks for new recording
        mediaRecorder.addEventListener("dataavailable", event => {
            audioChunks.push(event.data);
        });

        mediaRecorder.addEventListener("stop", () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' }); // Or 'audio/webm' or other supported types
            const audioUrl = URL.createObjectURL(audioBlob);
            // For debugging: const audio = new Audio(audioUrl);
            // audio.play();

            // Create a File object from the Blob
            const audioFile = new File([audioBlob], "recorded_audio.wav", {type: 'audio/wav'});
            
            // Put the recorded audio into the file input
            const dataTransfer = new DataTransfer();
            dataTransfer.items.add(audioFile);
            document.getElementById('audio_data').files = dataTransfer.files;

            // Optionally, submit the form automatically or enable a submit button
            // document.getElementById('noteForm').submit(); 
        });

        document.getElementById('recordButton').disabled = true;
        document.getElementById('stopButton').disabled = false;
        document.getElementById('text_input').disabled = true; // Disable text input during recording
        document.getElementById('audio_data').disabled = true; // Disable file upload during recording
        console.log("Recording started");
    } catch (err) {
        console.error("Error starting recording: ", err);
        alert("Could not start recording. Please ensure you have a microphone and have granted permission.");
    }
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state === "recording") {
        mediaRecorder.stop();
        // The "stop" event listener for mediaRecorder will handle the audio blob creation.
        console.log("Recording stopped");
    }
    document.getElementById('recordButton').disabled = false;
    document.getElementById('stopButton').disabled = true;
    document.getElementById('text_input').disabled = false;
    document.getElementById('audio_data').disabled = false;

} 