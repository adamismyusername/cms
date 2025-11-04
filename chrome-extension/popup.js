// Popup script for CMS Quote Capture extension

const API_BASE_URL = 'http://localhost:8090';
let authToken = null;
let selectedAuthorId = null;
let debounceTimer = null;

// Initialize popup when DOM is ready
document.addEventListener('DOMContentLoaded', async () => {
  // Load auth token from storage
  const storage = await chrome.storage.sync.get(['authToken']);
  authToken = storage.authToken;

  if (!authToken) {
    showStatusBanner('invalid', 'No authentication token configured. Please set up your token.', true);
    document.getElementById('saveBtn').disabled = true;
    return;
  }

  // Validate token with API
  const isValid = await validateAuthToken();
  if (!isValid) {
    showStatusBanner('invalid', 'Authentication token is invalid or expired. Please update your token.', true);
    document.getElementById('saveBtn').disabled = true;
    return;
  }

  // Token is valid - show success banner
  showStatusBanner('valid', 'Authentication active - Ready to save quotes', false);

  // Load pending quote data from storage
  const local = await chrome.storage.local.get(['pendingQuote']);
  if (local.pendingQuote) {
    populateForm(local.pendingQuote);
  }

  // Set up event listeners
  setupEventListeners();
});

/**
 * Populate form with quote data
 */
function populateForm(quoteData) {
  document.getElementById('quoteText').value = quoteData.quoteText || '';
  document.getElementById('context').value = quoteData.surroundingContext || '';
  document.getElementById('source').value = quoteData.source || '';
}

/**
 * Set up event listeners
 */
function setupEventListeners() {
  // Form submission
  document.getElementById('quoteForm').addEventListener('submit', handleSubmit);

  // Cancel button
  document.getElementById('cancelBtn').addEventListener('click', () => {
    window.close();
  });

  // Open options button (in status banner)
  const openOptionsBtn = document.getElementById('openOptionsBtn');
  if (openOptionsBtn) {
    openOptionsBtn.addEventListener('click', openExtensionOptions);
  }

  // Author autocomplete
  const authorInput = document.getElementById('author');
  authorInput.addEventListener('input', handleAuthorInput);
  authorInput.addEventListener('blur', () => {
    // Delay hiding suggestions to allow click
    setTimeout(() => {
      document.getElementById('authorSuggestions').classList.add('hidden');
    }, 200);
  });
}

/**
 * Validate auth token with API
 */
async function validateAuthToken() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/validate-token`, {
      headers: {
        'Authorization': `Bearer ${authToken}`
      }
    });

    if (!response.ok) {
      return false;
    }

    const data = await response.json();
    return data.valid === true;
  } catch (error) {
    console.error('Token validation error:', error);
    return false;
  }
}

/**
 * Show status banner
 */
function showStatusBanner(type, message, showOpenOptions) {
  const banner = document.getElementById('tokenStatusBanner');
  const textDiv = document.getElementById('tokenStatusText');
  const actionsDiv = document.getElementById('tokenStatusActions');

  // Set message
  textDiv.textContent = message;

  // Set styling based on type
  banner.className = 'status-banner ' + type;

  // Show/hide open options button
  if (showOpenOptions) {
    actionsDiv.classList.remove('hidden');
  } else {
    actionsDiv.classList.add('hidden');
  }

  // Show banner
  banner.classList.remove('hidden');
}

/**
 * Handle authentication errors (401)
 */
function handleAuthError() {
  showStatusBanner('invalid', 'Your authentication token has expired or is invalid. Please update your token.', true);
  showError('Authentication failed. Please update your token in extension options.');
  document.getElementById('saveBtn').disabled = true;
}

/**
 * Open extension options page
 */
function openExtensionOptions() {
  chrome.runtime.openOptionsPage();
}

/**
 * Handle author input with debouncing
 */
function handleAuthorInput(e) {
  const query = e.target.value.trim();

  // Clear previous timer
  if (debounceTimer) {
    clearTimeout(debounceTimer);
  }

  // Clear selected author ID when typing
  selectedAuthorId = null;
  document.getElementById('authorId').value = '';

  // Reset hint
  const hint = document.getElementById('authorHint');
  if (query.length < 2) {
    hint.textContent = 'Type 2+ characters to search';
    document.getElementById('authorSuggestions').classList.add('hidden');
    return;
  }

  // Debounce search (300ms)
  debounceTimer = setTimeout(async () => {
    await searchAuthors(query);
  }, 300);
}

/**
 * Search for authors via API
 */
async function searchAuthors(query) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/authors/search?q=${encodeURIComponent(query)}`, {
      headers: {
        'Authorization': `Bearer ${authToken}`
      }
    });

    // Check for authentication error
    if (response.status === 401) {
      handleAuthError();
      document.getElementById('authorHint').textContent = 'Authentication expired';
      return;
    }

    if (!response.ok) {
      throw new Error('Failed to search authors');
    }

    const data = await response.json();
    displayAuthorSuggestions(data.authors || []);
  } catch (error) {
    console.error('Author search error:', error);
    document.getElementById('authorHint').textContent = 'Error searching authors';
  }
}

/**
 * Display author suggestions dropdown
 */
