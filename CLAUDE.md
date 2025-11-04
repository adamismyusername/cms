# CLAUDE.md

**Version:** 0.0.2
**Last Updated:** 2025-11-04 at 5:45 AM PST

---

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Goldco CMS is a content management system built with Flask and Supabase, featuring:
- Quote management with auto-tagging capabilities
- Author database and search
- File upload and management system
- Chrome extension for capturing quotes from web pages
- Background worker for scheduled tasks (stats logging, cleanup)
- **AI-powered chat interface with local LLM integration** (Mistral 7B and Llama 3.2 3B models)
- Integration with external goldco-ai service for AI capabilities

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

**Note:** The application depends on the external `goldco-ai` service for AI chat functionality. Ensure the goldco-ai containers are running before starting the CMS. The AI service may take 30-60 seconds to fully initialize on startup.

### Environment Setup

- Copy `.env` file and configure:
  - `SUPABASE_URL` and `SUPABASE_ANON_KEY` (Supabase credentials)
  - `SECRET_KEY` (Flask session key)
  - `FLASK_ENV` (development/production)
  - `AI_API_URL` (optional, defaults to http://goldco-api:8080) - URL for goldco-ai API service
  - `GITHUB_USER`, `GITHUB_REPO`, `GITHUB_BRANCH`, `GITHUB_PAT` (GitHub integration for deployment/version tracking)

### Database Migrations

Run SQL migrations manually in Supabase SQL Editor:
- `database/migrations/add_auto_tags.sql` - Adds auto-tagging columns to quotes table
- `chrome-extension/setup-database.sql` - Creates extension token authentication table
- `chrome-extension/fix-rls-policies.sql` - Fixes Row Level Security policies

## Architecture

### Core Components

**Flask Application (`app/app.py`)**
- Single monolithic Flask app with ~1500+ lines
- Session-based authentication via Supabase Auth
- Role-based access control (admin/viewer)
- Four main sections: Frontend (public), Backend (admin), Quotes system, AI Chat
- API endpoints for Chrome extension integration
- AI API proxy for chat functionality

**AI Chat Interface (`/ai-chat`, `app/static/js/ai-chat.js`)**
- **Admin-only** chat interface for interacting with local LLM models
- **Two AI Models:**
  - **Smart Model**: Mistral 7B (30-60 second response time, more accurate)
  - **Fast Model**: Llama 3.2 3B (10-15 second response time, faster responses)
- **Features:**
  - Real-time AI service health monitoring with visual status indicator
  - Session-based chat history (last 20 messages stored in Flask session)
  - Response metrics display (model used, response time)
  - Copy responses to clipboard
  - Model selection during conversation
  - Clear chat history to start new conversations
  - Character counter for input tracking
  - Auto-resizing textarea for input
  - Graceful error handling for timeouts and connection failures
  - Activity logging for all AI queries
- **Integration:**
  - Connects to external `goldco-ai` API service via Docker networking
  - Uses goldco-ai_default external network
  - 2-minute timeout for slow model responses
  - Health check endpoint polls AI service status

**Worker Service (`app/worker.py`)**
- APScheduler-based background worker running in separate container
- Stats logging job (every 6 hours)
- Activity log cleanup job (every 24 hours, removes logs >90 days)
- Runs initial stats collection on startup

**Auto-Tagging System (`app/auto_tagger.py`)**
- CSV-driven keyword-to-tag mapping (`app/data/auto-tag-keywords.csv`)
- In-memory cache for keyword mappings
- Whole-word, case-insensitive keyword matching with regex
- Tracks user-removed tags to prevent reapplication
- Supports hot-reload of keyword mappings without restart

**Chrome Extension (`chrome-extension/`)**
- Captures highlighted text from any webpage via context menu
- Token-based authentication (7-day validity)
- Live author search with autocomplete (2+ characters)
- Inline author creation directly from extension
- Automatic context extraction (surrounding paragraph)
- Recent quotes view in popup (last 5 quotes)
- Browser notifications for save confirmations
- Token validation testing from options page
- Multiple metadata fields: date, approximation, notes, source URL

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
- `/backend` - Admin dashboard with stats, activity log, recent uploads
- `/upload` - File upload form
- `/edit/<content_id>` - Content editing
- `/delete/<content_id>` - Content deletion

**Quotes System Routes** (login_required)
- `/quotes` - Quote browser with filtering/sorting
- `/quotes/search` - Quote search across text, authors, sources, tags
- `/quotes/<quote_id>` - Quote detail view
- `/quotes/new` - Create new quote
- `/quotes/edit/<quote_id>` - Edit quote
- `/quotes/delete/<quote_id>` - Delete quote
- `/quotes/<quote_id>/remove-auto-tag` - Remove individual auto-tag
- `/quotes/admin/auto-tags` - Auto-tag administration dashboard with statistics
- `/quotes/admin/reload-keywords` - Hot-reload keyword CSV
- `/quotes/admin/reprocess-all` - Reprocess all quotes for auto-tags

**Author Routes** (login_required)
- `/authors/<author_id>` - Author profile with quote list
- `/authors/new` - Create new author
- `/authors/edit/<author_id>` - Edit author

**AI Routes** (admin_required)
- `/ai-chat` - AI chat interface for interacting with LLM models
- `/api/ai/health` - Check AI service availability and status
- `/api/ai/chat` - Proxy chat requests to goldco-ai API
- `/api/ai/clear-history` - Clear session chat history

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
   - 7-day persistent sessions

2. **Chrome Extension**: Token-based
   - User logs into web app, clicks "Extension Token" button
   - Token stored in `cms_extension_tokens` table with 7-day expiration
   - Extension validates token on each API request via `validate_extension_token()` helper
   - Expired tokens automatically cleaned up via SQL function

### Data Storage

**Supabase Tables**
- `cms_content` - General content items and files
  - Columns: id, title, content_type, content, description, file_name, file_size, created_at, updated_at, created_by
- `cms_user_roles` - User role assignments (admin/viewer)
  - Columns: id, user_id, role, created_at
- `cms_activity_log` - Activity tracking (cleaned up after 90 days)
  - Columns: id, user_id, action, details, created_at
- `cms_quotes` - Quote storage with manual and auto-tags
  - Columns: id, text, author_id, source, date, date_approximation, tags (manual), auto_tags (auto-generated), removed_auto_tags (user-removed), user_notes (why saved), surrounding_context (full paragraph), created_at, updated_at, created_by
- `cms_authors` - Author profiles
  - Columns: id, name, description, created_at, updated_at
- `cms_extension_tokens` - Chrome extension auth tokens
  - Columns: id, user_id, token, expires_at, created_at

**File System**
- `/app/uploads/files` - User-uploaded files
- `/app/uploads/archives` - Archived files (not actively used)
- `/app/uploads/temp` - Temporary file storage
- `/app/data/auto-tag-keywords.csv` - Keyword-to-tag mappings for auto-tagging
- `/app/static/js/ai-chat.js` - AI chat interface JavaScript

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
9. Admin dashboard shows auto-tag statistics: coverage, frequency, top tags

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
5. User searches for author with autocomplete (2+ characters required)
6. User can create new author inline if not found
7. User fills optional fields: date, approximation, notes, source URL
8. Quote saved via POST to `/api/quote`
9. Browser notification confirms save
10. Last 5 quotes displayed in popup for reference

**Token Management**:
- Tokens generated from web app at `/api/get-extension-token`
- Stored in extension storage (not Chrome sync)
- Validated before each API request
- Can test token validity from options page
- Auto-prompts for new token when expired

### Docker Architecture

The application uses a multi-container Docker setup:

**Containers:**
1. **cms-app** (Flask application)
   - Main web application on port 8090
   - Runs Flask development server with live reload
   - Volume mounts for code changes without rebuild

2. **cms-worker** (Background worker)
   - Same image as cms-app with different entrypoint
   - Runs `worker.py` with APScheduler
   - Shares database connection with main app

**Networking:**
- Default internal network for cms-app and cms-worker communication
- External `goldco-ai_default` network for AI service integration
- Port mapping: 8090:80 (host:container)

**Volume Mounts:**
- `./app:/app/app` - Live code reloading for Flask app
- `./database:/app/database` - Database migration scripts
- `./uploads:/app/uploads` - Persistent file storage

**Image:**
- Single Dockerfile builds image for both app and worker
- Python 3.11 base image
- All dependencies from `requirements.txt`
- Different containers use same image with command override

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
- AI chat interface shows graceful error messages for timeouts/failures

### Template Structure
- Base template: `templates/base.html`
- Jinja2 templates with includes in `templates/includes/`
- Templates use Bootstrap for styling (in `static/`)
- Dark mode support throughout UI

### Activity Logging
- All major actions logged to `cms_activity_log` table
- Includes: uploads, creates, updates, deletes, AI queries, auto-tag operations
- Automatically cleaned up after 90 days by worker
- Displayed on admin dashboard for recent activity monitoring

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
- AI service must be running on goldco-ai_default network for chat functionality
- AI service startup can take 30-60 seconds to initialize models

## Chrome Extension Development

To test extension changes:
1. Edit files in `chrome-extension/`
2. Go to `chrome://extensions/`
3. Click reload icon on the extension card
4. Test the changes

Extension must be loaded as "unpacked" from the `chrome-extension/` folder.

---

## How to Update This Claude.md File

This section provides instructions for keeping this documentation up-to-date. Update this file whenever significant features, routes, or architectural changes are made to the application.

### When to Update

Update this file when:
- New features are added (new routes, pages, functionality)
- Existing features are significantly modified
- Database schema changes (new tables, columns, or relationships)
- Architecture changes (new services, Docker configuration, external integrations)
- Development workflow changes (new commands, environment variables, setup steps)
- After major refactoring that changes how components work

### How to Update

1. **Increment Version Number** (at top of file)
   - Format: `X.Y.Z` (e.g., 0.0.2)
   - Increment rules:
     - `X` (major): Complete rewrite or major architecture changes
     - `Y` (minor): New features, new sections, significant additions
     - `Z` (patch): Small updates, corrections, clarifications
   - Current version: **0.0.2**

2. **Update Timestamp** (at top of file)
   - Format: `YYYY-MM-DD at HH:MM AM/PM TIMEZONE`
   - Example: `2025-11-04 at 10:45 AM PST`
   - Update whenever any changes are made

3. **Review and Update Sections**
   - **Project Overview**: Add/remove bullet points for major features
   - **Development Commands**: Update commands if Docker setup or environment changes
   - **Environment Setup**: Add new environment variables
   - **Core Components**: Add new major components or update descriptions
   - **Route Organization**: Add new routes in appropriate sections
   - **Data Storage**: Update table schemas when columns/tables change
   - **Architecture sections**: Update flows, patterns, or workflows
   - **Key Patterns**: Document new conventions or standards

4. **Use Clear, Concise Language**
   - Write for developers who are new to the codebase
   - Include file paths and line numbers where helpful (e.g., `app/app.py:715`)
   - Use code blocks for examples
   - Organize with clear headers and bullet points

5. **Verify Accuracy**
   - Test that commands actually work
   - Verify route paths match actual routes in `app.py`
   - Check that database schema matches actual Supabase tables
   - Ensure environment variables are correctly named

### Example Update Workflow

```bash
# 1. Make changes to codebase (e.g., add new feature)
# 2. Open CLAUDE.md
# 3. Update version: 0.0.2 -> 0.0.3
# 4. Update timestamp: 2025-11-04 at 10:45 AM PST
# 5. Add new feature to Project Overview
# 6. Add new routes to Route Organization section
# 7. Update relevant architecture sections
# 8. Save and commit with descriptive message
```

### Tips for Maintaining Quality

- Keep descriptions concise but complete
- Maintain consistent formatting throughout
- Group related items logically
- Use the existing sections as templates
- Don't let the file get stale - update it regularly
- When in doubt, provide more detail rather than less
- Include "why" along with "what" for non-obvious decisions
