// Options script for CMS Quote Capture extension

const API_BASE_URL = 'http://localhost:8090';

// Initialize options page
document.addEventListener('DOMContentLoaded', async () => {
  // Load saved token if exists
  const storage = await chrome.storage.sync.get(['authToken', 'lastValidated']);
  if (storage.authToken) {
    document.getElementById('authToken').value = storage.authToken;

    // Check if we have last validation timestamp
    const lastValidated = storage.lastValidated;
    if (lastValidated) {
      const timeAgo = getTimeAgo(new Date(lastValidated));
      updateStatus(`Token saved (validated ${timeAgo})`, 'success');
    } else {
      updateStatus('Token saved (not yet validated)', 'success');
    }
  }

  // Set up event listeners
  setupEventListeners();
});

/**
 * Set up event listeners
 */
function setupEventListeners() {
  // Form submission
  document.getElementById('optionsForm').addEventListener('submit', handleSave);

  // Test token button
  document.getElementById('testBtn').addEventListener('click', handleTest);

  // Toggle password visibility
  document.getElementById('toggleToken').addEventListener('click', toggleTokenVisibility);
}

/**
 * Handle save token
 */
async function handleSave(e) {
  e.preventDefault();

  const token = document.getElementById('authToken').value.trim();

  if (!token) {
    showMessage('Please enter a token', 'error');
    return;
  }

  // Disable buttons
  const saveBtn = document.getElementById('saveBtn');
  saveBtn.disabled = true;
  saveBtn.textContent = 'Saving...';

  try {
    // Validate token with API
    const validationResult = await validateToken(token);

    if (validationResult.valid) {
      // Save to Chrome storage with timestamp
      await chrome.storage.sync.set({
        authToken: token,
        lastValidated: new Date().toISOString()
      });
      showMessage('Token saved and validated successfully!', 'success');
      updateStatus('Token active and valid (just now)', 'success');
    } else {
      // Show specific error message
      const errorMsg = validationResult.error || 'Token is invalid. Please check and try again.';
      showMessage(errorMsg, 'error');
      updateStatus('Invalid token', 'error');
    }
  } catch (error) {
    console.error('Save error:', error);
    showMessage('Error validating token: ' + error.message, 'error');
  } finally {
    saveBtn.disabled = false;
    saveBtn.textContent = 'Save Token';
  }
}

/**
 * Handle test token
 */
async function handleTest() {
  const token = document.getElementById('authToken').value.trim();

  if (!token) {
    showMessage('Please enter a token to test', 'error');
    return;
  }

  const testBtn = document.getElementById('testBtn');
  testBtn.disabled = true;
  testBtn.textContent = 'Testing...';

  try {
    const validationResult = await validateToken(token);

    if (validationResult.valid) {
      showMessage('Token is valid!', 'success');
      updateStatus('Token is valid (just tested)', 'success');
    } else {
      const errorMsg = validationResult.error || 'Token is invalid';
      showMessage(errorMsg, 'error');
      updateStatus('Invalid token', 'error');
    }
  } catch (error) {
    console.error('Test error:', error);
    showMessage('Error testing token: ' + error.message, 'error');
  } finally {
    testBtn.disabled = false;
    testBtn.textContent = 'Test Token';
  }
}

/**
 * Validate token with API
 */
async function validateToken(token) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/validate-token`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (response.status === 401) {
      return {
        valid: false,
        error: 'Token is unauthorized or has expired. Please generate a new token from the CMS.'
      };
    }

    if (!response.ok) {
      return {
        valid: false,
        error: `Server error (${response.status}). Please try again.`
      };
    }

    const data = await response.json();
    return {
      valid: data.valid === true,
      error: data.error || null
    };
  } catch (error) {
    console.error('Validation error:', error);
    throw new Error('Unable to connect to CMS. Make sure it is running at http://localhost:8090');
  }
}

/**
 * Toggle token visibility
 */
function toggleTokenVisibility() {
  const tokenInput = document.getElementById('authToken');
  const toggleBtn = document.getElementById('toggleToken');

  if (tokenInput.type === 'password') {
    tokenInput.type = 'text';
    toggleBtn.textContent = 'Hide';
  } else {
    tokenInput.type = 'password';
    toggleBtn.textContent = 'Show';
  }
}

/**
 * Show message
 */
function showMessage(message, type) {
  const messageDiv = document.getElementById('statusMessage');
  messageDiv.textContent = message;
  messageDiv.className = `message ${type}`;
  messageDiv.classList.remove('hidden');
}

/**
 * Update status display
 */
function updateStatus(message, type) {
  const statusDiv = document.getElementById('tokenStatus');
  statusDiv.textContent = message;
  statusDiv.className = type;
}

/**
 * Get human-readable time ago string
 */
function getTimeAgo(date) {
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'just now';
  if (diffMins === 1) return '1 minute ago';
  if (diffMins < 60) return `${diffMins} minutes ago`;
  if (diffHours === 1) return '1 hour ago';
  if (diffHours < 24) return `${diffHours} hours ago`;
  if (diffDays === 1) return '1 day ago';
  return `${diffDays} days ago`;
}
