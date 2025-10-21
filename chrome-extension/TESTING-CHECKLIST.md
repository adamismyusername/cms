# Chrome Extension Testing Checklist

Complete this checklist to verify the extension works correctly.

## Pre-Testing Setup

- [ ] Run database migration (`setup-database.sql` in Supabase SQL Editor)
- [ ] CMS is running at http://localhost:8090
- [ ] Docker containers are up: `docker-compose up`
- [ ] Extension is loaded in Chrome (`chrome://extensions/` → Load unpacked)

## Initial Setup Tests

### 1. Database Table Creation
- [ ] Table `cms_extension_tokens` exists in Supabase
- [ ] Table has correct columns: id, token, user_id, created_at, expires_at
- [ ] RLS policies are enabled

### 2. Get Auth Token
- [ ] Log in to CMS at http://localhost:8090
- [ ] "Extension Token" button appears in header
- [ ] Click button → Token is copied to clipboard
- [ ] Alert shows with instructions
- [ ] Button shows "✓ Copied!" confirmation

### 3. Extension Installation
- [ ] Extension loads without errors
- [ ] Extension icon appears in Chrome toolbar
- [ ] Right-click extension icon → "Options" is available

### 4. Token Configuration
- [ ] Open extension options (right-click icon → Options)
- [ ] Paste token in auth token field
- [ ] Click "Save Token" → Success message appears
- [ ] Click "Test Token" → "Token is valid!" message
- [ ] Status shows "Token active and valid"

## Core Functionality Tests

### 5. Basic Quote Capture
- [ ] Navigate to any webpage (e.g., https://en.wikipedia.org)
- [ ] Highlight some text
- [ ] Right-click highlighted text
- [ ] "Save Quote to CMS" appears in context menu
- [ ] Click menu item → Popup window opens
- [ ] Quote text is pre-filled with selected text
- [ ] Source URL is pre-filled with page URL

### 6. Author Autocomplete - Existing Author
- [ ] In popup, type 2+ characters in Author field
- [ ] Dropdown shows matching authors (if any exist)
- [ ] Click an author from dropdown
- [ ] Author field populates with selected name
- [ ] Hint shows "Author selected"

### 7. Author Autocomplete - New Author
- [ ] Type a name that doesn't exist (e.g., "Test Author 123")
- [ ] Hint shows "No matches found - will create new author"
- [ ] Continue to save (tested in next section)

### 8. Save Quote with Existing Author
- [ ] Fill in all required fields (quote + existing author)
- [ ] Optionally fill: date, date approximation, notes
- [ ] Click "Save Quote"
- [ ] Button shows "Saving..." temporarily
- [ ] Browser notification: "Quote saved!"
- [ ] Success message appears in popup
- [ ] "Last 5 Quotes" section appears
- [ ] Saved quote shows in the list

### 9. Save Quote with New Author
- [ ] Clear form or capture new quote
- [ ] Enter new author name (not in system)
- [ ] Save quote
- [ ] Quote saves successfully
- [ ] New author is created in CMS
- [ ] Verify in CMS: Author appears in authors list

### 10. Surrounding Context Capture
- [ ] Capture a quote from within a paragraph
- [ ] Check "Surrounding Context" field
- [ ] Should show full paragraph containing selection
- [ ] Context should be readonly (can't edit)

### 11. Optional Fields
- [ ] Save quote with only required fields (quote + author)
- [ ] Verify it saves successfully
- [ ] Save quote with all optional fields filled:
  - [ ] Source URL
  - [ ] Quote Date
  - [ ] Date Approximation
  - [ ] User Notes
- [ ] Verify all fields save to database

### 12. Recent Quotes Display
- [ ] After saving a quote, "Last 5 Quotes" section shows
- [ ] Most recent quote appears at top
- [ ] Shows: quote text, author name, timestamp
- [ ] Save 5+ quotes → Only last 5 appear
- [ ] Quotes are for current user only

## Edge Cases & Error Handling

### 13. Empty Selection
- [ ] Don't select any text on a page
- [ ] Right-click anywhere
- [ ] "Save Quote to CMS" should NOT appear

### 14. Form Validation
- [ ] Open popup, clear quote text field
- [ ] Try to save → Error: "Quote text is required"
- [ ] Fill quote, clear author
- [ ] Try to save → Error: "Author is required"

### 15. Network Errors
- [ ] Stop CMS server: `docker-compose down`
- [ ] Try to save a quote
- [ ] Error message appears
- [ ] Notification shows error
- [ ] Restart CMS, try again → Works

### 16. Invalid Token
- [ ] Go to extension options
- [ ] Enter random invalid token
- [ ] Click "Test Token" → "Token is invalid"
- [ ] Try to save quote → Error about invalid token

### 17. Expired Token
- [ ] (Manual test after 7 days, or modify DB)
- [ ] Try to save quote with expired token
- [ ] Should show error
- [ ] Get new token and update options

### 18. Different HTML Structures
Test paragraph extraction on various sites:
- [ ] Wikipedia article
- [ ] Blog post
- [ ] News article
- [ ] Documentation page
- [ ] If `<p>` not found, context should be empty (not crash)

### 19. Special Characters
- [ ] Capture quote with special chars: "quotes", 'apostrophes', & symbols
- [ ] Unicode characters: émojis, ñ, ü
- [ ] Long text (500+ words)
- [ ] All should save correctly without corruption

### 20. Multiple Quotes in Session
- [ ] Save 3-4 quotes in a row without closing popup
- [ ] Each should save successfully
- [ ] "Last 5 Quotes" should update each time
- [ ] Form should reset after each save

## CMS Integration Tests

### 21. Verify in CMS Database
- [ ] Log in to CMS web interface
- [ ] Navigate to Quotes page
- [ ] Find recently saved quotes from extension
- [ ] All fields match what was entered
- [ ] `surrounding_context` field populated
- [ ] `user_notes` field populated

### 22. Author Creation
- [ ] Check Authors list in CMS
- [ ] Verify new authors created by extension appear
- [ ] Click author name → Profile shows quotes from extension

### 23. Activity Log
- [ ] Check CMS activity log (if visible)
- [ ] Should show "quote_created_via_extension" actions

## Performance & UX

### 24. Speed
- [ ] Popup opens quickly (<1 second)
- [ ] Author autocomplete responds quickly (<500ms after typing stops)
- [ ] Save operation completes in reasonable time (<2 seconds)

### 25. UI/UX
- [ ] All text is readable
- [ ] Form fields are appropriately sized
- [ ] Buttons are clearly labeled
- [ ] Error messages are helpful
- [ ] Success messages are clear

## Browser Compatibility

### 26. Chrome Version
- [ ] Test on latest Chrome stable
- [ ] Extension installs and runs without warnings

## Final Verification

### 27. End-to-End Flow
- [ ] Fresh start: Clear extension data
- [ ] Get new token from CMS
- [ ] Set up extension
- [ ] Capture quote from real website
- [ ] Save with new author
- [ ] Verify in CMS
- [ ] Capture another quote with same author
- [ ] Complete flow works smoothly

---

## Issues Found

Document any issues encountered during testing:

1. **Issue**:
   **Steps to reproduce**:
   **Expected**:
   **Actual**:
   **Severity**:

---

## Sign-Off

- [ ] All critical tests passed
- [ ] Major issues documented and/or fixed
- [ ] Extension ready for use

**Tested by**: ________________
**Date**: ________________
**Chrome version**: ________________
