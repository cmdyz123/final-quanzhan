/**
 * AI Nutritionist Chat functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chatForm');
    const chatInput = document.getElementById('chatInput');
    const chatMessages = document.getElementById('chatMessages');
    const sendBtn = document.getElementById('sendBtn');
    const quickBtns = document.querySelectorAll('.quick-btn');

    if (!chatForm || !chatInput) return;

    // Scroll to bottom
    function scrollToBottom() {
        if (chatMessages) {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }
    scrollToBottom();

    // Quick question buttons
    quickBtns.forEach(function(btn) {
        btn.addEventListener('click', function() {
            chatInput.value = this.dataset.question;
            chatInput.focus();
            sendMessage();
        });
    });

    // Form submit
    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        sendMessage();
    });

    function sendMessage() {
        const message = chatInput.value.trim();
        if (!message) return;

        // Disable input while sending
        chatInput.disabled = true;
        sendBtn.disabled = true;

        // Add user message to chat
        appendMessage('user', message);
        chatInput.value = '';

        // Add loading indicator
        const loadingId = 'loading-' + Date.now();
        appendLoading(loadingId);

        // Send to API
        fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: message })
        })
        .then(function(response) {
            return response.json();
        })
        .then(function(data) {
            // Remove loading
            removeLoading(loadingId);

            if (data.success) {
                appendMessage('assistant', data.reply);
            } else {
                appendMessage('assistant', '抱歉，我遇到了一些问题，请稍后再试。');
            }
        })
        .catch(function(error) {
            removeLoading(loadingId);
            appendMessage('assistant', '网络连接异常，请检查网络后重试。');
            console.error('Chat error:', error);
        })
        .finally(function() {
            chatInput.disabled = false;
            sendBtn.disabled = false;
            chatInput.focus();
        });
    }

    function appendMessage(role, content) {
        if (!chatMessages) return;

        const isUser = role === 'user';
        const time = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });

        const html = `
            <div class="chat-message ${role} mb-3">
                <div class="d-flex ${isUser ? 'justify-content-end' : ''}">
                    ${!isUser ? `
                    <div class="me-2">
                        <div class="bg-primary rounded-circle d-flex align-items-center justify-content-center" style="width: 32px; height: 32px;">
                            <i class="bi bi-robot text-white small"></i>
                        </div>
                    </div>` : ''}
                    <div class="chat-bubble rounded p-3 ${isUser ? 'bg-primary text-white' : 'bg-light'}" style="max-width: 80%;">
                        <p class="mb-0" style="white-space: pre-wrap;">${escapeHtml(content)}</p>
                        <small class="${isUser ? 'text-white-50' : 'text-muted'}">${time}</small>
                    </div>
                    ${isUser ? `
                    <div class="ms-2">
                        <div class="bg-secondary rounded-circle d-flex align-items-center justify-content-center" style="width: 32px; height: 32px;">
                            <i class="bi bi-person text-white small"></i>
                        </div>
                    </div>` : ''}
                </div>
            </div>
        `;

        chatMessages.insertAdjacentHTML('beforeend', html);
        scrollToBottom();
    }

    function appendLoading(id) {
        if (!chatMessages) return;

        const html = `
            <div class="chat-message assistant mb-3" id="${id}">
                <div class="d-flex">
                    <div class="me-2">
                        <div class="bg-primary rounded-circle d-flex align-items-center justify-content-center" style="width: 32px; height: 32px;">
                            <i class="bi bi-robot text-white small"></i>
                        </div>
                    </div>
                    <div class="chat-bubble bg-light rounded p-3">
                        <div class="d-flex gap-1">
                            <span class="dot-typing"></span>
                            <span class="dot-typing" style="animation-delay: 0.2s;"></span>
                            <span class="dot-typing" style="animation-delay: 0.4s;"></span>
                        </div>
                    </div>
                </div>
            </div>
        `;

        chatMessages.insertAdjacentHTML('beforeend', html);
        scrollToBottom();
    }

    function removeLoading(id) {
        const el = document.getElementById(id);
        if (el) {
            el.remove();
        }
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
});
