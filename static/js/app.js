// Initialize Application
document.addEventListener('DOMContentLoaded', function() {
    console.log('PhotoFetchr Flask version initializing...');
    initializeTheme();
    initializeNavigation();
    initializePhotoGrid();
    initializeTooltips();
});

// Theme Management
function initializeTheme() {
    const savedTheme = localStorage.getItem('photofetchr-theme') || 'dark';
    
    setTheme(savedTheme);
}

function setTheme(theme) {
    document.body.setAttribute('data-color-scheme', theme);
    localStorage.setItem('photofetchr-theme', theme);
}

const photoDetailModal = document.getElementById('photo-detail');
const modalBackdrop = document.getElementById('modal-backdrop');
const detailClose = document.getElementById('detail-close');
// Make sure photo detail overlay can be closed on all pages
if (photoDetailModal && modalBackdrop && detailClose) {
    detailClose.addEventListener('click', closePhotoDetail);
    modalBackdrop.addEventListener('click', closePhotoDetail);
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && photoDetailModal.style.display === 'block') {
            closePhotoDetail();
        }
    });
}
// Navigation - Flask uses server-side routing
function initializeNavigation() {
    const navBtns = document.querySelectorAll('.nav-btn');
    
    navBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const page = this.getAttribute('data-page');
            
            // Navigate using Flask routes
            switch(page) {
                case 'homepage':
                    window.location.href = '/';
                    break;
                case 'search':
                    window.location.href = '/search';
                    break;
                case 'upload':
                    window.location.href = '/upload';
                    break;
            }
        });
    });
}
// Loading overlay
function showLoading(show) {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.toggle('hidden', !show);
    }
}


// Tooltips
function showTooltip(e) {
    const text = e.target.getAttribute('data-tooltip');
    if (!text) return;
    
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = text;
    tooltip.id = 'active-tooltip';
    
    document.body.appendChild(tooltip);
    
    const rect = e.target.getBoundingClientRect();
    tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
    tooltip.style.top = rect.top - tooltip.offsetHeight - 10 + 'px';
}

// Utility functions
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDate(date) {
    return new Date(date).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

// Add smooth scrolling
function smoothScrollTo(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth' });
    }
}

// Add to window for global access
window.PhotoFetchr = {
    showLoading,
    setTheme
};

// Search page
// Global variables
let currentSearchResults = [];
let activeFilters = {
    search: '',
    country: '',
    people: [],
    dateFrom: '',
    dateTo: ''
};

// DOM elements
const searchInput = document.getElementById('main-search');
const searchBtn = document.getElementById('main-search-btn');
const countryFilter = document.getElementById('country-filter');
const peopleSearch = document.getElementById('people-search');
const peopleList = document.getElementById('people-list');
const dateFromInput = document.getElementById('date-from');
const dateToInput = document.getElementById('date-to');
const sortSelect = document.getElementById('sort-select');
const viewToggle = document.querySelectorAll('.view-btn');
const searchResults = document.getElementById('search-results');
const resultsCount = document.getElementById('results-count');
const activeFiltersContainer = document.getElementById('active-filters');
const clearFiltersBtn = document.getElementById('clear-filters');

// Initialize the page
document.addEventListener('DOMContentLoaded', function() {
    // Search functionality
    searchBtn.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            performSearch();
        }
    });

    // Filter change handlers
    countryFilter.addEventListener('change', updateFiltersAndSearch);
    dateFromInput.addEventListener('change', updateFiltersAndSearch);
    dateToInput.addEventListener('change', updateFiltersAndSearch);
    sortSelect.addEventListener('change', performSearch);

    // People filter search
    peopleSearch.addEventListener('input', filterPeopleList);

    // People checkboxes
    const peopleCheckboxes = document.querySelectorAll('#people-list input[type="checkbox"]');
    peopleCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', updateFiltersAndSearch);
    });

    // View toggle
    viewToggle.forEach(btn => {
        btn.addEventListener('click', function() {
            viewToggle.forEach(b => b.classList.remove('active'));
            this.classList.add('active');

            const view = this.dataset.view;
            if (view === 'list') {
                searchResults.classList.add('list-view');
            } else {
                searchResults.classList.remove('list-view');
            }
        });
    });

    // Clear filters
    clearFiltersBtn.addEventListener('click', clearAllFilters);

    // Perform initial search to show some results
    performSearch();
});

