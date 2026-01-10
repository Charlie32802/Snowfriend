// ============================================================================
// CHAT-MODALS.JS - MODAL MANAGEMENT SYSTEM
// ============================================================================
// Handles all modal interactions: clear, confirmation, export, fullscreen, crisis
// ============================================================================

// ============================================================================
// MODAL STACK MANAGEMENT
// ============================================================================

let modalStack = {
    count: 0,
    debug: false,
    
    open() {
        this.count++;
        if (this.debug) console.log(`📖 Modal opened. Count: ${this.count}`);
        
        if (this.count === 1) {
            document.documentElement.style.overflow = 'hidden';
            document.body.style.overflow = 'hidden';
            if (this.debug) console.log('🔒 Overflow hidden (first modal)');
        }
    },
    
    close() {
        if (this.debug) console.log(`📕 Modal closing. Count before: ${this.count}`);
        this.count--;
        
        if (this.count < 0) {
            console.error('⚠️ Modal stack count went negative!');
            console.trace();
            this.count = 0;
        }
        
        if (this.count === 0) {
            document.documentElement.style.overflow = '';
            document.body.style.overflow = '';
            if (this.debug) console.log('🔓 Overflow restored (all modals closed)');
        } else {
            if (this.debug) console.log(`🔒 Overflow still hidden (${this.count} modal(s) remaining)`);
        }
    },
    
    forceReset() {
        console.warn('🔧 Force resetting modal stack');
        this.count = 0;
        document.documentElement.style.overflow = '';
        document.body.style.overflow = '';
    }
};

/**
 * Open modal with stack management
 */
const openModal = (modalElement) => {
    modalStack.open();
    modalElement.classList.add('show');
};

/**
 * Close modal with stack management
 */
const closeModal = (modalElement) => {
    modalElement.classList.add('closing');
    modalStack.close();
    
    setTimeout(() => {
        modalElement.classList.remove('show', 'closing');
    }, 300);
};

/**
 * Create message element structure (needed for streaming media responses)
 */
window.createMessageElement = (sender) => {
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
    timestampDiv.textContent = window.formatTimestamp(timestampValue);

    messageBody.appendChild(contentDiv);
    messageBody.appendChild(timestampDiv);

    if (sender === 'bot') {
        const avatarImg = document.createElement('img');
        const logoIcon = document.querySelector('.logo-icon');
        if (logoIcon) avatarImg.src = logoIcon.src;
        avatarImg.alt = 'Snowfriend';
        avatarDiv.appendChild(avatarImg);
        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(messageBody);
    } else {
        avatarDiv.innerHTML = window.createUserAvatar();
        messageDiv.appendChild(messageBody);
        messageDiv.appendChild(avatarDiv);
    }

    return messageDiv;
};

// ============================================================================
// TOOLTIP SETUP FUNCTIONS
// ============================================================================

const setupExportTooltip = () => {
    const exportButton = document.getElementById('exportButton');
    const tooltip = exportButton.querySelector('.export-tooltip');
    let tooltipTimeout;
    let tooltipVisible = false;

    const positionTooltip = () => {
        if (!tooltip) return;

        const buttonRect = exportButton.getBoundingClientRect();
        const tooltipRect = tooltip.getBoundingClientRect();
        const left = buttonRect.left + (buttonRect.width / 2) - (tooltipRect.width / 2);
        const top = buttonRect.top - tooltipRect.height - 8;
        const adjustedLeft = Math.max(10, Math.min(left, window.innerWidth - tooltipRect.width - 10));
        const adjustedTop = Math.max(10, top);

        tooltip.style.left = `${adjustedLeft}px`;
        tooltip.style.top = `${adjustedTop}px`;
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
        if (tooltipTimeout) clearTimeout(tooltipTimeout);
        if (tooltip && tooltipVisible) {
            tooltip.classList.remove('show');
            tooltipVisible = false;
        }
    });

    exportButton.addEventListener('click', () => {
        if (tooltipTimeout) clearTimeout(tooltipTimeout);
        if (tooltip && tooltipVisible) {
            tooltip.classList.remove('show');
            tooltipVisible = false;
        }
    });

    window.addEventListener('scroll', () => {
        if (tooltipVisible) positionTooltip();
    });

    window.addEventListener('resize', () => {
        if (tooltipVisible) positionTooltip();
    });
};

