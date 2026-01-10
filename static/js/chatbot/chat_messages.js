// ============================================================================
// CHAT-MESSAGES.JS - MESSAGE HANDLING & STREAMING (COMPLETE FIXED VERSION)
// ============================================================================
// ✅ FIXED Issue #1: CSS spacing after page refresh (removed ALL newlines)
// ✅ FIXED Issue #4: "Snowfriend is typing & searching..." for media requests
// ============================================================================

// ============================================================================
// TEXT PROCESSING & CLEANING
// ============================================================================

const cleanMessageText = (text) => {
    if (!text) return '';

    const hasMarkers = text.includes('[[EMAIL:') || text.includes('[[FEEDBACK:');

    text = text.replace(/<s>/g, '');  
    text = text.replace(/<\/s>/g, '');  
    text = text.replace(/❌.*ASTERISKS.*❌/g, '').trim();
    text = text.replace(/❌[^\n]*\n?/g, '').trim();
    text = text.replace(/<\|im_end(_id)?\|>/g, '');
    text = text.replace(/<\|im_start\|>/g, '');
    text = text.replace(/Session (end|begin)\./g, '');
    text = text.replace(/\[YOU SHOULD'?VE SAID:.*?\]/gi, '');
    text = text.replace(/\[A BETTER RESPONSE WOULD BE:.*?\]/gi, '');
    text = replaceAsterisksWithQuotes(text);

    if (text.startsWith('(') && text.endsWith(')')) {
        if (!(text.includes("I'm here to listen") && text.includes("professional"))) {
            text = text.slice(1, -1).trim();
        }
    }

    const lines = text.split('\n');
    const cleanedLines = [];
    let consecutiveEmpty = 0;

    for (const line of lines) {
        const lineStripped = line.trim();
        if (lineStripped) {
            const lineCleaned = lineStripped.replace(/\s+/g, ' ');
            cleanedLines.push(lineCleaned);
            consecutiveEmpty = 0;
        } else {
            consecutiveEmpty++;
            if (consecutiveEmpty <= 1) {
                cleanedLines.push('');
            }
        }
    }

    text = cleanedLines.join('\n');
    text = fixBulletListSpacing(text);
    text = text.replace(/ +\./g, '.');
    text = text.replace(/ +\?/g, '?');
    text = text.replace(/ +!/g, '!');
    text = text.replace(/ +,/g, ',');
    text = text.trim();

    if (hasMarkers) {
        if (!text.includes('[[EMAIL:') && !text.includes('[[FEEDBACK:')) {
            console.warn('⚠️ Markers were removed during cleaning! This is a bug.');
        }
    }

    return text;
};

const replaceAsterisksWithQuotes = (text) => {
    if (!text || !text.includes('*')) return text;

    const disclaimerPattern = /\*\([^)]*I'm here to listen[^)]*professional[^)]*\)\*/i;
    const hasDisclaimer = disclaimerPattern.test(text);

    if (hasDisclaimer) {
        const disclaimer = text.match(disclaimerPattern)[0];
        const textWithoutDisclaimer = text.replace(disclaimer, '<<<DISCLAIMER_PLACEHOLDER>>>');
        const processed = replaceAsterisksInText(textWithoutDisclaimer);
        return processed.replace('<<<DISCLAIMER_PLACEHOLDER>>>', disclaimer);
    } else {
        return replaceAsterisksInText(text);
    }
};

const replaceAsterisksInText = (text) => {
    const pattern = /\*([^*]+)\*/g;

    return text.replace(pattern, (match, content) => {
        const wordCount = content.trim().split(/\s+/).length;

        if (wordCount <= 2) {
            return `'${content}'`;
        } else {
            return `"${content}"`;
        }
    });
};

const fixBulletListSpacing = (text) => {
    if (!text) return text;

    const lines = text.split('\n');
    const fixedLines = [];
    let inList = false;

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const lineStripped = line.trim();
        const isListItem = /^[-•*]\s/.test(lineStripped) || /^\d+\.\s/.test(lineStripped);

        if (isListItem && !inList) {
            if (i > 0 && fixedLines.length > 0 && fixedLines[fixedLines.length - 1].trim()) {
                fixedLines.push('');
            }
            inList = true;
        }

        if (!isListItem && inList && lineStripped) {
            inList = false;
            if (fixedLines.length > 0 && fixedLines[fixedLines.length - 1].trim()) {
                fixedLines.push('');
            }
        }

        fixedLines.push(line);
    }

    return fixedLines.join('\n');
};

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
        '<a href="#" onclick="event.preventDefault(); window.openFeedbackModal();" class="fallback-link">$1</a>'
    );

    return text;
};

// ============================================================================
// MEDIA MESSAGE HANDLING
// ============================================================================

const isMediaMessage = (message) => {
    return message.is_media_message && message.media_data && message.media_type;
};

/**
 * ✅ FIXED Issue #1: Render media message instantly (NO newlines between elements!)
 * Uses window.createVideoCard() from chat_media.js
 */
