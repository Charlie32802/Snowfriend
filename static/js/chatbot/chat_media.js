// ============================================================================
// CHAT-MEDIA.JS - MEDIA SEARCH & DISPLAY (COMPLETE FIXED VERSION)
// ============================================================================
// Handles YouTube video search, image search, and media result display
// ✅ NO DUPLICATES - All media functions defined here
// ✅ REMOVED: showMediaLoading() - unused function removed
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

    const topic = extractTopicFromQuery(query);
    const isEmotional = /\b(depressed|hopeless|sad|stressed|anxious|worried|struggling|can'?t|help me|feeling bad|down)\b/i.test(query);

    const intro = isEmotional
        ? `I'm sorry you're going through this. Here are some videos about ${topic} that might help:`
        : `Here are some helpful videos about ${topic}:`;

    const outro = isEmotional
        ? "These videos might give you some guidance. I'm here if you need to talk more about it."
        : "Let me know if you want more specific recommendations!";

    return {
        type: 'media',
        intro: intro,
        videos: videos.map((video, index) => ({
            number: index + 1,
            title: decodeHTMLEntities(video.title),
            url: video.url,
            videoId: video.video_id,
            channel: decodeHTMLEntities(video.channel_title),
            description: video.description ? decodeHTMLEntities(video.description.substring(0, 150)) + '...' : 'Click to watch this video.'
        })),
        outro: outro
    };
}

/**
 * ✅ MAIN FUNCTION: Animate media results with typing + fade-in effects
 */
async function animateMediaResults(messageBody, data) {
    const contentDiv = messageBody.querySelector('.message-content');

    // 1. Type intro text
    await typeTextSafe(contentDiv, data.intro);
    contentDiv.innerHTML += '<br><br>';

    // 2. For each video: TYPE title, then fade in thumbnail
    for (let i = 0; i < data.videos.length; i++) {
        const video = data.videos[i];

        const videoNumber = video.number || (i + 1);
        const videoTitle = video.title || 'Untitled Video';

        // Type the video title as BOLD text
        const titleSpan = document.createElement('span');
        titleSpan.style.cssText = 'display:block;margin-bottom:2px;margin-top:0;font-weight:700;font-size:16px;line-height:1.2;';
        contentDiv.appendChild(titleSpan);

        await typeTextSafe(titleSpan, `${videoNumber}. ${videoTitle}`);

        // Create video card (thumbnail only)
        const videoCard = createVideoCard(video);
        if (videoCard) {
            contentDiv.appendChild(videoCard);

            // Fade in animation
            videoCard.style.opacity = '0';
            videoCard.style.transform = 'translateY(10px)';
            await new Promise(resolve => setTimeout(resolve, 100));

            videoCard.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            videoCard.style.opacity = '1';
            videoCard.style.transform = 'translateY(0)';
            await new Promise(resolve => setTimeout(resolve, 400));
        }

        // Add channel and description
        const detailsDiv = document.createElement('div');
        detailsDiv.style.cssText = 'margin-top:2px;margin-bottom:0;line-height:1.4;';
        contentDiv.appendChild(detailsDiv);

        const channelSpan = document.createElement('span');
        channelSpan.style.fontWeight = '700';
        detailsDiv.appendChild(channelSpan);
        await typeTextSafe(channelSpan, `By ${video.channel}`);

        detailsDiv.appendChild(document.createElement('br'));

        const descSpan = document.createElement('span');
        descSpan.style.fontWeight = '400';
        detailsDiv.appendChild(descSpan);
        await typeTextSafe(descSpan, video.description);

        if (i < data.videos.length - 1) {
            contentDiv.innerHTML += '<br>';
        }

        window.scrollToBottomIfNotScrolledUp();
    }

    // 3. Type outro text
    contentDiv.innerHTML += '<br><br>';
    await typeTextSafe(contentDiv, data.outro);
    window.scrollToBottomIfNotScrolledUp();
}

/**
 * ✅ Create video card element (thumbnail with play button)
 * This is the ONLY place this function should be defined
 */
