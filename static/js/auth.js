document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');

    const validateEmail = (email) => {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email.toLowerCase());
    };

    const showError = (inputId, message) => {
        const input = document.getElementById(inputId);
        const error = document.getElementById(`${inputId}Error`);
        
        if (input && error) {
            input.classList.add('error');
            error.textContent = message;
            error.classList.add('visible');
        }
    };

    const clearError = (inputId) => {
        const input = document.getElementById(inputId);
        const error = document.getElementById(`${inputId}Error`);
        
        if (input && error) {
            input.classList.remove('error');
            error.textContent = '';
            error.classList.remove('visible');
        }
    };

    const clearAllErrors = (form) => {
        const inputs = form.querySelectorAll('.form-input');
        inputs.forEach(input => {
            clearError(input.id);
        });
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

    // Home icon and tooltip functionality with 200ms delay
    const setupHomeIcon = () => {
        const homeIcon = document.querySelector('.home-icon');
        if (!homeIcon) return;

        const tooltip = homeIcon.querySelector('.tooltip');
        let tooltipTimeout;
        let tooltipVisible = false;

        // Show tooltip after 200ms delay
        homeIcon.addEventListener('mouseenter', () => {
            if (tooltip && !tooltipVisible) {
                tooltipTimeout = setTimeout(() => {
                    tooltip.classList.add('show');
                    tooltipVisible = true;
                }, 200); // 200ms delay
            }
        });

        // Hide tooltip immediately
        homeIcon.addEventListener('mouseleave', () => {
            if (tooltipTimeout) {
                clearTimeout(tooltipTimeout);
            }
            if (tooltip && tooltipVisible) {
                tooltip.classList.remove('show');
                tooltipVisible = false;
            }
        });

        // Also hide on click
        homeIcon.addEventListener('click', () => {
            if (tooltipTimeout) {
                clearTimeout(tooltipTimeout);
            }
            if (tooltip && tooltipVisible) {
                tooltip.classList.remove('show');
                tooltipVisible = false;
            }
        });

        // Touch events for mobile
        homeIcon.addEventListener('touchstart', (e) => {
            e.preventDefault();
            if (tooltip && !tooltipVisible) {
                tooltipTimeout = setTimeout(() => {
                    tooltip.classList.add('show');
                    tooltipVisible = true;
                }, 200);
            }
        });

        homeIcon.addEventListener('touchend', (e) => {
            e.preventDefault();
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

    // Fix links to not scroll to top
    const fixLinks = () => {
        // Fix "Already have an account?" and "Don't have an account?" links
        const authLinks = document.querySelectorAll('.link');
        authLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                // Save current scroll position
                const scrollPosition = window.scrollY;
                
                // Save position in sessionStorage so it persists across page loads
                sessionStorage.setItem('restoreScrollPosition', scrollPosition.toString());
            });
        });

        // Also fix the home icon link
        const homeLink = document.querySelector('.home-icon');
        if (homeLink) {
            homeLink.addEventListener('click', (e) => {
                // Save current scroll position for consistency
                const scrollPosition = window.scrollY;
                sessionStorage.setItem('restoreScrollPosition', scrollPosition.toString());
            });
        }
    };

    // Restore scroll position on page load
    const restoreScrollPosition = () => {
        const savedPosition = sessionStorage.getItem('restoreScrollPosition');
        if (savedPosition) {
            // Restore after a slight delay to ensure DOM is ready
            setTimeout(() => {
                window.scrollTo(0, parseInt(savedPosition, 10));
                sessionStorage.removeItem('restoreScrollPosition');
            }, 50);
        }
    };

    // Message close functionality
    const setupMessages = () => {
        const messages = document.querySelectorAll('.message');
        
        messages.forEach((message, index) => {
            // Auto-dismiss after 5 seconds
            setTimeout(() => {
                message.style.animation = 'slideOut 0.3s ease forwards';
                setTimeout(() => {
                    message.remove();
                }, 300);
            }, 5000 + (index * 100));
            
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

    // Initialize all functions
    setupPasswordToggles();
    setupHomeIcon();
    fixLinks();
    restoreScrollPosition();
    setupMessages();

    if (loginForm) {
        const inputs = loginForm.querySelectorAll('.form-input');
        const submitButton = document.getElementById('loginButton');
        
        inputs.forEach(input => {
            input.addEventListener('input', () => {
                clearError(input.id);
            });
        });

        // Show loading instantly on button click
        if (submitButton) {
            submitButton.addEventListener('click', (e) => {
                // Show loading immediately
                submitButton.classList.add('loading');
            });
        }

        loginForm.addEventListener('submit', (e) => {
            e.preventDefault();
            clearAllErrors(loginForm);
            
            const email = document.getElementById('email').value.trim();
            const password = document.getElementById('password').value;
            
            let isValid = true;

            if (!email) {
                showError('email', 'Please enter your email or username');
                isValid = false;
            }

            if (!password) {
                showError('password', 'Please enter your password');
                isValid = false;
            }

            if (isValid) {
                // Save scroll position before form submission
                sessionStorage.setItem('restoreScrollPosition', window.scrollY.toString());
                loginForm.submit();
            } else {
                // Remove loading if validation failed
                if (submitButton) {
                    submitButton.classList.remove('loading');
                }
            }
        });
    }

    if (registerForm) {
        const inputs = registerForm.querySelectorAll('.form-input');
        const submitButton = document.getElementById('registerButton');
        
        inputs.forEach(input => {
            input.addEventListener('input', () => {
                clearError(input.id);
            });
        });

        // Show loading instantly on button click
        if (submitButton) {
            submitButton.addEventListener('click', (e) => {
                // Show loading immediately
                submitButton.classList.add('loading');
            });
        }

        registerForm.addEventListener('submit', (e) => {
            e.preventDefault();
            clearAllErrors(registerForm);
            
            const fullname = document.getElementById('fullname').value.trim();
            const email = document.getElementById('email').value.trim();
            const password = document.getElementById('password').value;
            const confirmPassword = document.getElementById('confirmPassword').value;
            
            let isValid = true;

            if (!fullname) {
                showError('fullname', 'Please enter your full name');
                isValid = false;
            }

            if (!email) {
                showError('email', 'Please enter your email');
                isValid = false;
            } else if (!validateEmail(email)) {
                showError('email', 'Please enter a valid email address');
                isValid = false;
            }

            if (!password) {
                showError('password', 'Please enter a password');
                isValid = false;
            } else if (password.length < 8) {
                showError('password', 'Password must be at least 8 characters');
                isValid = false;
            }

            if (!confirmPassword) {
                showError('confirmPassword', 'Please confirm your password');
                isValid = false;
            } else if (password !== confirmPassword) {
                showError('confirmPassword', 'Passwords do not match');
                isValid = false;
            }

            if (isValid) {
                // Save scroll position before form submission
                sessionStorage.setItem('restoreScrollPosition', window.scrollY.toString());
                registerForm.submit();
            } else {
                // Remove loading if validation failed
                if (submitButton) {
                    submitButton.classList.remove('loading');
                }
            }
        });
    }
});