function updateFiltersAndSearch() {
    updateActiveFilters();
    performSearch();
}

function updateActiveFilters() {
    activeFilters.search = searchInput.value.trim();
    activeFilters.country = countryFilter.value;
    activeFilters.dateFrom = dateFromInput.value;
    activeFilters.dateTo = dateToInput.value;

    // Get selected people
    const selectedPeople = [];
    const peopleCheckboxes = document.querySelectorAll('#people-list input[type="checkbox"]:checked');
    peopleCheckboxes.forEach(checkbox => {
        selectedPeople.push(checkbox.value);
    });
    activeFilters.people = selectedPeople;

    updateActiveFiltersDisplay();
}

function updateActiveFiltersDisplay() {
    activeFiltersContainer.innerHTML = '';

    if (activeFilters.search) {
        addFilterChip('Text', activeFilters.search, () => {
            searchInput.value = '';
            updateFiltersAndSearch();
        });
    }

    if (activeFilters.country) {
        addFilterChip('Country', activeFilters.country, () => {
            countryFilter.value = '';
            updateFiltersAndSearch();
        });
    }

    activeFilters.people.forEach(person => {
        addFilterChip('Person', person, () => {
            const checkbox = document.querySelector(`#people-list input[value="${person}"]`);
            if (checkbox) checkbox.checked = false;
            updateFiltersAndSearch();
        });
    });

    if (activeFilters.dateFrom) {
        addFilterChip('From', activeFilters.dateFrom, () => {
            dateFromInput.value = '';
            updateFiltersAndSearch();
        });
    }

    if (activeFilters.dateTo) {
        addFilterChip('To', activeFilters.dateTo, () => {
            dateToInput.value = '';
            updateFiltersAndSearch();
        });
    }
}

function addFilterChip(type, value, removeCallback) {
    const chip = document.createElement('div');
    chip.className = 'filter-chip';
    chip.innerHTML = `${type}: ${value} <button class="filter-chip-remove">×</button>`;

    const removeBtn = chip.querySelector('.filter-chip-remove');
    removeBtn.addEventListener('click', removeCallback);

    activeFiltersContainer.appendChild(chip);
}

function clearAllFilters() {
    searchInput.value = '';
    countryFilter.value = '';
    dateFromInput.value = '';
    dateToInput.value = '';

    const peopleCheckboxes = document.querySelectorAll('#people-list input[type="checkbox"]');
    peopleCheckboxes.forEach(checkbox => {
        checkbox.checked = false;
    });

    updateFiltersAndSearch();
}

function filterPeopleList() {
    const searchTerm = peopleSearch.value.toLowerCase();
    const peopleItems = document.querySelectorAll('.person-checkbox');

    peopleItems.forEach(item => {
        const label = item.querySelector('label').textContent.toLowerCase();
        if (label.includes(searchTerm)) {
            item.style.display = 'flex';
        } else {
            item.style.display = 'none';
        }
    });
}

async function performSearch() {
    updateActiveFilters();

    // Show loading state
    searchResults.innerHTML = '<div class="loading-results">Searching photos...</div>';
    resultsCount.textContent = 'Searching...';

    try {
        const searchData = {
            search_text: activeFilters.search,
            countries: activeFilters.country ? [activeFilters.country] : [],
            people: activeFilters.people,
            date_from: activeFilters.dateFrom,
            date_to: activeFilters.dateTo,
            sort_by: sortSelect.value
        };

        const response = await fetch('/api/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(searchData)
        });

        const data = await response.json();

        if (data.success) {
            currentSearchResults = data.results;
            displaySearchResults(data.results);
            resultsCount.textContent = `Found ${data.count} photos`;
        } else {
            searchResults.innerHTML = '<div class="loading-results">Error: ' + data.error + '</div>';
            resultsCount.textContent = 'Error occurred';
        }

    } catch (error) {
        console.error('Search error:', error);
        searchResults.innerHTML = '<div class="loading-results">Error connecting to server</div>';
        resultsCount.textContent = 'Connection error';
    }
}

