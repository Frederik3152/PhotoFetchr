// Initialize Application
document.addEventListener('DOMContentLoaded', function() {
    console.log('PhotoFetchr Flask version initializing...');
    initializeTheme();
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
// Utility functions
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Track current rotation angle
let currentRotation = 0;

// Initialize rotation button (add inside your DOMContentLoaded)
const rotateBtn = document.getElementById('rotate-btn');
if (rotateBtn) {
    rotateBtn.addEventListener('click', rotateDetailImage);
}

// Rotation function
function rotateDetailImage() {
    const image = document.getElementById('detail-image');
    if (!image || !image.src) return;
    
    // Increment by 90 degrees
    currentRotation = (currentRotation + 90) % 360;
    
    // Apply rotation using CSS transform
    image.style.transform = `rotate(${currentRotation}deg)`;
    
    // Visual feedback on button
    const btn = document.getElementById('rotate-btn');
    if (btn) {
        const svg = btn.querySelector('svg');
        if (svg) {
            svg.style.transform = 'rotate(90deg)';
            setTimeout(() => {
                svg.style.transform = 'rotate(0deg)';
            }, 200);
        }
    }
}

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
    const photoDetailModal = document.getElementById('photo-detail');
    const modalBackdrop = document.getElementById('modal-backdrop');

    currentRotation = 0;
    const image = document.getElementById('detail-image');
    if (image) {
        image.style.transform = 'rotate(0deg)';
    }

    photoDetailModal.style.display = 'none';
    document.body.style.overflow = 'auto';
}

// The upload page has its own script, upload.js
