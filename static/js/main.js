let mediaRecorder;
let audioChunks = [];
let isRecording = false;
let isPaused = false;
let transcriptionText = '';

document.addEventListener('DOMContentLoaded', () => {
    // Dashboard elements
    const patientNameInput = document.getElementById('patientName');
    const patientIdInput = document.getElementById('patientId');
    const startNoteTakingButton = document.getElementById('startNoteTaking');
    const recentPatientsContainer = document.querySelector('.grid');

    // Recording screen elements
    const startButton = document.getElementById('startRecording');
    const pauseButton = document.getElementById('pauseRecording');
    const stopButton = document.getElementById('stopRecording');
    const transcriptionArea = document.querySelector('.real-time-transcription');
    
    // Transcription screen elements
    const transcriptionEditArea = document.getElementById('transcriptionText');
    const saveTranscriptionButton = document.getElementById('saveTranscription');
    
    // Clinical record screen elements
    const editButton = document.getElementById('editRecord');
    const saveClinicalButton = document.getElementById('saveRecord');
    const clinicalRecordArea = document.querySelector('.clinical-record');

    // Patient search functionality
    const searchInput = document.getElementById('searchInput');
    const searchButton = document.getElementById('searchButton');
    const searchResults = document.getElementById('searchResults');
    const searchResultsList = document.getElementById('searchResultsList');

    // Handle dashboard functionality
    if (patientNameInput && patientIdInput) {
        loadRecentPatients();

        // Enable/disable start button based on inputs
        const validateInputs = () => {
            const nameValid = patientNameInput.value.trim() !== '';
            const idValid = patientIdInput.value.trim() !== '';
            startNoteTakingButton.disabled = !(nameValid && idValid);
        };

        patientNameInput.addEventListener('input', validateInputs);
        patientIdInput.addEventListener('input', validateInputs);

        startNoteTakingButton.addEventListener('click', () => {
            const patientName = patientNameInput.value.trim();
            const patientId = patientIdInput.value.trim();
            
            if (patientName && patientId) {
                const form = document.createElement('form');
                form.method = 'POST';
                form.action = '/start-recording';
                
                const nameInput = document.createElement('input');
                nameInput.type = 'hidden';
                nameInput.name = 'patient_name';
                nameInput.value = patientName;
                
                const idInput = document.createElement('input');
                idInput.type = 'hidden';
                idInput.name = 'patient_id';
                idInput.value = patientId;
                
                form.appendChild(nameInput);
                form.appendChild(idInput);
                document.body.appendChild(form);
                form.submit();
            }
        });
    }

    // Initialize Web Speech API for recording screen
    if (startButton) {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            startButton.disabled = true;
            alert('Speech recognition is not supported in this browser. Please use Chrome, Edge, or Safari.');
            return;
        }

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        recognition.onstart = () => {
            console.log('Speech recognition started');
            if (transcriptionArea) {
                transcriptionArea.textContent = 'Listening...';
            }
        };

        recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            if (transcriptionArea) {
                transcriptionArea.textContent = 'Error: ' + event.error;
            }
        };

        startButton.addEventListener('click', () => {
            if (!isRecording) {
                startRecording(recognition);
                startButton.classList.add('bg-[#303030]');
                startButton.classList.remove('bg-black');
                pauseButton.disabled = false;
                stopButton.disabled = false;
            }
        });

        if (pauseButton) {
            pauseButton.addEventListener('click', () => {
                if (isRecording && !isPaused) {
                    pauseRecording(recognition);
                    pauseButton.textContent = 'Resume Recording';
                    pauseButton.classList.add('bg-black');
                    pauseButton.classList.remove('bg-[#303030]');
                } else if (isRecording && isPaused) {
                    resumeRecording(recognition);
                    pauseButton.textContent = 'Pause Recording';
                    pauseButton.classList.remove('bg-black');
                    pauseButton.classList.add('bg-[#303030]');
                }
            });
        }

        if (stopButton) {
            stopButton.addEventListener('click', () => {
                if (isRecording) {
                    stopRecording(recognition);
                    // Save transcription and navigate to review screen
                    localStorage.setItem('transcription', transcriptionText);
                    window.location.href = '/transcription';
                }
            });
        }
    }

    // Handle transcription editing
    if (transcriptionEditArea) {
        // Load the transcription from localStorage
        const savedTranscription = localStorage.getItem('transcription');
        if (savedTranscription) {
            transcriptionEditArea.value = savedTranscription;
        }
    }

    if (saveTranscriptionButton) {
        saveTranscriptionButton.addEventListener('click', async () => {
            const transcriptionEditArea = document.getElementById('transcriptionText');
            if (!transcriptionEditArea || !transcriptionEditArea.value.trim()) {
                alert('Please enter some transcription text before saving.');
                return;
            }

            const transcriptionText = transcriptionEditArea.value.trim();
            try {
                const response = await fetch('/process_transcription', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ 
                        transcription: transcriptionText
                    }),
                });
                
                if (response.ok) {
                    const result = await response.json();
                    if (result.clinical_record) {
                        // Store both the transcription and the clinical record
                        localStorage.setItem('transcription', transcriptionText);
                        localStorage.setItem('clinicalRecord', result.clinical_record);
                        window.location.href = '/clinical-record';
                    } else {
                        alert('Error: No clinical record generated');
                    }
                } else {
                    alert('Error processing transcription. Please try again.');
                }
            } catch (error) {
                console.error('Error processing transcription:', error);
                alert('Error processing transcription. Please try again.');
            }
        });
    }

    // Handle clinical record
    if (clinicalRecordArea) {
        const savedRecord = localStorage.getItem('clinicalRecord');
        if (savedRecord) {
            const textarea = document.getElementById('clinicalRecordText');
            if (textarea) {
                textarea.value = savedRecord;
            }
        }
    }

    if (editButton) {
        editButton.addEventListener('click', () => {
            const textarea = clinicalRecordArea.querySelector('textarea');
            if (textarea) {
                textarea.readOnly = false;
                textarea.focus();
            }
        });
    }

    if (saveClinicalButton) {
        saveClinicalButton.addEventListener('click', async () => {
            const textarea = document.getElementById('clinicalRecordText');
            if (textarea) {
                try {
                    const response = await fetch('/save-note', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ 
                            content: textarea.value,
                            timestamp: new Date().toISOString()
                        })
                    });

                    if (response.ok) {
                        const result = await response.json();
                        alert('Clinical record saved successfully!');
                        // Redirect to patient's note history
                        const currentPatient = await fetch('/get-current-patient').then(res => res.json());
                        if (currentPatient && currentPatient.id) {
                            window.location.href = `/patient/${currentPatient.id}`;
                        } else {
                            window.location.href = '/patients';
                        }
                    } else {
                        const error = await response.json();
                        alert('Error saving clinical record: ' + (error.error || 'Unknown error'));
                    }
                } catch (error) {
                    console.error('Error saving clinical record:', error);
                    alert('Error saving clinical record. Please try again.');
                }
            }
        });
    }

    if (searchInput && searchButton) {
        // Enable search on Enter key
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                performSearch();
            }
        });

        // Enable search on button click
        searchButton.addEventListener('click', performSearch);
    }
});