function displaySearchResults(results) {
    if (results.length === 0) {
        searchResults.innerHTML = `
            <div class="empty-state">
                <div class="empty-content">
                    <div class="empty-icon">🔍</div>
                    <h3>No Photos Found</h3>
                    <p>No photos match your search criteria. Try adjusting your filters.</p>
                </div>
            </div>`;
        return;
    }

    searchResults.innerHTML = '';

    results.forEach(photo => {
        const photoCard = document.createElement('div');
        photoCard.className = 'photo-card';
        photoCard.addEventListener('click', () => showPhotoDetail(photo.id));

        photoCard.innerHTML = `
            <div class="photo-thumbnail">
                <img src="${photo.thumbnail_url}" alt="${photo.title}" loading="lazy" 
                     onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                <div style="display:none; align-items:center; justify-content:center; height:100%; background:var(--color-bg-2); color:var(--color-text-secondary);">📷</div>
                <div class="photo-overlay"></div>
            </div>
            <div class="photo-info">
                <h4 class="photo-title">${photo.title}</h4>
                <div class="photo-meta">
                    <span>🌍 ${photo.country || 'Unknown'}</span>
                    <span>📅 ${photo.date_taken ? new Date(photo.date_taken).toLocaleDateString() : 'No date'}</span>
                </div>
            </div>
        `;

        searchResults.appendChild(photoCard);
    });
}

async function showPhotoDetail(photoId) {
    try {
        const response = await fetch(`/api/photo/${photoId}`);
        const data = await response.json();

        if (data.success) {
            const photo = data.photo;

            document.getElementById('detail-image').src = photo.image_url;
            document.getElementById('detail-title').textContent = photo.title;
            document.getElementById('detail-date').textContent = photo.date_taken ? 
                new Date(photo.date_taken).toLocaleDateString() : 'No date';
            document.getElementById('detail-country').textContent = photo.country || 'Unknown';
            document.getElementById('detail-filesize').textContent = formatFileSize(photo.file_size);

            // Display people
            const peopleContainer = document.getElementById('detail-people');
            peopleContainer.innerHTML = '';
            if (photo.people && photo.people.length > 0) {
                photo.people.forEach(person => {
                    const tag = document.createElement('span');
                    tag.className = 'person-tag';
                    tag.textContent = person;
                    peopleContainer.appendChild(tag);
                });
            } else {
                peopleContainer.innerHTML = '<span style="color: var(--color-text-secondary);">No people tagged</span>';
            }

            photoDetailModal.style.display = 'block';
            document.body.style.overflow = 'hidden';
        }
    } catch (error) {
        console.error('Error loading photo details:', error);
        // Show toast notification if available
        console.log('Error loading photo details');
    }
}

function closePhotoDetail() {
    photoDetailModal.style.display = 'none';
    document.body.style.overflow = 'auto';
}

