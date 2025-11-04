/**
 * Goldco AI Chat Interface
 * Handles chat interaction with the goldco-ai API
 */

(function() {
  'use strict';

  // DOM Elements
  const chatForm = document.getElementById('chat-form');
  const chatInput = document.getElementById('chat-input');
  const sendBtn = document.getElementById('send-btn');
  const messagesContainer = document.getElementById('messages-container');
  const chatMessages = document.getElementById('chat-messages');
  const welcomeMessage = document.getElementById('welcome-message');
  const newChatBtn = document.getElementById('new-chat-btn');
  const modelSelect = document.getElementById('model-select');
  const charCount = document.getElementById('char-count');
  const healthStatus = document.getElementById('health-status');

  // State
  let isLoading = false;

  /**
   * Initialize the chat interface
   */
  function init() {
    checkHealth();
    setupEventListeners();
    updateCharCount();
  }

  /**
   * Setup event listeners
   */
  function setupEventListeners() {
    // Form submission
    chatForm.addEventListener('submit', handleSubmit);

    // New chat button
    newChatBtn.addEventListener('click', handleNewChat);

    // Character count
    chatInput.addEventListener('input', updateCharCount);

    // Auto-resize textarea
    chatInput.addEventListener('input', function() {
      this.style.height = 'auto';
      this.style.height = (this.scrollHeight) + 'px';
    });

    // Enter key to submit (Shift+Enter for new line)
    chatInput.addEventListener('keydown', function(e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        chatForm.dispatchEvent(new Event('submit'));
      }
    });
  }

  /**
   * Check AI API health
   */
  async function checkHealth() {
    try {
      const response = await fetch('/api/ai/health');
      const data = await response.json();

      if (data.status === 'online') {
        updateHealthStatus('online', 'AI Online');
      } else {
        updateHealthStatus('error', 'AI Offline');
      }
    } catch (error) {
      updateHealthStatus('error', 'AI Offline');
    }
  }

  /**
   * Update health status indicator
   */
  function updateHealthStatus(status, text) {
    const statusDot = healthStatus.querySelector('span:first-child');
    const statusText = healthStatus.querySelector('span:last-child');

    if (status === 'online') {
      statusDot.className = 'inline-flex size-2 rounded-full bg-green-500';
      statusText.textContent = text;
      statusText.className = 'text-xs text-green-600 dark:text-green-500';
    } else {
      statusDot.className = 'inline-flex size-2 rounded-full bg-red-500';
      statusText.textContent = text;
      statusText.className = 'text-xs text-red-600 dark:text-red-500';
    }
  }

  /**
   * Update character count
   */
  function updateCharCount() {
    const count = chatInput.value.length;
    charCount.textContent = count;
  }

  /**
   * Handle form submission
   */
  async function handleSubmit(e) {
    e.preventDefault();

    const question = chatInput.value.trim();
    if (!question || isLoading) return;

    const model = modelSelect.value;

    // Clear input and hide welcome message
    chatInput.value = '';
    updateCharCount();
    hideWelcomeMessage();

    // Add user message
    addUserMessage(question);

    // Show loading indicator
    const loadingEl = showLoading();

    // Disable input
    setLoading(true);

    try {
      const response = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ question, model })
      });

      const data = await response.json();

      // Remove loading indicator
      removeLoading(loadingEl);

      if (response.ok && data.success) {
        // Add AI response
        addAIMessage(data.answer, data.model_used, data.response_time);
      } else {
        // Show error
        addErrorMessage(data.error || 'An error occurred', data.message);
      }
    } catch (error) {
      removeLoading(loadingEl);
      addErrorMessage('Connection Error', 'Failed to connect to AI service. Please try again.');
      console.error('AI Chat Error:', error);
    } finally {
      setLoading(false);
    }
  }

  /**
   * Add user message to chat
   */
  function addUserMessage(text) {
    const messageEl = document.createElement('div');
    messageEl.className = 'w-[700px] mx-auto py-4';
    messageEl.innerHTML = `
      <div class="flex gap-x-4">
        <span class="shrink-0 inline-flex items-center justify-center size-10 rounded-lg bg-gray-600 dark:bg-neutral-700">
          <span class="text-sm font-medium text-white">${getUserInitials()}</span>
        </span>
        <div class="grow space-y-3">
          <p class="text-gray-800 dark:text-neutral-200 whitespace-pre-wrap">${escapeHtml(text)}</p>
        </div>
      </div>
    `;
    messagesContainer.appendChild(messageEl);
    scrollToBottom();
  }

  /**
   * Add AI message to chat
   */
  function addAIMessage(text, model, responseTime) {
    const messageEl = document.createElement('div');
    messageEl.className = 'w-[700px] mx-auto py-4';

    const modelName = model.includes('mistral') ? 'Smart (Mistral)' : 'Fast (Llama)';

    messageEl.innerHTML = `
      <div class="flex gap-x-4">
        <svg class="shrink-0 size-10 rounded-lg" width="40" height="40" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect width="40" height="40" rx="8" fill="#2563EB" />
          <path d="M10 28V18.64C10 13.8683 14.0294 10 19 10C23.9706 10 28 13.8683 28 18.64C28 23.4117 23.9706 27.28 19 27.28H18.25" stroke="white" stroke-width="1.5" />
          <path d="M13 28V18.7552C13 15.5104 15.6863 12.88 19 12.88C22.3137 12.88 25 15.5104 25 18.7552C25 22 22.3137 24.6304 19 24.6304H18.25" stroke="white" stroke-width="1.5" />
          <ellipse cx="19" cy="18.6554" rx="3.75" ry="3.6" fill="white" />
        </svg>
        <div class="grow space-y-3">
          <div class="space-y-3">
            <p class="text-sm text-gray-800 dark:text-white whitespace-pre-wrap">${escapeHtml(text)}</p>
          </div>
          <div class="flex items-center gap-x-2">
            <button type="button" class="copy-btn inline-flex items-center gap-x-1 text-xs text-gray-500 hover:text-gray-800 dark:text-neutral-500 dark:hover:text-neutral-200">
              <svg class="size-3" xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                <path d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1h1v-1z"/>
                <path d="M9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5h3zm-3-1A1.5 1.5 0 0 0 5 1.5v1A1.5 1.5 0 0 0 6.5 4h3A1.5 1.5 0 0 0 11 2.5v-1A1.5 1.5 0 0 0 9.5 0h-3z"/>
              </svg>
              Copy
            </button>
            <span class="text-xs text-gray-400 dark:text-neutral-600">•</span>
            <span class="text-xs text-gray-500 dark:text-neutral-500">${modelName}</span>
            <span class="text-xs text-gray-400 dark:text-neutral-600">•</span>
            <span class="text-xs text-gray-500 dark:text-neutral-500">${responseTime}s</span>
          </div>
        </div>
      </div>
    `;

    messagesContainer.appendChild(messageEl);

    // Add copy functionality
    const copyBtn = messageEl.querySelector('.copy-btn');
    copyBtn.addEventListener('click', () => copyToClipboard(text, copyBtn));

    scrollToBottom();
  }

  /**
   * Add error message to chat
   */
  function addErrorMessage(title, details) {
    const messageEl = document.createElement('div');
    messageEl.className = 'w-[700px] mx-auto py-4';
    messageEl.innerHTML = `
      <div class="flex gap-x-4">
        <div class="shrink-0 inline-flex items-center justify-center size-10 rounded-lg bg-red-100 dark:bg-red-900/30">
          <svg class="size-5 text-red-600 dark:text-red-500" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
        </div>
        <div class="grow space-y-2">
          <h4 class="font-semibold text-red-800 dark:text-red-500">${escapeHtml(title)}</h4>
          <p class="text-sm text-gray-600 dark:text-neutral-400">${escapeHtml(details)}</p>
        </div>
      </div>
    `;
    messagesContainer.appendChild(messageEl);
    scrollToBottom();
  }

  /**
   * Show loading indicator
   */
  function showLoading() {
    const template = document.getElementById('loading-template');
    const loadingEl = template.content.cloneNode(true).firstElementChild;
    messagesContainer.appendChild(loadingEl);
    scrollToBottom();
    return messagesContainer.lastElementChild;
  }

  /**
   * Remove loading indicator
   */
  function removeLoading(loadingEl) {
    if (loadingEl && loadingEl.parentNode) {
      loadingEl.remove();
    }
  }

  /**
   * Hide welcome message
   */
  function hideWelcomeMessage() {
    if (welcomeMessage) {
      welcomeMessage.style.display = 'none';
    }
  }

  /**
   * Show welcome message
   */
  function showWelcomeMessage() {
    if (welcomeMessage) {
      welcomeMessage.style.display = 'flex';
    }
  }

  /**
   * Set loading state
   */
  function setLoading(loading) {
    isLoading = loading;
    chatInput.disabled = loading;
    sendBtn.disabled = loading;

    if (loading) {
      sendBtn.classList.add('opacity-50', 'cursor-not-allowed');
    } else {
      sendBtn.classList.remove('opacity-50', 'cursor-not-allowed');
      chatInput.focus();
    }
  }

  /**
   * Handle new chat
   */
  async function handleNewChat() {
    if (!confirm('Start a new chat? This will clear the current conversation.')) {
      return;
    }

    try {
      const response = await fetch('/api/ai/clear-history', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (response.ok) {
        // Clear messages
        messagesContainer.innerHTML = '';
        showWelcomeMessage();
        chatInput.value = '';
        updateCharCount();
      }
    } catch (error) {
      console.error('Error clearing chat:', error);
      alert('Failed to clear chat. Please refresh the page.');
    }
  }

  /**
   * Copy text to clipboard
   */
  async function copyToClipboard(text, button) {
    try {
      await navigator.clipboard.writeText(text);

      // Update button text temporarily
      const originalHTML = button.innerHTML;
      button.innerHTML = `
        <svg class="size-3" xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
          <path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z"/>
        </svg>
        Copied!
      `;
      button.classList.add('text-green-600');

      setTimeout(() => {
        button.innerHTML = originalHTML;
        button.classList.remove('text-green-600');
      }, 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
      alert('Failed to copy to clipboard');
    }
  }

  /**
   * Scroll chat to bottom
   */
  function scrollToBottom() {
    setTimeout(() => {
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }, 100);
  }

  /**
   * Get user initials from session
   */
  function getUserInitials() {
    // Try to get from meta tag or default to 'U'
    const email = document.querySelector('meta[name="user-email"]');
    if (email) {
      const parts = email.content.split('@')[0].split('.');
      return parts.map(p => p[0].toUpperCase()).join('').slice(0, 2);
    }
    return 'U';
  }

  /**
   * Escape HTML to prevent XSS
   */
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // Initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