const setupClearTooltip = () => {
    const clearButton = document.getElementById('clearButton');
    if (!clearButton) return;

    const tooltip = clearButton.querySelector('.clear-tooltip');
    let tooltipTimeout;
    let tooltipVisible = false;

    const positionTooltip = () => {
        if (!tooltip) return;

        const buttonRect = clearButton.getBoundingClientRect();
        const tooltipRect = tooltip.getBoundingClientRect();
        const left = buttonRect.left + (buttonRect.width / 2) - (tooltipRect.width / 2);
        const top = buttonRect.top - tooltipRect.height - 8;
        const adjustedLeft = Math.max(10, Math.min(left, window.innerWidth - tooltipRect.width - 10));
        const adjustedTop = Math.max(10, top);

        tooltip.style.left = `${adjustedLeft}px`;
        tooltip.style.top = `${adjustedTop}px`;
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
        if (tooltipTimeout) clearTimeout(tooltipTimeout);
        if (tooltip && tooltipVisible) {
            tooltip.classList.remove('show');
            tooltipVisible = false;
        }
    });

    clearButton.addEventListener('click', () => {
        if (tooltipTimeout) clearTimeout(tooltipTimeout);
        if (tooltip && tooltipVisible) {
            tooltip.classList.remove('show');
            tooltipVisible = false;
        }
    });

    window.addEventListener('scroll', () => {
        if (tooltipVisible) positionTooltip();
    });

    window.addEventListener('resize', () => {
        if (tooltipVisible) positionTooltip();
    });
};

const setupExpandTooltip = () => {
    const expandPreviewButton = document.getElementById('expandPreviewButton');
    let tooltip = expandPreviewButton.querySelector('.expand-tooltip');
    if (!tooltip) return;

    tooltip.remove();
    document.body.appendChild(tooltip);

    let tooltipTimeout;
    let tooltipVisible = false;

    const positionTooltip = () => {
        const buttonRect = expandPreviewButton.getBoundingClientRect();
        const tooltipRect = tooltip.getBoundingClientRect();
        const tooltipWidth = tooltipRect.width || 180;
        const left = buttonRect.left + (buttonRect.width / 2) - (tooltipWidth / 2);
        const top = buttonRect.top - 40;
        const adjustedLeft = Math.max(10, Math.min(left, window.innerWidth - tooltipWidth - 10));
        const adjustedTop = Math.max(10, top);

        tooltip.style.left = `${adjustedLeft}px`;
        tooltip.style.top = `${adjustedTop}px`;
    };

    expandPreviewButton.addEventListener('mouseenter', () => {
        if (!tooltipVisible) {
            tooltipTimeout = setTimeout(() => {
                positionTooltip();
                tooltip.classList.add('show');
                tooltipVisible = true;
            }, 200);
        }
    });

    expandPreviewButton.addEventListener('mouseleave', () => {
        if (tooltipTimeout) clearTimeout(tooltipTimeout);
        if (tooltipVisible) {
            tooltip.classList.remove('show');
            tooltipVisible = false;
        }
    });

    expandPreviewButton.addEventListener('click', () => {
        if (tooltipTimeout) clearTimeout(tooltipTimeout);
        if (tooltipVisible) {
            tooltip.classList.remove('show');
            tooltipVisible = false;
        }
    });

    window.addEventListener('scroll', () => {
        if (tooltipVisible) positionTooltip();
    }, { passive: true });

    window.addEventListener('resize', () => {
        if (tooltipVisible) positionTooltip();
    }, { passive: true });
};

const setupHomeTooltip = () => {
    const homeButton = document.getElementById('homeButton');
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
        if (tooltipTimeout) clearTimeout(tooltipTimeout);
        if (tooltip && tooltipVisible) {
            tooltip.classList.remove('show');
            tooltipVisible = false;
        }
    });

    homeButton.addEventListener('click', () => {
        if (tooltipTimeout) clearTimeout(tooltipTimeout);
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
        if (tooltipTimeout) clearTimeout(tooltipTimeout);
        if (tooltip && tooltipVisible) {
            setTimeout(() => {
                tooltip.classList.remove('show');
                tooltipVisible = false;
            }, 1000);
        }
    });
};

