# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Goldco CMS is a content management system built with Flask and Supabase, featuring:
- Quote management with auto-tagging capabilities
- Author database and search
- File upload and management system
- Chrome extension for capturing quotes from web pages
- Background worker for scheduled tasks (stats logging, cleanup)

## Development Commands

### Running the Application

```bash
# Start both CMS app and worker
docker-compose up

# Start in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

The CMS will be available at http://localhost:8090

### Environment Setup

- Copy `.env` file and configure:
  - `SUPABASE_URL` and `SUPABASE_ANON_KEY` (Supabase credentials)
  - `SECRET_KEY` (Flask session key)
  - `FLASK_ENV` (development/production)
  - `GITHUB_USER`, `GITHUB_REPO`, `GITHUB_BRANCH`, `GITHUB_PAT` (GitHub integration)

### Database Migrations

Run SQL migrations manually in Supabase SQL Editor:
- `database/migrations/add_auto_tags.sql` - Adds auto-tagging columns to quotes table
- `chrome-extension/setup-database.sql` - Creates extension token authentication table
- `chrome-extension/fix-rls-policies.sql` - Fixes Row Level Security policies

## Architecture

### Core Components

**Flask Application (`app/app.py`)**
- Single monolithic Flask app with ~1400 lines
- Session-based authentication via Supabase Auth
- Role-based access control (admin/viewer)
- Three main sections: Frontend (public), Backend (admin), Quotes system
- API endpoints for Chrome extension integration

**Worker Service (`app/worker.py`)**
- APScheduler-based background worker running in separate container
- Stats logging job (every 6 hours)
- Activity log cleanup job (every 24 hours, removes logs >90 days)

**Auto-Tagging System (`app/auto_tagger.py`)**
- CSV-driven keyword-to-tag mapping (`app/data/auto-tag-keywords.csv`)
- In-memory cache for keyword mappings
- Whole-word, case-insensitive keyword matching with regex
- Tracks user-removed tags to prevent reapplication
- Supports hot-reload of keyword mappings without restart

**Chrome Extension (`chrome-extension/`)**
- Captures highlighted text from any webpage via context menu
- Token-based authentication (7-day validity)
- Live author search with autocomplete
- Automatic context extraction (surrounding paragraph)
- Recent quotes view in popup

### Route Organization

The Flask app is organized into logical sections:

**Public Routes**
- `/login` - Supabase authentication

**Protected Frontend Routes** (login_required)
- `/` and `/frontend` - Main content browser
- `/search` - Content search
- `/uploads/<filename>` - File serving
- `/download/<content_id>` - File downloads

**Admin Routes** (admin_required)
- `/backend` - Admin dashboard
- `/upload` - File upload form
- `/edit/<content_id>` - Content editing
- `/delete/<content_id>` - Content deletion

**Quotes System Routes** (login_required)
- `/quotes` - Quote browser with filtering/sorting
- `/quotes/search` - Quote search
- `/quotes/<quote_id>` - Quote detail view
- `/quotes/new` - Create new quote
- `/quotes/edit/<quote_id>` - Edit quote
- `/quotes/delete/<quote_id>` - Delete quote
- `/quotes/<quote_id>/remove-auto-tag` - Remove individual auto-tag
- `/quotes/admin/auto-tags` - Auto-tag administration dashboard
- `/quotes/admin/reload-keywords` - Hot-reload keyword CSV
- `/quotes/admin/reprocess-all` - Reprocess all quotes for auto-tags

**Author Routes** (login_required)
- `/authors/<author_id>` - Author profile with quote list
- `/authors/new` - Create new author
- `/authors/edit/<author_id>` - Edit author

**API Routes** (for Chrome Extension)
- `/api/get-extension-token` - Generate 7-day auth token (login_required)
- `/api/validate-token` - Validate token (token auth)
- `/api/quote` - Save new quote (token auth)
- `/api/authors/search?q=<query>` - Author autocomplete (token auth)
- `/api/quotes/recent` - Get last 5 quotes (token auth)

### Authentication Flow

1. **Web App**: Session-based via Supabase Auth
   - Login creates session with user ID, email, and role
   - Role fetched from `cms_user_roles` table
   - Decorators: `@login_required` and `@admin_required`

2. **Chrome Extension**: Token-based
   - User logs into web app, clicks "Extension Token" button
   - Token stored in `cms_extension_tokens` table with 7-day expiration
   - Extension validates token on each API request via `validate_extension_token()` helper

### Data Storage

**Supabase Tables**
- `cms_content` - General content items and files
- `cms_user_roles` - User role assignments (admin/viewer)
- `cms_activity_log` - Activity tracking (cleaned up after 90 days)
- `cms_quotes` - Quote storage with auto_tags and removed_auto_tags arrays
- `cms_authors` - Author profiles
- `cms_extension_tokens` - Chrome extension auth tokens

**File System**
- `/app/uploads/files` - User-uploaded files
- `/app/uploads/archives` - Archived files (not actively used)
- `/app/uploads/temp` - Temporary file storage
- `/app/data/auto-tag-keywords.csv` - Keyword-to-tag mappings for auto-tagging

### Auto-Tagging System

The auto-tagging system automatically applies tags to quotes based on keyword matching:

1. Keywords and their associated tags are defined in CSV format
2. Module loads CSV into memory cache on startup
3. When quotes are created/edited, text is scanned for keywords
4. Matching keywords trigger their associated tags to be applied
5. Users can remove individual auto-tags, which are tracked in `removed_auto_tags`
6. Removed tags will not be reapplied on subsequent edits
7. Admin can hot-reload CSV without restart via `/quotes/admin/reload-keywords`
8. Admin can reprocess all quotes via `/quotes/admin/reprocess-all`

**Key Functions**:
- `load_keyword_mappings()` - Load CSV into cache
- `extract_keywords()` - Find matching keywords in text using regex
- `generate_auto_tags()` - Generate tags for quote, excluding removed ones

### Chrome Extension Architecture

The extension consists of multiple components:

1. **Content Script (`content.js`)**: Captures selected text and surrounding context
2. **Background Service Worker (`background.js`)**: Handles context menu creation
3. **Popup (`popup.html/js`)**: Quote submission form with author autocomplete
4. **Options Page (`options.html/js`)**: Token configuration and validation

**Quote Capture Flow**:
1. User highlights text and right-clicks
2. Context menu item "Save Quote to CMS" appears
3. Content script extracts text + surrounding paragraph
4. Popup opens with pre-filled quote form
5. User searches for author (or creates new one)
6. Quote saved via POST to `/api/quote`
7. Browser notification confirms save
8. Last 5 quotes displayed in popup

## Key Patterns and Conventions

### File Upload Handling
- Files are validated against `ALLOWED_EXTENSIONS` whitelist
- Filenames are sanitized with `secure_filename()`
- 16MB max file size enforced
- Files stored with original names in `/app/uploads/files`
- File metadata stored in `cms_content` table with `content_type='file'`

### Error Handling
- Flash messages used for user feedback (success/error/warning)
- Try-catch blocks around Supabase operations
- Extension uses browser notifications for save confirmations

### Template Structure
- Base template: `templates/base.html`
- Jinja2 templates with includes in `templates/includes/`
- Templates use Bootstrap for styling (in `static/`)

### CSV Format for Auto-Tagging
```csv
keyword,tags
gold,"gold, precious metals"
inflation,"inflation, economy"
```
- Keywords are case-insensitive and matched as whole words
- Tags are comma-separated and normalized to lowercase
- File location: `app/data/auto-tag-keywords.csv`

## Development Notes

- The app runs inside Docker containers with volume mounts for live code reloading
- Worker container runs `worker.py` via command override in docker-compose
- Both containers share the same image built from Dockerfile
- Logs are visible via `docker-compose logs -f`
- Direct Flask development (outside Docker) requires Python 3.11 and packages from `requirements.txt`

## Chrome Extension Development

To test extension changes:
1. Edit files in `chrome-extension/`
2. Go to `chrome://extensions/`
3. Click reload icon on the extension card
4. Test the changes

Extension must be loaded as "unpacked" from the `chrome-extension/` folder.
