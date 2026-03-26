document.addEventListener('DOMContentLoaded', function() {
    const startButton = document.getElementById('startConversation');
    
    if (startButton) {
        startButton.addEventListener('click', function() {
            window.location.href = '/chat/';
        });
    }
    
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
    
    setupMessages();
});