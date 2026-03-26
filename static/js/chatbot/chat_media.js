// ============================================================================
// CHAT-MEDIA.JS - MEDIA SEARCH & DISPLAY
// ============================================================================
// Handles YouTube video search, image search, and media result display
// ============================================================================


/**
 * ✅ Decode HTML entities in text
 */
function decodeHTMLEntities(text) {
    if (!text) return '';

    const textarea = document.createElement('textarea');
    textarea.innerHTML = text;
    return textarea.value;
}

/**
 * Detect if user is asking for media (videos or images)
 */
function detectMediaRequest(userMessage) {
    const msgLower = userMessage.toLowerCase();

    // Video request patterns - UNIVERSAL coverage
    const videoPatterns = [
        /show me (some |any )?videos?/,
        /find (me )?(some |any )?videos?/,
        /recommend (some |any )?videos?/,
        /can you (find|show|recommend|give me|send me|share) (some |any )?videos?/,
        /do you have (any |some )?videos?/,
        /(got|have) (any |some )?videos? (i can watch|to watch|about|on|for)/,
        /(got|have) (any )?video recommendations?/,
        /videos? (i can watch|to watch|about|on|for) /,
        /what videos? (should|can|do you recommend|would help) /,
        /(any |some )?videos? (about|on|for|to) /
    ];

    // Image request patterns - UNIVERSAL coverage
    const imagePatterns = [
        /show me (a |an |some )?((picture|image|photo)s?|pic)/,
        /find (me )?(a |an |some )?((picture|image|photo)s?|pic)/,
        /can you (find|show|send|share) (me )?(a |an |some )?((picture|image|photo)s?|pic)/,
        /do you have (any |some |a |an )?((picture|image|photo)s?|pic)/,
        /(got|have) (any |some |a |an )?((picture|image|photo)s?|pic)/,
        /send (me )?(a |an |some )?((picture|image|photo)s?|pic)/,
        /((picture|image|photo)s?|pic) (of|about) /
    ];

    if (videoPatterns.some(pattern => pattern.test(msgLower))) {
        const query = msgLower
            .replace(/^(show me|find me|recommend|can you|got|have|what|send me)\s+/i, '')
            .replace(/(some |any )?(videos?|video recommendations?)/i, '')
            .replace(/(about|on|of|should|can i watch)/gi, '')
            .trim();

        return { type: 'video', query };
    }

    if (imagePatterns.some(pattern => pattern.test(msgLower))) {
        const query = msgLower
            .replace(/^(show me|find me|can you|got|have|send me)\s+/i, '')
            .replace(/(a |an |some )?(picture|image|photo|pic)s?/i, '')
            .replace(/(of|about)/gi, '')
            .trim();

        return { type: 'image', query };
    }

    return null;
}

/**
 * Search for media (videos or images)
 */
async function searchMedia(query, mediaType, count = 3) {
    try {
        const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || window.getCookie('csrftoken');

        const response = await fetch('/chat/api/media/search/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken,
            },
            body: JSON.stringify({
                query: query,
                media_type: mediaType,
                count: count
            }),
        });

        const data = await response.json();

        if (data.success) {
            return data.results;
        } else {
            console.error('Media search failed:', data.error);
            return null;
        }
    } catch (error) {
        console.error('Error searching media:', error);
        return null;
    }
}

/**
 * Extract topic from user query for media search
 */
