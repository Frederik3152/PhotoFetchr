// PhotoFetchr Flask JavaScript - Adapted from SPA to Flask routing

// Application State
let currentTheme = 'light';

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
    currentTheme = theme;
    localStorage.setItem('photofetchr-theme', theme);
    
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.textContent = theme === 'light' ? '🌙' : '☀️';
    }
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

// Photo Grid Interactions
function initializePhotoGrid() {
    // Photo card hover effects
    const photoCards = document.querySelectorAll('.photo-card');
    
    photoCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-4px)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
    
    // Action button handlers
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('action-btn')) {
            e.stopPropagation();
            handlePhotoAction(e.target, e.target.textContent);
        }
    });
}

// View individual photo
function viewPhoto(photoId) {
    window.location.href = `/photo/${photoId}`;
}

// Search functionality for homepage
function initializeSearch() {
    const heroSearch = document.getElementById('hero-search');
    const searchForm = document.querySelector('.search-container form');
    
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            const searchInput = this.querySelector('.search-input');
            if (!searchInput.value.trim()) {
                e.preventDefault();
                showToast('Please enter a search term', 'warning');
            }
        });
    }
}

// Upload functionality
function initializeUpload() {
    const uploadArea = document.querySelector('.upload-area');
    const fileInput = document.getElementById('file-input');
    
    if (uploadArea) {
        // Drag and drop handlers
        uploadArea.addEventListener('dragover', function(e) {
            e.preventDefault();
            this.classList.add('drag-over');
        });
        
        uploadArea.addEventListener('dragleave', function(e) {
            e.preventDefault();
            this.classList.remove('drag-over');
        });
        
        uploadArea.addEventListener('drop', function(e) {
            e.preventDefault();
            this.classList.remove('drag-over');
            
            const files = e.dataTransfer.files;
            handleFileUpload(files);
        });
        
        // Click to upload
        uploadArea.addEventListener('click', function() {
            if (fileInput) {
                fileInput.click();
            }
        });
    }
    
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            handleFileUpload(this.files);
        });
    }
}

// File upload handling
function handleFileUpload(files) {
    if (!files || files.length === 0) {
        return;
    }
    
    const formData = new FormData();
    let validFiles = 0;
    
    Array.from(files).forEach(file => {
        if (isValidImageFile(file)) {
            formData.append('files', file);
            validFiles++;
        }
    });
    
    if (validFiles === 0) {
        showToast('No valid image files selected', 'error');
        return;
    }
    
    showLoading(true);
    
    // Upload using Flask route
    fetch('/api/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        showLoading(false);
        if (data.success) {
            showToast(`Successfully uploaded ${data.count} photos`, 'success');
            // Optionally redirect or refresh page
        } else {
            showToast(data.message || 'Upload failed', 'error');
        }
    })
    .catch(error => {
        showLoading(false);
        showToast('Upload failed: ' + error.message, 'error');
    });
}

function isValidImageFile(file) {
    const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    const maxSize = 10 * 1024 * 1024; // 10MB
    
    return validTypes.includes(file.type) && file.size <= maxSize;
}

// Loading overlay
function showLoading(show) {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.toggle('hidden', !show);
    }
}

// Toast notification system
function showToast(message, type = 'info', duration = 3000) {
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) return;
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const iconMap = {
        'success': '✅',
        'error': '❌',
        'warning': '⚠️',
        'info': 'ℹ️'
    };
    
    toast.innerHTML = `
        <div class="toast-content">
            <span class="toast-icon">${iconMap[type] || 'ℹ️'}</span>
            <span class="toast-message">${message}</span>
            <button class="toast-close" onclick="this.parentElement.parentElement.remove()">×</button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    // Auto-remove after duration
    setTimeout(() => {
        if (toast.parentElement) {
            toast.remove();
        }
    }, duration);
}

// Tooltips
function initializeTooltips() {
    const elementsWithTooltips = document.querySelectorAll('[data-tooltip]');
    
    elementsWithTooltips.forEach(element => {
        element.addEventListener('mouseenter', showTooltip);
        element.addEventListener('mouseleave', hideTooltip);
    });
}

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

function hideTooltip() {
    const tooltip = document.getElementById('active-tooltip');
    if (tooltip) {
        tooltip.remove();
    }
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

// Add keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + K for search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.querySelector('.search-input');
        if (searchInput) {
            searchInput.focus();
        }
    }
    
    // Escape key to close modals/overlays
    if (e.key === 'Escape') {
        showLoading(false);
        hideTooltip();
    }
});

// Initialize search on homepage if present
document.addEventListener('DOMContentLoaded', function() {
    initializeSearch();
    initializeUpload();
});

// Add to window for global access
window.PhotoFetchr = {
    showToast,
    showLoading,
    viewPhoto,
    toggleTheme,
    setTheme
};