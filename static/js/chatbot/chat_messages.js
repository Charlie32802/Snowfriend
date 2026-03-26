// ============================================================================
// CHAT-MESSAGES.JS - PROPER MEDIA ANIMATION
// ============================================================================

// Helper: Animate text character by character into a SPECIFIC element
const animateText = async (element, text) => {
    const cleanText = convertMarkersToPlainText(text);
    const startTime = performance.now();
    const duration = cleanText.length * 20; // Total animation time

    return new Promise((resolve) => {
        const animate = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const charIndex = Math.floor(progress * cleanText.length);

            element.innerHTML = cleanText.substring(0, charIndex);
            window.scrollToBottomIfNotScrolledUp();

            if (progress < 1) {
                requestAnimationFrame(animate);
            } else {
                // Convert markers after animation
                if (text.includes('[[EMAIL:') || text.includes('[[FEEDBACK:')) {
                    element.innerHTML = convertMarkersToLinks(text);
                }
                resolve();
            }
        };

        requestAnimationFrame(animate);
    });
};

// Helper: Sleep function
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

// ✅ Helper: Build video HTML (instant, no typing) - with fade-in
const buildVideoHTML = (video, index) => {
    const videoId = video.videoId || video.video_id || '';
    const videoUrl = video.url || `https://www.youtube.com/watch?v=${videoId}`;
    const videoTitle = window.decodeHTMLEntities(video.title || 'Untitled Video');
    const thumbnailUrl = video.thumbnail || `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`;

    let html = '';
    html += `<div class="video-result media-fade-in" data-video-url="${videoUrl}" data-video-title="${videoTitle}" data-video-id="${videoId}">`;
    html += `<a href="${videoUrl}" target="_blank" rel="noopener noreferrer" class="video-thumbnail-link">`;
    html += `<div class="video-thumbnail-wrapper">`;
    html += `<img src="${thumbnailUrl}" alt="${videoTitle}" class="video-thumbnail" onerror="this.style.opacity='0'">`;
    html += `<div class="video-play-overlay"><svg class="play-button" width="68" height="48" viewBox="0 0 68 48"><path d="M66.52,7.74c-0.78-2.93-2.49-5.41-5.42-6.19C55.79,.13,34,0,34,0S12.21,.13,6.9,1.55 C3.97,2.33,2.27,4.81,1.48,7.74C0.06,13.05,0,24,0,24s0.06,10.95,1.48,16.26c0.78,2.93,2.49,5.41,5.42,6.19 C12.21,47.87,34,48,34,48s21.79-0.13,27.1-1.55c2.93-0.78,4.64-3.26,5.42-6.19C67.94,34.95,68,24,68,24S67.94,13.05,66.52,7.74z" fill="#f00"></path><path d="M 45,24 27,14 27,34" fill="#fff"></path></svg></div>`;
    html += `</div></a></div>`;

    return html;
};

// ✅ Helper: Build image HTML (instant, no typing) - with fade-in and NO HOVER SCALE
const buildImageHTML = (image, index) => {
    const imageAlt = window.decodeHTMLEntities(image.alt || 'Image');
    const imageUrl = image.url || '';

    let html = '';
    html += `<div class="image-result media-fade-in" data-image-url="${imageUrl}">`;
    html += `<a href="${imageUrl}" target="_blank" rel="noopener noreferrer" class="image-link" onclick="event.preventDefault(); event.stopPropagation(); window.openImageModal('${imageUrl.replace(/'/g, "\\'")}', '${imageAlt.replace(/'/g, "\\'")}');">`;
    html += `<div class="image-wrapper">`;
    html += `<img src="${imageUrl}" alt="${imageAlt}" class="message-image" onerror="this.style.opacity='0'" style="max-width: 100%; height: auto; border-radius: 8px; cursor: pointer; display: block;">`;
    html += `</div></a></div>`;

    return html;
};

// ✅ UNIFIED: Single router for all media types
window.animateMediaResults = async (messageBody, mediaContent) => {
    console.log('🎬 animateMediaResults called');

    if ((mediaContent.videos && mediaContent.videos.length > 0) ||
        (mediaContent.images && mediaContent.images.length > 0)) {
        await animateMediaResults_Internal(messageBody, mediaContent);
    }

    if (window.scrollToBottom) {
        window.scrollToBottomIfNotScrolledUp();
    }
};