const setupCounterTooltip = () => {
    const messageCounter = document.getElementById('messageCounter');
    if (!messageCounter) return;

    const tooltip = messageCounter.querySelector('.counter-tooltip');
    if (!tooltip) return;

    // ✅ CRITICAL FIX: Move tooltip to body to avoid parent positioning
    tooltip.remove();
    document.body.appendChild(tooltip);

    let tooltipTimeout;
    let tooltipVisible = false;
    let isOverTooltip = false;
    let isOverCounter = false;

    const positionTooltip = () => {
        if (!tooltip || !tooltipVisible) return;

        const counterRect = messageCounter.getBoundingClientRect();
        const tooltipRect = tooltip.getBoundingClientRect();
        const viewportWidth = window.innerWidth;
        
        // Calculate centered position above the counter
        let left = counterRect.left + (counterRect.width / 2) - (tooltipRect.width / 2);
        const top = counterRect.top - tooltipRect.height - 8;
        
        // Ensure tooltip stays within viewport with padding
        const minLeft = 10;
        const maxLeft = viewportWidth - tooltipRect.width - 10;
        left = Math.max(minLeft, Math.min(left, maxLeft));
        
        const adjustedTop = Math.max(10, top);
        
        // Apply positioning
        tooltip.style.left = `${left}px`;
        tooltip.style.top = `${adjustedTop}px`;
        tooltip.style.right = 'auto';
    };

    const showTooltip = () => {
        if (tooltipVisible) return;
        
        // Update tooltip message count dynamically
        const currentMessages = window.messageLimitState?.remaining || 15;
        const tooltipCounter = tooltip.querySelector('#tooltipMessagesLeft');
        if (tooltipCounter) {
            tooltipCounter.textContent = currentMessages;
        }
        
        tooltip.classList.add('show');
        tooltipVisible = true;
        
        // Position after it's visible so we get accurate dimensions
        setTimeout(() => positionTooltip(), 0);
    };

    const hideTooltip = () => {
        // Only hide if cursor is not over counter OR tooltip
        setTimeout(() => {
            if (!isOverCounter && !isOverTooltip) {
                tooltip.classList.remove('show');
                tooltipVisible = false;
            }
        }, 100);
    };

    // Counter mouse events
    messageCounter.addEventListener('mouseenter', () => {
        isOverCounter = true;
        if (!tooltipVisible) {
            tooltipTimeout = setTimeout(showTooltip, 200);
        }
    });

    messageCounter.addEventListener('mouseleave', () => {
        isOverCounter = false;
        if (tooltipTimeout) clearTimeout(tooltipTimeout);
        hideTooltip();
    });

    // Tooltip mouse events (to keep it visible when hovering over it)
    tooltip.addEventListener('mouseenter', () => {
        isOverTooltip = true;
    });

    tooltip.addEventListener('mouseleave', () => {
        isOverTooltip = false;
        hideTooltip();
    });

    messageCounter.addEventListener('click', () => {
        if (tooltipTimeout) clearTimeout(tooltipTimeout);
        if (tooltipVisible) {
            isOverCounter = false;
            isOverTooltip = false;
            tooltip.classList.remove('show');
            tooltipVisible = false;
        }
    });

    // ✅ Touch support for mobile
    let touchTimeout;
    messageCounter.addEventListener('touchstart', (e) => {
        if (!tooltipVisible) {
            showTooltip();
            
            // Auto-hide after 4 seconds on mobile
            touchTimeout = setTimeout(() => {
                if (tooltipVisible) {
                    tooltip.classList.remove('show');
                    tooltipVisible = false;
                }
            }, 4000);
        } else {
            // Close if already visible
            tooltip.classList.remove('show');
            tooltipVisible = false;
        }
    });

    // ✅ Reposition on resize AND scroll
    window.addEventListener('resize', () => {
        if (tooltipVisible) {
            positionTooltip();
        }
    }, { passive: true });

    window.addEventListener('scroll', () => {
        if (tooltipVisible) {
            positionTooltip();
        }
    }, { passive: true });
};

// ============================================================================
// CLEAR MODAL FUNCTIONS
// ============================================================================

