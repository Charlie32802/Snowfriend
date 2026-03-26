// ============================================================================
// CHAT-LIMITS.JS - MESSAGE LIMIT MANAGEMENT
// ============================================================================
// Handles message limit state, countdown timer, and limit checking
// ============================================================================

// ============================================
// MESSAGE LIMIT STATE
// ============================================

window.messageLimitState = {
    total: 15,
    remaining: 15,
    canSend: true,
    timeRemaining: 0,
    timerInterval: null,
    checkInterval: null
};

/**
 * Get future reset time formatted as "6:00 AM"
 */
function getResetTimeString(secondsRemaining) {
    if (secondsRemaining <= 0) return "now";
    
    const now = new Date();
    const resetTime = new Date(now.getTime() + (secondsRemaining * 1000));
    
    let hours = resetTime.getHours();
    const minutes = resetTime.getMinutes();
    const ampm = hours >= 12 ? 'PM' : 'AM';
    
    hours = hours % 12;
    hours = hours ? hours : 12;
    
    const minutesStr = minutes < 10 ? '0' + minutes : minutes;
    
    return `${hours}:${minutesStr} ${ampm}`;
}

/**
 * Fetch current message limit from server
 */
async function fetchMessageLimit() {
    try {
        const response = await fetch('/chat/api/limit/', {
            method: 'GET',
            headers: {
                'X-CSRFToken': window.getCSRFToken()
            }
        });

        if (!response.ok) throw new Error('Failed to fetch limit');

        const data = await response.json();

        if (data.success) {
            window.messageLimitState.total = data.total_messages;
            window.messageLimitState.remaining = data.messages_remaining;
            window.messageLimitState.canSend = data.can_send;
            window.messageLimitState.timeRemaining = data.time_remaining_seconds;

            updateMessageLimitUI();

            if (data.notifications && data.notifications.length > 0) {
                data.notifications.forEach(notification => {
                    window.showNotification(notification.message, getNotificationType(notification.type));
                });
            }

            if (!data.can_send && data.time_remaining_seconds > 0) {
                startCountdownTimer();
            } else {
                stopCountdownTimer();
            }
        }
    } catch (error) {
        console.error('Error fetching message limit:', error);
    }
}

/**
 * Update UI elements based on message limit state
 */
function updateMessageLimitUI() {
    const messagesLeftElement = document.getElementById('messagesLeft');
    const sendButton = document.getElementById('sendButton');
    const messageInput = document.getElementById('messageInput');
    const messageCounter = document.getElementById('messageCounter');

    if (messagesLeftElement) {
        messagesLeftElement.textContent = window.messageLimitState.remaining;

        messageCounter.classList.remove('counter-zero', 'counter-low', 'counter-half');

        if (window.messageLimitState.remaining === 0) {
            messageCounter.classList.add('counter-zero');
        } else if (window.messageLimitState.remaining <= 3) {
            messageCounter.classList.add('counter-low');
        } else if (window.messageLimitState.remaining <= window.messageLimitState.total / 2) {
            messageCounter.classList.add('counter-half');
        }
    }

    if (!window.messageLimitState.canSend) {
        sendButton.disabled = true;
        messageInput.disabled = true;
        const resetTimeStr = getResetTimeString(window.messageLimitState.timeRemaining);
        messageInput.placeholder = `You can chat Snowfriend again at ${resetTimeStr}`;
    } else {
        messageInput.disabled = false;
        messageInput.placeholder = "Type what's on your mind…";
    }
}

/**
 * Start countdown timer display
 */
function startCountdownTimer() {
    const timerElement = document.getElementById('countdownTimer');
    const timerTextElement = document.getElementById('timerText');

    if (!timerElement || !timerTextElement) return;

    // Show timer with fade-in animation
    timerElement.style.display = 'flex';
    setTimeout(() => {
        timerElement.style.opacity = '1';
    }, 10);

    if (window.messageLimitState.timerInterval) {
        clearInterval(window.messageLimitState.timerInterval);
    }

    // Set initial time immediately (no flash)
    timerTextElement.textContent = formatTime(window.messageLimitState.timeRemaining);

    window.messageLimitState.timerInterval = setInterval(() => {
        if (window.messageLimitState.timeRemaining > 0) {
            window.messageLimitState.timeRemaining--;
            timerTextElement.textContent = formatTime(window.messageLimitState.timeRemaining);
        } else {
            stopCountdownTimer();
            fetchMessageLimit();
            window.showNotification('Message limit has been reset!', 'success');
        }
    }, 1000);
}

/**
 * Stop countdown timer display
 */
function stopCountdownTimer() {
    const timerElement = document.getElementById('countdownTimer');

    if (window.messageLimitState.timerInterval) {
        clearInterval(window.messageLimitState.timerInterval);
        window.messageLimitState.timerInterval = null;
    }

    if (timerElement) {
        // Fade out before hiding
        timerElement.style.opacity = '0';
        setTimeout(() => {
            timerElement.style.display = 'none';
        }, 300);
    }
}

/**
 * Format seconds as HH:MM:SS
 */
function formatTime(seconds) {
    if (seconds <= 0) return '00:00:00';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

/**
 * Get notification type based on limit notification type
 */
function getNotificationType(type) {
    switch (type) {
        case 'half': return 'info';
        case 'three': return 'error';
        case 'zero': return 'error';
        default: return 'info';
    }
}

/**
 * Start periodic message limit checking
 */
function startMessageLimitCheck() {
    fetchMessageLimit();

    if (window.messageLimitState.checkInterval) {
        clearInterval(window.messageLimitState.checkInterval);
    }

    window.messageLimitState.checkInterval = setInterval(() => {
        fetchMessageLimit();
    }, 30000); // Check every 30 seconds
}

// ============================================================================
// EXPOSE FUNCTIONS GLOBALLY
// ============================================================================

window.fetchMessageLimit = fetchMessageLimit;
window.startMessageLimitCheck = startMessageLimitCheck;
window.getResetTimeString = getResetTimeString;
window.stopCountdownTimer = stopCountdownTimer;