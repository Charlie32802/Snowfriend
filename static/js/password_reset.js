// Password Reset Modal Functionality
document.addEventListener('DOMContentLoaded', () => {
    const passwordResetModal = document.getElementById('passwordResetModal');
    const passwordResetForm = document.getElementById('passwordResetForm');
    const cancelResetButton = document.getElementById('cancelResetButton');
    const sendResetButton = document.getElementById('sendResetButton');
    const resetEmailInput = document.getElementById('resetEmail');
    const resetEmailError = document.getElementById('resetEmailError');

    // Open password reset modal function - CONSISTENT WITH FEEDBACK MODAL
    window.openPasswordResetModal = () => {
        // First set display to flex
        passwordResetModal.style.display = 'flex';
        
        // Force reflow to ensure display change is applied
        passwordResetModal.offsetHeight;
        
        // Then add show class for animation in next frame
        requestAnimationFrame(() => {
            passwordResetModal.classList.add('show');
            document.documentElement.classList.add('modal-open');
            document.body.classList.add('modal-open');
            resetEmailInput.focus();
        });
    };

    // Close password reset modal
    const closePasswordResetModal = () => {
        passwordResetModal.classList.add('closing');
        setTimeout(() => {
            passwordResetModal.classList.remove('show', 'closing');
            passwordResetModal.style.display = 'none';
            document.documentElement.classList.remove('modal-open');
            document.body.classList.remove('modal-open');
            passwordResetForm.reset();
            clearError();
            sendResetButton.classList.remove('loading');
        }, 300);
    };

    // Cancel button
    cancelResetButton.addEventListener('click', closePasswordResetModal);

    // Close on outside click
    passwordResetModal.addEventListener('click', (e) => {
        if (e.target === passwordResetModal) {
            closePasswordResetModal();
        }
    });

    // Close on ESC key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && passwordResetModal.classList.contains('show')) {
            closePasswordResetModal();
        }
    });

    // Email validation
    const validateEmail = (email) => {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email.toLowerCase());
    };

    // Show error
    const showError = (message) => {
        resetEmailInput.classList.add('error');
        resetEmailError.textContent = message;
        resetEmailError.classList.add('visible');
    };

    // Clear error
    const clearError = () => {
        resetEmailInput.classList.remove('error');
        resetEmailError.textContent = '';
        resetEmailError.classList.remove('visible');
    };

    // Clear error on input
    resetEmailInput.addEventListener('input', clearError);

    // Show notification
    const showNotification = (message, type = 'success') => {
        let container = document.querySelector('.notification-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'notification-container';
            document.body.appendChild(container);
        }

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

        container.appendChild(notification);

        // Auto-dismiss after 6 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(() => {
                notification.remove();
            }, 300);
        }, 6000);

        // Manual close
        const closeBtn = notification.querySelector('.notification-close');
        closeBtn.addEventListener('click', () => {
            notification.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(() => {
                notification.remove();
            }, 300);
        });
    };

    // Form submission
    passwordResetForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        clearError();

        const email = resetEmailInput.value.trim();

        // Validate email
        if (!email) {
            showError('Please enter your email address');
            return;
        }

        if (!validateEmail(email)) {
            showError('Please enter a valid email address');
            return;
        }

        // Show loading state
        sendResetButton.classList.add('loading');

        try {
            // Get CSRF token
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

            // Send request to backend
            const response = await fetch('/accounts/password-reset/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': csrfToken
                },
                body: new URLSearchParams({
                    'email': email
                })
            });

            const data = await response.json();

            // Remove loading state
            sendResetButton.classList.remove('loading');

            if (data.success) {
                // Close modal
                closePasswordResetModal();

                // Show success notification
                showNotification('Password reset link has been sent to your email. Please check your inbox.', 'success');
            } else {
                // Show error
                showError(data.message || 'An error occurred. Please try again.');
            }
        } catch (error) {
            console.error('Password reset error:', error);
            sendResetButton.classList.remove('loading');
            showError('Unable to send reset link. Please try again later.');
        }
    });
});