function extractTopicFromQuery(query) {
    let topic = query.toLowerCase()
        .replace(/^(hello|hi|hey|yo)[,.]?\s*/i, '')
        .replace(/^i'?m (feeling |really |very |so )?(depressed|sad|hopeless|stressed|anxious|worried|down|frustrated)[,.]?\s*/i, '')
        .replace(/^(can you|could you|please|do you have)\s*/i, '')
        .replace(/\b(show me|find me|recommend|give me|send me|share|looking for)\s+(some |any )?(videos?|images?|pics?|pictures?|photos?)\s+(about|on|of|for|to|how to|that)\s*/i, '')
        .replace(/\?+$/, '')
        .replace(/\bmy\b/gi, '')
        .trim();

    if (!topic || topic.length < 3) {
        const aboutMatch = query.match(/(?:about|on|for|to improve|how to)\s+(.+?)(?:\?|$)/i);
        if (aboutMatch) {
            topic = aboutMatch[1].trim();
        } else {
            const words = query.split(' ').slice(-5);
            topic = words.join(' ').replace(/[?.!,]/g, '');
        }
    }

    topic = topic.replace(/^(the |a |an |some |any )/i, '');
    return topic || 'this topic';
}

/**
 * Format YouTube results as structured data
 */
function formatYouTubeResults(videos, query) {
    if (!videos || videos.length === 0) {
        const topic = extractTopicFromQuery(query);
        return {
            type: 'text',
            content: `I couldn't find any videos about "${topic}". Try searching on YouTube directly: https://www.youtube.com/results?search_query=${encodeURIComponent(topic)}`
        };
    }

    // ✅ Intro/outro now come from backend LLM - minimal fallback for client-side only
    return {
        type: 'media',
        intro: "Here are some videos:",  // Minimal fallback
        videos: videos.map((video, index) => ({
            number: index + 1,
            title: decodeHTMLEntities(video.title),
            url: video.url,
            videoId: video.video_id,
            channel: decodeHTMLEntities(video.channel_title),
            description: video.description ? decodeHTMLEntities(video.description.substring(0, 150)) + '...' : 'Click to watch this video.'
        })),
        outro: "Let me know if you want more!"
    };
}

/**
 * Format image results as structured data (matches video structure)
 */
function formatImageResults(images, query) {
    if (!images || images.length === 0) {
        const topic = extractTopicFromQuery(query);
        return {
            type: 'text',
            content: `I couldn't find any images about "${topic}". Try searching on Google Images: https://www.google.com/search?tbm=isch&q=${encodeURIComponent(topic)}`
        };
    }

    const intro = "Here is an image:";
    const outro = "Let me know if you want more!";

    return {
        type: 'media',
        intro: intro,
        images: images.map((image, index) => ({
            number: index + 1,
            alt: decodeHTMLEntities(image.alt || topic),
            url: image.url,
            photographer: decodeHTMLEntities(image.photographer || 'Unknown'),
            photographer_url: image.photographer_url || ''
        })),
        outro: outro
    };
}

/**
 * Create empty message element (for manual animation)
 */
function createMessageElement(sender) {
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
    timestampDiv.textContent = window.formatTimestamp(timestampValue);

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
        avatarDiv.innerHTML = window.createUserAvatar();
        messageDiv.appendChild(messageBody);
        messageDiv.appendChild(avatarDiv);
    }

    return messageDiv;
}

/**
 * ✅ NEW: Create video card (no longer referenced but defined for safety)
 */
function createVideoCard(video, index) {
    // This function is now handled by renderVideoItem in chat_messages.js
    // Keeping it defined to prevent errors
    console.warn('createVideoCard is deprecated, use renderVideoItem instead');
    return '';
}

/**
 * ✅ NEW: Create image card (no longer referenced but defined for safety)
 */
function createImageCard(image, index) {
    // This function is now handled by renderImageItem in chat_messages.js
    // Keeping it defined to prevent errors
    console.warn('createImageCard is deprecated, use renderImageItem instead');
    return '';
}

/**
 * ✅ NEW: Safe text typing function (previously missing)
 */
async function typeTextSafe(element, text, delay = 20) {
    for (let i = 0; i <= text.length; i++) {
        element.textContent = text.substring(0, i);
        if (window.scrollToBottom) window.scrollToBottom();
        await new Promise(resolve => setTimeout(resolve, delay));
    }
}

/**
 * Convert markdown to HTML with media support
 */
function convertMarkdownToHTML(text) {
    if (!text) return '';

    text = convertYouTubeLinks(text);

    text = text.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (match, alt, url) => {
        return `<img src="${url}" alt="${alt}" class="message-image" loading="lazy" onclick="openImageModal('${url}', '${alt}')">`;
    });

    text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, linkText, url) => {
        return `<a href="${url}" class="message-link" target="_blank" rel="noopener noreferrer">${linkText}</a>`;
    });

    text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    text = text.replace(/\_([^_]+)\_/g, '<em>$1</em>');
    text = text.replace(/\n/g, '<br>');

    return text;
}

