// PhotoFetchr Flask JavaScript - Adapted from SPA to Flask routing

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