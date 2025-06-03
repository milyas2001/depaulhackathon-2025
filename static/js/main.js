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
    const transcriptionArea = document.getElementById('transcriptionArea') || document.querySelector('.real-time-transcription');
    
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
        recognition.maxAlternatives = 1;

        recognition.onstart = () => {
            console.log('Speech recognition started');
            if (transcriptionArea) {
                transcriptionArea.textContent = 'Listening... Start speaking!';
                transcriptionArea.style.border = '2px solid #22c55e'; // Green border when listening
            }
        };

        recognition.onend = () => {
            console.log('Speech recognition ended');
            if (isRecording && !isPaused) {
                // Restart recognition if we're still recording (it stops after silence)
                setTimeout(() => {
                    try {
                        recognition.start();
                    } catch (error) {
                        console.log('Recognition restart failed:', error);
                    }
                }, 100);
            } else {
                if (transcriptionArea) {
                    transcriptionArea.style.border = '1px solid #374151'; // Reset border
                }
            }
        };

        recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            if (transcriptionArea) {
                if (event.error === 'no-speech') {
                    transcriptionArea.textContent = transcriptionText || 'No speech detected. Continue speaking...';
                } else if (event.error === 'network') {
                    transcriptionArea.textContent = transcriptionText || 'Network error. Please check your connection.';
                } else {
                    transcriptionArea.textContent = transcriptionText || `Error: ${event.error}`;
                }
                transcriptionArea.style.border = '2px solid #ef4444'; // Red border on error
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
                    
                    // Get patient ID from the URL
                    const currentUrl = window.location.pathname;
                    const patientId = currentUrl.split('/').pop();
                    
                    // Redirect to transcription page with patient ID
                    window.location.href = `/transcription/${patientId}`;
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
        saveTranscriptionButton.addEventListener('click', function(e) {
            const transcriptionEditArea = document.getElementById('transcriptionText');
            if (!transcriptionEditArea || !transcriptionEditArea.value.trim()) {
                alert('Please enter some transcription text before saving.');
                e.preventDefault();
                return;
            }

            // Show loading animation on the button
            saveTranscriptionButton.disabled = true;
            saveTranscriptionButton.innerHTML = '<span class="loading">Processing...</span>';

            // Form will submit normally - no need for AJAX request
            // The transcription will be sent to the backend via form POST
            
            // Clear the localStorage after submission
            localStorage.removeItem('transcription');
        });
    }

    // Add loading animation styles
    const style = document.createElement('style');
    style.textContent = `
        .loading {
            display: inline-block;
            position: relative;
            padding-right: 24px;
        }
        .loading::after {
            content: '';
            position: absolute;
            right: 0;
            top: 50%;
            transform: translateY(-50%);
            width: 16px;
            height: 16px;
            border: 2px solid #ffffff;
            border-radius: 50%;
            border-top-color: transparent;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            to {
                transform: translateY(-50%) rotate(360deg);
            }
        }
    `;
    document.head.appendChild(style);

    // Handle clinical record
    if (clinicalRecordArea) {
        const savedTranscription = localStorage.getItem('transcription');
        if (savedTranscription) {
            const textarea = document.getElementById('clinicalRecordText');
            if (textarea) {
                textarea.value = savedTranscription;
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
                    saveClinicalButton.disabled = true;
                    saveClinicalButton.textContent = 'Saving...';

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
                        
                        if (result.success) {
                            // Clear localStorage
                            localStorage.removeItem('transcription');
                            
                            alert('Note saved successfully!');
                            
                            // Redirect to patient's note history
                            if (result.patient_id) {
                                window.location.href = `/patient/${result.patient_id}`;
                            } else {
                                window.location.href = '/patients';
                            }
                        } else {
                            alert('Error: ' + (result.error || 'Failed to save note'));
                        }
                    } else {
                        const error = await response.json();
                        alert('Error saving note: ' + (error.error || 'Unknown error'));
                    }
                } catch (error) {
                    console.error('Error saving note:', error);
                    alert('Error saving note. Please try again.');
                } finally {
                    saveClinicalButton.disabled = false;
                    saveClinicalButton.textContent = 'Save Note';
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

    // Add event listeners for delete patient buttons
    document.querySelectorAll('.delete-patient-button').forEach(button => {
        button.addEventListener('click', (event) => {
            const patientId = event.target.dataset.patientId;
            const patientName = event.target.dataset.patientName;
            
            if (!patientId || !patientName) {
                alert('Error: Patient ID or Name not found.');
                return;
            }

            // Show the custom confirmation modal instead of using confirm()
            const modal = document.getElementById('deleteConfirmModal');
            const deletePatientIdField = document.getElementById('deletePatientId');
            const deletePatientNameField = document.getElementById('deletePatientName');
            const deleteButtonRefField = document.getElementById('deleteButtonRef');
            
            if (modal && deletePatientIdField && deletePatientNameField) {
                // Store the patient info and button reference in hidden fields
                deletePatientIdField.value = patientId;
                deletePatientNameField.value = patientName;
                deleteButtonRefField.value = event.target.id || Date.now(); // Use ID or timestamp as reference
                
                // Add reference to button as a data attribute
                modal.dataset.triggerButton = event.target.id || '';
                
                // Display the modal
                modal.classList.remove('hidden');
            } else {
                console.error('Delete confirmation modal or fields not found in the DOM');
            }
        });
    });

    // Handle modal button clicks
    const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
    const cancelDeleteBtn = document.getElementById('cancelDeleteBtn');
    const deleteModal = document.getElementById('deleteConfirmModal');
    
    if (confirmDeleteBtn && deleteModal) {
        confirmDeleteBtn.addEventListener('click', async () => {
            // Get patient info from hidden fields
            const patientId = document.getElementById('deletePatientId').value;
            const patientName = document.getElementById('deletePatientName').value;
            
            if (!patientId) {
                hideDeleteModal();
                return;
            }
            
            try {
                // Disable the button and show processing state
                confirmDeleteBtn.disabled = true;
                confirmDeleteBtn.innerHTML = '<span class="inline-block">Deleting...</span>';
                
                console.log(`Proceeding with deletion of patient: ${patientId}`);
                
                const response = await fetch(`/delete-patient/${patientId}`, {
                    method: 'DELETE',
                    headers: {
                        'Content-Type': 'application/json',
                        'Cache-Control': 'no-cache'
                    }
                });
                
                console.log('Delete response status:', response.status);
                const result = await response.json();
                console.log('Delete response data:', result);
                
                if (response.ok && result.success) {
                    console.log(`Successfully deleted patient: ${patientId}`);
                    
                    // Find the patient card to remove from the UI
                    const patientCard = findPatientCard(patientId);
                    
                    if (patientCard) {
                        // Remove the patient card from the DOM
                        patientCard.remove();
                        
                        // Update the patient counter if it exists
                        updatePatientCounter(-1);
                    } else {
                        console.warn(`Could not find patient card for ID: ${patientId}`);
                    }
                    
                    // Show success message
                    alert(`Patient "${patientName}" deleted successfully.`);
                } else {
                    console.error(`Error deleting patient: ${result.error || 'Unknown error'}`);
                    alert(`Error deleting patient: ${result.error || 'Unknown server error'}`);
                }
            } catch (error) {
                console.error('Error in delete operation:', error);
                alert('An unexpected error occurred while deleting the patient.');
            } finally {
                // Hide the modal and reset its state
                hideDeleteModal();
            }
        });
    }
    
    if (cancelDeleteBtn && deleteModal) {
        cancelDeleteBtn.addEventListener('click', () => {
            hideDeleteModal();
        });
    }
    
    // Helper function to hide the delete modal
    function hideDeleteModal() {
        const modal = document.getElementById('deleteConfirmModal');
        if (modal) {
            modal.classList.add('hidden');
            
            // Reset button state
            const confirmBtn = document.getElementById('confirmDeleteBtn');
            if (confirmBtn) {
                confirmBtn.disabled = false;
                confirmBtn.textContent = 'Yes, Delete';
            }
            
            // Clear the stored values
            const idField = document.getElementById('deletePatientId');
            const nameField = document.getElementById('deletePatientName');
            if (idField) idField.value = '';
            if (nameField) nameField.value = '';
        }
    }
    
    // Helper function to find patient card by ID
    function findPatientCard(patientId) {
        // Try to find the patient card using the ID attribute
        let card = document.querySelector(`.patient-card-item[data-patient-id="${patientId}"]`);
        
        // If not found, search for a card containing a button with the matching data-patient-id
        if (!card) {
            const deleteButton = document.querySelector(`button[data-patient-id="${patientId}"]`);
            if (deleteButton) {
                card = deleteButton.closest('.patient-card-item');
            }
        }
        
        return card;
    }
    
    // Helper function to update the patient counter
    function updatePatientCounter(change) {
        const patientCountElement = document.querySelector('.text-2xl.font-bold');
        if (patientCountElement) {
            const currentCount = parseInt(patientCountElement.textContent);
            if (!isNaN(currentCount)) {
                patientCountElement.textContent = (currentCount + change).toString();
            }
        }
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
    if (!isRecording) {
        isRecording = true;
        isPaused = false;
        transcriptionText = '';  // Reset transcription
        
        // Clear any existing cursor
        const existingCursor = document.querySelector('.cursor');
        if (existingCursor) {
            existingCursor.remove();
        }
        
        recognition.onresult = (event) => {
            let finalTranscript = '';
            let interimTranscript = '';
            
            // Process all results from the current recognition session
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript + ' ';
                } else {
                    interimTranscript += transcript;
                }
            }
            
            // Store the cumulative final transcript
            if (finalTranscript) {
                transcriptionText += finalTranscript;
                console.log('Final transcript added:', finalTranscript);
            }
            
            // Update display with both final and interim results in real-time
            const combinedText = transcriptionText + interimTranscript;
            console.log('Updating display with:', combinedText);
            updateTranscriptionDisplay(combinedText);
        };
        
        recognition.onspeechstart = () => {
            console.log('Speech detected - real-time transcription starting');
            if (transcriptionArea) {
                transcriptionArea.style.border = '2px solid #22c55e';
            }
        };
        
        recognition.onspeechend = () => {
            console.log('Speech ended - waiting for more speech');
        };
        
        try {
            recognition.start();
            console.log('Recording started - speak now for real-time transcription');
        } catch (error) {
            console.error('Failed to start recognition:', error);
            if (transcriptionArea) {
                transcriptionArea.textContent = 'Failed to start speech recognition. Please try again.';
            }
        }
    }
}

