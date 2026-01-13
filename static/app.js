/**
 * MedScan - Enhanced Medical Form Digitizer
 * Handles navigation, file upload, API calls, and PDF download
 */

// DOM Elements - Navigation
const sidebar = document.getElementById('sidebar');
const menuToggle = document.getElementById('menuToggle');
const navItems = document.querySelectorAll('.nav-item');
const pageTitle = document.getElementById('pageTitle');

// DOM Elements - Sections
const homeSection = document.getElementById('homeSection');
const digitizeSection = document.getElementById('digitizeSection');
const overlaySection = document.getElementById('overlaySection');

// DOM Elements - Upload
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
const uploadCard = document.getElementById('uploadCard');
const fileCard = document.getElementById('fileCard');
const fileName = document.getElementById('fileName');
const fileSize = document.getElementById('fileSize');
const removeFile = document.getElementById('removeFile');
const processBtn = document.getElementById('processBtn');
const processingCard = document.getElementById('processingCard');
const processingStatus = document.getElementById('processingStatus');
const progressFill = document.getElementById('progressFill');
const resultCard = document.getElementById('resultCard');
const resultInfo = document.getElementById('resultInfo');
const downloadBtn = document.getElementById('downloadBtn');
const newUploadBtn = document.getElementById('newUploadBtn');
const errorCard = document.getElementById('errorCard');
const errorMessage = document.getElementById('errorMessage');
const retryBtn = document.getElementById('retryBtn');

// State
let selectedFile = null;
let downloadUrl = null;
let currentSection = 'home';

// API endpoint
const API_URL = '/api/v1/process/generate';

// Section titles
const sectionTitles = {
    'home': 'Welcome',
    'digitize': 'Digitize Medical Form',
    'overlay': 'Form Overlay'
};

// Navigation
function showSection(sectionId) {
    currentSection = sectionId;

    // Update nav items
    navItems.forEach(item => {
        item.classList.remove('active');
        if (item.dataset.section === sectionId) {
            item.classList.add('active');
        }
    });

    // Update page title
    pageTitle.textContent = sectionTitles[sectionId] || 'MedScan';

    // Show/hide sections
    document.querySelectorAll('.section').forEach(section => {
        section.classList.remove('active');
    });

    const targetSection = document.getElementById(sectionId + 'Section');
    if (targetSection) {
        targetSection.classList.add('active');
    }

    // Close mobile sidebar
    sidebar.classList.remove('open');
}

// Make showSection global for onclick handlers
window.showSection = showSection;

// Nav item clicks
navItems.forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        showSection(item.dataset.section);
    });
});

// Mobile menu toggle
menuToggle.addEventListener('click', () => {
    sidebar.classList.toggle('open');
});

// Close sidebar when clicking outside on mobile
document.addEventListener('click', (e) => {
    if (window.innerWidth <= 768) {
        if (!sidebar.contains(e.target) && !menuToggle.contains(e.target)) {
            sidebar.classList.remove('open');
        }
    }
});

// Utility functions
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function showCard(card) {
    // Hide all cards
    [uploadCard, fileCard, processingCard, resultCard, errorCard].forEach(c => {
        c.classList.add('hidden');
    });
    // Show target card
    card.classList.remove('hidden');
}

function resetUploadState() {
    selectedFile = null;
    if (downloadUrl) {
        URL.revokeObjectURL(downloadUrl);
        downloadUrl = null;
    }
    progressFill.style.width = '0%';
    showCard(uploadCard);
}

// File handling
function handleFile(file) {
    // Validate file type
    const validTypes = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg'];
    if (!validTypes.includes(file.type)) {
        alert('Please upload a PDF, JPG, or PNG file.');
        return;
    }

    // Validate file size (max 50MB)
    const maxSize = 50 * 1024 * 1024;
    if (file.size > maxSize) {
        alert('File size must be less than 50MB.');
        return;
    }

    selectedFile = file;
    fileName.textContent = file.name;
    fileSize.textContent = formatFileSize(file.size);
    showCard(fileCard);
}

// Drag & Drop
dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
});

dropzone.addEventListener('dragleave', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
});

dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');

    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
});

// Click to upload
dropzone.addEventListener('click', () => {
    fileInput.click();
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFile(e.target.files[0]);
    }
});

// Remove file
removeFile.addEventListener('click', () => {
    resetUploadState();
});

// Process document
processBtn.addEventListener('click', async () => {
    if (!selectedFile) return;

    showCard(processingCard);

    // Simulate progress
    let progress = 0;
    const progressInterval = setInterval(() => {
        progress += Math.random() * 15;
        if (progress > 90) progress = 90;
        progressFill.style.width = progress + '%';
    }, 500);

    // Update status messages
    const statusMessages = [
        'Uploading document...',
        'Extracting text with OCR...',
        'Processing pages...',
        'Generating PDF...'
    ];
    let statusIndex = 0;
    const statusInterval = setInterval(() => {
        statusIndex = (statusIndex + 1) % statusMessages.length;
        processingStatus.textContent = statusMessages[statusIndex];
    }, 2000);

    try {
        const formData = new FormData();
        formData.append('file', selectedFile);

        const response = await fetch(API_URL, {
            method: 'POST',
            body: formData
        });

        clearInterval(progressInterval);
        clearInterval(statusInterval);

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Processing failed');
        }

        // Get the PDF blob
        const pdfBlob = await response.blob();

        // Create download URL
        downloadUrl = URL.createObjectURL(pdfBlob);

        // Get page count from header
        const pageCount = response.headers.get('X-Page-Count') || 'Unknown';

        // Update UI
        progressFill.style.width = '100%';
        resultInfo.textContent = `${pageCount} pages processed`;

        // Set download link
        const baseName = selectedFile.name.replace(/\.[^/.]+$/, '');
        downloadBtn.href = downloadUrl;
        downloadBtn.download = `${baseName}_digitized.pdf`;

        setTimeout(() => {
            showCard(resultCard);
        }, 500);

    } catch (error) {
        clearInterval(progressInterval);
        clearInterval(statusInterval);

        console.error('Processing error:', error);
        errorMessage.textContent = error.message || 'An error occurred while processing your document.';
        showCard(errorCard);
    }
});

// New upload
newUploadBtn.addEventListener('click', () => {
    resetUploadState();
});

// Retry
retryBtn.addEventListener('click', () => {
    if (selectedFile) {
        showCard(fileCard);
    } else {
        resetUploadState();
    }
});

// Keyboard accessibility
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        sidebar.classList.remove('open');
    }
});

console.log('MedScan loaded');