// ✅ PROPER ANIMATION: Type intro → type title → show media → type description → repeat
async function animateMediaResults_Internal(messageBody, mediaContent) {
    const contentDiv = messageBody.querySelector('.message-content');
    contentDiv.innerHTML = ''; // Start clean

    // Helper to append a new span/div and type into it
    const typeIntoNewElement = async (parent, tag, styles, text) => {
        const el = document.createElement(tag);
        if (styles) el.style.cssText = styles;
        parent.appendChild(el);
        await animateText(el, text);
        return el;
    };

    // Helper to inject raw HTML directly
    const injectHTML = (parent, htmlString) => {
        const wrapper = document.createElement('div');
        wrapper.innerHTML = htmlString;
        while (wrapper.firstChild) {
            parent.appendChild(wrapper.firstChild);
        }
    };

    // 1. Type intro character by character
    if (mediaContent.intro) {
        await typeIntoNewElement(contentDiv, 'span', '', mediaContent.intro);
        injectHTML(contentDiv, '<br><br>');
        await sleep(100);
    }

    // 2. Animate videos
    if (mediaContent.videos && mediaContent.videos.length > 0) {
        for (let i = 0; i < mediaContent.videos.length; i++) {
            const video = mediaContent.videos[i];
            const videoNumber = video.number || (i + 1);
            const videoTitle = window.decodeHTMLEntities(video.title || 'Untitled Video');
            const videoChannel = window.decodeHTMLEntities(video.channel || video.channel_title || 'Unknown Channel');
            const videoDescription = video.description ? window.decodeHTMLEntities(video.description) : 'Click to watch this video.';

            // Type video title
            const titleText = `${videoNumber}. ${videoTitle}`;
            await typeIntoNewElement(contentDiv, 'span', 'display:block;margin-bottom:0;margin-top:0;font-weight:700;font-size:16px;line-height:1.2;', titleText);
            await sleep(50);

            // Show video (fade-in animation)
            const videoHTML = buildVideoHTML(video, i);
            injectHTML(contentDiv, videoHTML);

            // Trigger fade-in
            await sleep(10); // Let browser paint
            const videoElement = contentDiv.querySelectorAll('.media-fade-in')[contentDiv.querySelectorAll('.media-fade-in').length - 1];
            if (videoElement) {
                videoElement.classList.add('show');
                await sleep(400); // Wait for fade-in to complete
            }
            window.scrollToBottomIfNotScrolledUp();

            // Create wrapper for description block
            const descWrapper = document.createElement('div');
            descWrapper.style.cssText = 'margin-top:4px;margin-bottom:0;line-height:1.4;';
            contentDiv.appendChild(descWrapper);

            // Type publisher line
            const publisherEl = document.createElement('span');
            publisherEl.style.fontWeight = '700';
            descWrapper.appendChild(publisherEl);
            await animateText(publisherEl, `By ${videoChannel}`);
            injectHTML(descWrapper, '<br>');
            await sleep(50);

            // Type description
            const descEl = document.createElement('span');
            descEl.style.fontWeight = '400';
            descWrapper.appendChild(descEl);
            await animateText(descEl, videoDescription);

            // Add line break (except for last item)
            if (i < mediaContent.videos.length - 1) {
                injectHTML(contentDiv, '<br>');
            }

            await sleep(100);
            window.scrollToBottomIfNotScrolledUp();
        }
    }

    // 3. Animate images
    if (mediaContent.images && mediaContent.images.length > 0) {
        for (let i = 0; i < mediaContent.images.length; i++) {
            const image = mediaContent.images[i];
            const imageNumber = image.number || (i + 1);
            const imageAlt = window.decodeHTMLEntities(image.alt || 'Image');
            const photographer = window.decodeHTMLEntities(image.photographer || 'Unknown');
            const photographerUrl = image.photographer_url || '';

            // Type image title
            const titleText = `${imageNumber}. ${imageAlt}`;
            await typeIntoNewElement(contentDiv, 'span', 'display:block;margin-bottom:0;margin-top:0;font-weight:700;font-size:16px;line-height:1.2;', titleText);
            await sleep(50);

            // Show image (fade-in animation)
            const imageHTML = buildImageHTML(image, i);
            injectHTML(contentDiv, imageHTML);

            // Trigger fade-in
            await sleep(10); // Let browser paint
            const imageElement = contentDiv.querySelectorAll('.media-fade-in')[contentDiv.querySelectorAll('.media-fade-in').length - 1];
            if (imageElement) {
                imageElement.classList.add('show');
                await sleep(400); // Wait for fade-in to complete
            }
            window.scrollToBottomIfNotScrolledUp();

            // Create wrapper for photographer info
            const descWrapper = document.createElement('div');
            descWrapper.style.cssText = 'margin-top:0;margin-bottom:0;line-height:1.4;';
            contentDiv.appendChild(descWrapper);

            // Type photographer
            const photoEl = document.createElement('span');
            photoEl.style.fontWeight = '700';
            descWrapper.appendChild(photoEl);
            await animateText(photoEl, `Photo by ${photographer}`);
            injectHTML(descWrapper, '<br>');
            await sleep(50);

            // Type "View profile"
            if (photographerUrl) {
                const linkWrapper = document.createElement('span');
                linkWrapper.style.fontWeight = '400';
                descWrapper.appendChild(linkWrapper);
                await animateText(linkWrapper, 'View profile');
                // Convert text to link
                linkWrapper.innerHTML = `<a href="${photographerUrl}" target="_blank" rel="noopener noreferrer" class="fallback-link">View profile</a>`;
            }

            // Add line break (except for last item)
            if (i < mediaContent.images.length - 1) {
                injectHTML(contentDiv, '<br>');
            }

            await sleep(100);
            window.scrollToBottomIfNotScrolledUp();
        }
    }

    // 4. Type outro
    if (mediaContent.outro) {
        injectHTML(contentDiv, '<br><br>');
        await typeIntoNewElement(contentDiv, 'span', '', mediaContent.outro);
    }

    window.scrollToBottomIfNotScrolledUp();
}

