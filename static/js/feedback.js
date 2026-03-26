document.addEventListener('DOMContentLoaded', () => {
    // ============================================
    // DOM ELEMENT REFERENCES
    // ============================================
    const feedbackModal = document.getElementById('feedbackModal');
    const feedbackForm = document.getElementById('feedbackForm');
    const cancelFeedback = document.getElementById('cancelFeedback');
    const submitFeedback = document.getElementById('submitFeedback');
    const feedbackNotificationContainer = document.getElementById('feedbackNotificationContainer');

    // Star rating elements
    const starRating = document.getElementById('starRating');
    const ratingText = document.getElementById('ratingText');
    const stars = starRating.querySelectorAll('.star');
    const ratingTooltip = document.getElementById('ratingTooltip');

    // Message elements
    const feedbackMessage = document.getElementById('feedbackMessage');
    const charCount = document.getElementById('charCount');

    // Image upload elements
    const imageUploadArea = document.getElementById('imageUploadArea');
    const feedbackImage = document.getElementById('feedbackImage');
    const uploadPrompt = document.getElementById('uploadPrompt');
    const imagePreview = document.getElementById('imagePreview');
    const previewImg = document.getElementById('previewImg');
    const removeImage = document.getElementById('removeImage');

    // Loading spinner
    const submitSpinner = document.getElementById('submitSpinner');

    // Tooltip timeout reference
    let tooltipTimeout = null;

    // ============================================
    // MODAL FUNCTIONS
    // ============================================

    const openFeedbackModal = () => {
        // First set display to flex
        feedbackModal.style.display = 'flex';
        
        // Force reflow to ensure display change is applied
        feedbackModal.offsetHeight;
        
        // Then add show class for animation in next frame
        requestAnimationFrame(() => {
            feedbackModal.classList.add('show');
            // Ensure modal-open class is always applied, even if transitioning from another modal
            document.documentElement.classList.add('modal-open');
            document.body.classList.add('modal-open');
        });
    };

    const closeFeedbackModal = () => {
        feedbackModal.classList.add('closing');
        setTimeout(() => {
            feedbackModal.classList.remove('show', 'closing');
            feedbackModal.style.display = 'none';
            // Remove modal-open class when closing
            document.documentElement.classList.remove('modal-open');
            document.body.classList.remove('modal-open');
            resetForm();
        }, 300);
    };

    const resetForm = () => {
        feedbackForm.reset();
        ratingText.textContent = 'Select a rating';
        ratingText.classList.remove('selected');
        charCount.textContent = '0';
        charCount.parentElement.classList.remove('limit-warning', 'limit-reached');
        clearImagePreview();
        submitFeedback.classList.remove('loading');
        hideRatingTooltip(); // Hide tooltip on form reset
    };

    // ============================================
    // RATING TOOLTIP FUNCTIONS
    // ============================================

    const showRatingTooltip = () => {
        // Clear any existing timeout
        if (tooltipTimeout) {
            clearTimeout(tooltipTimeout);
        }

        // Show the tooltip
        ratingTooltip.classList.add('show');

        // Auto-hide after 3.5 seconds
        tooltipTimeout = setTimeout(() => {
            hideRatingTooltip();
        }, 3500);
    };

    const hideRatingTooltip = () => {
        ratingTooltip.classList.remove('show');
        if (tooltipTimeout) {
            clearTimeout(tooltipTimeout);
            tooltipTimeout = null;
        }
    };

    // ============================================
    // STAR RATING FUNCTIONALITY
    // ============================================

    const ratingMessages = {
        5: '⭐ Excellent!',
        4: '⭐ Very Good',
        3: '⭐ Good',
        2: '⭐ Fair',
        1: '⭐ Needs Improvement'
    };

    stars.forEach(star => {
        star.addEventListener('click', (e) => {
            const rating = e.currentTarget.getAttribute('data-value');
            ratingText.textContent = ratingMessages[rating];
            ratingText.classList.add('selected');
            
            // Hide tooltip when user selects a rating
            hideRatingTooltip();
        });

        star.addEventListener('mouseenter', (e) => {
            const rating = e.currentTarget.getAttribute('data-value');
            ratingText.textContent = ratingMessages[rating];
        });
    });

    starRating.addEventListener('mouseleave', () => {
        const selectedRating = starRating.querySelector('input[type="radio"]:checked');
        if (selectedRating) {
            ratingText.textContent = ratingMessages[selectedRating.value];
        } else {
            ratingText.textContent = 'Select a rating';
            ratingText.classList.remove('selected');
        }
    });

    // ============================================
    // CHARACTER COUNTER
    // ============================================

    feedbackMessage.addEventListener('input', () => {
        const count = feedbackMessage.value.length;
        charCount.textContent = count;

        const counterElement = charCount.parentElement;
        counterElement.classList.remove('limit-warning', 'limit-reached');

        if (count >= 1000) {
            counterElement.classList.add('limit-reached');
        } else if (count >= 900) {
            counterElement.classList.add('limit-warning');
        }
    });

    // ============================================
    // IMAGE UPLOAD FUNCTIONALITY
    // ============================================

    imageUploadArea.addEventListener('click', (e) => {
        if (e.target !== removeImage && !removeImage.contains(e.target)) {
            feedbackImage.click();
        }
    });

    // Drag and drop
    imageUploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        imageUploadArea.classList.add('dragover');
    });

    imageUploadArea.addEventListener('dragleave', () => {
        imageUploadArea.classList.remove('dragover');
    });

    imageUploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        imageUploadArea.classList.remove('dragover');

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleImageUpload(files[0]);
        }
    });

    feedbackImage.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleImageUpload(e.target.files[0]);
        }
    });

    const handleImageUpload = (file) => {
        // Validate file type
        if (!file.type.startsWith('image/')) {
            showNotification('Please upload an image file (PNG, JPG, GIF)', 'error');
            return;
        }

        // Validate file size (5MB)
        if (file.size > 5 * 1024 * 1024) {
            showNotification('Image size must be less than 5MB', 'error');
            return;
        }

        // Show preview
        const reader = new FileReader();
        reader.onload = (e) => {
            previewImg.src = e.target.result;
            uploadPrompt.style.display = 'none';
            imagePreview.style.display = 'flex';
        };
        reader.readAsDataURL(file);
    };

    removeImage.addEventListener('click', (e) => {
        e.stopPropagation();
        clearImagePreview();
    });

    const clearImagePreview = () => {
        feedbackImage.value = '';
        previewImg.src = '';
        uploadPrompt.style.display = 'flex';
        imagePreview.style.display = 'none';
    };

    // ============================================
    // FORM SUBMISSION
    // ============================================

    feedbackForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Check if a rating has been selected
        const selectedRating = starRating.querySelector('input[type="radio"]:checked');
        if (!selectedRating) {
            // Show the rating tooltip
            showRatingTooltip();
            
            // Scroll to the star rating section smoothly
            const feedbackSection = document.querySelector('.feedback-section:has(.star-rating)');
            if (feedbackSection) {
                feedbackSection.scrollIntoView({ 
                    behavior: 'smooth', 
                    block: 'center' 
                });
            }
            
            // Prevent form submission
            return;
        }

        // Get form data
        const formData = new FormData(feedbackForm);

        // Show loading state
        submitFeedback.classList.add('loading');

        try {
            const response = await fetch('/feedback/api/submit/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                },
            });

            const data = await response.json();

            if (data.success) {
                closeFeedbackModal();
                // Show notification after modal closes
                setTimeout(() => {
                    showNotification('Thank you for your feedback!', 'success');
                }, 300);
            } else {
                showNotification(data.error || 'Failed to submit feedback. Please try again.', 'error');
                submitFeedback.classList.remove('loading');
            }
        } catch (error) {
            console.error('Error submitting feedback:', error);
            showNotification('Network error. Please check your connection and try again.', 'error');
            submitFeedback.classList.remove('loading');
        }
    });

    // ============================================
    // EVENT LISTENERS
    // ============================================

    cancelFeedback.addEventListener('click', () => closeFeedbackModal());

    feedbackModal.addEventListener('click', (e) => {
        if (e.target === feedbackModal) {
            closeFeedbackModal();
        }
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && feedbackModal.classList.contains('show')) {
            closeFeedbackModal();
        }
    });

    // ============================================
    // NOTIFICATION SYSTEM
    // ============================================

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

        feedbackNotificationContainer.appendChild(notification);

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

    // ============================================
    // UTILITY FUNCTIONS
    // ============================================

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

    // ============================================
    // EXPOSE GLOBAL FUNCTION
    // ============================================

    // Make openFeedbackModal available globally for the Contact link
    window.openFeedbackModal = openFeedbackModal;
});