const clearConversation = async () => {
    const messagesContainer = document.getElementById('messagesContainer');
    const loadingOverlay = document.getElementById('loadingOverlay');
    
    messagesContainer.innerHTML = '';
    loadingOverlay.classList.add('show');
    modalStack.open();

    try {
        const csrftoken = window.getCSRFToken();

        const response = await fetch('/chat/api/clear/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken,
            },
        });

        const data = await response.json();

        setTimeout(() => {
            loadingOverlay.classList.remove('show');
            modalStack.close();

            if (data.success) {
                window.showNotification('All conversations have been cleared.', 'success');
            } else {
                window.showNotification('Error clearing conversation.', 'error');
            }

            window.isInitialTyping = true;
            window.updateSendButton();

            setTimeout(() => {
                window.addInitialMessage();
            }, 500);
        }, 2000);
    } catch (error) {
        console.error('Error clearing conversation:', error);
        loadingOverlay.classList.remove('show');
        modalStack.close();
        window.showNotification('Error clearing conversation.', 'error');
    }
};

const closeClearModal = () => {
    const clearModal = document.getElementById('clearModal');
    closeModal(clearModal);
};

// ============================================================================
// CONFIRMATION MODAL FUNCTIONS
// ============================================================================

let countdownTimer = null;
let cancelCountdownHandler = null;
let mainClickHandler = null;
window.isCountdownActive = false;

const resetConfirmationButton = () => {
    const button = document.getElementById('confirmDeletion');
    if (!button) return;

    if (countdownTimer) {
        clearInterval(countdownTimer);
        countdownTimer = null;
    }

    if (cancelCountdownHandler) {
        button.removeEventListener('click', cancelCountdownHandler);
        cancelCountdownHandler = null;
    }

    button.textContent = 'Yes, Delete Everything';
    button.className = 'modal-button modal-button-danger';
    button.disabled = false;

    const cancelConfirmation = document.getElementById('cancelConfirmation');
    if (cancelConfirmation) {
        cancelConfirmation.style.display = '';
    }

    if (mainClickHandler && !button.hasAttribute('data-handler-attached')) {
        button.addEventListener('click', mainClickHandler);
        button.setAttribute('data-handler-attached', 'true');
    }
};

const clearConversationAndMemory = async () => {
    const messagesContainer = document.getElementById('messagesContainer');
    const loadingOverlay = document.getElementById('loadingOverlay');
    
    loadingOverlay.classList.add('show');
    modalStack.open();

    try {
        const csrftoken = window.getCSRFToken();

        const response = await fetch('/chat/api/clear-all/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken,
            },
        });

        const data = await response.json();

        setTimeout(() => {
            messagesContainer.innerHTML = '';
            loadingOverlay.classList.remove('show');
            modalStack.close();

            if (data.success) {
                window.showNotification('All conversations and memories have been deleted. Snowfriend will start fresh.', 'success');
            } else {
                window.showNotification('Error clearing conversation and memory.', 'error');
            }

            resetConfirmationButton();

            window.isInitialTyping = true;
            window.updateSendButton();

            setTimeout(() => {
                window.addInitialMessage();
            }, 500);
        }, 2000);
    } catch (error) {
        console.error('Error clearing conversation and memory:', error);
        loadingOverlay.classList.remove('show');
        modalStack.close();
        window.showNotification('Error clearing conversation and memory.', 'error');
        resetConfirmationButton();
    }
};