// Upload page
// Upload functionality with Python backend integration
document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('file-input');
    const browseBtn = document.getElementById('browse-files');
    const uploadArea = document.getElementById('upload-area');
    const uploadQueue = document.getElementById('upload-queue');
    const fileList = document.getElementById('file-list');
    const uploadForm = document.getElementById('upload-form');
    const uploadBtn = document.getElementById('upload-btn');
    const clearBtn = document.getElementById('clear-files');
    const peopleSearch = document.getElementById('people-search');
    const resultsSection = document.getElementById('results-section');
    const resultsList = document.getElementById('results-list');
    const countrySelect = document.getElementById('country-select');
    const countryNewInput = document.getElementById('country-new');

    let selectedFiles = [];

    // Browse files button
    browseBtn.addEventListener('click', () => {
        fileInput.click();
    });

    // File input change
    fileInput.addEventListener('change', (e) => {
        handleFiles(Array.from(e.target.files));
    });

    // Drag and drop functionality
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        const files = Array.from(e.dataTransfer.files).filter(file => 
            file.type.startsWith('image/')
        );
        handleFiles(files);
    });

    // Handle file selection
    function handleFiles(files) {
        files.forEach(file => {
            if (file.size > 10 * 1024 * 1024) { // 10MB limit
                alert(`File ${file.name} is too large. Maximum size is 10MB.`);
                return;
            }

            if (!selectedFiles.find(f => f.name === file.name)) {
                selectedFiles.push(file);
            }
        });

        updateFileList();
        updateUploadButton();
    }

    // Update file list display
    function updateFileList() {
        if (selectedFiles.length === 0) {
            uploadQueue.style.display = 'none';
            return;
        }

        uploadQueue.style.display = 'block';
        fileList.innerHTML = '';

        selectedFiles.forEach((file, index) => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';
            fileItem.innerHTML = `
                <div class="file-info">
                    <span class="file-name">${file.name}</span>
                    <span class="file-size">${formatFileSize(file.size)}</span>
                </div>
                <button type="button" class="file-remove" onclick="removeFile(${index})">Remove</button>
            `;
            fileList.appendChild(fileItem);
        });
    }

    if (countrySelect && countryNewInput) {
        countrySelect.addEventListener('change', function() {
            if (this.value === '__NEW__') {
                // Show the new country input field
                countryNewInput.style.display = 'block';
                countryNewInput.required = true;
                countryNewInput.focus();
                // Clear and disable the select so the text input is used
                this.removeAttribute('name');
            } else {
                // Hide the new country input field
                countryNewInput.style.display = 'none';
                countryNewInput.required = false;
                countryNewInput.value = '';
                // Re-enable the select
                this.setAttribute('name', 'country');
            }
        });

        // If user starts typing in new country, keep it visible
        countryNewInput.addEventListener('input', function() {
            if (this.value.length > 0) {
                countrySelect.value = '__NEW__';
            }
        });
    }

    // Remove file
    window.removeFile = function(index) {
        selectedFiles.splice(index, 1);
        updateFileList();
        updateUploadButton();
    }

    // Clear all files
    clearBtn.addEventListener('click', () => {
        selectedFiles = [];
        fileInput.value = '';
        updateFileList();
        updateUploadButton();
        resultsSection.style.display = 'none';
    });

    // Update upload button state
    function updateUploadButton() {
        uploadBtn.disabled = selectedFiles.length === 0;
    }

    // People search functionality
    peopleSearch.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        const checkboxes = document.querySelectorAll('.person-checkbox');

        checkboxes.forEach(checkbox => {
            const label = checkbox.querySelector('.checkbox-label').textContent.toLowerCase();
            if (label.includes(searchTerm)) {
                checkbox.style.display = 'flex';
            } else {
                checkbox.style.display = 'none';
            }
        });
    });

    // Form submission
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();

        if (selectedFiles.length === 0) {
            alert('Please select files to upload.');
            return;
        }

        const country = document.getElementById('country').value;
        if (!country) {
            alert('Please select a country.');
            return;
        }

        // Show loading state
        const btnText = uploadBtn.querySelector('.btn-text');
        const btnLoader = uploadBtn.querySelector('.btn-loader');
        btnText.style.display = 'none';
        btnLoader.style.display = 'inline';
        uploadBtn.disabled = true;

        // Create FormData
        const formData = new FormData();

        // Add files
        selectedFiles.forEach(file => {
            formData.append('photos', file);
        });

        // Add metadata
        formData.append('country', country);

        const date = document.getElementById('date').value;
        if (date) {
            formData.append('date', date);
        }

        // Add selected people
        const selectedPeople = Array.from(document.querySelectorAll('input[name="people"]:checked'))
            .map(cb => cb.value);
        selectedPeople.forEach(person => {
            formData.append('people', person);
        });

        // Submit to Flask backend
        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            displayResults(data);

            // Reset form on success
            const hasSuccess = data.some(result => result.success);
            if (hasSuccess) {
                selectedFiles = [];
                fileInput.value = '';
                updateFileList();
                uploadForm.reset();
            }
        })
        .catch(error => {
            console.error('Upload error:', error);
            displayResults([{
                success: false,
                filename: 'Upload Error',
                error: 'Connection error occurred'
            }]);
        })
        .finally(() => {
            // Reset button state
            btnText.style.display = 'inline';
            btnLoader.style.display = 'none';
            updateUploadButton();
        });
    });

    // Display upload results
    function displayResults(results) {
        resultsSection.style.display = 'block';
        resultsList.innerHTML = '';

        results.forEach(result => {
            const resultItem = document.createElement('div');
            resultItem.className = `result-item ${result.success ? 'success' : 'error'}`;

            if (result.success) {
                resultItem.innerHTML = `
                    <span>✓</span>
                    <div>
                        <strong>${result.filename}</strong> uploaded successfully
                        <br><small>ID: ${result.id} | Date: ${result.date}</small>
                    </div>
                `;
            } else {
                resultItem.innerHTML = `
                    <span>✗</span>
                    <div>
                        <strong>${result.filename}</strong> failed
                        <br><small>${result.error}</small>
                    </div>
                `;
            }

            resultsList.appendChild(resultItem);
        });

        // Scroll to results
        resultsSection.scrollIntoView({ behavior: 'smooth' });
    }
});