// Password Update Page - Matching Login/Register Functionality
document.addEventListener('DOMContentLoaded', () => {
    const passwordUpdateForm = document.getElementById('passwordUpdateForm');
    const updatePasswordButton = document.getElementById('updatePasswordButton');
    const newPasswordInput = document.getElementById('newPassword');
    const confirmPasswordInput = document.getElementById('confirmPassword');
    const newPasswordError = document.getElementById('newPasswordError');
    const confirmPasswordError = document.getElementById('confirmPasswordError');

    // Show error
    const showError = (inputElement, errorElement, message) => {
        inputElement.classList.add('error');
        errorElement.textContent = message;
        errorElement.classList.add('visible');
    };

    // Clear error
    const clearError = (inputElement, errorElement) => {
        inputElement.classList.remove('error');
        errorElement.textContent = '';
        errorElement.classList.remove('visible');
    };

    // Clear all errors
    const clearAllErrors = () => {
        if (newPasswordInput && newPasswordError) {
            clearError(newPasswordInput, newPasswordError);
        }
        if (confirmPasswordInput && confirmPasswordError) {
            clearError(confirmPasswordInput, confirmPasswordError);
        }
    };

    // Password toggle functionality
    const setupPasswordToggles = () => {
        const toggleButtons = document.querySelectorAll('.password-toggle');
        
        toggleButtons.forEach(button => {
            button.addEventListener('click', () => {
                const wrapper = button.closest('.password-wrapper');
                const input = wrapper.querySelector('input');
                const eyeOpen = button.querySelector('.eye-open');
                const eyeClosed = button.querySelector('.eye-closed');
                
                if (input.type === 'password') {
                    input.type = 'text';
                    eyeOpen.style.display = 'none';
                    eyeClosed.style.display = 'block';
                } else {
                    input.type = 'password';
                    eyeOpen.style.display = 'block';
                    eyeClosed.style.display = 'none';
                }
            });
        });
    };

    // Message close functionality
    const setupMessages = () => {
        const messages = document.querySelectorAll('.message');
        
        messages.forEach((message, index) => {
            // Auto-dismiss after 6 seconds
            setTimeout(() => {
                message.style.animation = 'slideOut 0.3s ease forwards';
                setTimeout(() => {
                    message.remove();
                }, 300);
            }, 6000 + (index * 100));
            
            // Manual close
            const closeBtn = message.querySelector('.message-close');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => {
                    message.style.animation = 'slideOut 0.3s ease forwards';
                    setTimeout(() => {
                        message.remove();
                    }, 300);
                });
            }
        });
        
        // Add slideOut animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes slideOut {
                from {
                    opacity: 1;
                    transform: translateX(0);
                }
                to {
                    opacity: 0;
                    transform: translateX(100%);
                }
            }
        `;
        if (!document.querySelector('style[data-messages]')) {
            style.setAttribute('data-messages', 'true');
            document.head.appendChild(style);
        }
    };

    // Initialize
    setupPasswordToggles();
    setupMessages();

    // Clear error on input
    if (newPasswordInput) {
        newPasswordInput.addEventListener('input', () => {
            if (newPasswordError) {
                clearError(newPasswordInput, newPasswordError);
            }
        });
    }

    if (confirmPasswordInput) {
        confirmPasswordInput.addEventListener('input', () => {
            if (confirmPasswordError) {
                clearError(confirmPasswordInput, confirmPasswordError);
            }
        });
    }

    // Show loading on button click
    if (updatePasswordButton) {
        updatePasswordButton.addEventListener('click', (e) => {
            // Loading will be shown after validation passes
            updatePasswordButton.classList.add('loading');
        });
    }

    // Form submission
    if (passwordUpdateForm) {
        passwordUpdateForm.addEventListener('submit', (e) => {
            e.preventDefault();
            clearAllErrors();

            const newPassword = newPasswordInput.value;
            const confirmPassword = confirmPasswordInput.value;

            let isValid = true;

            // Validate new password
            if (!newPassword) {
                showError(newPasswordInput, newPasswordError, 'Please enter a new password');
                isValid = false;
            } else if (newPassword.length < 8) {
                showError(newPasswordInput, newPasswordError, 'Password must be at least 8 characters');
                isValid = false;
            }

            // Validate confirm password
            if (!confirmPassword) {
                showError(confirmPasswordInput, confirmPasswordError, 'Please confirm your password');
                isValid = false;
            } else if (newPassword !== confirmPassword) {
                showError(confirmPasswordInput, confirmPasswordError, 'Passwords do not match');
                isValid = false;
            }

            if (isValid) {
                // Keep loading state and submit form
                passwordUpdateForm.submit();
            } else {
                // Remove loading if validation failed
                if (updatePasswordButton) {
                    updatePasswordButton.classList.remove('loading');
                }
            }
        });
    }
});