const startDeletionCountdown = (button) => {
    let countdown = 5;
    const originalText = 'Yes, Delete Everything';
    const originalClass = 'modal-button modal-button-danger';

    window.isCountdownActive = true;

    if (mainClickHandler) {
        button.removeEventListener('click', mainClickHandler);
        button.removeAttribute('data-handler-attached');
    }

    button.textContent = `Undo? ${countdown}`;
    button.className = 'modal-button modal-button-danger countdown-active';
    button.disabled = false;

    const cancelConfirmation = document.getElementById('cancelConfirmation');
    if (cancelConfirmation) {
        cancelConfirmation.style.display = 'none';
    }

    cancelCountdownHandler = (e) => {
        e.preventDefault();
        e.stopPropagation();

        if (countdownTimer) {
            clearInterval(countdownTimer);
            countdownTimer = null;
        }

        window.isCountdownActive = false;

        button.textContent = originalText;
        button.className = originalClass;
        button.disabled = false;

        if (cancelConfirmation) {
            cancelConfirmation.style.display = '';
        }

        button.removeEventListener('click', cancelCountdownHandler);
        cancelCountdownHandler = null;

        if (mainClickHandler) {
            button.addEventListener('click', mainClickHandler);
            button.setAttribute('data-handler-attached', 'true');
        }

        window.showNotification('Deletion cancelled', 'info');
    };

    button.addEventListener('click', cancelCountdownHandler);

    countdownTimer = setInterval(() => {
        countdown--;

        if (countdown > 0) {
            button.textContent = `Undo? ${countdown}`;
        } else {
            clearInterval(countdownTimer);
            countdownTimer = null;
            window.isCountdownActive = false;

            if (cancelCountdownHandler) {
                button.removeEventListener('click', cancelCountdownHandler);
                cancelCountdownHandler = null;
            }

            button.disabled = true;
            button.textContent = 'Deleting...';

            closeConfirmationModal();
            setTimeout(() => {
                clearConversationAndMemory();
            }, 300);
        }
    }, 1000);
};

mainClickHandler = (e) => {
    e.preventDefault();
    e.stopPropagation();
    startDeletionCountdown(e.target);
};

const closeConfirmationModal = () => {
    if (countdownTimer) {
        clearInterval(countdownTimer);
        countdownTimer = null;
    }

    const button = document.getElementById('confirmDeletion');
    if (cancelCountdownHandler && button) {
        button.removeEventListener('click', cancelCountdownHandler);
        cancelCountdownHandler = null;
    }

    const confirmationModal = document.getElementById('confirmationModal');
    confirmationModal.classList.add('closing');
    modalStack.close();
    
    setTimeout(() => {
        confirmationModal.classList.remove('show', 'closing');
        resetConfirmationButton();
    }, 300);
};

// ============================================================================
// EXPORT MODAL FUNCTIONS
// ============================================================================

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

const extractMessageContent = (message) => {
    const content = message.querySelector('.message-content');
    if (!content) return '';
    
    // ✅ Check if this is a media message
    const isMedia = message.getAttribute('data-is-media') === 'true';
    
    if (isMedia) {
        const mediaType = message.getAttribute('data-media-type');
        const mediaDataStr = message.getAttribute('data-media-data');
        
        if (mediaDataStr) {
            try {
                const mediaData = JSON.parse(mediaDataStr);
                return formatMediaAsText(mediaData, mediaType);
            } catch (e) {
                console.error('Failed to parse media data:', e);
            }
        }
    }
    
    // Regular text message
    return content.textContent;
};

const formatMediaAsText = (mediaData, mediaType) => {
    let text = '';
    
    // Add intro
    if (mediaData.intro) {
        text += mediaData.intro + '\n\n';
    }
    
    // Add media items
    if (mediaType === 'video' && mediaData.videos) {
        mediaData.videos.forEach((video, index) => {
            text += `${index + 1}. ${video.title}\n`;
            text += `   🎬 ${video.url}\n`;
            text += `   By ${video.channel}\n`;
            if (video.description) {
                text += `   ${video.description}\n`;
            }
            text += '\n';
        });
    } else if (mediaType === 'image' && mediaData.images) {
        mediaData.images.forEach((image, index) => {
            text += `${index + 1}. ${image.alt || 'Image'}\n`;
            text += `   🖼️ ${image.url}\n`;
            if (image.photographer) {
                text += `   📸 Photo by ${image.photographer}\n`;
            }
            if (image.photographer_url) {
                text += `   Source: ${image.photographer_url}\n`;
            }
            text += '\n';
        });
    }
    
    // Add outro
    if (mediaData.outro) {
        text += mediaData.outro;
    }
    
    return text.trim();
};

