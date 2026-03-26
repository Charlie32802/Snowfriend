// ============================================================================
// CHAT.JS - MAIN ORCHESTRATOR
// ============================================================================
// This is the main entry point that initializes and coordinates all modules
// Dependencies: chat-limits.js, chat-ui.js, chat-modals.js, chat-messages.js, chat-media.js
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // ============================================
    // DOM ELEMENT REFERENCES
    // ============================================
    const messagesContainer = document.getElementById('messagesContainer');
    window.messagesContainer = messagesContainer;
    const messageInput = document.getElementById('messageInput');
    const sendButton = document.getElementById('sendButton');
    const homeButton = document.getElementById('homeButton');

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
    const generateTitleButton = document.getElementById('generateTitleButton');

    // Fullscreen preview elements
    const expandPreviewButton = document.getElementById('expandPreviewButton');
    const fullscreenPreview = document.getElementById('fullscreenPreview');
    const closeFullscreenButton = document.getElementById('closeFullscreenButton');

    // ============================================
    // STATE VARIABLES
    // ============================================
    window.isTyping = false;
    window.isInitialTyping = true;

    // ============================================
    // INPUT EVENT LISTENERS
    // ============================================
    messageInput.addEventListener('input', () => {
        window.autoResize();
        window.updateSendButton();
    });

    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!sendButton.hasAttribute('disabled')) {
                window.sendMessage();
            }
        }
    });

    sendButton.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        window.sendMessage();
    });

    // ============================================
    // CLEAR MODAL EVENT LISTENERS
    // ============================================
    clearButton.addEventListener('click', () => {
        window.openModal(clearModal);
    });

    cancelClear.addEventListener('click', () => {
        if (!clearModal.classList.contains('closing')) {
            window.closeClearModal();
        }
    });

    confirmClear.addEventListener('click', () => {
        window.closeClearModal();
        setTimeout(() => window.clearConversation(), 150);
    });

    clearModal.addEventListener('click', (e) => {
        if (e.target === clearModal && !clearModal.classList.contains('closing')) {
            window.closeClearModal();
        }
    });

    // ============================================
    // CONFIRMATION MODAL EVENT LISTENERS
    // ============================================
    confirmClearAll.addEventListener('click', () => {
        window.resetConfirmationButton();
        window.openModal(confirmationModal);
        
        setTimeout(() => {
            window.closeClearModal();
        }, 50);
    });

    cancelConfirmation.addEventListener('click', (e) => {
        if (window.isCountdownActive) {
            e.stopPropagation();
            e.preventDefault();
            return;
        }
        
        if (!confirmationModal.classList.contains('closing')) {
            window.resetConfirmationButton();
            window.closeConfirmationModal();
        }
    });

    confirmDeletion.addEventListener('click', window.mainClickHandler);
    confirmDeletion.setAttribute('data-handler-attached', 'true');

    confirmationModal.addEventListener('click', (e) => {
        if (e.target === confirmationModal) {
            if (window.isCountdownActive) {
                e.stopPropagation();
                e.preventDefault();
                return;
            }
            
            if (!confirmationModal.classList.contains('closing')) {
                window.closeConfirmationModal();
            }
        }
    });

    // ============================================
    // EXPORT MODAL EVENT LISTENERS
    // ============================================
    exportButton.addEventListener('click', () => {
        window.openModal(exportModal);
        window.buildExportPreview();
        setTimeout(() => window.setupExpandTooltip(), 100);
    });

    cancelExport.addEventListener('click', () => {
        if (!exportModal.classList.contains('closing')) {
            window.closeExportModal();
        }
    });

    confirmExport.addEventListener('click', () => window.exportConversation());
    generateTitleButton.addEventListener('click', () => window.generateAITitle());

    exportModal.addEventListener('click', (e) => {
        if (e.target === exportModal && !exportModal.classList.contains('closing')) {
            window.closeExportModal();
        }
    });

    // ============================================
    // FULLSCREEN PREVIEW EVENT LISTENERS
    // ============================================
    expandPreviewButton.addEventListener('click', () => window.openFullscreenPreview());
    
    closeFullscreenButton.addEventListener('click', () => {
        if (!fullscreenPreview.classList.contains('closing')) {
            window.closeFullscreenPreview();
        }
    });

    fullscreenPreview.addEventListener('click', (e) => {
        if (e.target === fullscreenPreview && !fullscreenPreview.classList.contains('closing')) {
            window.closeFullscreenPreview();
        }
    });

    // ============================================
    // MASTER ESC HANDLER
    // ============================================
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            // Check modals in priority order (innermost to outermost)
            if (fullscreenPreview.classList.contains('show') && !fullscreenPreview.classList.contains('closing')) {
                e.preventDefault();
                e.stopPropagation();
                window.closeFullscreenPreview();
                return;
            }
            
            if (confirmationModal.classList.contains('show') && !confirmationModal.classList.contains('closing')) {
                if (window.isCountdownActive) {
                    e.preventDefault();
                    e.stopPropagation();
                    return;
                }
                e.preventDefault();
                e.stopPropagation();
                window.resetConfirmationButton();
                window.closeConfirmationModal();
                return;
            }
            
            if (exportModal.classList.contains('show') && !exportModal.classList.contains('closing')) {
                e.preventDefault();
                e.stopPropagation();
                window.closeExportModal();
                return;
            }
            
            if (clearModal.classList.contains('show') && !clearModal.classList.contains('closing')) {
                e.preventDefault();
                e.stopPropagation();
                window.closeClearModal();
                return;
            }
        }
    });

    // ============================================
    // INITIALIZATION
    // ============================================
    window.setupExportTooltip();
    window.setupClearTooltip();
    window.setupExpandTooltip();
    window.setupHomeTooltip();
    window.setupCounterTooltip();
    window.loadConversationHistory();

    setTimeout(() => window.scrollToBottom(), 100);
    setInterval(window.updateAllTimestamps, 10000);

    window.startMessageLimitCheck();

    // ============================================
    // CLEANUP ON PAGE UNLOAD
    // ============================================
    window.addEventListener('beforeunload', () => {
        if (window.messageLimitState.checkInterval) {
            clearInterval(window.messageLimitState.checkInterval);
        }
        window.stopCountdownTimer?.();
    });
});