const renderMediaMessageInstant = async (messageBody, mediaData, mediaType) => {
    const contentDiv = messageBody.querySelector('.message-content');

    let htmlContent = '';

    // ✅ CRITICAL FIX: Convert markers to links in intro text
    if (mediaData.intro) {
        let introText = mediaData.intro;
        
        // Convert [[EMAIL:text]] to link
        introText = introText.replace(
            /\[\[EMAIL:([^\]]+)\]\]/g,
            '<a href="https://mail.google.com/mail/?view=cm&fs=1&to=marcdaryll.trinidad@gmail.com&su=Snowfriend%20Chat%20Inquiry" class="fallback-link" target="_blank" rel="noopener noreferrer">$1</a>'
        );
        
        // Convert [[FEEDBACK:text]] to link
        introText = introText.replace(
            /\[\[FEEDBACK:([^\]]+)\]\]/g,
            '<a href="#" onclick="event.preventDefault(); window.openFeedbackModal();" class="fallback-link">$1</a>'
        );
        
        htmlContent += `<span>${introText}</span><br><br>`;
    }

    if (mediaType === 'video' && mediaData.videos) {
        for (let i = 0; i < mediaData.videos.length; i++) {
            const video = mediaData.videos[i];

            const videoId = video.videoId || video.video_id || '';
            const videoNumber = video.number || (i + 1);
            const videoTitle = window.decodeHTMLEntities(video.title || 'Untitled Video');
            const videoChannel = window.decodeHTMLEntities(video.channel || video.channel_title || 'Unknown Channel');
            const videoDescription = video.description ? window.decodeHTMLEntities(video.description) : 'Click to watch this video.';
            const videoUrl = video.url || `https://www.youtube.com/watch?v=${videoId}`;

            if (!videoId) {
                console.error('Video is missing ID:', video);
                continue;
            }

            const thumbnailUrl = `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`;
            
            // ✅ NO NEWLINES between HTML elements (prevents spacing gaps)
            htmlContent += `<span style="display:block;margin-bottom:2px;margin-top:0;font-weight:700;font-size:16px;line-height:1.2;">${videoNumber}. ${videoTitle}</span>`;
            htmlContent += `<div class="video-result" data-video-url="${videoUrl}" data-video-title="${videoTitle}" data-video-id="${videoId}"><a href="${videoUrl}" target="_blank" rel="noopener noreferrer" class="video-thumbnail-link"><div class="video-thumbnail-wrapper"><img src="${thumbnailUrl}" alt="${videoTitle}" class="video-thumbnail" loading="lazy" onerror="this.src='https://via.placeholder.com/480x360?text=Video+Unavailable'"><div class="video-play-overlay"><svg class="play-button" width="68" height="48" viewBox="0 0 68 48"><path d="M66.52,7.74c-0.78-2.93-2.49-5.41-5.42-6.19C55.79,.13,34,0,34,0S12.21,.13,6.9,1.55 C3.97,2.33,2.27,4.81,1.48,7.74C0.06,13.05,0,24,0,24s0.06,10.95,1.48,16.26c0.78,2.93,2.49,5.41,5.42,6.19 C12.21,47.87,34,48,34,48s21.79-0.13,27.1-1.55c2.93-0.78,4.64-3.26,5.42-6.19C67.94,34.95,68,24,68,24S67.94,13.05,66.52,7.74z" fill="#f00"></path><path d="M 45,24 27,14 27,34" fill="#fff"></path></svg></div></div></a></div>`;
            htmlContent += `<div style="margin-top:2px;margin-bottom:0;line-height:1.4;"><span style="font-weight: 700;">By ${videoChannel}</span><br><span style="font-weight: 400;">${videoDescription}</span></div>`;

            if (i < mediaData.videos.length - 1) {
                htmlContent += '<br>';
            }
        }
    }

    // ✅ CRITICAL FIX: Convert markers to links in outro text
    if (mediaData.outro) {
        let outroText = mediaData.outro;
        
        // Convert [[EMAIL:text]] to link
        outroText = outroText.replace(
            /\[\[EMAIL:([^\]]+)\]\]/g,
            '<a href="https://mail.google.com/mail/?view=cm&fs=1&to=marcdaryll.trinidad@gmail.com&su=Snowfriend%20Chat%20Inquiry" class="fallback-link" target="_blank" rel="noopener noreferrer">$1</a>'
        );
        
        // Convert [[FEEDBACK:text]] to link
        outroText = outroText.replace(
            /\[\[FEEDBACK:([^\]]+)\]\]/g,
            '<a href="#" onclick="event.preventDefault(); window.openFeedbackModal();" class="fallback-link">$1</a>'
        );
        
        htmlContent += `<br><br><span>${outroText}</span>`;
    }

    contentDiv.innerHTML = htmlContent;
};

// ============================================================================
// ✅ NEW: MEDIA REQUEST DETECTION (Issue #4)
// ============================================================================

/**
 * ✅ FIXED Issue #4: Detect if message is a media request
 */
