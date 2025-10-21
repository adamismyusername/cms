# CMS Quote Capture - Chrome Extension

A Chrome extension that allows you to capture quotes from any webpage and save them directly to the Goldco CMS database.

## Features

- Right-click context menu on highlighted text
- Capture quote with surrounding context
- Live author search with autocomplete
- Create new authors on the fly
- Save quotes with optional metadata (date, notes, tags)
- View last 5 saved quotes
- Browser notifications for save confirmations

## Installation & Setup

### 1. Database Setup

First, create the required database table in Supabase:

1. Log in to your Supabase project dashboard
2. Go to the SQL Editor
3. Copy the contents of `setup-database.sql`
4. Run the SQL to create the `cms_extension_tokens` table

### 2. Chrome Extension Installation

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select the `chrome-extension` folder (this folder)
5. The extension should now appear in your extensions list

### 3. Get Your Auth Token

1. Start the CMS server: `docker-compose up` (or however you run it)
2. Open http://localhost:8090 in your browser
3. Log in to the CMS
4. Click the "Extension Token" button in the header
5. The token will be copied to your clipboard

### 4. Configure the Extension

1. Right-click the extension icon in Chrome
2. Click "Options"
3. Paste your auth token in the field
4. Click "Save Token"
5. The extension will validate the token

## Usage

### Capturing a Quote

1. Navigate to any webpage
2. Highlight the text you want to save as a quote
3. Right-click the highlighted text
4. Click "Save Quote to CMS"
5. A popup window will open with the quote form
6. Fill in the details:
   - **Quote Text** (required, pre-filled): Edit if needed
   - **Surrounding Context** (auto-captured): Full paragraph containing the quote
   - **Author** (required): Type to search existing authors, or enter a new name
   - **Source URL** (optional): Pre-filled with page URL
   - **Quote Date** (optional): Date the quote was said/written
   - **Date Approximation** (optional): For approximate dates like "circa 1995"
   - **Notes** (optional): Why you saved this quote
7. Click "Save Quote"
8. You'll see a browser notification confirming the save
9. The popup will show your last 5 saved quotes

### Tips

- The extension automatically captures the full paragraph containing your selection
- If an author doesn't exist, the extension will create it automatically
- All HTML formatting is stripped from captured quotes (plain text only)
- Tokens are valid for 7 days - you'll need to refresh after expiration

## File Structure

```
chrome-extension/
├── manifest.json          # Extension configuration
├── background.js          # Service worker (context menu handler)
├── content.js             # Text capture logic
├── popup.html             # Quote form UI
├── popup.js               # Form logic and API calls
├── options.html           # Token setup page
├── options.js             # Token storage logic
├── styles.css             # Extension styling
├── icons/                 # Extension icons
│   ├── icon16.png
│   ├── icon48.png
│   └── icon128.png
├── setup-database.sql     # Database migration
└── README.md              # This file
```

## API Endpoints

The extension communicates with these CMS API endpoints:

- `GET /api/get-extension-token` - Generate auth token
- `GET /api/validate-token` - Validate token
- `POST /api/quote` - Save new quote
- `GET /api/authors/search?q={query}` - Search authors
- `GET /api/quotes/recent` - Get last 5 quotes

## Troubleshooting

### Extension won't save quotes

- Check that the CMS is running (http://localhost:8090)
- Verify your token is still valid (click "Test Token" in options)
- Check browser console for errors (F12 → Console tab)

### Author autocomplete not working

- Make sure you've typed at least 2 characters
- Check that you're logged in to the CMS
- Verify the API endpoint is accessible

### Context menu doesn't appear

- Make sure you've selected/highlighted text
- Try reloading the page
- Check that the extension is enabled in chrome://extensions/

### Token expired

- Click "Extension Token" in the CMS header again
- Get a new token and update it in extension options
- Tokens last 7 days by default

## Development

To modify the extension:

1. Edit the files in this folder
2. Go to `chrome://extensions/`
3. Click the reload icon on the extension card
4. Test your changes

## Icon Placeholders

The `icons/` folder currently has placeholder files. To add proper icons:

1. Create PNG images: 16x16, 48x48, and 128x128 pixels
2. Use a quote-themed design (quote marks, book, etc.)
3. Replace the placeholder files in the `icons/` folder
4. Reload the extension

## Notes

- This extension is for internal use only
- Works with localhost:8090 by default
- Add production URL to manifest.json host_permissions for deployment
- Simple paragraph extraction - finds nearest `<p>` tag
- Can be improved based on real-world testing
