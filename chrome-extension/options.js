// Options script for CMS Quote Capture extension

const API_BASE_URL = 'http://localhost:8090';

// Initialize options page
document.addEventListener('DOMContentLoaded', async () => {
  // Load saved token if exists
  const storage = await chrome.storage.sync.get(['authToken']);
  if (storage.authToken) {
    document.getElementById('authToken').value = storage.authToken;
    updateStatus('Token saved', 'success');
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
    const isValid = await validateToken(token);

    if (isValid) {
      // Save to Chrome storage
      await chrome.storage.sync.set({ authToken: token });
      showMessage('Token saved and validated successfully!', 'success');
      updateStatus('Token active and valid', 'success');
    } else {
      showMessage('Token is invalid. Please check and try again.', 'error');
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
    const isValid = await validateToken(token);

    if (isValid) {
      showMessage('Token is valid!', 'success');
      updateStatus('Token is valid', 'success');
    } else {
      showMessage('Token is invalid', 'error');
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

    if (!response.ok) {
      return false;
    }

    const data = await response.json();
    return data.valid === true;
  } catch (error) {
    console.error('Validation error:', error);
    throw new Error('Unable to connect to CMS. Make sure it is running.');
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
