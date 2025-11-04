// Content script for CMS Quote Capture extension

// Listen for messages from background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'captureQuote') {
    const quoteData = captureQuoteData(request.selectedText);

    // Send data back to background script to open popup
    chrome.runtime.sendMessage({
      action: 'openPopup',
      quoteData: quoteData
    });
  }
});

/**
 * Capture quote data from the current page
 * @param {string} selectedText - The text selected by the user
 * @returns {object} Quote data including text, context, source, etc.
 */
function captureQuoteData(selectedText) {
  // Strip HTML and get plain text
  const quoteText = stripHtml(selectedText);

  // Get surrounding context - find nearest <p> parent
  const surroundingContext = getSurroundingContext();

  // Get page metadata
  const pageUrl = window.location.href;
  const pageTitle = document.title;

  return {
    quoteText: quoteText,
    surroundingContext: surroundingContext,
    source: pageUrl,
    pageTitle: pageTitle
  };
}

/**
 * Strip HTML tags and return plain text
 * @param {string} html - HTML string
 * @returns {string} Plain text
 */
function stripHtml(html) {
  const tmp = document.createElement('div');
  tmp.innerHTML = html;
  return tmp.textContent || tmp.innerText || '';
}

/**
 * Get surrounding context by finding the nearest <p> tag parent
 * @returns {string} Paragraph text containing the selection
 */
function getSurroundingContext() {
  const selection = window.getSelection();
  if (!selection.rangeCount) return '';

  // Get the anchor node (where selection starts)
  let node = selection.anchorNode;

  // If it's a text node, get its parent element
  if (node.nodeType === Node.TEXT_NODE) {
    node = node.parentElement;
  }

  // Walk up the DOM tree to find the nearest <p> tag
  let paragraphElement = node;
  while (paragraphElement && paragraphElement.tagName !== 'P') {
    paragraphElement = paragraphElement.parentElement;

    // Stop at body to avoid infinite loop
    if (paragraphElement === document.body || !paragraphElement) {
      break;
    }
  }

  // If we found a <p> tag, return its text content
  if (paragraphElement && paragraphElement.tagName === 'P') {
    return paragraphElement.textContent.trim();
  }

  // Fallback: return empty or the selected text itself
  return '';
}
