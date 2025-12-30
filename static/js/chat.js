document.addEventListener('DOMContentLoaded', () => {
    // ✅ UPDATED: Message Limit State (20 → 15)
    let messageLimitState = {
        total: 15,
        remaining: 15,
        canSend: true,
        timeRemaining: 0,
        timerInterval: null,
        checkInterval: null
    };
    
    // ✅ FIX 1: Helper function to get future reset time formatted as "6:00 AM"
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
    
    // ✅ FINAL FIX: Modal stack with overflow-only approach and defensive checks
    let modalStack = {
        count: 0,
        debug: false, // Set to true to enable debug logging
        
        open() {
            this.count++;
            if (this.debug) console.log(`📖 Modal opened. Count: ${this.count}`);
            
            if (this.count === 1) {
                // First modal opening - hide overflow
                document.documentElement.style.overflow = 'hidden';
                document.body.style.overflow = 'hidden';
                if (this.debug) console.log('🔒 Overflow hidden (first modal)');
            }
        },
        
        close() {
            if (this.debug) console.log(`📕 Modal closing. Count before: ${this.count}`);
            this.count--;
            
            // ✅ Defensive check: prevent negative count
            if (this.count < 0) {
                console.error('⚠️ Modal stack count went negative! This indicates close() was called more times than open().');
                console.error(`📊 Stack trace:`);
                console.trace();
                this.count = 0;
            }
            
            if (this.count === 0) {
                // Last modal closed - restore overflow
                document.documentElement.style.overflow = '';
                document.body.style.overflow = '';
                if (this.debug) console.log('🔓 Overflow restored (all modals closed)');
            } else {
                if (this.debug) console.log(`🔒 Overflow still hidden (${this.count} modal(s) remaining)`);
            }
        },
        
        forceReset() {
            // Emergency reset if modals get out of sync
            console.warn('🔧 Force resetting modal stack');
            this.count = 0;
            document.documentElement.style.overflow = '';
            document.body.style.overflow = '';
        }
    };
    
    // ============================================
    // DOM ELEMENT REFERENCES
    // ============================================
    const messagesContainer = document.getElementById('messagesContainer');
    const messageInput = document.getElementById('messageInput');
    const sendButton = document.getElementById('sendButton');
    const homeButton = document.getElementById('homeButton');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const notificationContainer = document.getElementById('notificationContainer');

    // Clear modal elements
    const clearButton = document.getElementById('clearButton');
    const clearModal = document.getElementById('clearModal');
    const cancelClear = document.getElementById('cancelClear');
    const confirmClear = document.getElementById('confirmClear');

    const confirmClearAll = document.getElementById('confirmClearAll');
    const confirmationModal = document.getElementById('confirmationModal');
    const cancelConfirmation = document.getElementById('cancelConfirmation');
    const confirmDeletion = document.getElementById('confirmDeletion');

    // Export modal elements
    const exportButton = document.getElementById('exportButton');
    const exportModal = document.getElementById('exportModal');
    const cancelExport = document.getElementById('cancelExport');
    const confirmExport = document.getElementById('confirmExport');
    const chatTitleInput = document.getElementById('chatTitle');
    const generateTitleButton = document.getElementById('generateTitleButton');
    const exportPreview = document.getElementById('exportPreview');
    const messageCount = document.getElementById('messageCount');

    // Fullscreen preview elements
    const expandPreviewButton = document.getElementById('expandPreviewButton');
    const fullscreenPreview = document.getElementById('fullscreenPreview');
    const closeFullscreenButton = document.getElementById('closeFullscreenButton');
    const fullscreenPreviewContent = document.getElementById('fullscreenPreviewContent');

    // ============================================
    // STATE VARIABLES
    // ============================================
    let isTyping = false;
    let isInitialTyping = true;

    // ============================================
    // MODAL UTILITY FUNCTIONS (FIXED)
    // ============================================
    
    const openModal = (modalElement) => {
        modalStack.open();
        modalElement.classList.add('show');
    };
    
    const closeModal = (modalElement) => {
        // ✅ CRITICAL: Add closing class FIRST to prevent duplicate ESC presses
        modalElement.classList.add('closing');
        
        // Then close modal via centralized stack management
        modalStack.close();
        
        setTimeout(() => {
            modalElement.classList.remove('show', 'closing');
        }, 300);
    };

    // ============================================
    // TOOLTIP SETUP FUNCTIONS
    // ============================================
    const setupExportTooltip = () => {
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
        let tooltip = expandPreviewButton.querySelector('.expand-tooltip');
        if (!tooltip) return;

        // Move tooltip outside the modal to prevent clipping
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

    // ============================================
    // FULLSCREEN PREVIEW FUNCTIONS (FIXED)
    // ============================================
    const openFullscreenPreview = () => {
        const previewContent = document.getElementById('exportPreview');
        fullscreenPreviewContent.innerHTML = previewContent.innerHTML;
        
        modalStack.open();
        fullscreenPreview.classList.add('show');
    };

    const closeFullscreenPreview = () => {
        // ✅ CRITICAL: Add closing class FIRST to prevent duplicate ESC presses
        fullscreenPreview.classList.add('closing');
        
        // Then close modal via centralized stack management
        modalStack.close();

        setTimeout(() => {
            fullscreenPreview.classList.remove('show', 'closing');
        }, 400);
    };

    // ============================================
    // EXPORT MODAL FUNCTIONS
    // ============================================
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
                titleInput.value = data.title;
                showNotification('✨ Unique title generated!', 'success');
            } else {
                const date = new Date();
                const formattedDate = date.toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric'
                });
                titleInput.value = `Conversation - ${formattedDate}`;
                showNotification('Generated default title', 'info');
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
            showNotification('Generated default title', 'info');
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

    const closeExportModal = () => {
        closeModal(exportModal);
    };

    // ============================================
    // CLEAR MODAL FUNCTIONS
    // ============================================
    const clearConversation = async () => {
        messagesContainer.innerHTML = '';

        loadingOverlay.classList.add('show');
        modalStack.open();

        try {
            const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || getCookie('csrftoken');

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
                    showNotification('All conversations have been cleared.', 'success');
                } else {
                    showNotification('Error clearing conversation.', 'error');
                }

                isInitialTyping = true;
                updateSendButton();

                setTimeout(() => {
                    addInitialMessage();
                }, 500);
            }, 2000);
        } catch (error) {
            console.error('Error clearing conversation:', error);
            loadingOverlay.classList.remove('show');
            modalStack.close();
            showNotification('Error clearing conversation.', 'error');
        }
    };

    // ============================================
    // CONFIRMATION MODAL FUNCTIONS
    // ============================================

    let countdownTimer = null;
    let cancelCountdownHandler = null;
    let mainClickHandler = null;
    let isCountdownActive = false;

    const resetConfirmationButton = () => {
        const button = document.getElementById('confirmDeletion');
        if (!button) return;

        // Clear any existing countdown
        if (countdownTimer) {
            clearInterval(countdownTimer);
            countdownTimer = null;
        }

        // Remove cancel handler if exists
        if (cancelCountdownHandler) {
            button.removeEventListener('click', cancelCountdownHandler);
            cancelCountdownHandler = null;
        }

        // Reset button to original state
        button.textContent = 'Yes, Delete Everything';
        button.className = 'modal-button modal-button-danger';
        button.disabled = false;

        // Show the cancel button again
        if (cancelConfirmation) {
            cancelConfirmation.style.display = '';
        }

        // ✅ Re-attach main handler if it was removed
        if (mainClickHandler && !button.hasAttribute('data-handler-attached')) {
            button.addEventListener('click', mainClickHandler);
            button.setAttribute('data-handler-attached', 'true');
        }
    };

    const clearConversationAndMemory = async () => {
        loadingOverlay.classList.add('show');
        modalStack.open();

        try {
            const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || getCookie('csrftoken');

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
                    showNotification('All conversations and memories have been deleted. Snowfriend will start fresh.', 'success');
                } else {
                    showNotification('Error clearing conversation and memory.', 'error');
                }

                // Reset button state after deletion completes
                resetConfirmationButton();

                isInitialTyping = true;
                updateSendButton();

                setTimeout(() => {
                    addInitialMessage();
                }, 500);
            }, 2000);
        } catch (error) {
            console.error('Error clearing conversation and memory:', error);
            loadingOverlay.classList.remove('show');
            modalStack.close();
            showNotification('Error clearing conversation and memory.', 'error');
            // Reset button on error too
            resetConfirmationButton();
        }
    };

    const startDeletionCountdown = (button) => {
        let countdown = 5;

        // Store original state
        const originalText = 'Yes, Delete Everything';
        const originalClass = 'modal-button modal-button-danger';

        // ✅ Mark countdown as active
        isCountdownActive = true;

        // ✅ Remove the main click handler during countdown
        if (mainClickHandler) {
            button.removeEventListener('click', mainClickHandler);
            button.removeAttribute('data-handler-attached');
        }

        // Update button for countdown
        button.textContent = `Undo? ${countdown}`;
        button.className = 'modal-button modal-button-danger countdown-active';
        button.disabled = false;

        // Hide the "No, I changed my mind" button during countdown
        if (cancelConfirmation) {
            cancelConfirmation.style.display = 'none';
        }

        // Create cancel handler
        cancelCountdownHandler = (e) => {
            e.preventDefault(); // ✅ Prevent any default behavior
            e.stopPropagation(); // ✅ Stop event bubbling

            // Clear the countdown
            if (countdownTimer) {
                clearInterval(countdownTimer);
                countdownTimer = null;
            }

            // ✅ Mark countdown as inactive
            isCountdownActive = false;

            // Reset button
            button.textContent = originalText;
            button.className = originalClass;
            button.disabled = false;

            // Show the cancel button again
            if (cancelConfirmation) {
                cancelConfirmation.style.display = '';
            }

            // Remove this cancel handler
            button.removeEventListener('click', cancelCountdownHandler);
            cancelCountdownHandler = null;

            // ✅ Re-attach the main handler
            if (mainClickHandler) {
                button.addEventListener('click', mainClickHandler);
                button.setAttribute('data-handler-attached', 'true');
            }

            showNotification('Deletion cancelled', 'info');
        };

        // Add cancel handler
        button.addEventListener('click', cancelCountdownHandler);

        // Start countdown
        countdownTimer = setInterval(() => {
            countdown--;

            if (countdown > 0) {
                button.textContent = `Undo? ${countdown}`;
            } else {
                // Countdown finished
                clearInterval(countdownTimer);
                countdownTimer = null;

                // ✅ Mark countdown as inactive
                isCountdownActive = false;

                // Remove cancel handler
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

    // ✅ Store the main handler as a named function
    mainClickHandler = (e) => {
        e.preventDefault();
        e.stopPropagation();
        startDeletionCountdown(e.target);
    };

    const closeConfirmationModal = () => {
        // Stop countdown immediately if running
        if (countdownTimer) {
            clearInterval(countdownTimer);
            countdownTimer = null;
        }

        // Remove cancel handler if exists
        const button = document.getElementById('confirmDeletion');
        if (cancelCountdownHandler && button) {
            button.removeEventListener('click', cancelCountdownHandler);
            cancelCountdownHandler = null;
        }

        // ✅ CRITICAL: Add closing class FIRST to prevent duplicate ESC presses
        confirmationModal.classList.add('closing');
        
        // Then close modal via centralized stack management
        modalStack.close();
        
        setTimeout(() => {
            confirmationModal.classList.remove('show', 'closing');
            
            // Reset button state when modal closes
            resetConfirmationButton();
        }, 300);
    };

    const closeClearModal = () => {
        closeModal(clearModal);
    };

    // ============================================
    // CHAT MESSAGE FUNCTIONS
    // ============================================
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
                isInitialTyping = false;
                updateSendButton();
                messagesContainer.innerHTML = '';

                data.messages.forEach(msg => {
                    if (msg.role === 'user') {
                        appendMessage(msg.content, 'user', msg.timestamp);
                    } else if (msg.role === 'assistant') {
                        appendMessage(msg.content, 'bot', msg.timestamp);
                    }
                });

                scrollToBottom();
            } else {
                addInitialMessage();
            }
        } catch (error) {
            console.error('Error loading conversation history:', error);
            addInitialMessage();
        }
    };

    const scrollToBottom = () => {
        window.scrollTo({
            top: document.documentElement.scrollHeight,
            behavior: 'smooth'
        });
    };

    const cleanMessageText = (text) => {
        if (!text) return '';

        // Remove validation error messages if they leaked through
        text = text.replace(/❌.*ASTERISKS.*❌/g, '').trim();
        text = text.replace(/❌[^\n]*\n?/g, '').trim();

        // ✅ NEW: Replace asterisks with quotes (except AI disclaimer)
        text = replaceAsterisksWithQuotes(text);

        // Remove unnecessary parentheses wrapping (unless it's AI disclaimer)
        if (text.startsWith('(') && text.endsWith(')')) {
            if (!(text.includes("I'm here to listen") && text.includes("professional"))) {
                text = text.slice(1, -1).trim();
            }
        }

        // Clean up line breaks but preserve intentional formatting
        const lines = text.split('\n');
        const cleanedLines = [];
        let consecutiveEmpty = 0;

        for (const line of lines) {
            const lineStripped = line.trim();
            if (lineStripped) {
                // Remove multiple spaces within line only
                const lineCleaned = lineStripped.replace(/\s+/g, ' ');
                cleanedLines.push(lineCleaned);
                consecutiveEmpty = 0;
            } else {
                consecutiveEmpty++;
                if (consecutiveEmpty <= 1) {  // Allow max 1 empty line
                    cleanedLines.push('');
                }
            }
        }

        text = cleanedLines.join('\n');

        // ✅ NEW: Fix bullet list spacing
        text = fixBulletListSpacing(text);

        // Remove trailing spaces before punctuation
        text = text.replace(/ +\./g, '.');
        text = text.replace(/ +\?/g, '?');
        text = text.replace(/ +!/g, '!');
        text = text.replace(/ +,/g, ',');

        // Final trim
        text = text.trim();

        return text;
    };

    const replaceAsterisksWithQuotes = (text) => {
        if (!text || !text.includes('*')) return text;

        // Check if text has AI disclaimer format
        const disclaimerPattern = /\*\([^)]*I'm here to listen[^)]*professional[^)]*\)\*/i;
        const hasDisclaimer = disclaimerPattern.test(text);

        if (hasDisclaimer) {
            const disclaimer = text.match(disclaimerPattern)[0];
            const textWithoutDisclaimer = text.replace(disclaimer, '<<<DISCLAIMER_PLACEHOLDER>>>');
            const processed = replaceAsterisksInText(textWithoutDisclaimer);
            return processed.replace('<<<DISCLAIMER_PLACEHOLDER>>>', disclaimer);
        } else {
            return replaceAsterisksInText(text);
        }
    };

    // ✅ NEW HELPER FUNCTION: Replace asterisks in text
    const replaceAsterisksInText = (text) => {
        // Pattern to match text wrapped in asterisks
        const pattern = /\*([^*]+)\*/g;

        return text.replace(pattern, (match, content) => {
            const wordCount = content.trim().split(/\s+/).length;

            // Single word or short phrase (1-2 words): single quotes
            if (wordCount <= 2) {
                return `'${content}'`;
            }
            // Longer phrase (3+ words): double quotes
            else {
                return `"${content}"`;
            }
        });
    };

    // ✅ NEW HELPER FUNCTION: Fix bullet list spacing
    const fixBulletListSpacing = (text) => {
        if (!text) return text;

        const lines = text.split('\n');
        const fixedLines = [];
        let inList = false;

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            const lineStripped = line.trim();
            const isListItem = /^[-•*]\s/.test(lineStripped) || /^\d+\.\s/.test(lineStripped);

            // Entering a list
            if (isListItem && !inList) {
                // Add blank line before list (if previous line wasn't empty)
                if (i > 0 && fixedLines.length > 0 && fixedLines[fixedLines.length - 1].trim()) {
                    fixedLines.push('');
                }
                inList = true;
            }

            // Exiting a list
            if (!isListItem && inList && lineStripped) {
                inList = false;
                // Add blank line after list
                if (fixedLines.length > 0 && fixedLines[fixedLines.length - 1].trim()) {
                    fixedLines.push('');
                }
            }

            fixedLines.push(line);
        }

        return fixedLines.join('\n');
    };

    const createUserAvatar = () => {
        return `
            <svg class="avatar-svg" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="12" cy="8" r="4" fill="currentColor" opacity="0.6"/>
                <path d="M4 20c0-4.4 3.6-8 8-8s8 3.6 8 8" stroke="currentColor" stroke-width="2" opacity="0.6"/>
            </svg>
        `;
    };

    const appendMessage = (text, sender, timestamp = null) => {
        // ✅ CRITICAL: Clean the text first
        text = cleanMessageText(text);

        if (!text) {
            console.warn('Empty message after cleaning, skipping append');
            return;
        }

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
            if (logoIcon) avatarImg.src = logoIcon.src;
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

    const showTypingIndicator = () => {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message message-bot';

        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        const avatarImg = document.createElement('img');
        const logoIcon = document.querySelector('.logo-icon');
        if (logoIcon) avatarImg.src = logoIcon.src;
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

    const appendMessageWithTyping = (text, sender, callback) => {
        // ✅ CRITICAL: Clean the text first
        text = cleanMessageText(text);

        if (!text) {
            console.warn('Empty message after cleaning, skipping append');
            if (callback) callback();
            return;
        }

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
            if (logoIcon) avatarImg.src = logoIcon.src;
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

    const updateAllTimestamps = () => {
        const timestamps = document.querySelectorAll('.message-timestamp');
        timestamps.forEach(timestamp => {
            const isoDate = timestamp.getAttribute('data-timestamp');
            if (isoDate) {
                timestamp.textContent = formatTimestamp(isoDate);
            }
        });
    };

    const sendMessage = async () => {
        const text = messageInput.value.trim();  // ✅ Get text FIRST

        if (!text || isTyping || isInitialTyping) return;

        // ✅ THEN check message limit
if (!messageLimitState.canSend) {
    const resetTimeStr = getResetTimeString(messageLimitState.timeRemaining);
    showNotification(
        `You have no messages remaining. Please wait until ${resetTimeStr} to get another ${messageLimitState.total} messages.`,
        'error'
    );
    return;
}

        appendMessage(text, 'user');
        messageInput.value = '';
        messageInput.style.height = 'auto';
        isTyping = true;
        updateSendButton();

        const typingIndicator = showTypingIndicator();

        try {
            const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || getCookie('csrftoken');

            // ✅ TRY STREAMING FIRST (fast - users see response in 0.5-1s)
            const streamingSupported = await tryStreaming(text, csrftoken, typingIndicator);

            // ✅ If streaming fails, fall back to regular request
            if (!streamingSupported) {
                console.log('Streaming not supported, using regular request');
                await regularRequest(text, csrftoken, typingIndicator);
            }

            fetchMessageLimit();

        } catch (error) {
            console.error('Error sending message:', error);
            typingIndicator.remove();
            appendMessage("Sorry, I'm having trouble connecting. Please try again.", 'bot');
            isTyping = false;
            updateSendButton();
        }
    };

    // ============================================================================
    // MESSAGE LIMIT FUNCTIONS
    // ============================================================================

    async function fetchMessageLimit() {
        try {
            const response = await fetch('/chat/api/limit/', {
                method: 'GET',
                headers: {
                    'X-CSRFToken': getCSRFToken()
                }
            });

            if (!response.ok) throw new Error('Failed to fetch limit');

            const data = await response.json();

            if (data.success) {
                messageLimitState.total = data.total_messages;
                messageLimitState.remaining = data.messages_remaining;
                messageLimitState.canSend = data.can_send;
                messageLimitState.timeRemaining = data.time_remaining_seconds;

                updateMessageLimitUI();

                if (data.notifications && data.notifications.length > 0) {
                    data.notifications.forEach(notification => {
                        showNotification(notification.message, getNotificationType(notification.type));
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

    function updateMessageLimitUI() {
        const messagesLeftElement = document.getElementById('messagesLeft');
        const sendButton = document.getElementById('sendButton');
        const messageInput = document.getElementById('messageInput');
        const messageCounter = document.getElementById('messageCounter');

        if (messagesLeftElement) {
            messagesLeftElement.textContent = messageLimitState.remaining;

            messageCounter.classList.remove('counter-zero', 'counter-low', 'counter-half');

            if (messageLimitState.remaining === 0) {
                messageCounter.classList.add('counter-zero');
            } else if (messageLimitState.remaining <= 3) {
                messageCounter.classList.add('counter-low');
            } else if (messageLimitState.remaining <= messageLimitState.total / 2) {
                messageCounter.classList.add('counter-half');
            }
        }

        if (!messageLimitState.canSend) {
    sendButton.disabled = true;
    messageInput.disabled = true;
    // ✅ FIX: Show future time instead of countdown
    const resetTimeStr = getResetTimeString(messageLimitState.timeRemaining);
    messageInput.placeholder = `No messages left. You can chat Snowfriend again at ${resetTimeStr} to get another ${messageLimitState.total} messages`;
} else {
    messageInput.disabled = false;
    messageInput.placeholder = "Type what's on your mind…";
}
    }

    function startCountdownTimer() {
    const timerElement = document.getElementById('countdownTimer');
    const timerTextElement = document.getElementById('timerText');

    if (!timerElement || !timerTextElement) return;

    // ✅ Show timer with fade-in animation
    timerElement.style.display = 'flex';
    setTimeout(() => {
        timerElement.style.opacity = '1';
    }, 10);

    if (messageLimitState.timerInterval) {
        clearInterval(messageLimitState.timerInterval);
    }

    // ✅ Set initial time immediately (no flash)
    timerTextElement.textContent = formatTime(messageLimitState.timeRemaining);

    messageLimitState.timerInterval = setInterval(() => {
        if (messageLimitState.timeRemaining > 0) {
            messageLimitState.timeRemaining--;
            timerTextElement.textContent = formatTime(messageLimitState.timeRemaining);
        } else {
            stopCountdownTimer();
            fetchMessageLimit();
            showNotification('Message limit has been reset!', 'success');
        }
    }, 1000);
}

    function stopCountdownTimer() {
    const timerElement = document.getElementById('countdownTimer');

    if (messageLimitState.timerInterval) {
        clearInterval(messageLimitState.timerInterval);
        messageLimitState.timerInterval = null;
    }

    if (timerElement) {
        // ✅ Fade out before hiding
        timerElement.style.opacity = '0';
        setTimeout(() => {
            timerElement.style.display = 'none';
        }, 300);
    }
}

    function formatTime(seconds) {
        if (seconds <= 0) return '00:00:00';
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;
        return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    }

    function getNotificationType(type) {
        switch (type) {
            case 'half': return 'info';
            case 'three': return 'error';
            case 'zero': return 'error';
            default: return 'info';
        }
    }

    function startMessageLimitCheck() {
        fetchMessageLimit();

        if (messageLimitState.checkInterval) {
            clearInterval(messageLimitState.checkInterval);
        }

        messageLimitState.checkInterval = setInterval(() => {
            fetchMessageLimit();
        }, 30000);
    }

    const tryStreaming = async (text, csrftoken, typingIndicator) => {
        try {
            const response = await fetch('/chat/api/send/streaming/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken,
                },
                body: JSON.stringify({ message: text }),
            });

            if (!response.ok || !response.body) {
                return false; // Streaming not supported
            }

            // Remove typing indicator once we start receiving chunks
            typingIndicator.remove();

            // Read streaming response
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let fullResponse = '';
            let messageElement = null;

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                // Decode chunk
                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));

                            if (data.chunk) {
                                fullResponse += data.chunk;

                                // Create message element on first chunk
                                if (!messageElement) {
                                    messageElement = createStreamingMessage();
                                }

                                // Update message content with new chunk
                                updateStreamingMessage(messageElement, fullResponse);
                            }

                            if (data.done) {
                                // ✅ Clean only the final accumulated response
                                if (messageElement) {
                                    const cleanedResponse = cleanMessageText(fullResponse);
                                    messageElement.textContent = cleanedResponse;
                                }
                                isTyping = false;
                                updateSendButton();
                                return true;
                            }

                            if (data.error) {
                                throw new Error(data.error);
                            }
                        } catch (e) {
                            // Ignore JSON parse errors for incomplete chunks
                            if (e instanceof SyntaxError) continue;
                            throw e;
                        }
                    }
                }
            }

            isTyping = false;
            updateSendButton();
            return true;

        } catch (error) {
            console.error('Streaming error:', error);
            return false; // Fall back to regular request
        }
    };

    // ✅ NEW FUNCTION 2: Create message element for streaming
    const createStreamingMessage = () => {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message message-bot';

        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        const avatarImg = document.createElement('img');
        const logoIcon = document.querySelector('.logo-icon');
        if (logoIcon) avatarImg.src = logoIcon.src;
        avatarImg.alt = 'Snowfriend';
        avatarDiv.appendChild(avatarImg);

        const messageBody = document.createElement('div');
        messageBody.className = 'message-body';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = '';

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

        return contentDiv;
    };

    const updateStreamingMessage = (element, content) => {
        element.textContent = content;
        scrollToBottom();
    };

    // ✅ NEW FUNCTION 4: Regular request fallback (if streaming fails)
    const regularRequest = async (text, csrftoken, typingIndicator) => {
        const response = await fetch('/chat/api/send/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken,
            },
            body: JSON.stringify({ message: text }),
        });

        const data = await response.json();
        typingIndicator.remove();

        if (data.success) {
            if (data.notification) {
                showNotification(data.notification.message, data.notification.type);
            }
            appendMessageWithTyping(data.response, 'bot');
        } else {
            appendMessage('Sorry, I encountered an error. Please try again.', 'bot');
            isTyping = false;
            updateSendButton();
        }
    };

    const addInitialMessage = () => {
        // ✅ UPDATED: Simplified fallback greeting (server generates dynamic greetings)
        const greeting = `Hi ${typeof userName !== 'undefined' ? userName : 'there'}! I'm Snowfriend. I'm here to listen and help you reflect.`;

        const messageDiv = document.createElement('div');
        messageDiv.className = 'message message-bot';

        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        const avatarImg = document.createElement('img');
        const logoIcon = document.querySelector('.logo-icon');
        if (logoIcon) avatarImg.src = logoIcon.src;
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

        let currentIndex = 0;
        const typingSpeed = 25;

        const typeCharacter = () => {
            if (currentIndex < greeting.length) {
                contentDiv.textContent = greeting.substring(0, currentIndex + 1);
                currentIndex++;
                scrollToBottom();
                setTimeout(typeCharacter, typingSpeed);
            } else {
                isInitialTyping = false;
                updateSendButton();
            }
        };

        setTimeout(typeCharacter, 300);
    };

    // ============================================
    // UI HELPER FUNCTIONS
    // ============================================
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

    const updateSendButton = () => {
        const hasText = messageInput.value.trim().length > 0;

        if (hasText && !isTyping && !isInitialTyping) {
            sendButton.removeAttribute('disabled');
        } else {
            sendButton.setAttribute('disabled', 'disabled');
        }
    };

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
    
    const getCSRFToken = () => {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || getCookie('csrftoken');
    };

    // ============================================
    // EVENT LISTENERS
    // ============================================

    // Message input
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

    // Clear modal
    clearButton.addEventListener('click', () => {
        openModal(clearModal);
    });

    cancelClear.addEventListener('click', () => closeClearModal());
    confirmClear.addEventListener('click', () => {
        closeClearModal();
        setTimeout(() => clearConversation(), 150);
    });

    clearModal.addEventListener('click', (e) => {
        if (e.target === clearModal) closeClearModal();
    });

    // Confirmation modal (add after the clear modal listeners)
    confirmClearAll.addEventListener('click', () => {
        // ✅ FIX: Open confirmation modal FIRST (while clear modal still open)
        // This keeps modalStack.count from going to 0, preventing scroll restoration
        resetConfirmationButton();
        openModal(confirmationModal);
        
        // Then close clear modal after a tiny delay
        setTimeout(() => {
            closeClearModal();
        }, 50);
    });

    cancelConfirmation.addEventListener('click', (e) => {
        // ✅ Prevent closing if countdown is active
        if (isCountdownActive) {
            e.stopPropagation();
            e.preventDefault();
            return;
        }
        resetConfirmationButton();
        closeConfirmationModal();
    });

    confirmDeletion.addEventListener('click', mainClickHandler);
    confirmDeletion.setAttribute('data-handler-attached', 'true');

    confirmationModal.addEventListener('click', (e) => {
        if (e.target === confirmationModal) {
            // ✅ Prevent closing if countdown is active
            if (isCountdownActive) {
                e.stopPropagation();
                e.preventDefault();
                return;
            }
            closeConfirmationModal();
        }
    });

    // Export modal
    exportButton.addEventListener('click', () => {
        openModal(exportModal);
        buildExportPreview();
        setTimeout(() => setupExpandTooltip(), 100);
    });

    cancelExport.addEventListener('click', () => closeExportModal());
    confirmExport.addEventListener('click', () => exportConversation());
    generateTitleButton.addEventListener('click', () => generateAITitle());

    exportModal.addEventListener('click', (e) => {
        if (e.target === exportModal) closeExportModal();
    });

    // Fullscreen preview
    expandPreviewButton.addEventListener('click', () => openFullscreenPreview());
    closeFullscreenButton.addEventListener('click', () => closeFullscreenPreview());

    fullscreenPreview.addEventListener('click', (e) => {
        if (e.target === fullscreenPreview) closeFullscreenPreview();
    });

    // ✅ MASTER ESC HANDLER - Single handler with closing state protection
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            // Check modals in priority order (innermost to outermost)
            // ✅ CRITICAL: Check if modal is NOT already closing before handling ESC
            if (fullscreenPreview.classList.contains('show') && !fullscreenPreview.classList.contains('closing')) {
                e.preventDefault();
                e.stopPropagation();
                closeFullscreenPreview();
                return;
            }
            
            if (confirmationModal.classList.contains('show') && !confirmationModal.classList.contains('closing')) {
                // Prevent closing if countdown is active
                if (isCountdownActive) {
                    e.preventDefault();
                    e.stopPropagation();
                    return;
                }
                e.preventDefault();
                e.stopPropagation();
                resetConfirmationButton();
                closeConfirmationModal();
                return;
            }
            
            if (exportModal.classList.contains('show') && !exportModal.classList.contains('closing')) {
                e.preventDefault();
                e.stopPropagation();
                closeExportModal();
                return;
            }
            
            if (clearModal.classList.contains('show') && !clearModal.classList.contains('closing')) {
                e.preventDefault();
                e.stopPropagation();
                closeClearModal();
                return;
            }
            
            // ✅ Don't prevent default if no modal is open
            // This allows dynamically created modals (like crisis modal) to handle ESC
        }
    });

    // ============================================
    // INITIALIZATION
    // ============================================
    setupExportTooltip();
    setupClearTooltip();
    setupExpandTooltip();
    setupHomeTooltip();
    loadConversationHistory();

    setTimeout(() => scrollToBottom(), 100);
    setInterval(updateAllTimestamps, 10000);

    startMessageLimitCheck();

    window.addEventListener('beforeunload', () => {
        if (messageLimitState.checkInterval) {
            clearInterval(messageLimitState.checkInterval);
        }
        stopCountdownTimer();
    });
});

// ============================================
// GLOBAL FUNCTIONS (called from HTML) - FIXED
// ============================================
function showResourcesModal() {
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
    
    // ✅ FINAL FIX: Use consistent modal stack for crisis modal
    const modalStack = {
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
    
    modalStack.open();

    setTimeout(() => {
        modal.classList.add('show');
    }, 10);

    const closeCrisisModal = () => {
        // ✅ CRITICAL: Add closing class FIRST to prevent duplicate ESC presses
        modal.classList.add('closing');
        
        // Then close modal via centralized stack management
        modalStack.close();
        
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
}