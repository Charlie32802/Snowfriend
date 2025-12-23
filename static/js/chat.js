const exportButton = document.getElementById('exportButton');
const exportModal = document.getElementById('exportModal');
const cancelExport = document.getElementById('cancelExport');
const confirmExport = document.getElementById('confirmExport');
const chatTitleInput = document.getElementById('chatTitle');
const generateTitleButton = document.getElementById('generateTitleButton');
const exportPreview = document.getElementById('exportPreview');
const messageCount = document.getElementById('messageCount');

document.addEventListener('DOMContentLoaded', () => {
    const messagesContainer = document.getElementById('messagesContainer');
    const chatContainer = document.getElementById('chatContainer');
    const messageInput = document.getElementById('messageInput');
    const sendButton = document.getElementById('sendButton');
    const homeButton = document.getElementById('homeButton');
    const clearButton = document.getElementById('clearButton');
    const clearModal = document.getElementById('clearModal');
    const cancelClear = document.getElementById('cancelClear');
    const confirmClear = document.getElementById('confirmClear');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const notificationContainer = document.getElementById('notificationContainer');

    let isTyping = false;
    let isInitialTyping = true;

    // Setup export tooltip
    const setupExportTooltip = () => {
        const tooltip = exportButton.querySelector('.export-tooltip');
        let tooltipTimeout;
        let tooltipVisible = false;

        const positionTooltip = () => {
            if (!tooltip) return;

            const buttonRect = exportButton.getBoundingClientRect();
            const tooltipRect = tooltip.getBoundingClientRect();

            // Center the tooltip above the button
            const left = buttonRect.left + (buttonRect.width / 2) - (tooltipRect.width / 2);
            const top = buttonRect.top - tooltipRect.height - 8;

            tooltip.style.left = `${left}px`;
            tooltip.style.top = `${top}px`;
        };

        exportButton.addEventListener('mouseenter', () => {
            if (tooltip && !tooltipVisible) {
                tooltipTimeout = setTimeout(() => {
                    positionTooltip();
                    tooltip.classList.add('show');
                    tooltipVisible = true;
                }, 200);
            }
        });

        exportButton.addEventListener('mouseleave', () => {
            if (tooltipTimeout) {
                clearTimeout(tooltipTimeout);
            }
            if (tooltip && tooltipVisible) {
                tooltip.classList.remove('show');
                tooltipVisible = false;
            }
        });

        exportButton.addEventListener('click', () => {
            if (tooltipTimeout) {
                clearTimeout(tooltipTimeout);
            }
            if (tooltip && tooltipVisible) {
                tooltip.classList.remove('show');
                tooltipVisible = false;
            }
        });
    };

    // Initialize export tooltip
    setupExportTooltip();

    // Format date for export
    const formatDateForExport = (dateString) => {
        const date = new Date(dateString);
        return date.toLocaleString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    // Build preview content
    const buildExportPreview = () => {
        const messages = document.querySelectorAll('.message');
        let previewHTML = '';
        let count = 0;

        messages.forEach(message => {
            const isBot = message.classList.contains('message-bot');
            const content = message.querySelector('.message-content');
            const timestamp = message.querySelector('.message-timestamp');

            if (content) {
                count++;
                const sender = isBot ? 'Snowfriend' : 'You';
                const time = timestamp ? timestamp.getAttribute('data-timestamp') : new Date().toISOString();
                const formattedTime = formatDateForExport(time);

                previewHTML += `
                <div class="preview-message ${isBot ? 'preview-message-bot' : 'preview-message-user'}">
                    <div class="preview-message-header">${sender} • ${formattedTime}</div>
                    <div class="preview-message-content">${content.textContent}</div>
                </div>
            `;
            }
        });

        messageCount.textContent = count;
        exportPreview.innerHTML = previewHTML || '<em>No messages to export</em>';
    };

    // Generate AI title
    const generateAITitle = async () => {
        try {
            const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || getCookie('csrftoken');

            const response = await fetch('/chat/api/generate-title/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken,
                },
            });

            const data = await response.json();

            if (data.success && data.title) {
                chatTitleInput.value = data.title;
                showNotification('AI title generated successfully!', 'success');
            } else {
                // Fallback to default title
                const date = new Date();
                const formattedDate = date.toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric'
                });
                chatTitleInput.value = `Conversation - ${formattedDate}`;
                showNotification('Generated default title', 'info');
            }
        } catch (error) {
            console.error('Error generating title:', error);
            const date = new Date();
            const formattedDate = date.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric'
            });
            chatTitleInput.value = `Conversation - ${formattedDate}`;
            showNotification('Generated default title', 'info');
        }
    };

    // Export conversation
    const exportConversation = async () => {
    const title = chatTitleInput.value.trim() || 'Snowfriend Conversation';
    const messages = Array.from(document.querySelectorAll('.message')).map(message => {
        const isBot = message.classList.contains('message-bot');
        const content = message.querySelector('.message-content');
        const timestamp = message.querySelector('.message-timestamp');

        return {
            sender: isBot ? 'Snowfriend' : 'You',
            content: content ? content.textContent : '',
            timestamp: timestamp ? timestamp.getAttribute('data-timestamp') : new Date().toISOString(),
            formattedTime: timestamp ? formatDateForExport(timestamp.getAttribute('data-timestamp')) : formatDateForExport(new Date().toISOString())
        };
    });

    // Check if there are messages to export
    if (messages.length === 0) {
        showNotification('No messages to export', 'error');
        return;
    }

    try {
        const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || getCookie('csrftoken');

        const response = await fetch('/chat/api/export/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken,
            },
            body: JSON.stringify({ title, messages }),
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.txt`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            showNotification('Conversation exported successfully!', 'success');
            closeExportModal();
        } else {
            // Try to get error message from response
            const errorData = await response.json().catch(() => ({}));
            const errorMsg = errorData.error || 'Error exporting conversation';
            showNotification(errorMsg, 'error');
            console.error('Export failed:', errorData);
        }
    } catch (error) {
        console.error('Error exporting:', error);
        showNotification('Network error while exporting', 'error');
    }
};

    // Modal handlers for export
    exportButton.addEventListener('click', () => {
        buildExportPreview();
        exportModal.classList.add('show');
    });

    const closeExportModal = () => {
    exportModal.classList.remove('show');
    exportModal.classList.remove('closing');
};

    cancelExport.addEventListener('click', () => {
        closeExportModal();
    });

    confirmExport.addEventListener('click', () => {
        exportConversation();
    });

    generateTitleButton.addEventListener('click', () => {
        generateAITitle();
    });

    exportModal.addEventListener('click', (e) => {
        if (e.target === exportModal) {
            closeExportModal();
        }
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && exportModal.classList.contains('show')) {
            closeExportModal();
        }
    });

    // Load conversation history on page load
    const loadConversationHistory = async () => {
        try {
            const response = await fetch('/chat/api/history/', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            const data = await response.json();

            if (data.success && data.messages && data.messages.length > 0) {
                // Clear initial typing flag since we have history
                isInitialTyping = false;
                updateSendButton();

                // Clear the initial greeting message
                messagesContainer.innerHTML = '';

                // Display all historical messages
                data.messages.forEach(msg => {
                    if (msg.role === 'user') {
                        appendMessage(msg.content, 'user', msg.timestamp);
                    } else if (msg.role === 'assistant') {
                        appendMessage(msg.content, 'bot', msg.timestamp);
                    }
                });

                scrollToBottom();
            } else {
                // No history, show initial greeting
                addInitialMessage();
            }
        } catch (error) {
            console.error('Error loading conversation history:', error);
            addInitialMessage();
        }
    };

    // Scroll to bottom of messages
    const scrollToBottom = () => {
        if (chatContainer) {
            chatContainer.scrollTo({
                top: chatContainer.scrollHeight,
                behavior: 'smooth'
            });
        }
    };

    // Create user avatar SVG
    const createUserAvatar = () => {
        return `
            <svg class="avatar-svg" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="12" cy="8" r="4" fill="currentColor" opacity="0.6"/>
                <path d="M4 20c0-4.4 3.6-8 8-8s8 3.6 8 8" stroke="currentColor" stroke-width="2" opacity="0.6"/>
            </svg>
        `;
    };

    // Auto-resize textarea
    const autoResize = () => {
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

    // Update send button state
    const updateSendButton = () => {
        const hasText = messageInput.value.trim().length > 0;

        if (hasText && !isTyping && !isInitialTyping) {
            sendButton.removeAttribute('disabled');
        } else {
            sendButton.setAttribute('disabled', 'disabled');
        }
    };

    // Show notification
    const showNotification = (message, type = 'success') => {
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

        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(() => {
                notification.remove();
            }, 300);
        }, 5000);

        // Manual close
        const closeBtn = notification.querySelector('.notification-close');
        closeBtn.addEventListener('click', () => {
            notification.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(() => {
                notification.remove();
            }, 300);
        });
    };

    // Append message to chat (instant - for user messages)
    const appendMessage = (text, sender, timestamp = null) => {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message message-${sender}`;

        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';

        const messageBody = document.createElement('div');
        messageBody.className = 'message-body';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = text;

        const timestampDiv = document.createElement('div');
        timestampDiv.className = 'message-timestamp';
        const timestampValue = timestamp || new Date().toISOString();
        timestampDiv.setAttribute('data-timestamp', timestampValue);
        timestampDiv.textContent = formatTimestamp(timestampValue);

        messageBody.appendChild(contentDiv);
        messageBody.appendChild(timestampDiv);

        if (sender === 'bot') {
            const avatarImg = document.createElement('img');
            const logoIcon = document.querySelector('.logo-icon');
            if (logoIcon) {
                avatarImg.src = logoIcon.src;
            }
            avatarImg.alt = 'Snowfriend';
            avatarDiv.appendChild(avatarImg);

            messageDiv.appendChild(avatarDiv);
            messageDiv.appendChild(messageBody);
        } else {
            avatarDiv.innerHTML = createUserAvatar();
            messageDiv.appendChild(messageBody);
            messageDiv.appendChild(avatarDiv);
        }

        messagesContainer.appendChild(messageDiv);
        scrollToBottom();
    };

    // Show typing indicator
    const showTypingIndicator = () => {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message message-bot';

        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        const avatarImg = document.createElement('img');
        const logoIcon = document.querySelector('.logo-icon');
        if (logoIcon) {
            avatarImg.src = logoIcon.src;
        }
        avatarImg.alt = 'Snowfriend';
        avatarDiv.appendChild(avatarImg);

        const typingDiv = document.createElement('div');
        typingDiv.className = 'typing-indicator';
        typingDiv.innerHTML = `
            <span class="typing-text">Snowfriend is typing<span class="typing-dots"><span class="typing-dot">.</span><span class="typing-dot">.</span><span class="typing-dot">.</span></span></span>
        `;

        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(typingDiv);
        messagesContainer.appendChild(messageDiv);

        scrollToBottom();

        return messageDiv;
    };

    // Append message with typing effect
    const appendMessageWithTyping = (text, sender, callback) => {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message message-${sender}`;

        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';

        const messageBody = document.createElement('div');
        messageBody.className = 'message-body';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        const timestampDiv = document.createElement('div');
        timestampDiv.className = 'message-timestamp';
        const timestampValue = new Date().toISOString();
        timestampDiv.setAttribute('data-timestamp', timestampValue);
        timestampDiv.textContent = formatTimestamp(timestampValue);

        messageBody.appendChild(contentDiv);
        messageBody.appendChild(timestampDiv);

        if (sender === 'bot') {
            const avatarImg = document.createElement('img');
            const logoIcon = document.querySelector('.logo-icon');
            if (logoIcon) {
                avatarImg.src = logoIcon.src;
            }
            avatarImg.alt = 'Snowfriend';
            avatarDiv.appendChild(avatarImg);

            messageDiv.appendChild(avatarDiv);
            messageDiv.appendChild(messageBody);
        } else {
            avatarDiv.innerHTML = createUserAvatar();
            messageDiv.appendChild(messageBody);
            messageDiv.appendChild(avatarDiv);
        }

        messagesContainer.appendChild(messageDiv);
        scrollToBottom();

        let currentIndex = 0;
        const typingSpeed = 30;

        const typeCharacter = () => {
            if (currentIndex < text.length) {
                contentDiv.textContent = text.substring(0, currentIndex + 1);
                currentIndex++;
                scrollToBottom();
                setTimeout(typeCharacter, typingSpeed);
            } else {
                isTyping = false;
                updateSendButton();
                if (callback) callback();
            }
        };

        typeCharacter();
    };

    const formatTimestamp = (date) => {
        const now = new Date();
        const messageDate = new Date(date);
        const diffMs = now - messageDate;
        const diffSecs = Math.floor(diffMs / 1000);
        const diffMins = Math.floor(diffSecs / 60);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);

        // Just now (0-10 seconds)
        if (diffSecs < 10) {
            return 'Just now';
        }

        // Seconds ago (10-59 seconds)
        if (diffSecs < 60) {
            return `${diffSecs} ${diffSecs === 1 ? 'second' : 'seconds'} ago`;
        }

        // Minutes ago (1-59 minutes)
        if (diffMins < 60) {
            return `${diffMins} ${diffMins === 1 ? 'minute' : 'minutes'} ago`;
        }

        // Hours ago (1-23 hours)
        if (diffHours < 24) {
            return `${diffHours} ${diffHours === 1 ? 'hour' : 'hours'} ago`;
        }

        // Yesterday (24-47 hours)
        if (diffDays === 1) {
            const timeStr = messageDate.toLocaleTimeString('en-US', {
                hour: 'numeric',
                minute: '2-digit',
                hour12: true
            });
            return `Yesterday ${timeStr}`;
        }

        // Older than yesterday - show date and time
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

    // Update all timestamps in the chat
    const updateAllTimestamps = () => {
        const timestamps = document.querySelectorAll('.message-timestamp');
        timestamps.forEach(timestamp => {
            const isoDate = timestamp.getAttribute('data-timestamp');
            if (isoDate) {
                timestamp.textContent = formatTimestamp(isoDate);
            }
        });
    };

    // Send message to backend
    const sendMessage = async () => {
        const text = messageInput.value.trim();

        if (!text || isTyping || isInitialTyping) {
            return;
        }

        // Display user message immediately
        appendMessage(text, 'user');

        messageInput.value = '';
        messageInput.style.height = 'auto';
        isTyping = true;
        updateSendButton();

        const typingIndicator = showTypingIndicator();

        try {
            // Get CSRF token
            const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]')?.value
                || getCookie('csrftoken');

            // Send message to backend
            const response = await fetch('/chat/api/send/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken,
                },
                body: JSON.stringify({ message: text }),
            });

            const data = await response.json();

            // Remove typing indicator
            typingIndicator.remove();

            if (data.success) {
                // ✅ NEW: Check for truncation notification
                if (data.notification) {
                    showNotification(data.notification.message, data.notification.type);
                }

                // Display bot response with typing effect
                appendMessageWithTyping(data.response, 'bot');
            } else {
                // Handle error
                appendMessage('Sorry, I encountered an error. Please try again.', 'bot');
                isTyping = false;
                updateSendButton();
            }
        } catch (error) {
            console.error('Error sending message:', error);
            typingIndicator.remove();
            appendMessage("Sorry, I'm having trouble connecting. Please try again.", 'bot');
            isTyping = false;
            updateSendButton();
        }
    };

    // Helper function to get CSRF token from cookies
    const getCookie = (name) => {
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

    // Clear conversation
    const clearConversation = async () => {
        // Show loading overlay
        loadingOverlay.classList.add('show');

        try {
            // Get CSRF token
            const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]')?.value
                || getCookie('csrftoken');

            // Call backend to clear conversation
            const response = await fetch('/chat/api/clear/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken,
                },
            });

            const data = await response.json();

            // Wait for visual feedback
            setTimeout(() => {
                // Clear UI messages
                messagesContainer.innerHTML = '';

                // Hide loading
                loadingOverlay.classList.remove('show');

                // Show notification
                if (data.success) {
                    showNotification('All conversations have been cleared.', 'success');
                } else {
                    showNotification('Error clearing conversation.', 'error');
                }

                // Reset initial typing flag
                isInitialTyping = true;
                updateSendButton();

                // Add initial message again
                setTimeout(() => {
                    addInitialMessage();
                }, 500);
            }, 2000);
        } catch (error) {
            console.error('Error clearing conversation:', error);
            loadingOverlay.classList.remove('show');
            showNotification('Error clearing conversation.', 'error');
        }
    };

    // Setup tooltip for home button
    const setupTooltip = () => {
        if (!homeButton) return;

        const tooltip = homeButton.querySelector('.tooltip');
        let tooltipTimeout;
        let tooltipVisible = false;

        homeButton.addEventListener('mouseenter', () => {
            if (tooltip && !tooltipVisible) {
                tooltipTimeout = setTimeout(() => {
                    tooltip.classList.add('show');
                    tooltipVisible = true;
                }, 200);
            }
        });

        homeButton.addEventListener('mouseleave', () => {
            if (tooltipTimeout) {
                clearTimeout(tooltipTimeout);
            }
            if (tooltip && tooltipVisible) {
                tooltip.classList.remove('show');
                tooltipVisible = false;
            }
        });

        homeButton.addEventListener('click', () => {
            if (tooltipTimeout) {
                clearTimeout(tooltipTimeout);
            }
            if (tooltip && tooltipVisible) {
                tooltip.classList.remove('show');
                tooltipVisible = false;
            }
        });

        homeButton.addEventListener('touchstart', () => {
            if (tooltip && !tooltipVisible) {
                tooltipTimeout = setTimeout(() => {
                    tooltip.classList.add('show');
                    tooltipVisible = true;
                }, 200);
            }
        });

        homeButton.addEventListener('touchend', () => {
            if (tooltipTimeout) {
                clearTimeout(tooltipTimeout);
            }
            if (tooltip && tooltipVisible) {
                setTimeout(() => {
                    tooltip.classList.remove('show');
                    tooltipVisible = false;
                }, 1000);
            }
        });
    };

    // Setup tooltip for clear button
    const setupClearTooltip = () => {
        if (!clearButton) return;

        const tooltip = clearButton.querySelector('.clear-tooltip');
        let tooltipTimeout;
        let tooltipVisible = false;

        const positionTooltip = () => {
            if (!tooltip) return;

            const buttonRect = clearButton.getBoundingClientRect();
            const tooltipRect = tooltip.getBoundingClientRect();

            // Center the tooltip above the button
            const left = buttonRect.left + (buttonRect.width / 2) - (tooltipRect.width / 2);
            const top = buttonRect.top - tooltipRect.height - 8;

            tooltip.style.left = `${left}px`;
            tooltip.style.top = `${top}px`;
        };

        clearButton.addEventListener('mouseenter', () => {
            if (tooltip && !tooltipVisible) {
                tooltipTimeout = setTimeout(() => {
                    positionTooltip();
                    tooltip.classList.add('show');
                    tooltipVisible = true;
                }, 200);
            }
        });

        clearButton.addEventListener('mouseleave', () => {
            if (tooltipTimeout) {
                clearTimeout(tooltipTimeout);
            }
            if (tooltip && tooltipVisible) {
                tooltip.classList.remove('show');
                tooltipVisible = false;
            }
        });

        clearButton.addEventListener('click', () => {
            if (tooltipTimeout) {
                clearTimeout(tooltipTimeout);
            }
            if (tooltip && tooltipVisible) {
                tooltip.classList.remove('show');
                tooltipVisible = false;
            }
        });

        clearButton.addEventListener('touchstart', () => {
            if (tooltip && !tooltipVisible) {
                tooltipTimeout = setTimeout(() => {
                    positionTooltip();
                    tooltip.classList.add('show');
                    tooltipVisible = true;
                }, 200);
            }
        });

        clearButton.addEventListener('touchend', () => {
            if (tooltipTimeout) {
                clearTimeout(tooltipTimeout);
            }
            if (tooltip && tooltipVisible) {
                setTimeout(() => {
                    tooltip.classList.remove('show');
                    tooltipVisible = false;
                }, 1000);
            }
        });
    };

    // Add initial greeting message with typing animation
    const addInitialMessage = () => {
        const greeting = `Hi ${typeof userName !== 'undefined' ? userName : 'there'}! I'm Snowfriend. You can share your thoughts here at your own pace. I'm here to listen and help you reflect.`;

        const messageDiv = document.createElement('div');
        messageDiv.className = 'message message-bot';

        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        const avatarImg = document.createElement('img');
        const logoIcon = document.querySelector('.logo-icon');
        if (logoIcon) {
            avatarImg.src = logoIcon.src;
        }
        avatarImg.alt = 'Snowfriend';
        avatarDiv.appendChild(avatarImg);

        const messageBody = document.createElement('div');
        messageBody.className = 'message-body';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        const timestampDiv = document.createElement('div');
        timestampDiv.className = 'message-timestamp';
        const timestampValue = new Date().toISOString();
        timestampDiv.setAttribute('data-timestamp', timestampValue);
        timestampDiv.textContent = formatTimestamp(timestampValue);

        messageBody.appendChild(contentDiv);
        messageBody.appendChild(timestampDiv);

        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(messageBody);
        messagesContainer.appendChild(messageDiv);

        scrollToBottom();

        // Typing animation for initial message
        let currentIndex = 0;
        const typingSpeed = 25;

        const typeCharacter = () => {
            if (currentIndex < greeting.length) {
                contentDiv.textContent = greeting.substring(0, currentIndex + 1);
                currentIndex++;
                scrollToBottom();
                setTimeout(typeCharacter, typingSpeed);
            } else {
                // Initial typing is complete
                isInitialTyping = false;
                updateSendButton();
            }
        };

        // Start typing after a brief delay
        setTimeout(typeCharacter, 300);
    };

    // Modal handlers
    clearButton.addEventListener('click', () => {
        clearModal.classList.add('show');
    });

    const closeModal = () => {
    clearModal.classList.remove('show');
    clearModal.classList.remove('closing');
};

    cancelClear.addEventListener('click', () => {
        closeModal();
    });

    confirmClear.addEventListener('click', () => {
        closeModal();
        setTimeout(() => {
            clearConversation();
        }, 150);
    });

    clearModal.addEventListener('click', (e) => {
        if (e.target === clearModal) {
            closeModal();
        }
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && clearModal.classList.contains('show')) {
            closeModal();
        }
    });

    // Initialize
    setupTooltip();
    setupClearTooltip();
    loadConversationHistory();

    // Event listeners
    messageInput.addEventListener('input', () => {
        autoResize();
        updateSendButton();
    });

    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!sendButton.hasAttribute('disabled')) {
                sendMessage();
            }
        }
    });

    sendButton.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        sendMessage();
    });

    setTimeout(() => {
        scrollToBottom();
    }, 100);

    // Update timestamps every 10 seconds
    setInterval(updateAllTimestamps, 10000);
});

function showResourcesModal() {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
        <div class="modal-content crisis-modal-content">
            <h2 class="modal-title">Crisis Resources</h2>
            <p class="modal-text">If you're in crisis or need immediate support, please contact these services:</p>
            
            <div class="modal-privacy-box crisis-resources-box">
                <div class="modal-privacy-item">
                    <div>
                        <strong>🇵🇭 Philippines (24/7):</strong>
                        <div class="crisis-resource-list">
                            <div>• NCMH Crisis Hotline: <strong>0917-899-8727</strong> or <strong>989-8727</strong></div>
                            <div>• Hopeline Philippines: <strong>(02) 8804-4673</strong> or <strong>0917-558-4673</strong></div>
                            <div>• Emergency: <strong>911</strong></div>
                        </div>
                    </div>
                </div>
                
                <div class="modal-privacy-item">
                    <div>
                        <strong>🌍 International:</strong>
                        <div class="crisis-resource-list">
                            <div>• US: <strong>988</strong> (Suicide & Crisis Lifeline)</div>
                            <div>• Crisis Text Line: Text <strong>HOME</strong> to <strong>741741</strong></div>
                            <div>• UK: <strong>116 123</strong> (Samaritans)</div>
                            <div>• Canada: <strong>1-833-456-4566</strong></div>
                            <div>• Australia: <strong>13 11 14</strong> (Lifeline)</div>
                        </div>
                    </div>
                </div>
                
                <div class="modal-privacy-item crisis-note-item">
                    <svg class="modal-privacy-icon" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M8 4V8L10 10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                        <circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.5"/>
                    </svg>
                    <span><strong>Note:</strong> These are direct lines to trained professionals who can provide immediate support.</span>
                </div>
            </div>
            
            <div class="modal-actions">
                <button class="modal-button modal-button-cancel" id="crisisModalClose">Close</button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // Trigger animation
    setTimeout(() => {
        modal.classList.add('show');
    }, 10);

    // Close button handler
    const closeBtn = modal.querySelector('#crisisModalClose');
    closeBtn.addEventListener('click', () => {
        closeCrisisModal(modal);
    });

    // Click outside to close
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeCrisisModal(modal);
        }
    });

    // ESC key to close
    document.addEventListener('keydown', handleEscapeKey);
}

function closeCrisisModal(modal) {
    if (!modal) return;

    modal.classList.add('closing');
    setTimeout(() => {
        if (modal.parentNode) {
            modal.remove();
        }

        // Remove the ESC event listener
        document.removeEventListener('keydown', handleEscapeKey);
    }, 300);
}

// Helper function for ESC key handling
function handleEscapeKey(e) {
    if (e.key === 'Escape') {
        const crisisModal = document.querySelector('.modal-overlay:not(#clearModal)');
        if (crisisModal) {
            closeCrisisModal(crisisModal);
        }
    }
}