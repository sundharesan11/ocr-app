/**
 * MedScan - Medical Form Digitizer
 * Handles navigation, file upload, API calls, and preview
 */

// DOM Elements - Navigation
const sidebar = document.getElementById('sidebar');
const sidebarOverlay = document.getElementById('sidebarOverlay');
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
const uploadContainer = document.getElementById('uploadContainer');
const fileCard = document.getElementById('fileCard');
const fileName = document.getElementById('fileName');
const fileSize = document.getElementById('fileSize');
const removeFile = document.getElementById('removeFile');
const browseBtn = document.querySelector('.btn-browse');
const uploadedFilesList = document.getElementById('uploadedFilesList');
const uploadedFileEmpty = document.getElementById('uploadedFileEmpty');
const processBtn = document.getElementById('processBtn');
const hipaaDisclaimer = document.getElementById('hipaaDisclaimer');
const processingCard = document.getElementById('processingCard');
const processingStatus = document.getElementById('processingStatus');
const progressFill = document.getElementById('progressFill');
const progressPercent = document.getElementById('progressPercent');
const resultCard = document.getElementById('resultCard');
const resultTimestamp = document.getElementById('resultTimestamp');
const downloadBtn = document.getElementById('downloadBtn');
const newUploadBtn = document.getElementById('newUploadBtn');
const copyBtn = document.getElementById('copyBtn');
const errorCard = document.getElementById('errorCard');
const errorMessage = document.getElementById('errorMessage');
const retryBtn = document.getElementById('retryBtn');
const ocrTips = document.getElementById('ocrTips');

// Preview Elements
const markdownPreview = document.getElementById('markdownPreview');
const pdfPreview = document.getElementById('pdfPreview');
const previewTabs = document.querySelectorAll('.preview-tab');

// State
let selectedFile = null;
let downloadUrl = null;
let currentSection = 'home';
let rawMarkdown = '';

// API endpoint - using preview endpoint for markdown + PDF
const API_URL = '/api/v1/process/preview';

// Section titles
const sectionTitles = {
    'home': 'MedScan',
    'digitize': 'Upload Document',
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
    closeSidebar();

    // Reset upload state when entering digitize section
    if (sectionId === 'digitize') {
        // Show OCR tips
        ocrTips.classList.remove('hidden');
    }
}

// Make showSection global for onclick handlers
window.showSection = showSection;

// Sidebar functions
function openSidebar() {
    sidebar.classList.add('open');
    sidebarOverlay.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeSidebar() {
    sidebar.classList.remove('open');
    sidebarOverlay.classList.remove('active');
    document.body.style.overflow = '';
}

// Nav item clicks
navItems.forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        showSection(item.dataset.section);
    });
});

// Mobile menu toggle
menuToggle.addEventListener('click', () => {
    if (sidebar.classList.contains('open')) {
        closeSidebar();
    } else {
        openSidebar();
    }
});

// Close sidebar when clicking overlay
sidebarOverlay.addEventListener('click', closeSidebar);

// Preview tab switching
previewTabs.forEach(tab => {
    tab.addEventListener('click', () => {
        const tabName = tab.dataset.tab;

        // Update tab styles
        previewTabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');

        // Show/hide content
        if (tabName === 'markdown') {
            markdownPreview.classList.remove('hidden');
            pdfPreview.classList.add('hidden');
        } else {
            markdownPreview.classList.add('hidden');
            pdfPreview.classList.remove('hidden');
        }
    });
});

// Utility functions
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function formatTime(date) {
    return date.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
    });
}

function showUploadState() {
    uploadContainer.classList.remove('hidden');
    fileCard.classList.add('hidden');
    processBtn.classList.add('hidden');
    hipaaDisclaimer.classList.add('hidden');
    processingCard.classList.add('hidden');
    resultCard.classList.add('hidden');
    errorCard.classList.add('hidden');
    if (ocrTips) ocrTips.classList.remove('hidden');
    // Reset uploaded files list
    if (uploadedFileEmpty) uploadedFileEmpty.classList.remove('hidden');
}