const buildExportPreview = () => {
    const messages = document.querySelectorAll('.message');
    const exportPreview = document.getElementById('exportPreview');
    const messageCount = document.getElementById('messageCount');
    
    let previewHTML = '';
    let count = 0;

    messages.forEach(message => {
        const isBot = message.classList.contains('message-bot');
        const timestamp = message.querySelector('.message-timestamp');

        // ✅ Extract content (handles both regular and media messages)
        const contentText = extractMessageContent(message);
        
        if (contentText) {
            count++;
            const sender = isBot ? 'Snowfriend' : 'You';
            const time = timestamp ? timestamp.getAttribute('data-timestamp') : new Date().toISOString();
            const formattedTime = formatDateForExport(time);

            previewHTML += `
                <div class="preview-message ${isBot ? 'preview-message-bot' : 'preview-message-user'}">
                    <div class="preview-message-header">${sender} • ${formattedTime}</div>
                    <div class="preview-message-content" style="white-space: pre-wrap;">${contentText}</div>
                </div>
            `;
        }
    });

    messageCount.textContent = count;
    exportPreview.innerHTML = previewHTML || '<em>No messages to export</em>';
};

const generateAITitle = async () => {
    try {
        const titleInput = document.getElementById('chatTitle');
        const generateButton = document.getElementById('generateTitleButton');
        const inputWrapper = document.getElementById('titleInputWrapper');
        const spinner = document.getElementById('titleLoadingSpinner');

        titleInput.disabled = true;
        generateButton.disabled = true;
        inputWrapper.classList.add('loading');
        spinner.classList.add('show');

        const csrftoken = window.getCSRFToken();

        const response = await fetch('/chat/api/generate-title/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken,
            },
        });

        const data = await response.json();

        if (data.success && data.title) {
            titleInput.value = data.title;
            window.showNotification('✨ Unique title generated!', 'success');
        } else {
            const date = new Date();
            const formattedDate = date.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric'
            });
            titleInput.value = `Conversation - ${formattedDate}`;
            window.showNotification('Generated default title', 'info');
        }
    } catch (error) {
        console.error('Error generating title:', error);
        const titleInput = document.getElementById('chatTitle');
        const date = new Date();
        const formattedDate = date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        });
        titleInput.value = `Conversation - ${formattedDate}`;
        window.showNotification('Generated default title', 'info');
    } finally {
        const titleInput = document.getElementById('chatTitle');
        const generateButton = document.getElementById('generateTitleButton');
        const inputWrapper = document.getElementById('titleInputWrapper');
        const spinner = document.getElementById('titleLoadingSpinner');

        titleInput.disabled = false;
        generateButton.disabled = false;
        inputWrapper.classList.remove('loading');
        spinner.classList.remove('show');
    }
};

const exportConversation = async () => {
    const chatTitleInput = document.getElementById('chatTitle');
    const title = chatTitleInput.value.trim() || 'Snowfriend Conversation';
    
    const messages = Array.from(document.querySelectorAll('.message')).map(message => {
        const isBot = message.classList.contains('message-bot');
        const timestamp = message.querySelector('.message-timestamp');

        // ✅ Extract content (handles both regular and media messages)
        const contentText = extractMessageContent(message);

        return {
            sender: isBot ? 'Snowfriend' : 'You',
            content: contentText,
            timestamp: timestamp ? timestamp.getAttribute('data-timestamp') : new Date().toISOString(),
            formattedTime: timestamp ? formatDateForExport(timestamp.getAttribute('data-timestamp')) : formatDateForExport(new Date().toISOString())
        };
    });

    if (messages.length === 0) {
        window.showNotification('No messages to export', 'error');
        return;
    }

    try {
        const csrftoken = window.getCSRFToken();

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

            window.showNotification('Conversation exported successfully!', 'success');
            closeExportModal();
        } else {
            const errorData = await response.json().catch(() => ({}));
            const errorMsg = errorData.error || 'Error exporting conversation';
            window.showNotification(errorMsg, 'error');
            console.error('Export failed:', errorData);
        }
    } catch (error) {
        console.error('Error exporting:', error);
        window.showNotification('Network error while exporting', 'error');
    }
};

const closeExportModal = () => {
    const exportModal = document.getElementById('exportModal');
    closeModal(exportModal);
};

// ============================================================================
// FULLSCREEN PREVIEW FUNCTIONS
// ============================================================================