async function loadRecentPatients() {
    try {
        const response = await fetch('/get-recent-patients');
        if (response.ok) {
            const patients = await response.json();
            const container = document.querySelector('.grid');
            if (container && patients.length > 0) {
                container.innerHTML = patients.map(patient => `
                    <div class="flex items-center justify-between bg-[#303030] rounded-xl p-4">
                        <div class="flex flex-col">
                            <span class="text-white text-base font-medium">${patient.name}</span>
                            <span class="text-[#ababab] text-sm">ID: ${patient.id}</span>
                        </div>
                        <button
                            onclick="selectPatient('${patient.name}', '${patient.id}')"
                            class="flex items-center justify-center rounded-full h-8 px-3 bg-black text-white text-sm font-bold"
                        >
                            Start Note
                        </button>
                    </div>
                `).join('');
            } else if (container) {
                container.innerHTML = '<p class="text-[#ababab] text-sm">No recent patients</p>';
            }
        }
    } catch (error) {
        console.error('Error loading recent patients:', error);
    }
}

function selectPatient(name, id) {
    const nameInput = document.getElementById('patientName');
    const idInput = document.getElementById('patientId');
    if (nameInput && idInput) {
        nameInput.value = name;
        idInput.value = id;
        const startButton = document.getElementById('startNoteTaking');
        if (startButton) {
            startButton.disabled = false;
            startButton.click();
        }
    }
}

function startRecording(recognition) {
    isRecording = true;
    isPaused = false;
    transcriptionText = '';
    
    try {
        recognition.start();
        
        recognition.onresult = (event) => {
            const transcript = Array.from(event.results)
                .map(result => result[0].transcript)
                .join('');
            
            transcriptionText = transcript;
            updateTranscriptionDisplay(transcript);
        };
    } catch (error) {
        console.error('Error starting recording:', error);
        alert('Error starting recording. Please try again.');
    }
}

function pauseRecording(recognition) {
    isPaused = true;
    try {
        recognition.stop();
    } catch (error) {
        console.error('Error pausing recording:', error);
    }
}

function resumeRecording(recognition) {
    isPaused = false;
    try {
        recognition.start();
    } catch (error) {
        console.error('Error resuming recording:', error);
    }
}

function stopRecording(recognition) {
    isRecording = false;
    isPaused = false;
    try {
        recognition.stop();
    } catch (error) {
        console.error('Error stopping recording:', error);
    }
}

function updateTranscriptionDisplay(text) {
    const transcriptionArea = document.querySelector('.real-time-transcription');
    if (transcriptionArea) {
        transcriptionArea.textContent = text || 'No transcription available';
    }
}

async function performSearch() {
    const query = searchInput.value.trim();
    if (!query) {
        searchResults.classList.add('hidden');
        return;
    }

    try {
        const response = await fetch(`/search-patients?q=${encodeURIComponent(query)}`);
        if (response.ok) {
            const results = await response.json();
            displaySearchResults(results);
        } else {
            console.error('Error searching patients');
        }
    } catch (error) {
        console.error('Error searching patients:', error);
    }
}

function displaySearchResults(results) {
    if (!searchResults || !searchResultsList) return;

    if (results.length === 0) {
        searchResultsList.innerHTML = '<p class="text-[#ababab] text-sm">No matching patients found</p>';
    } else {
        searchResultsList.innerHTML = results.map(patient => `
            <div class="flex items-center justify-between bg-[#303030] rounded-xl p-4">
                <div class="flex flex-col">
                    <span class="text-white text-base font-medium">${patient.name}</span>
                    <span class="text-[#ababab] text-sm">ID: ${patient.id}</span>
                </div>
                <div class="flex gap-2">
                    <button
                        onclick="window.location.href='/patient/${patient.id}'"
                        class="flex items-center justify-center rounded-full h-8 px-3 bg-[#212121] text-white text-sm font-bold"
                    >
                        View History
                    </button>
                    <button
                        onclick="window.location.href='/start-recording?patient_id=${patient.id}'"
                        class="flex items-center justify-center rounded-full h-8 px-3 bg-black text-white text-sm font-bold"
                    >
                        New Note
                    </button>
                </div>
            </div>
        `).join('');
    }

    searchResults.classList.remove('hidden');
} 