function showFileState() {
    uploadContainer.classList.remove('hidden');
    fileCard.classList.remove('hidden');
    processBtn.classList.remove('hidden');
    hipaaDisclaimer.classList.remove('hidden');
    processingCard.classList.add('hidden');
    resultCard.classList.add('hidden');
    errorCard.classList.add('hidden');
    if (ocrTips) ocrTips.classList.remove('hidden');
    // Hide empty state
    if (uploadedFileEmpty) uploadedFileEmpty.classList.add('hidden');
}

function showProcessingState() {
    uploadContainer.classList.add('hidden');
    fileCard.classList.add('hidden');
    processBtn.classList.add('hidden');
    hipaaDisclaimer.classList.add('hidden');
    processingCard.classList.remove('hidden');
    resultCard.classList.add('hidden');
    errorCard.classList.add('hidden');
    if (ocrTips) ocrTips.classList.add('hidden');
}

function showResultState() {
    uploadContainer.classList.add('hidden');
    fileCard.classList.add('hidden');
    processBtn.classList.add('hidden');
    hipaaDisclaimer.classList.add('hidden');
    processingCard.classList.add('hidden');
    resultCard.classList.remove('hidden');
    errorCard.classList.add('hidden');
    if (ocrTips) ocrTips.classList.add('hidden');
}

function showErrorState() {
    uploadContainer.classList.add('hidden');
    fileCard.classList.add('hidden');
    processBtn.classList.add('hidden');
    hipaaDisclaimer.classList.add('hidden');
    processingCard.classList.add('hidden');
    resultCard.classList.add('hidden');
    errorCard.classList.remove('hidden');
    if (ocrTips) ocrTips.classList.add('hidden');
}

function resetUploadState() {
    selectedFile = null;
    rawMarkdown = '';
    if (downloadUrl) {
        URL.revokeObjectURL(downloadUrl);
        downloadUrl = null;
    }
    progressFill.style.width = '0%';
    progressPercent.textContent = '0%';
    markdownPreview.innerHTML = '';
    pdfPreview.src = '';

    // Clear uploaded files list
    if (uploadedFilesList) {
        const existingItems = uploadedFilesList.querySelectorAll('.uploaded-file-item');
        existingItems.forEach(item => item.remove());
    }
    if (uploadedFileEmpty) uploadedFileEmpty.classList.remove('hidden');

    // Hide process button and disclaimer
    processBtn.classList.add('hidden');
    hipaaDisclaimer.classList.add('hidden');

    // Show upload container
    uploadContainer.classList.remove('hidden');
}