const openFullscreenPreview = () => {
    const previewContent = document.getElementById('exportPreview');
    const fullscreenPreviewContent = document.getElementById('fullscreenPreviewContent');
    const fullscreenPreview = document.getElementById('fullscreenPreview');
    
    // ✅ Copy preview content (already formatted with media as text)
    fullscreenPreviewContent.innerHTML = previewContent.innerHTML;
    modalStack.open();
    fullscreenPreview.classList.add('show');
};

const closeFullscreenPreview = () => {
    const fullscreenPreview = document.getElementById('fullscreenPreview');
    fullscreenPreview.classList.add('closing');
    modalStack.close();

    setTimeout(() => {
        fullscreenPreview.classList.remove('show', 'closing');
    }, 400);
};

// ============================================================================
// CRISIS RESOURCES MODAL
// ============================================================================

window.showResourcesModal = function() {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
        <div class="modal-content crisis-modal-content">
            <h2 class="modal-title">
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="display: inline-block; vertical-align: middle; margin-right: 0.5rem;">
        <circle cx="12" cy="12" r="10" stroke="#e74c3c" stroke-width="2" fill="none"/>
        <path d="M12 7v5M12 16h.01" stroke="#e74c3c" stroke-width="2" stroke-linecap="round"/>
    </svg>
    Crisis Resources & Emergency Hotlines
</h2>
            <p class="modal-text">If you or someone you know is in crisis, please reach out for immediate support:</p>
            
            <div class="modal-privacy-box crisis-resources-box">
                <!-- EMERGENCY SERVICES -->
                <div class="modal-privacy-item">
                    <div>
                        <strong>🚨 EMERGENCY SERVICES (24/7):</strong>
                        <div class="crisis-resource-list">
                            <div>• <strong>National Emergency Hotline:</strong> 911</div>
                            <div>• <strong>PNP Hotline:</strong> 0998-539-8568</div>
                            <div>• <strong>Bureau of Fire Protection:</strong> (02) 8426-0219 / 0962-458-4237</div>
                            <div>• <strong>Philippine Red Cross:</strong> 143</div>
                        </div>
                    </div>
                </div>

                <!-- MENTAL HEALTH CRISIS -->
                <div class="modal-privacy-item">
                    <div>
                        <strong>🧠 MENTAL HEALTH CRISIS HOTLINES (24/7):</strong>
                        <div class="crisis-resource-list">
                            <div>• <strong>NCMH Crisis Hotline:</strong> 0917-899-8727 / 989-8727 / 1553 (PLDT)</div>
                            <div>• <strong>Hopeline Philippines:</strong> (02) 8804-4673 / 0917-558-4673 / 2919 (PLDT)</div>
                            <div>• <strong>Mental Health Crisis Line:</strong> 0919-057-1553</div>
                            <div>• <strong>Tawag Paglaum (Call for Hope):</strong>
                                <div style="margin-left: 1.5rem;">
                                    - SMART/TNT: 0939-936-5433 / 0939-937-5433<br>
                                    - GLOBE/TM: 0966-467-9626
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- REGIONAL CRISIS HOTLINES -->
                <div class="modal-privacy-item">
                    <div>
                        <strong>📍 REGIONAL CRISIS HOTLINES:</strong>
                        <div class="crisis-resource-list">
                            <div>• <strong>Cagayan Valley Medical Center:</strong> 0929-646-2625 / 0967-125-7906</div>
                            <div>• <strong>Zamboanga City Medical Center:</strong> 0938-300-4003 / 0936-491-9398</div>
                            <div>• <strong>Baguio General Hospital:</strong> 0956-991-6841</div>
                            <div>• <strong>Philippine Navy Crisis Hotline:</strong> 0939-982-8339 / 0917-512-8339</div>
                            <div>• <strong>BARMM Mental Health Unit:</strong> 0962-683-2476 / 0953-884-2462</div>
                        </div>
                    </div>
                </div>

                <!-- LOCAL GOVERNMENT HOTLINES -->
                <div class="modal-privacy-item">
                    <div>
                        <strong>🏛️ LOCAL GOVERNMENT HOTLINES:</strong>
                        <div class="crisis-resource-list">
                            <div>• <strong>LGU Quezon City:</strong> 122</div>
                            <div>• <strong>LGU Cavite Province:</strong> 0977-006-9226 / 0930-763-6069</div>
                            <div>• <strong>Taguig City Health Office:</strong> 0929-521-8373 / 0967-039-3456</div>
                        </div>
                    </div>
                </div>

                <!-- DISASTER & CALAMITY -->
                <div class="modal-privacy-item">
                    <div>
                        <strong>🌪️ DISASTER MANAGEMENT:</strong>
                        <div class="crisis-resource-list">
                            <div>• <strong>NDRRMC:</strong> (02) 8911-5061 / (02) 8911-1406</div>
                            <div>• <strong>PAGASA Weather:</strong> (02) 8929-4656</div>
                            <div>• <strong>PHIVOLCS:</strong> (02) 8426-1468</div>
                        </div>
                    </div>
                </div>

                <!-- INTERNATIONAL HOTLINES -->
                <div class="modal-privacy-item">
                    <div>
                        <strong>🌍 INTERNATIONAL CRISIS HOTLINES:</strong>
                        <div class="crisis-resource-list">
                            <div>• <strong>US:</strong> 988 (Suicide & Crisis Lifeline) | Text HOME to 741741</div>
                            <div>• <strong>UK:</strong> 116 123 (Samaritans - 24/7)</div>
                            <div>• <strong>Canada:</strong> 1-833-456-4566 (24/7)</div>
                            <div>• <strong>Australia:</strong> 13 11 14 (Lifeline - 24/7)</div>
                        </div>
                    </div>
                </div>
                
                <!-- IMPORTANT NOTE -->
                <div class="modal-privacy-item crisis-note-item">
                    <svg class="modal-privacy-icon" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.5"/>
                        <path d="M8 4V8L10 10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                    </svg>
                    <span><strong>Important:</strong> These are direct lines to trained professionals who provide confidential, immediate support. You don't have to face a crisis alone.</span>
                </div>
            </div>
            
            <div class="modal-actions">
                <button class="modal-button modal-button-confirm" id="crisisModalClose">Close</button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
    
    const crisisModalStack = {
        count: 0,
        
        open() {
            this.count++;
            if (this.count === 1) {
                document.documentElement.style.overflow = 'hidden';
                document.body.style.overflow = 'hidden';
            }
        },
        
        close() {
            this.count--;
            if (this.count < 0) {
                console.warn('Crisis modal stack count went negative, resetting to 0');
                this.count = 0;
            }
            if (this.count === 0) {
                document.documentElement.style.overflow = '';
                document.body.style.overflow = '';
            }
        }
    };
    
    crisisModalStack.open();

    setTimeout(() => {
        modal.classList.add('show');
    }, 10);

    const closeCrisisModal = () => {
        modal.classList.add('closing');
        crisisModalStack.close();
        
        setTimeout(() => {
            if (modal.parentNode) modal.remove();
        }, 300);
    };

    const closeBtn = modal.querySelector('#crisisModalClose');
    closeBtn.addEventListener('click', closeCrisisModal);

    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeCrisisModal();
    });

    document.addEventListener('keydown', function handleEscapeKey(e) {
        if (e.key === 'Escape' && modal.classList.contains('show')) {
            closeCrisisModal();
            document.removeEventListener('keydown', handleEscapeKey);
        }
    });
};

// ============================================================================
// EXPOSE FUNCTIONS GLOBALLY
// ============================================================================

window.setupExportTooltip = setupExportTooltip;
window.setupClearTooltip = setupClearTooltip;
window.setupExpandTooltip = setupExpandTooltip;
window.setupHomeTooltip = setupHomeTooltip;
window.clearConversation = clearConversation;
window.closeClearModal = closeClearModal;
window.closeConfirmationModal = closeConfirmationModal;
window.closeExportModal = closeExportModal;
window.buildExportPreview = buildExportPreview;
window.generateAITitle = generateAITitle;
window.exportConversation = exportConversation;
window.openFullscreenPreview = openFullscreenPreview;
window.closeFullscreenPreview = closeFullscreenPreview;
window.resetConfirmationButton = resetConfirmationButton;
window.mainClickHandler = mainClickHandler;
window.openModal = openModal;
window.closeModal = closeModal;
window.setupCounterTooltip = setupCounterTooltip;