function pauseRecording(recognition) {
    if (isRecording && !isPaused) {
        recognition.stop();
        isPaused = true;
        console.log('Recording paused');
    }
}

function resumeRecording(recognition) {
    if (isRecording && isPaused) {
        recognition.start();
        isPaused = false;
        console.log('Recording resumed');
    }
}

function stopRecording(recognition) {
    if (isRecording) {
        recognition.stop();
        isRecording = false;
        isPaused = false;
        
        // Remove blinking cursor
        const cursor = document.querySelector('.cursor');
        if (cursor) {
            cursor.remove();
        }
        
        // Reset border style
        if (transcriptionArea) {
            transcriptionArea.style.border = '1px solid #374151';
        }
        
        // Ensure we have transcription text
        if (!transcriptionText.trim()) {
            // Get text from the display area as fallback
            const displayArea = document.getElementById('transcriptionArea');
            if (displayArea) {
                const textContent = displayArea.textContent || displayArea.innerText || '';
                // Remove any placeholder text
                if (textContent && !textContent.includes('Listening') && !textContent.includes('Error')) {
                    transcriptionText = textContent;
                }
            }
        }
        
        console.log('Recording stopped. Final transcription:', transcriptionText);
        
        // Show completion message
        if (transcriptionArea && transcriptionText.trim()) {
            transcriptionArea.innerHTML = `<span style="color: #ffffff;">${transcriptionText}</span><br><br><span style="color: #22c55e; font-style: italic;">✓ Recording completed! Redirecting to review...</span>`;
        }
    }
}