/**
 * Convert YouTube URLs to rich embeds with thumbnails
 */
function convertYouTubeLinks(text) {
    const youtubeRegex = /https?:\/\/(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/g;

    return text.replace(youtubeRegex, (match, _p1, _p2, videoId) => {
        const thumbnailUrl = `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`;
        const watchUrl = `https://www.youtube.com/watch?v=${videoId}`;

        return `
            <a href="${watchUrl}" target="_blank" class="youtube-embed" rel="noopener noreferrer">
                <img src="${thumbnailUrl}" alt="YouTube video thumbnail" class="youtube-thumbnail">
                <div class="youtube-play-button">
                    <svg width="68" height="48" viewBox="0 0 68 48">
                        <path d="M66.52,7.74c-0.78-2.93-2.49-5.41-5.42-6.19C55.79,.13,34,0,34,0S12.21,.13,6.9,1.55 C3.97,2.33,2.27,4.81,1.48,7.74C0.06,13.05,0,24,0,24s0.06,10.95,1.48,16.26c0.78,2.93,2.49,5.41,5.42,6.19 C12.21,47.87,34,48,34,48s21.79-0.13,27.1-1.55c2.93-0.78,4.64-3.26,5.42-6.19C67.94,34.95,68,24,68,24S67.94,13.05,66.52,7.74z" fill="#f00"></path>
                        <path d="M 45,24 27,14 27,34" fill="#fff"></path>
                    </svg>
                </div>
            </a>
        `;
    });
}

/**
 * ✅ FIXED: Open image in full-screen modal with fade animations and proper X button
 */
function openImageModal(src, alt) {
    const modal = document.createElement('div');
    modal.className = 'image-modal';
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.9);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        opacity: 0;
        transition: opacity 0.3s ease-in-out;
    `;
    
    modal.innerHTML = `
        <div class="image-modal-content" style="position: relative; max-width: 90%; max-height: 90%; display: flex; align-items: center; justify-content: center;">
            <span class="image-modal-close" style="
                position: absolute;
                top: 0;
                right: 20px;
                font-size: 40px;
                font-weight: bold;
                color: white;
                cursor: pointer;
                z-index: 10001;
                transition: color 0.2s;
                user-select: none;
            " onmouseover="this.style.color='#ccc'" onmouseout="this.style.color='white'">&times;</span>
            <img src="${src}" alt="${alt || 'Full size image'}" style="max-width: 100%; max-height: 90vh; object-fit: contain; border-radius: 8px;">
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Fade in
    setTimeout(() => {
        modal.style.opacity = '1';
    }, 10);
    
    // Close button handler with fade out
    const closeBtn = modal.querySelector('.image-modal-close');
    const closeModal = () => {
        modal.style.opacity = '0';
        setTimeout(() => {
            modal.remove();
        }, 300); // Wait for fade-out animation
    };
    
    closeBtn.addEventListener('click', closeModal);

    // Click outside to close (with fade out)
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeModal();
        }
    });

    // ESC key to close (with fade out)
    const escHandler = (e) => {
        if (e.key === 'Escape') {
            closeModal();
            document.removeEventListener('keydown', escHandler);
        }
    };
    document.addEventListener('keydown', escHandler);
}

// ============================================================================
// ✅ EXPOSE ALL FUNCTIONS GLOBALLY
// ============================================================================

window.detectMediaRequest = detectMediaRequest;
window.searchMedia = searchMedia;
window.formatYouTubeResults = formatYouTubeResults;
window.formatImageResults = formatImageResults;
window.createMessageElement = createMessageElement;
window.extractTopicFromQuery = extractTopicFromQuery;
window.createVideoCard = createVideoCard;
window.createImageCard = createImageCard;
window.typeTextSafe = typeTextSafe;
window.decodeHTMLEntities = decodeHTMLEntities;
window.openImageModal = openImageModal;