function displayAuthorSuggestions(authors) {
  const suggestionsDiv = document.getElementById('authorSuggestions');
  const hint = document.getElementById('authorHint');

  if (authors.length === 0) {
    hint.textContent = 'No matches found - will create new author';
    suggestionsDiv.classList.add('hidden');
    return;
  }

  hint.textContent = `${authors.length} author(s) found`;

  // Build suggestions HTML
  suggestionsDiv.innerHTML = authors.map(author => `
    <div class="suggestion-item" data-author-id="${author.id}" data-author-name="${author.name}">
      ${author.name}
    </div>
  `).join('');

  // Add click handlers
  suggestionsDiv.querySelectorAll('.suggestion-item').forEach(item => {
    item.addEventListener('click', () => {
      selectAuthor(item.dataset.authorId, item.dataset.authorName);
    });
  });

  suggestionsDiv.classList.remove('hidden');
}

/**
 * Select an author from suggestions
 */
function selectAuthor(authorId, authorName) {
  selectedAuthorId = authorId;
  document.getElementById('author').value = authorName;
  document.getElementById('authorId').value = authorId;
  document.getElementById('authorSuggestions').classList.add('hidden');
  document.getElementById('authorHint').textContent = 'Author selected';
}

/**
 * Handle form submission
 */
async function handleSubmit(e) {
  e.preventDefault();

  // Get form values
  const quoteText = document.getElementById('quoteText').value.trim();
  const author = document.getElementById('author').value.trim();
  const source = document.getElementById('source').value.trim();
  const quoteDate = document.getElementById('quoteDate').value;
  const dateApproximation = document.getElementById('dateApproximation').value.trim();
  const userNotes = document.getElementById('userNotes').value.trim();
  const surroundingContext = document.getElementById('context').value.trim();

  // Validation
  if (!quoteText) {
    showError('Quote text is required');
    return;
  }
  if (!author) {
    showError('Author is required');
    return;
  }

  // Disable save button
  const saveBtn = document.getElementById('saveBtn');
  saveBtn.disabled = true;
  saveBtn.textContent = 'Saving...';

  // Prepare data for API
  const quoteData = {
    quote_text: quoteText,
    surrounding_context: surroundingContext || null,
    source: source || null,
    quote_date: quoteDate || null,
    date_approximation: dateApproximation || null,
    user_notes: userNotes || null
  };

  // Add author info
  if (selectedAuthorId) {
    quoteData.author_id = selectedAuthorId;
  } else {
    quoteData.author_name = author;
  }

  try {
    // Save quote via API
    const response = await fetch(`${API_BASE_URL}/api/quote`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authToken}`
      },
      body: JSON.stringify(quoteData)
    });

    // Check for authentication error
    if (response.status === 401) {
      handleAuthError();
      return;
    }

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || 'Failed to save quote');
    }

    const result = await response.json();

    // Show success message
    showSuccess('Quote saved successfully!');

    // Show browser notification
    chrome.notifications.create({
      type: 'basic',
      iconUrl: 'icons/icon48.png',
      title: 'Quote Saved!',
      message: `Quote by ${author} saved to CMS`
    });

    // Load and display recent quotes
    await loadRecentQuotes();

    // Reset form for next quote
    resetForm();

  } catch (error) {
    console.error('Save error:', error);
    showError(error.message || 'Failed to save quote. Please try again.');
  } finally {
    saveBtn.disabled = false;
    saveBtn.textContent = 'Save Quote';
  }
}

/**
 * Load recent quotes from API
 */
async function loadRecentQuotes() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/quotes/recent`, {
      headers: {
        'Authorization': `Bearer ${authToken}`
      }
    });

    // Check for authentication error
    if (response.status === 401) {
      handleAuthError();
      return;
    }

    if (!response.ok) {
      throw new Error('Failed to load recent quotes');
    }

    const data = await response.json();
    displayRecentQuotes(data.quotes || []);
  } catch (error) {
    console.error('Error loading recent quotes:', error);
  }
}

/**
 * Display recent quotes
 */
function displayRecentQuotes(quotes) {
  const recentQuotesDiv = document.getElementById('recentQuotes');
  const listDiv = document.getElementById('recentQuotesList');

  if (quotes.length === 0) {
    recentQuotesDiv.classList.add('hidden');
    return;
  }

  // Build quotes HTML
  listDiv.innerHTML = quotes.map(quote => `
    <div class="quote-item">
      <p class="quote-text">"${quote.quote_text}"</p>
      <p class="quote-author">— ${quote.author_name}</p>
      <p class="quote-meta">${new Date(quote.created_at).toLocaleString()}</p>
    </div>
  `).join('');

  recentQuotesDiv.classList.remove('hidden');
}

/**
 * Reset form for next quote
 */
function resetForm() {
  document.getElementById('quoteText').value = '';
  document.getElementById('author').value = '';
  document.getElementById('authorId').value = '';
  document.getElementById('quoteDate').value = '';
  document.getElementById('dateApproximation').value = '';
  document.getElementById('userNotes').value = '';
  selectedAuthorId = null;
  document.getElementById('authorHint').textContent = 'Type 2+ characters to search';
}

/**
 * Show error message
 */
function showError(message) {
  const errorDiv = document.getElementById('errorMessage');
  errorDiv.textContent = message;
  errorDiv.classList.remove('hidden');

  const successDiv = document.getElementById('successMessage');
  successDiv.classList.add('hidden');
}

/**
 * Show success message
 */
function showSuccess(message) {
  const successDiv = document.getElementById('successMessage');
  successDiv.textContent = message;
  successDiv.classList.remove('hidden');

  const errorDiv = document.getElementById('errorMessage');
  errorDiv.classList.add('hidden');
}