// Render markdown to HTML
function renderMarkdown(markdown) {
    if (typeof marked !== 'undefined') {
        // Configure marked for better rendering
        marked.setOptions({
            breaks: true,  // Convert \n to <br>
            gfm: true,     // Enable GitHub Flavored Markdown
        });
        return marked.parse(markdown);
    }
    // Fallback: simple markdown rendering
    return markdown
        .replace(/^### (.*$)/gim, '<h3>$1</h3>')
        .replace(/^## (.*$)/gim, '<h2>$1</h2>')
        .replace(/^# (.*$)/gim, '<h1>$1</h1>')
        .replace(/^\* (.*$)/gim, '<li>$1</li>')
        .replace(/^\- (.*$)/gim, '<li>$1</li>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>');
}

// File handling
function handleFile(file) {
    // Validate file type
    const validTypes = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg'];
    if (!validTypes.includes(file.type)) {
        alert('Please upload a PDF, JPG, or PNG file.');
        return;
    }

    // Validate file size (max 10MB as per design)
    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
        alert('File size must be less than 10MB.');
        return;
    }

    selectedFile = file;

    // Hide empty state
    if (uploadedFileEmpty) uploadedFileEmpty.classList.add('hidden');

    // Add file to the uploaded files list on the right
    addFileToUploadedList(file);

    // Show process button and disclaimer
    processBtn.classList.remove('hidden');
    hipaaDisclaimer.classList.remove('hidden');
}

// Add file to the uploaded files list
function addFileToUploadedList(file) {
    // Clear existing files (single file mode)
    const existingItems = uploadedFilesList.querySelectorAll('.uploaded-file-item');
    existingItems.forEach(item => item.remove());

    // Get file extension for icon
    const ext = file.name.split('.').pop().toLowerCase();
    let iconClass = 'pdf';
    if (['jpg', 'jpeg', 'png'].includes(ext)) iconClass = 'img';

    // Create file item
    const fileItem = document.createElement('div');
    fileItem.className = 'uploaded-file-item';
    fileItem.id = 'currentFileItem';
    fileItem.innerHTML = `
        <div class="uploaded-file-icon ${iconClass}">${ext.toUpperCase()}</div>
        <div class="uploaded-file-info">
            <span class="uploaded-file-name">${file.name}</span>
            <div class="uploaded-file-progress">
                <div class="uploaded-file-progress-fill success" style="width: 100%"></div>
            </div>
        </div>
        <span class="uploaded-file-status cancel" id="cancelFileBtn">Cancel</span>
    `;

    uploadedFilesList.appendChild(fileItem);

    // Add cancel button handler
    const cancelBtn = fileItem.querySelector('#cancelFileBtn');
    cancelBtn.addEventListener('click', () => {
        resetUploadState();
    });
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

// Copy to clipboard
copyBtn.addEventListener('click', async () => {
    if (rawMarkdown) {
        try {
            await navigator.clipboard.writeText(rawMarkdown);
            copyBtn.textContent = '✓';
            setTimeout(() => {
                copyBtn.textContent = '📋';
            }, 2000);
        } catch (err) {
            console.error('Failed to copy:', err);
        }
    }
});

// Process document
processBtn.addEventListener('click', async () => {
    if (!selectedFile) return;

    showProcessingState();

    // Progress animation
    let progress = 0;
    const progressInterval = setInterval(() => {
        progress += Math.random() * 12;
        if (progress > 90) progress = 90;
        const roundedProgress = Math.round(progress);
        progressFill.style.width = roundedProgress + '%';
        progressPercent.textContent = roundedProgress + '%';
    }, 400);

    // Update status messages
    const statusMessages = [
        'AI is analyzing your document for medical data extraction',
        'Extracting text with OCR...',
        'Processing medical terminology...',
        'Structuring extracted data...'
    ];
    let statusIndex = 0;
    const statusInterval = setInterval(() => {
        statusIndex = (statusIndex + 1) % statusMessages.length;
        processingStatus.textContent = statusMessages[statusIndex];
    }, 2500);

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

        // Get JSON response with markdown and PDF
        const data = await response.json();

        // Store raw markdown
        rawMarkdown = data.raw_markdown;

        // Render markdown preview
        markdownPreview.innerHTML = renderMarkdown(rawMarkdown);

        // Create PDF blob from base64 and set preview
        const pdfBytes = Uint8Array.from(atob(data.pdf_base64), c => c.charCodeAt(0));
        const pdfBlob = new Blob([pdfBytes], { type: 'application/pdf' });
        downloadUrl = URL.createObjectURL(pdfBlob);

        // Set PDF preview
        pdfPreview.src = downloadUrl;

        // Update UI
        progressFill.style.width = '100%';
        progressPercent.textContent = '100%';

        // Set timestamp
        resultTimestamp.textContent = `Extracted at ${formatTime(new Date())}`;

        // Set download link
        downloadBtn.href = downloadUrl;
        downloadBtn.download = data.filename;

        // Reset to markdown tab
        previewTabs.forEach(t => t.classList.remove('active'));
        previewTabs[0].classList.add('active');
        markdownPreview.classList.remove('hidden');
        pdfPreview.classList.add('hidden');

        setTimeout(() => {
            showResultState();
        }, 300);

    } catch (error) {
        clearInterval(progressInterval);
        clearInterval(statusInterval);

        console.error('Processing error:', error);
        errorMessage.textContent = error.message || 'An error occurred while processing your document.';
        showErrorState();
    }
});

// New upload
newUploadBtn.addEventListener('click', () => {
    resetUploadState();
});

// Retry
retryBtn.addEventListener('click', () => {
    if (selectedFile) {
        showFileState();
    } else {
        resetUploadState();
    }
});

// Keyboard accessibility
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeSidebar();
    }
});

console.log('MedScan loaded');
