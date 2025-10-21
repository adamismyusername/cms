// Background service worker for CMS Quote Capture extension

// Create context menu on install
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'save-quote-to-cms',
    title: 'Save Quote to CMS',
    contexts: ['selection']
  });
});

// Handle context menu click
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === 'save-quote-to-cms') {
    // Send message to content script to capture quote details
    chrome.tabs.sendMessage(tab.id, {
      action: 'captureQuote',
      selectedText: info.selectionText
    });
  }
});

// Listen for messages from content script (to open popup)
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'openPopup') {
    // Store the quote data temporarily
    chrome.storage.local.set({ pendingQuote: request.quoteData }, () => {
      // Open popup in a new window
      chrome.windows.create({
        url: 'popup.html',
        type: 'popup',
        width: 500,
        height: 700
      });
    });
  }
});