// ============================================================================
// TEXT PROCESSING - MARKER CONVERSION
// ============================================================================

const convertMarkersToPlainText = (text) => {
    text = text.replace(/\[\[EMAIL:([^\]]+)\]\]/g, '$1');
    text = text.replace(/\[\[FEEDBACK:([^\]]+)\]\]/g, '$1');
    return text;
};

const convertMarkersToLinks = (text) => {
    text = text.replace(
        /\[\[EMAIL:([^\]]+)\]\]/g,
        '<a href="https://mail.google.com/mail/?view=cm&fs=1&to=marcdaryll.trinidad@gmail.com&su=Snowfriend%20Chat%20Inquiry" class="fallback-link" target="_blank" rel="noopener noreferrer">$1</a>'
    );

    text = text.replace(
        /\[\[FEEDBACK:([^\]]+)\]\]/g,
        '<a href="Contact" onclick="event.preventDefault(); window.openFeedbackModal();" class="fallback-link">$1</a>'
    );

    return text;
};

// ============================================================================
// MEDIA MESSAGE HANDLING
// ============================================================================

const isMediaMessage = (message) => {
    return message.is_media_message && message.media_data && message.media_type;
};

// ✅ Helper: Render video item for instant display (page reload)
const renderVideoItem = (video, index, isLast = false) => {
    const videoId = video.videoId || video.video_id || '';
    const videoNumber = video.number || (index + 1);
    const videoTitle = window.decodeHTMLEntities(video.title || 'Untitled Video');
    const videoChannel = window.decodeHTMLEntities(video.channel || video.channel_title || 'Unknown Channel');
    const videoDescription = video.description ? window.decodeHTMLEntities(video.description) : 'Click to watch this video.';
    const videoUrl = video.url || `https://www.youtube.com/watch?v=${videoId}`;
    const thumbnailUrl = video.thumbnail || `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`;

    let html = '';
    html += `<span style="display:block;margin-bottom:4px;margin-top:0;font-weight:700;font-size:16px;line-height:1.2;">${videoNumber}. ${videoTitle}</span>`;
    html += `<div class="video-result" data-video-url="${videoUrl}" data-video-title="${videoTitle}" data-video-id="${videoId}">`;
    html += `<a href="${videoUrl}" target="_blank" rel="noopener noreferrer" class="video-thumbnail-link">`;
    html += `<div class="video-thumbnail-wrapper">`;
    html += `<img src="${thumbnailUrl}" alt="${videoTitle}" class="video-thumbnail" onerror="this.style.opacity='0'">`;
    html += `<div class="video-play-overlay"><svg class="play-button" width="68" height="48" viewBox="0 0 68 48"><path d="M66.52,7.74c-0.78-2.93-2.49-5.41-5.42-6.19C55.79,.13,34,0,34,0S12.21,.13,6.9,1.55 C3.97,2.33,2.27,4.81,1.48,7.74C0.06,13.05,0,24,0,24s0.06,10.95,1.48,16.26c0.78,2.93,2.49,5.41,5.42,6.19 C12.21,47.87,34,48,34,48s21.79-0.13,27.1-1.55c2.93-0.78,4.64-3.26,5.42-6.19C67.94,34.95,68,24,68,24S67.94,13.05,66.52,7.74z" fill="#f00"></path><path d="M 45,24 27,14 27,34" fill="#fff"></path></svg></div>`;
    html += `</div></a></div>`;
    html += `<div style="margin-top:4px;margin-bottom:0;line-height:1.4;">`;
    html += `<span style="font-weight: 700;">By ${videoChannel}</span><br>`;
    html += `<span style="font-weight: 400;">${videoDescription}</span>`;
    html += `</div>`;

    if (!isLast) {
        html += '<br>';
    }

    return html;
};

