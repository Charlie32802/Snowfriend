document.addEventListener('DOMContentLoaded', () => {
    // ============================================
    // DOM ELEMENT REFERENCES
    // ============================================
    const termsOfServiceModal = document.getElementById('termsOfServiceModal');
    const closeTermsModal = document.getElementById('closeTermsModal');
    const closeTermsButton = document.getElementById('closeTermsButton');

    // ============================================
    // MODAL FUNCTIONS
    // ============================================

    const openTermsModal = () => {
        // First set display to flex
        termsOfServiceModal.style.display = 'flex';
        
        // Force reflow to ensure display change is applied
        termsOfServiceModal.offsetHeight;
        
        // Then add show class for animation in next frame
        requestAnimationFrame(() => {
            termsOfServiceModal.classList.add('show');
            document.documentElement.classList.add('modal-open');
            document.body.classList.add('modal-open');
        });
    };

    const closeTermsModalFunc = (keepModalOpen = false) => {
        termsOfServiceModal.classList.add('closing');
        setTimeout(() => {
            termsOfServiceModal.classList.remove('show', 'closing');
            termsOfServiceModal.style.display = 'none';
            
            // Only remove modal-open class if we're not transitioning to another modal
            if (!keepModalOpen) {
                document.documentElement.classList.remove('modal-open');
                document.body.classList.remove('modal-open');
            }
        }, 300);
    };

    // ============================================
    // MODAL TRANSITIONS
    // ============================================

    const transitionToPrivacyModal = () => {
        // Close terms modal but keep modal-open class active
        closeTermsModalFunc(true);
        
        // Wait for close animation to complete, then open privacy modal
        setTimeout(() => {
            if (typeof window.openPrivacyModal === 'function') {
                window.openPrivacyModal();
            } else {
                console.error('openPrivacyModal function not found');
            }
        }, 300);
    };

    const transitionToFeedbackModal = () => {
        // Close terms modal but keep modal-open class active
        closeTermsModalFunc(true);
        
        // Wait for close animation to complete, then open feedback modal
        setTimeout(() => {
            if (typeof window.openFeedbackModal === 'function') {
                window.openFeedbackModal();
            } else {
                console.error('openFeedbackModal function not found');
            }
        }, 300);
    };

    // ============================================
    // EVENT LISTENERS
    // ============================================

    // Close button (X)
    closeTermsModal.addEventListener('click', () => closeTermsModalFunc());

    // Close button (I Accept)
    closeTermsButton.addEventListener('click', () => closeTermsModalFunc());

    // Click outside modal to close
    termsOfServiceModal.addEventListener('click', (e) => {
        if (e.target === termsOfServiceModal) {
            closeTermsModalFunc();
        }
    });

    // ESC key to close
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && termsOfServiceModal.classList.contains('show')) {
            closeTermsModalFunc();
        }
    });

    // ============================================
    // MODAL TRANSITION LINKS - Document Level Event Listeners
    // ============================================

    // Handle all clicks on links that should transition to other modals
    document.addEventListener('click', (e) => {
        const target = e.target.closest('a.terms-link, a.privacy-link');
        
        if (target) {
            // Check if this is a Privacy Policy link
            if (target.textContent.includes('Privacy Policy')) {
                e.preventDefault();
                e.stopPropagation();
                transitionToPrivacyModal();
                return;
            }
            
            // Check if this is a feedback link
            if (target.textContent.includes('Share your feedback')) {
                e.preventDefault();
                e.stopPropagation();
                transitionToFeedbackModal();
                return;
            }
        }
    });

    // ============================================
    // EXPOSE GLOBAL FUNCTIONS
    // ============================================

    // Make functions available globally
    window.openTermsModal = openTermsModal;
    window.closeTermsModal = closeTermsModalFunc;
    window.transitionToPrivacyModal = transitionToPrivacyModal;
    window.transitionToFeedbackModal = transitionToFeedbackModal;
});