function createVideoCard(video) {
    const card = document.createElement('div');
    card.className = 'video-result';

    // ✅ Handle both camelCase and snake_case
    const videoId = video.videoId || video.video_id || '';

    if (!videoId) {
        console.error('Video is missing ID:', video);
        return null;
    }

    const videoTitle = video.title || 'Untitled Video';
    const videoUrl = video.url || `https://www.youtube.com/watch?v=${videoId}`;
    const thumbnailUrl = `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`;

    card.setAttribute('data-video-id', videoId);
    card.setAttribute('data-video-url', videoUrl);
    card.setAttribute('data-video-title', videoTitle);

    card.innerHTML = `
        <a href="${videoUrl}" target="_blank" rel="noopener noreferrer" class="video-thumbnail-link">
            <div class="video-thumbnail-wrapper">
                <img src="${thumbnailUrl}" 
                     alt="${videoTitle}" 
                     class="video-thumbnail" 
                     loading="lazy"
                     onerror="this.src='https://via.placeholder.com/480x360?text=Video+Unavailable'">
                <div class="video-play-overlay">
                    <svg class="play-button" width="68" height="48" viewBox="0 0 68 48">
                        <path d="M66.52,7.74c-0.78-2.93-2.49-5.41-5.42-6.19C55.79,.13,34,0,34,0S12.21,.13,6.9,1.55 C3.97,2.33,2.27,4.81,1.48,7.74C0.06,13.05,0,24,0,24s0.06,10.95,1.48,16.26c0.78,2.93,2.49,5.41,5.42,6.19 C12.21,47.87,34,48,34,48s21.79-0.13,27.1-1.55c2.93-0.78,4.64-3.26,5.42-6.19C67.94,34.95,68,24,68,24S67.94,13.05,66.52,7.74z" fill="#f00"></path>
                        <path d="M 45,24 27,14 27,34" fill="#fff"></path>
                    </svg>
                </div>
            </div>
        </a>
    `;

    return card;
}

/**
 * ✅ Type text character by character (SAFE version)
 * This is the ONLY place this function should be defined
 */
async function typeTextSafe(element, text) {
    if (!element || !text) return;

    const typingSpeed = 30;
    const textSpan = document.createElement('span');
    element.appendChild(textSpan);

    for (let i = 0; i < text.length; i++) {
        textSpan.textContent += text[i];
        if (window.scrollToBottomIfNotScrolledUp) {
            window.scrollToBottomIfNotScrolledUp();
        }
        await new Promise(resolve => setTimeout(resolve, typingSpeed));
    }
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
 * Format image results
 */
function formatImageResults(images, query) {
    if (!images || images.length === 0) {
        return `I couldn't find images of "${query}". Try searching on Google Images: https://www.google.com/search?tbm=isch&q=${encodeURIComponent(query)}`;
    }

    let html = `Here's what I found for "${query}":\n\n`;

    images.forEach((image, index) => {
        html += `![${image.alt}](${image.url})\n`;
        html += `📸 Photo by [${image.photographer}](${image.photographer_url})\n\n`;
    });

    return html;
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
 * Open image in full-screen modal
 */
function openImageModal(src, alt) {
    const modal = document.createElement('div');
    modal.className = 'image-modal';
    modal.innerHTML = `
        <div class="image-modal-content">
            <span class="image-modal-close" onclick="this.parentElement.parentElement.remove()">&times;</span>
            <img src="${src}" alt="${alt || 'Full size image'}">
        </div>
    `;
    document.body.appendChild(modal);

    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.remove();
        }
    });

    document.addEventListener('keydown', function closeOnEsc(e) {
        if (e.key === 'Escape') {
            modal.remove();
            document.removeEventListener('keydown', closeOnEsc);
        }
    });
}

// ============================================================================
// ✅ NOTE: showMediaLoading() function REMOVED (it was unused)
// The typing indicator in chat_messages.js now shows "typing & searching"
// ============================================================================

// ============================================================================
// ✅ EXPOSE ALL FUNCTIONS GLOBALLY (INCLUDING createVideoCard & typeTextSafe)
// ============================================================================

window.detectMediaRequest = detectMediaRequest;
window.searchMedia = searchMedia;
window.formatYouTubeResults = formatYouTubeResults;
window.animateMediaResults = animateMediaResults;
window.createMessageElement = createMessageElement;
window.extractTopicFromQuery = extractTopicFromQuery;
window.createVideoCard = createVideoCard;
window.typeTextSafe = typeTextSafe;
window.decodeHTMLEntities = decodeHTMLEntities;