function updateTranscriptionDisplay(text) {
    const transcriptionArea = document.getElementById('transcriptionArea');
    if (transcriptionArea) {
        if (!text || text.trim() === '') {
            transcriptionArea.innerHTML = '<span style="color: #6b7280; font-style: italic;">Listening... Start speaking!</span>';
        } else {
            // Split the text into final (stored) and interim (current) parts
            const finalText = transcriptionText || '';
            const currentText = text.replace(finalText, '');
            
            // Create HTML with different styling for final vs interim text
            let displayHTML = '';
            if (finalText) {
                displayHTML += `<span style="color: #ffffff;">${finalText}</span>`;
            }
            if (currentText) {
                displayHTML += `<span style="color: #3b82f6; font-style: italic; background: rgba(59, 130, 246, 0.1); padding: 0 2px; border-radius: 2px;">${currentText}</span>`;
            }
            
            transcriptionArea.innerHTML = displayHTML;
        }
        
        // Auto-scroll to bottom
        transcriptionArea.scrollTop = transcriptionArea.scrollHeight;
        
        // Add a blinking cursor effect
        if (isRecording && !transcriptionArea.querySelector('.cursor')) {
            const cursor = document.createElement('span');
            cursor.className = 'cursor';
            cursor.style.cssText = 'color: #22c55e; animation: blink 1s infinite; margin-left: 2px;';
            cursor.textContent = '|';
            transcriptionArea.appendChild(cursor);
            
            // Add CSS animation for blinking cursor
            if (!document.getElementById('cursor-animation')) {
                const style = document.createElement('style');
                style.id = 'cursor-animation';
                style.textContent = `
                    @keyframes blink {
                        0%, 50% { opacity: 1; }
                        51%, 100% { opacity: 0; }
                    }
                `;
                document.head.appendChild(style);
            }
        }
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