// ✅ Helper: Render image item for instant display (page reload)
const renderImageItem = (image, index, isLast = false) => {
    const imageNumber = index + 1;
    const imageAlt = window.decodeHTMLEntities(image.alt || 'Image');
    const imageUrl = image.url || '';
    const photographer = window.decodeHTMLEntities(image.photographer || 'Unknown');
    const photographerUrl = image.photographer_url || '';

    let html = '';
    html += `<span style="display:block;margin-bottom:0;margin-top:0;font-weight:700;font-size:16px;line-height:1.2;">${imageNumber}. ${imageAlt}</span>`;
    html += `<div class="image-result" data-image-url="${imageUrl}">`;
    html += `<a href="${imageUrl}" target="_blank" rel="noopener noreferrer" class="image-link" onclick="event.preventDefault(); event.stopPropagation(); window.openImageModal('${imageUrl.replace(/'/g, "\\'")}', '${imageAlt.replace(/'/g, "\\'")}');">`;
    html += `<div class="image-wrapper">`;
    html += `<img src="${imageUrl}" alt="${imageAlt}" class="message-image" onerror="this.style.opacity='0'" style="max-width: 100%; height: auto; border-radius: 8px; cursor: pointer; display: block;">`;
    html += `</div></a></div>`;

    html += `<div style="margin-top:0;margin-bottom:0;line-height:1.4;">`;
    html += `<span style="font-weight: 700;">Photo by ${photographer}</span><br>`;

    if (photographerUrl) {
        html += `<span style="font-weight: 400;"><a href="${photographerUrl}" target="_blank" rel="noopener noreferrer" class="fallback-link">View profile</a></span>`;
    }

    html += `</div>`;

    if (!isLast) {
        html += '<br>';
    }

    return html;
};

/**
 * ✅ Render media message instantly (for page reload)
 */
const renderMediaMessageInstant = async (messageBody, mediaData, mediaType) => {
    const contentDiv = messageBody.querySelector('.message-content');

    let htmlContent = '';

    // Intro
    if (mediaData.intro) {
        let introText = convertMarkersToLinks(mediaData.intro);
        htmlContent += `<span>${introText}</span><br><br>`;
    }

    // Render videos
    if (mediaType === 'video' && mediaData.videos) {
        for (let i = 0; i < mediaData.videos.length; i++) {
            const isLast = (i === mediaData.videos.length - 1);
            htmlContent += renderVideoItem(mediaData.videos[i], i, isLast);
        }
    }

    // Render images
    if (mediaType === 'image' && mediaData.images) {
        for (let i = 0; i < mediaData.images.length; i++) {
            const isLast = (i === mediaData.images.length - 1);
            htmlContent += renderImageItem(mediaData.images[i], i, isLast);
        }
    }

    // Outro
    if (mediaData.outro) {
        let outroText = convertMarkersToLinks(mediaData.outro);
        htmlContent += `<br><br><span>${outroText}</span>`;
    }

    contentDiv.innerHTML = htmlContent;
};

