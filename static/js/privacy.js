document.addEventListener('DOMContentLoaded', () => {
    // ============================================
    // DOM ELEMENT REFERENCES
    // ============================================
    const privacyPolicyModal = document.getElementById('privacyPolicyModal');
    const closePrivacyModal = document.getElementById('closePrivacyModal');
    const closePrivacyButton = document.getElementById('closePrivacyButton');

    // ============================================
    // MODAL FUNCTIONS
    // ============================================

    const openPrivacyModal = () => {
        // First set display to flex
        privacyPolicyModal.style.display = 'flex';
        
        // Force reflow to ensure display change is applied
        privacyPolicyModal.offsetHeight;
        
        // Then add show class for animation in next frame
        requestAnimationFrame(() => {
            privacyPolicyModal.classList.add('show');
            document.documentElement.classList.add('modal-open');
            document.body.classList.add('modal-open');
        });
    };

    const closePrivacyModalFunc = (keepModalOpen = false) => {
        privacyPolicyModal.classList.add('closing');
        setTimeout(() => {
            privacyPolicyModal.classList.remove('show', 'closing');
            privacyPolicyModal.style.display = 'none';
            
            // Only remove modal-open class if we're not transitioning to another modal
            if (!keepModalOpen) {
                document.documentElement.classList.remove('modal-open');
                document.body.classList.remove('modal-open');
            }
        }, 300);
    };

    // ============================================
    // TRANSITION TO FEEDBACK MODAL
    // ============================================

    const transitionToFeedbackModal = () => {
        // Close privacy modal but keep modal-open class active
        closePrivacyModalFunc(true);
        
        // Wait for close animation to complete, then open feedback modal
        setTimeout(() => {
            if (typeof window.openFeedbackModal === 'function') {
                window.openFeedbackModal();
            }
        }, 300);
    };

    // ============================================
    // EVENT LISTENERS
    // ============================================

    // Close button (X)
    closePrivacyModal.addEventListener('click', () => closePrivacyModalFunc());

    // Close button (I Understand)
    closePrivacyButton.addEventListener('click', () => closePrivacyModalFunc());

    // Click outside modal to close
    privacyPolicyModal.addEventListener('click', (e) => {
        if (e.target === privacyPolicyModal) {
            closePrivacyModalFunc();
        }
    });

    // ESC key to close
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && privacyPolicyModal.classList.contains('show')) {
            closePrivacyModalFunc();
        }
    });

    // ============================================
    // EXPOSE GLOBAL FUNCTIONS
    // ============================================

    // Make functions available globally
    window.openPrivacyModal = openPrivacyModal;
    window.closePrivacyModal = closePrivacyModalFunc;
    window.transitionToFeedbackModal = transitionToFeedbackModal;
});