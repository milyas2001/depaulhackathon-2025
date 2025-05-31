document.addEventListener('DOMContentLoaded', () => {
    const startNoteTakingButton = document.getElementById('startNoteTakingButton');

    if (startNoteTakingButton) {
        startNoteTakingButton.addEventListener('click', () => {
            window.location.href = '/note'; // Navigate to the note generation page
        });
    }
}); 