// ============================================================================
// MEDIA REQUEST DETECTION
// ============================================================================

function isMediaRequest(message) {
    // 🚨 DEPRECATED: We no longer rely on brittle frontend RegEx.
    // The backend LLM now dynamically streams a {"status": "searching"}
    // SSE event if it decides to perform a media search!
    return false;
}

// ============================================================================
// MESSAGE DISPLAY FUNCTIONS
// ============================================================================

const appendMessage = (text, sender, timestamp = null, mediaData = null) => {
    if (!text) {
        console.warn('Empty message, skipping append');
        return;
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${sender}`;

    if (mediaData) {
        messageDiv.setAttribute('data-is-media', 'true');
        messageDiv.setAttribute('data-media-type', mediaData.media_type || '');
        messageDiv.setAttribute('data-media-data', JSON.stringify(mediaData));
    }

    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'message-avatar';

    const messageBody = document.createElement('div');
    messageBody.className = 'message-body';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    if (text.includes('[[EMAIL:') || text.includes('[[FEEDBACK:')) {
        contentDiv.innerHTML = convertMarkersToLinks(text);
    } else {
        contentDiv.textContent = text;
    }

    const timestampDiv = document.createElement('div');
    timestampDiv.className = 'message-timestamp';
    const timestampValue = timestamp || new Date().toISOString();
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

    const messagesContainer = document.getElementById('messagesContainer');
    messagesContainer.appendChild(messageDiv);
    window.scrollToBottom();
};

const showTypingIndicator = (isSearching = false) => {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message message-bot';

    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'message-avatar';
    const avatarImg = document.createElement('img');
    const logoIcon = document.querySelector('.logo-icon');
    if (logoIcon) avatarImg.src = logoIcon.src;
    avatarImg.alt = 'Snowfriend';
    avatarDiv.appendChild(avatarImg);

    const typingDiv = document.createElement('div');
    typingDiv.className = 'typing-indicator';

    const typingText = isSearching
        ? 'Snowfriend is typing & searching'
        : 'Snowfriend is typing';

    typingDiv.innerHTML = `
        <span class="typing-text">${typingText}<span class="typing-dots"><span class="typing-dot">.</span><span class="typing-dot">.</span><span class="typing-dot">.</span></span></span>
    `;

    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(typingDiv);

    const messagesContainer = document.getElementById('messagesContainer');
    messagesContainer.appendChild(messageDiv);
    window.scrollToBottom();

    return messageDiv;
};

const appendMessageWithTyping = (text, sender, callback) => {
    if (!text) {
        console.warn('Empty message, skipping append');
        if (callback) callback();
        return;
    }

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

    const messagesContainer = document.getElementById('messagesContainer');
    messagesContainer.appendChild(messageDiv);
    window.scrollToBottom();

    const hasMarkers = text.includes('[[EMAIL:') || text.includes('[[FEEDBACK:');
    const displayText = hasMarkers ? convertMarkersToPlainText(text) : text;

    const typingSpeed = 20;
    const startTime = performance.now();
    const duration = displayText.length * typingSpeed;

    const animate = (currentTime) => {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const charIndex = Math.floor(progress * displayText.length);

        contentDiv.textContent = displayText.substring(0, charIndex);
        window.scrollToBottomIfNotScrolledUp();

        if (progress < 1) {
            requestAnimationFrame(animate);
        } else {
            if (hasMarkers) {
                contentDiv.innerHTML = convertMarkersToLinks(text);
            }

            setTimeout(() => {
                window.scrollToBottomIfNotScrolledUp();
                window.isTyping = false;
                window.updateSendButton();
                if (callback) callback();
            }, 50);
        }
    };

    requestAnimationFrame(animate);
};

// ============================================================================
// CONVERSATION HISTORY
// ============================================================================

const loadConversationHistory = async () => {
    try {
        const response = await fetch('/chat/api/history/', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        const data = await response.json();

        if (data.success && data.messages && data.messages.length > 0) {
            window.isInitialTyping = false;
            window.updateSendButton();

            const messagesContainer = document.getElementById('messagesContainer');
            messagesContainer.innerHTML = '';

            for (const msg of data.messages) {
                if (msg.role === 'user') {
                    appendMessage(msg.content, 'user', msg.timestamp);
                } else if (msg.role === 'assistant') {
                    if (msg.is_media_message && msg.media_data) {
                        const messageDiv = window.createMessageElement('bot');

                        messageDiv.setAttribute('data-is-media', 'true');
                        messageDiv.setAttribute('data-media-type', msg.media_type);
                        messageDiv.setAttribute('data-media-data', JSON.stringify(msg.media_data));

                        const timestampDiv = messageDiv.querySelector('.message-timestamp');
                        timestampDiv.setAttribute('data-timestamp', msg.timestamp);
                        timestampDiv.textContent = window.formatTimestamp(msg.timestamp);

                        messagesContainer.appendChild(messageDiv);

                        await renderMediaMessageInstant(
                            messageDiv.querySelector('.message-body'),
                            msg.media_data,
                            msg.media_type
                        );
                    } else {
                        appendMessage(msg.content, 'bot', msg.timestamp);
                    }
                }
            }

            window.scrollToBottom();
        } else {
            addInitialMessage();
        }
    } catch (error) {
        console.error('Error loading conversation history:', error);
        addInitialMessage();
    }
};

const addInitialMessage = () => {
    const greeting = `Hi ${typeof userName !== 'undefined' ? userName : 'there'}! I'm Snowfriend. I'm here to listen and help you reflect.`;

    const messageDiv = document.createElement('div');
    messageDiv.className = 'message message-bot';

    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'message-avatar';
    const avatarImg = document.createElement('img');
    const logoIcon = document.querySelector('.logo-icon');
    if (logoIcon) avatarImg.src = logoIcon.src;
    avatarImg.alt = 'Snowfriend';
    avatarDiv.appendChild(avatarImg);

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
    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(messageBody);

    const messagesContainer = document.getElementById('messagesContainer');
    messagesContainer.appendChild(messageDiv);
    window.scrollToBottom();

    const typingSpeed = 20;
    const startTime = performance.now();
    const duration = greeting.length * typingSpeed;

    const animate = (currentTime) => {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const charIndex = Math.floor(progress * greeting.length);

        contentDiv.textContent = greeting.substring(0, charIndex);
        window.scrollToBottomIfNotScrolledUp();

        if (progress < 1) {
            requestAnimationFrame(animate);
        } else {
            window.isInitialTyping = false;
            window.updateSendButton();
        }
    };

    setTimeout(() => requestAnimationFrame(animate), 300);
};

// ============================================================================
// STREAMING SUPPORT
// ============================================================================

const animateTextCharacterByCharacter = (element, text) => {
    return new Promise((resolve) => {
        const hasMarkers = text.includes('[[EMAIL:') || text.includes('[[FEEDBACK:');
        const displayText = hasMarkers ? convertMarkersToPlainText(text) : text;
        const startTime = performance.now();
        const duration = displayText.length * 20;

        const animate = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const charIndex = Math.floor(progress * displayText.length);

            element.textContent = displayText.substring(0, charIndex);
            window.scrollToBottomIfNotScrolledUp();

            if (progress < 1) {
                requestAnimationFrame(animate);
            } else {
                if (hasMarkers) {
                    element.innerHTML = convertMarkersToLinks(text);
                }
                setTimeout(() => {
                    window.scrollToBottomIfNotScrolledUp();
                    resolve();
                }, 50);
            }
        };

        requestAnimationFrame(animate);
    });
};

const tryStreaming = async (text, csrftoken, typingIndicator) => {
    try {
        const response = await fetch('/chat/api/send/streaming/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken,
            },
            body: JSON.stringify({ message: text }),
        });

        if (!response.ok) {
            return false;
        }

        const contentType = response.headers.get('content-type');

        if (contentType && contentType.includes('application/json')) {
            const data = await response.json();
            typingIndicator.remove();

            if (data.is_media && data.media_data) {
                try {
                    const messageDiv = window.createMessageElement('bot');

                    messageDiv.setAttribute('data-is-media', 'true');
                    messageDiv.setAttribute('data-media-type', data.media_type);
                    messageDiv.setAttribute('data-media-data', JSON.stringify(data.media_data));

                    const messagesContainer = document.getElementById('messagesContainer');
                    messagesContainer.appendChild(messageDiv);

                    window.isTyping = true;
                    window.updateSendButton();

                    await window.animateMediaResults(
                        messageDiv.querySelector('.message-body'),
                        data.media_data
                    );

                    window.isTyping = false;
                    window.updateSendButton();

                    return true;
                } catch (animError) {
                    console.error('❌ Media animation error:', animError);
                    window.isTyping = false;
                    window.updateSendButton();
                    return true;
                }
            } else if (data.response) {
                appendMessageWithTyping(data.response, 'bot');
                return true;
            }

            console.warn('⚠️ Unexpected JSON response format:', data);
            return true;
        }

        if (!response.body) {
            return false;
        }

        let messageElement = null;

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullResponse = "";
        let isFallbackMessage = false;

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));

                        // ✅ Status updates (Thinking, Searching)
                        if (data.status) {
                            if (document.body.contains(typingIndicator)) {
                                const typingText = typingIndicator.querySelector('.typing-text');
                                if (typingText) {
                                    if (data.status === 'searching') {
                                        typingText.innerHTML = 'Snowfriend is typing & searching<span class="typing-dots"><span class="typing-dot">.</span><span class="typing-dot">.</span><span class="typing-dot">.</span></span>';
                                    } else if (data.status === 'thinking') {
                                        typingText.innerHTML = 'Snowfriend is parsing<span class="typing-dots"><span class="typing-dot">.</span><span class="typing-dot">.</span><span class="typing-dot">.</span></span>';
                                    }
                                }
                            }
                            continue;
                        }

                        // ✅ DYNAMIC MEDIA: Backend streamed a media payload!
                        if (data.is_media && data.media_data) {
                            if (document.body.contains(typingIndicator)) {
                                typingIndicator.remove();
                            }
                            if (messageElement && document.body.contains(messageElement.parentElement.parentElement)) {
                                messageElement.parentElement.parentElement.remove();
                            }

                            // Manually create the message framework
                            const messageDiv = document.createElement('div');
                            messageDiv.className = 'message message-bot';
                            messageDiv.setAttribute('data-is-media', 'true');
                            messageDiv.setAttribute('data-media-type', data.media_type);
                            messageDiv.setAttribute('data-media-data', JSON.stringify(data.media_data));

                            const avatarDiv = document.createElement('div');
                            avatarDiv.className = 'message-avatar';
                            const avatarImg = document.createElement('img');
                            const logoIcon = document.querySelector('.logo-icon');
                            if (logoIcon) avatarImg.src = logoIcon.src;
                            avatarImg.alt = 'Snowfriend';
                            avatarDiv.appendChild(avatarImg);

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
                            messageDiv.appendChild(avatarDiv);
                            messageDiv.appendChild(messageBody);

                            const messagesContainer = document.getElementById('messagesContainer');
                            messagesContainer.appendChild(messageDiv);

                            window.isTyping = true;
                            await window.animateMediaResults(
                                messageBody,
                                data.media_data
                            );

                            window.isTyping = false;
                            window.updateSendButton();
                            return true;
                        }

                        if (data.chunk) {
                            // First valid chunk, safe to remove typing indicator and create msg box
                            if (!messageElement) {
                                if (document.body.contains(typingIndicator)) {
                                    typingIndicator.remove();
                                }
                                messageElement = createStreamingMessage();
                            }

                            fullResponse += data.chunk;

                            if (fullResponse.includes('[[EMAIL:') || fullResponse.includes('[[FEEDBACK:')) {
                                isFallbackMessage = true;
                            }

                            if (!isFallbackMessage) {
                                updateStreamingMessage(messageElement, fullResponse);
                            }
                        }

                        if (data.done) {
                            if (messageElement) {
                                if (isFallbackMessage) {
                                    await animateTextCharacterByCharacter(messageElement, fullResponse);
                                } else {
                                    if (fullResponse.includes('[[EMAIL]]') || fullResponse.includes('[[FEEDBACK]]')) {
                                        messageElement.innerHTML = convertMarkersToLinks(fullResponse);
                                    } else {
                                        messageElement.textContent = fullResponse;
                                    }
                                }
                            }
                            window.isTyping = false;
                            window.updateSendButton();
                            return true;
                        }

                        if (data.error) {
                            throw new Error(data.error);
                        }
                    } catch (e) {
                        if (e instanceof SyntaxError) continue;
                        throw e;
                    }
                }
            }
        }

        window.isTyping = false;
        window.updateSendButton();
        return true;

    } catch (error) {
        console.error('❌ Streaming error:', error);
        return false;
    }
};

const createStreamingMessage = () => {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message message-bot';

    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'message-avatar';
    const avatarImg = document.createElement('img');
    const logoIcon = document.querySelector('.logo-icon');
    if (logoIcon) avatarImg.src = logoIcon.src;
    avatarImg.alt = 'Snowfriend';
    avatarDiv.appendChild(avatarImg);

    const messageBody = document.createElement('div');
    messageBody.className = 'message-body';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = '';

    const timestampDiv = document.createElement('div');
    timestampDiv.className = 'message-timestamp';
    const timestampValue = new Date().toISOString();
    timestampDiv.setAttribute('data-timestamp', timestampValue);
    timestampDiv.textContent = window.formatTimestamp(timestampValue);

    messageBody.appendChild(contentDiv);
    messageBody.appendChild(timestampDiv);
    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(messageBody);

    const messagesContainer = document.getElementById('messagesContainer');
    messagesContainer.appendChild(messageDiv);
    window.scrollToBottom();

    return contentDiv;
};

const updateStreamingMessage = (element, content) => {
    const hasEmailMarker = content.includes('[[EMAIL:');
    const hasFeedbackMarker = content.includes('[[FEEDBACK:');

    if (hasEmailMarker || hasFeedbackMarker) {
        element.innerHTML = convertMarkersToLinks(content);
    } else {
        element.textContent = content;
    }
    window.scrollToBottomIfNotScrolledUp();
};

const regularRequest = async (text, csrftoken, typingIndicator) => {
    const response = await fetch('/chat/api/send/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken,
        },
        body: JSON.stringify({ message: text }),
    });

    const data = await response.json();
    typingIndicator.remove();

    if (data.success) {
        if (data.notification) {
            window.showNotification(data.notification.message, data.notification.type);
        }
        appendMessageWithTyping(data.response, 'bot');
    } else {
        appendMessage('Sorry, I encountered an error. Please try again.', 'bot');
        window.isTyping = false;
        window.updateSendButton();
    }
};

// ============================================================================
// SEND MESSAGE FUNCTION
// ============================================================================

const sendMessage = async () => {
    const messageInput = document.getElementById('messageInput');
    const text = messageInput.value.trim();

    if (!text || window.isTyping || window.isInitialTyping) return;

    if (!window.messageLimitState.canSend) {
        const resetTimeStr = window.getResetTimeString(window.messageLimitState.timeRemaining);
        window.showNotification(
            `You have no messages remaining. Please wait until ${resetTimeStr} to get another ${window.messageLimitState.total} messages.`,
            'error'
        );
        return;
    }

    messageInput.value = '';
    messageInput.style.height = 'auto';

    appendMessage(text, 'user');
    window.isTyping = true;
    window.updateSendButton();

    const isMediaReq = isMediaRequest(text);
    const typingIndicator = showTypingIndicator(isMediaReq);

    try {
        const csrftoken = window.getCSRFToken();

        const streamingSupported = await tryStreaming(text, csrftoken, typingIndicator);

        if (!streamingSupported) {
            console.log('Streaming not supported, using regular request');
            await regularRequest(text, csrftoken, typingIndicator);
        }

        window.fetchMessageLimit?.();

    } catch (error) {
        console.error('Error sending message:', error);
        typingIndicator.remove();
        appendMessage("Sorry, I'm having trouble connecting. Please try again.", 'bot');
        window.isTyping = false;
        window.updateSendButton();
    }
};

// ============================================================================
// EXPOSE FUNCTIONS GLOBALLY
// ============================================================================

window.sendMessage = sendMessage;
window.loadConversationHistory = loadConversationHistory;
window.appendMessage = appendMessage;
window.appendMessageWithTyping = appendMessageWithTyping;
window.addInitialMessage = addInitialMessage;
window.isMediaMessage = isMediaMessage;
window.renderMediaMessageInstant = renderMediaMessageInstant;
window.isMediaRequest = isMediaRequest;
window.animateMediaResults = animateMediaResults;