function isMediaRequest(message) {
    const msgLower = message.toLowerCase();
    
    const videoPatterns = [
        /\b(video|videos)\b/,
        /\b(show me|find me|get me|give me|recommend)\s+.*\b(video|videos)\b/,
        /\bwatch\b/,
    ];
    
    const imagePatterns = [
        /\b(image|images|picture|pictures|photo|photos|pic|pics)\b/,
        /\b(show me|find me)\s+.*\b(image|picture|photo)\b/,
    ];
    
    const isVideo = videoPatterns.some(pattern => pattern.test(msgLower));
    const isImage = imagePatterns.some(pattern => pattern.test(msgLower));
    
    return isVideo || isImage;
}

// ============================================================================
// MESSAGE DISPLAY FUNCTIONS
// ============================================================================

const appendMessage = (text, sender, timestamp = null, mediaData = null) => {
    text = cleanMessageText(text);

    if (!text) {
        console.warn('Empty message after cleaning, skipping append');
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

/**
 * ✅ FIXED Issue #4: Show typing with optional "& searching" text
 */
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
    
    // ✅ CRITICAL FIX #4: Change text based on whether we're searching for media
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
    text = cleanMessageText(text);

    if (!text) {
        console.warn('Empty message after cleaning, skipping append');
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

    let currentIndex = 0;
    const typingSpeed = 30;

    const typeCharacter = () => {
        if (currentIndex < displayText.length) {
            contentDiv.textContent = displayText.substring(0, currentIndex + 1);
            currentIndex++;
            window.scrollToBottom();
            setTimeout(typeCharacter, typingSpeed);
        } else {
            // ✅ CRITICAL: Convert markers to links after typing completes
            if (hasMarkers) {
                contentDiv.innerHTML = convertMarkersToLinks(text);
            }

            setTimeout(() => {
                window.scrollToBottom();
                window.isTyping = false;
                window.updateSendButton();
                if (callback) callback();
            }, 50);
        }
    };

    typeCharacter();
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

    let currentIndex = 0;
    const typingSpeed = 25;

    const typeCharacter = () => {
        if (currentIndex < greeting.length) {
            contentDiv.textContent = greeting.substring(0, currentIndex + 1);
            currentIndex++;
            window.scrollToBottom();
            setTimeout(typeCharacter, typingSpeed);
        } else {
            window.isInitialTyping = false;
            window.updateSendButton();
        }
    };

    setTimeout(typeCharacter, 300);
};

// ============================================================================
// STREAMING SUPPORT
// ============================================================================

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
                    {
                        type: 'media',
                        intro: data.media_data.intro,
                        videos: data.media_data.videos || [],
                        images: data.media_data.images || [],
                        outro: data.media_data.outro
                    }
                );

                window.isTyping = false;
                window.updateSendButton();
                return true;
            } else if (data.response) {
                appendMessageWithTyping(data.response, 'bot');
                return true;
            }

            return false;
        }

        if (!response.body) {
            return false;
        }

        const messageElement = createStreamingMessage();
        typingIndicator.remove();

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

                        if (data.chunk) {
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
                                const cleanedResponse = cleanMessageText(fullResponse);

                                if (isFallbackMessage) {
                                    await animateTextCharacterByCharacter(messageElement, cleanedResponse);
                                } else {
                                    if (cleanedResponse.includes('[[EMAIL]]') || cleanedResponse.includes('[[FEEDBACK]]')) {
                                        messageElement.innerHTML = convertMarkersToLinks(cleanedResponse);
                                    } else {
                                        messageElement.textContent = cleanedResponse;
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
        console.error('Streaming error:', error);
        return false;
    }
};

const animateTextCharacterByCharacter = (element, text) => {
    return new Promise((resolve) => {
        let currentIndex = 0;
        const typingSpeed = 30;
        const hasMarkers = text.includes('[[EMAIL:') || text.includes('[[FEEDBACK:');

        const displayText = hasMarkers ? convertMarkersToPlainText(text) : text;

        const typeCharacter = () => {
            if (currentIndex < displayText.length) {
                element.textContent = displayText.substring(0, currentIndex + 1);
                currentIndex++;
                window.scrollToBottom();
                setTimeout(typeCharacter, typingSpeed);
            } else {
                if (hasMarkers) {
                    element.innerHTML = convertMarkersToLinks(text);
                }

                setTimeout(() => {
                    window.scrollToBottom();
                    resolve();
                }, 50);
            }
        };

        typeCharacter();
    });
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

    const cleanedContent = cleanMessageText(content);

    if (hasEmailMarker || hasFeedbackMarker) {
        element.innerHTML = convertMarkersToLinks(cleanedContent);
    } else {
        element.textContent = cleanedContent;
    }
    window.scrollToBottom();
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
// ✅ FIXED Issue #4: SEND MESSAGE FUNCTION with media detection
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

    // ✅ CRITICAL FIX #4: Detect if this is a media request
    const isMediaReq = isMediaRequest(text);
    const typingIndicator = showTypingIndicator(isMediaReq);  // ← Pass the flag!

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