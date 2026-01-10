// ============================================================================
// CHAT-UI.JS - UI HELPER FUNCTIONS & UTILITIES
// ============================================================================
// Handles UI elements: scroll, notifications, timestamps, avatars, buttons
// ============================================================================

// ============================================================================
// SCROLL MANAGEMENT - SMART DETECTION
// ============================================================================

/**
 * Track if user has manually scrolled up
 */
window.userHasScrolledUp = false;
window.lastScrollPosition = 0;

/**
 * Detect when user scrolls manually
 */
window.addEventListener('scroll', () => {
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    const scrollHeight = document.documentElement.scrollHeight;
    const clientHeight = document.documentElement.clientHeight;
    
    // Calculate how far from bottom (in pixels)
    const distanceFromBottom = scrollHeight - (scrollTop + clientHeight);
    
    // If user is more than 100px from bottom, they've scrolled up
    if (distanceFromBottom > 100) {
        window.userHasScrolledUp = true;
    } else {
        window.userHasScrolledUp = false;
    }
    
    window.lastScrollPosition = scrollTop;
});

/**
 * Scroll to bottom ONLY if user hasn't scrolled up
 * ✅ This respects user's scroll position during typing
 */
window.scrollToBottomIfNotScrolledUp = () => {
    if (!window.userHasScrolledUp) {
        window.scrollTo({
            top: document.documentElement.scrollHeight,
            behavior: 'smooth'
        });
    }
};

/**
 * Force scroll to bottom (for new messages)
 * ✅ Use this when a NEW message arrives
 */
window.scrollToBottom = () => {
    window.userHasScrolledUp = false; // Reset the flag
    window.scrollTo({
        top: document.documentElement.scrollHeight,
        behavior: 'smooth'
    });
};

// ============================================================================
// AVATARS & UI ELEMENTS
// ============================================================================

/**
 * Create user avatar SVG
 */
window.createUserAvatar = () => {
    return `
        <svg class="avatar-svg" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="8" r="4" fill="currentColor" opacity="0.6"/>
            <path d="M4 20c0-4.4 3.6-8 8-8s8 3.6 8 8" stroke="currentColor" stroke-width="2" opacity="0.6"/>
        </svg>
    `;
};

/**
 * Format timestamp for display
 */
window.formatTimestamp = (date) => {
    const now = new Date();
    const messageDate = new Date(date);
    const diffMs = now - messageDate;
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffSecs < 10) return 'Just now';
    if (diffSecs < 60) return `${diffSecs} ${diffSecs === 1 ? 'second' : 'seconds'} ago`;
    if (diffMins < 60) return `${diffMins} ${diffMins === 1 ? 'minute' : 'minutes'} ago`;
    if (diffHours < 24) return `${diffHours} ${diffHours === 1 ? 'hour' : 'hours'} ago`;

    if (diffDays === 1) {
        const timeStr = messageDate.toLocaleTimeString('en-US', {
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
        });
        return `Yesterday ${timeStr}`;
    }

    if (diffDays > 1) {
        const dateStr = messageDate.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: now.getFullYear() !== messageDate.getFullYear() ? 'numeric' : undefined
        });
        const timeStr = messageDate.toLocaleTimeString('en-US', {
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
        });
        return `${dateStr} ${timeStr}`;
    }
};

/**
 * Update all timestamps in the chat
 */
const updateAllTimestamps = () => {
    const timestamps = document.querySelectorAll('.message-timestamp');
    timestamps.forEach(timestamp => {
        const isoDate = timestamp.getAttribute('data-timestamp');
        if (isoDate) {
            timestamp.textContent = window.formatTimestamp(isoDate);
        }
    });
};

/**
 * Auto-resize textarea based on content
 */
const autoResize = () => {
    const messageInput = document.getElementById('messageInput');
    const minHeight = parseFloat(getComputedStyle(messageInput).minHeight);
    messageInput.style.height = minHeight + 'px';

    const newHeight = messageInput.scrollHeight;
    const maxHeight = parseFloat(getComputedStyle(messageInput).maxHeight);

    if (newHeight > minHeight && newHeight <= maxHeight) {
        messageInput.style.height = newHeight + 'px';
        messageInput.style.overflowY = 'hidden';
    } else if (newHeight > maxHeight) {
        messageInput.style.height = maxHeight + 'px';
        messageInput.style.overflowY = 'auto';
    } else {
        messageInput.style.overflowY = 'hidden';
    }
};

/**
 * Update send button state based on input and typing status
 */
const updateSendButton = () => {
    const messageInput = document.getElementById('messageInput');
    const sendButton = document.getElementById('sendButton');
    const hasText = messageInput.value.trim().length > 0;

    if (hasText && !window.isTyping && !window.isInitialTyping) {
        sendButton.removeAttribute('disabled');
    } else {
        sendButton.setAttribute('disabled', 'disabled');
    }
};

/**
 * Show notification toast
 */
window.showNotification = (message, type = 'success') => {
    const notificationContainer = document.getElementById('notificationContainer');
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <span class="notification-text">${message}</span>
        <button class="notification-close" aria-label="Close notification">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 4L4 12M4 4L12 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
        </button>
    `;

    notificationContainer.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease forwards';
        setTimeout(() => notification.remove(), 300);
    }, 5000);

    const closeBtn = notification.querySelector('.notification-close');
    closeBtn.addEventListener('click', () => {
        notification.style.animation = 'slideOut 0.3s ease forwards';
        setTimeout(() => notification.remove(), 300);
    });
};

/**
 * Get cookie value by name
 */
window.getCookie = (name) => {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
};

/**
 * Get CSRF token for requests
 */
window.getCSRFToken = () => {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || window.getCookie('csrftoken');
};

// ============================================================================
// EXPOSE FUNCTIONS GLOBALLY
// ============================================================================

window.autoResize = autoResize;
window.updateSendButton = updateSendButton;
window.updateAllTimestamps = updateAllTimestamps;