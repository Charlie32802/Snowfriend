// static/js/landing.js
document.addEventListener('DOMContentLoaded', () => {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, observerOptions);

    const featureCards = document.querySelectorAll('.feature-card');
    featureCards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = `opacity 0.6s ease ${index * 0.15}s, transform 0.6s ease ${index * 0.15}s`;
        observer.observe(card);
    });

    const style = document.createElement('style');
    style.textContent = `
        .feature-card.visible {
            opacity: 1 !important;
            transform: translateY(0) !important;
        }
    `;
    document.head.appendChild(style);

    const buttons = document.querySelectorAll('.button-primary, .nav-button');
    buttons.forEach(button => {
        button.addEventListener('click', (e) => {
            button.style.transform = 'scale(0.97)';
            setTimeout(() => {
                button.style.transform = '';
            }, 100);
        });
    });

    let lastScroll = 0;
    const header = document.querySelector('.header');
    
    window.addEventListener('scroll', () => {
        const currentScroll = window.pageYOffset;
        
        if (currentScroll <= 0) {
            header.style.transform = 'translateY(0)';
        } else if (currentScroll > lastScroll && currentScroll > 100) {
            header.style.transform = 'translateY(-100%)';
        } else if (currentScroll < lastScroll) {
            header.style.transform = 'translateY(0)';
        }
        
        lastScroll = currentScroll;
    });

    header.style.transition = 'transform 0.3s ease';
});