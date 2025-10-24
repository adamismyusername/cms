from flask import Flask, render_template, redirect, url_for, request, session, flash, send_from_directory, jsonify, make_response
from functools import wraps
from supabase import create_client, Client
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timedelta
import secrets
import auto_tagger

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Upload folder configuration
UPLOAD_FOLDER = '/app/uploads/files'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'zip', 'txt'}

# Ensure upload directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('/app/uploads/archives', exist_ok=True)
os.makedirs('/app/uploads/temp', exist_ok=True)

# Initialize Supabase
supabase: Client = create_client(
    os.environ.get('SUPABASE_URL'),
    os.environ.get('SUPABASE_ANON_KEY')
)

# Decorators
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            flash('Please login to access this page', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            flash('Please login to access this page', 'warning')
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('frontend'))
        return f(*args, **kwargs)
    return decorated

# Helper function
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Public Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Redirect if already logged in
    if 'user' in session:
        return redirect(url_for('frontend'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            # Authenticate with Supabase
            auth = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            # Get user role
            role_data = supabase.table('cms_user_roles')\
                .select('role')\
                .eq('user_id', auth.user.id)\
                .execute()

            role = role_data.data[0]['role'] if role_data.data else 'viewer'

            # Set session
            session.permanent = True
            session['user'] = {
                'id': auth.user.id,
                'email': auth.user.email
            }
            session['role'] = role

            flash(f'Welcome back, {auth.user.email}!', 'success')
            return redirect(url_for('frontend'))

        except Exception as e:
            flash('Invalid credentials', 'error')

    return render_template('login.html')

# Protected Routes
@app.route('/')
@login_required
def index():
    return redirect(url_for('frontend'))

@app.route('/frontend')
@login_required
def frontend():
    try:
        # Fetch all content ordered by most recent
        result = supabase.table('cms_content')\
            .select('*')\
            .order('created_at', desc=True)\
            .execute()

        return render_template('frontend.html', content=result.data)
    except Exception as e:
        flash(f'Error loading content: {str(e)}', 'error')
        return render_template('frontend.html', content=[])

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('You have been logged out', 'success')
    return redirect(url_for('login'))

@app.route('/search')
@login_required
def search():
    query = request.args.get('q', '')
    if query:
        try:
            # Search across title, description, and content fields
            results = supabase.table('cms_content')\
                .select("*")\
                .or_(f"title.ilike.%{query}%,description.ilike.%{query}%,content.ilike.%{query}%")\
                .order('created_at', desc=True)\
                .execute()
            return render_template('search.html', results=results.data, query=query)
        except Exception as e:
            flash(f'Search error: {str(e)}', 'error')
            return render_template('search.html', results=[], query=query)
    return render_template('search.html', results=[], query='')

@app.route('/uploads/<path:filename>')
@login_required
def serve_file(filename):
    """Serve uploaded files"""
    return send_from_directory('/app/uploads', filename)

@app.route('/download/<content_id>')
@login_required
def download_file(content_id):
    """Download a file by content ID"""
    try:
        # Get file info from database
        result = supabase.table('cms_content')\
            .select('file_url, title')\
            .eq('id', content_id)\
            .execute()

        if result.data and result.data[0].get('file_url'):
            file_url = result.data[0]['file_url']
            # Remove /uploads/ prefix to get actual path
            file_path = file_url.replace('/uploads/', '')
            return send_from_directory('/app/uploads', file_path, as_attachment=True)

        flash('File not found', 'error')
        return redirect(url_for('frontend'))

    except Exception as e:
        flash('Error downloading file', 'error')
        return redirect(url_for('frontend'))

# Admin Routes
@app.route('/backend')
@admin_required
def backend():
    try:
        # Get total content count
        total_result = supabase.table('cms_content')\
            .select('id', count='exact')\
            .execute()
        total_count = total_result.count if total_result.count else 0

        # Get file count
        file_result = supabase.table('cms_content')\
            .select('id', count='exact')\
            .eq('content_type', 'file')\
            .execute()
        file_count = file_result.count if file_result.count else 0

        # Get recent content
        recent_result = supabase.table('cms_content')\
            .select('*')\
            .order('created_at', desc=True)\
            .limit(5)\
            .execute()

        # Get recent activity
        activity_result = supabase.table('cms_activity_log')\
            .select('*')\
            .order('created_at', desc=True)\
            .limit(10)\
            .execute()

        stats = {
            'total_content': total_count,
            'file_count': file_count,
            'recent_content': recent_result.data,
            'recent_activity': activity_result.data
        }

        return render_template('backend.html', stats=stats)
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('backend.html', stats={})

@app.route('/upload', methods=['GET', 'POST'])
@admin_required
def upload():
    if request.method == 'POST':
        try:
            content_type = request.form.get('content_type')
            title = request.form.get('title')
            description = request.form.get('description')

            if not title:
                flash('Title is required', 'error')
                return redirect(url_for('upload'))

            if content_type == 'file':
                file = request.files.get('file')
                if file and allowed_file(file.filename):
                    # Create unique filename with timestamp
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    original_name = secure_filename(file.filename)
                    filename = f"{timestamp}_{original_name}"

                    # Save file to local storage
                    file_path = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(file_path)

                    # Save metadata to database
                    data = {
                        'title': title,
                        'description': description,
                        'content_type': 'file',
                        'file_url': f'/uploads/files/{filename}',
                        'created_by': session['user']['id']
                    }
                    supabase.table('cms_content').insert(data).execute()

                    # Log activity
                    supabase.table('cms_activity_log').insert({
                        'user_id': session['user']['id'],
                        'action': 'file_upload',
                        'details': f'Uploaded file: {title}'
                    }).execute()

                    flash('File uploaded successfully', 'success')
                else:
                    flash('Invalid file type', 'error')

            elif content_type in ['text', 'link', 'code']:
                # Handle text/link/code uploads
                data = {
                    'title': title,
                    'description': description,
                    'content_type': content_type,
                    'content': request.form.get('content'),
                    'url': request.form.get('url') if content_type == 'link' else None,
                    'created_by': session['user']['id']
                }
                supabase.table('cms_content').insert(data).execute()

                # Log activity
                supabase.table('cms_activity_log').insert({
                    'user_id': session['user']['id'],
                    'action': 'content_created',
                    'details': f'Created {content_type}: {title}'
                }).execute()

                flash('Content uploaded successfully', 'success')
            else:
                flash('Invalid content type', 'error')

            return redirect(url_for('frontend'))

        except Exception as e:
            flash(f'Upload error: {str(e)}', 'error')

    return render_template('upload.html')

@app.route('/edit/<content_id>', methods=['GET', 'POST'])
@admin_required
def edit(content_id):
    if request.method == 'GET':
        try:
            # Load content for editing
            result = supabase.table('cms_content')\
                .select('*')\
                .eq('id', content_id)\
                .execute()

            if not result.data:
                flash('Content not found', 'error')
                return redirect(url_for('frontend'))

            return render_template('edit.html', content=result.data[0])
        except Exception as e:
            flash(f'Error loading content: {str(e)}', 'error')
            return redirect(url_for('frontend'))

    else:  # POST
        try:
            title = request.form.get('title')
            description = request.form.get('description')
            content = request.form.get('content')
            url = request.form.get('url')

            # Update content
            update_data = {
                'title': title,
                'description': description,
                'content': content,
                'url': url,
                'updated_at': datetime.now().isoformat()
            }

            supabase.table('cms_content')\
                .update(update_data)\
                .eq('id', content_id)\
                .execute()

            # Log activity
            supabase.table('cms_activity_log').insert({
                'user_id': session['user']['id'],
                'action': 'content_updated',
                'details': f'Updated content: {title}'
            }).execute()

            flash('Content updated successfully', 'success')
            return redirect(url_for('frontend'))

        except Exception as e:
            flash(f'Update error: {str(e)}', 'error')
            return redirect(url_for('edit', content_id=content_id))

@app.route('/delete/<content_id>', methods=['POST'])
@admin_required
def delete(content_id):
    try:
        # Get content info before deletion
        result = supabase.table('cms_content')\
            .select('*')\
            .eq('id', content_id)\
            .execute()

        if result.data:
            content = result.data[0]

            # If it's a file, optionally move to archives
            if content.get('file_url'):
                # Delete from database
                supabase.table('cms_content')\
                    .delete()\
                    .eq('id', content_id)\
                    .execute()

                # Log activity
                supabase.table('cms_activity_log').insert({
                    'user_id': session['user']['id'],
                    'action': 'content_deleted',
                    'details': f'Deleted: {content.get("title")}'
                }).execute()

                flash('Content deleted successfully', 'success')
            else:
                # Delete non-file content
                supabase.table('cms_content')\
                    .delete()\
                    .eq('id', content_id)\
                    .execute()

                # Log activity
                supabase.table('cms_activity_log').insert({
                    'user_id': session['user']['id'],
                    'action': 'content_deleted',
                    'details': f'Deleted: {content.get("title")}'
                }).execute()

                flash('Content deleted successfully', 'success')
        else:
            flash('Content not found', 'error')

    except Exception as e:
        flash(f'Delete error: {str(e)}', 'error')

    return redirect(url_for('frontend'))

# ==================== QUOTES ROUTES ====================

@app.route('/quotes')
@login_required
def quotes():
    """List all quotes with filtering options"""
    try:
        # Get filter parameters
        author_filter = request.args.get('author')
        source_filter = request.args.get('source')
        tags_filter = request.args.getlist('tags')
        search_query = request.args.get('q', '').strip()

        # If search query is provided, perform search
        if search_query:
            seen_ids = set()
            quotes_data = []

            # 1. Search in quote text
            quote_text_results = supabase.table('cms_quotes')\
                .select('*, author:cms_authors!left(id, name)')\
                .ilike('quote_text', f'%{search_query}%')\
                .execute()

            for quote in quote_text_results.data:
                if quote['id'] not in seen_ids:
                    seen_ids.add(quote['id'])
                    quotes_data.append(quote)

            # 2. Search in source
            source_results = supabase.table('cms_quotes')\
                .select('*, author:cms_authors!left(id, name)')\
                .ilike('source', f'%{search_query}%')\
                .execute()

            for quote in source_results.data:
                if quote['id'] not in seen_ids:
                    seen_ids.add(quote['id'])
                    quotes_data.append(quote)

            # 3. Search in author names
            authors_with_query = supabase.table('cms_authors')\
                .select('id')\
                .ilike('name', f'%{search_query}%')\
                .execute()

            author_ids = [a['id'] for a in authors_with_query.data]
            if author_ids:
                for author_id in author_ids:
                    author_quotes = supabase.table('cms_quotes')\
                        .select('*, author:cms_authors!left(id, name)')\
                        .eq('author_id', author_id)\
                        .execute()

                    for quote in author_quotes.data:
                        if quote['id'] not in seen_ids:
                            seen_ids.add(quote['id'])
                            quotes_data.append(quote)

            # 4. Search in tags and auto_tags
            all_quotes_for_tags = supabase.table('cms_quotes')\
                .select('*, author:cms_authors!left(id, name)')\
                .execute()

            for quote in all_quotes_for_tags.data:
                if quote['id'] not in seen_ids:
                    match_found = False

                    # Check manual tags
                    if quote.get('tags'):
                        for tag in quote.get('tags', []):
                            if search_query.lower() in tag.lower():
                                match_found = True
                                break

                    # Check auto tags
                    if not match_found and quote.get('auto_tags'):
                        for tag in quote.get('auto_tags', []):
                            if search_query.lower() in tag.lower():
                                match_found = True
                                break

                    if match_found:
                        seen_ids.add(quote['id'])
                        quotes_data.append(quote)
        else:
            # Normal filtering (no search query)
            # Base query with author join
            query = supabase.table('cms_quotes')\
                .select('*, author:cms_authors!left(id, name)')

            # Apply filters
            if author_filter:
                query = query.eq('author_id', author_filter)
            if source_filter:
                query = query.eq('source', source_filter)

            # Execute query
            result = query.order('created_at', desc=True).execute()
            quotes_data = result.data

            # Client-side tag filtering (checks both tags and auto_tags)
            if tags_filter:
                filtered_quotes = []
                # Convert filter tags to lowercase for case-insensitive matching
                tags_filter_lower = [tag.lower() for tag in tags_filter]

                for quote in quotes_data:
                    quote_tags = set(quote.get('tags') or [])
                    quote_auto_tags = set(quote.get('auto_tags') or [])
                    all_quote_tags = quote_tags | quote_auto_tags

                    # Convert quote tags to lowercase for comparison
                    all_quote_tags_lower = {tag.lower() for tag in all_quote_tags}

                    # Check if all selected tags are present in either tags or auto_tags (case-insensitive)
                    if all(tag in all_quote_tags_lower for tag in tags_filter_lower):
                        filtered_quotes.append(quote)

                quotes_data = filtered_quotes

        # Get all authors for filter dropdown
        authors_result = supabase.table('cms_authors')\
            .select('id, name')\
            .order('name')\
            .execute()

        # Get unique sources for filter dropdown
        sources_result = supabase.table('cms_quotes')\
            .select('source')\
            .execute()
        unique_sources = list(set([s['source'] for s in sources_result.data if s.get('source')]))
        unique_sources.sort()

        # Get all unique tags for filter dropdown (both manual and auto)
        all_tags = set()
        for quote in supabase.table('cms_quotes').select('tags, auto_tags').execute().data:
            if quote.get('tags'):
                all_tags.update(quote.get('tags') or [])
            if quote.get('auto_tags'):
                all_tags.update(quote.get('auto_tags') or [])
        unique_tags = sorted(list(all_tags))

        # Get author name for badge display if author filter is active
        selected_author_name = None
        if author_filter:
            author_match = next((a for a in authors_result.data if a['id'] == author_filter), None)
            if author_match:
                selected_author_name = author_match['name']

        return render_template('quotes.html',
                             quotes=quotes_data,
                             authors=authors_result.data,
                             sources=unique_sources,
                             tags=unique_tags,
                             selected_author=author_filter,
                             selected_author_name=selected_author_name,
                             selected_source=source_filter,
                             selected_tags=tags_filter)
    except Exception as e:
        flash(f'Error loading quotes: {str(e)}', 'error')
        return render_template('quotes.html', quotes=[], authors=[], sources=[], tags=[])

@app.route('/quotes/search')
@login_required
def search_quotes():
    """Search quotes - redirects to main quotes page with search parameter"""
    query = request.args.get('q', '')
    return redirect(url_for('quotes', q=query))

@app.route('/quotes/<quote_id>')
@login_required
def view_quote(quote_id):
    """View a single quote with full details"""
    try:
        result = supabase.table('cms_quotes')\
            .select('*, author:cms_authors(id, name, description)')\
            .eq('id', quote_id)\
            .execute()

        if not result.data:
            flash('Quote not found', 'error')
            return redirect(url_for('quotes'))

        return render_template('quote_detail.html', quote=result.data[0])
    except Exception as e:
        flash(f'Error loading quote: {str(e)}', 'error')
        return redirect(url_for('quotes'))

@app.route('/quotes/new', methods=['GET', 'POST'])
@admin_required
def new_quote():
    """Create a new quote with author handling"""
    if request.method == 'GET':
        # Load authors for dropdown
        try:
            authors_result = supabase.table('cms_authors')\
                .select('id, name')\
                .order('name')\
                .execute()
            return render_template('quote_form.html', authors=authors_result.data, quote=None)
        except Exception as e:
            flash(f'Error loading form: {str(e)}', 'error')
            return redirect(url_for('quotes'))

    else:  # POST
        try:
            quote_text = request.form.get('quote_text')
            author_option = request.form.get('author_id')
            source = request.form.get('source')
            quote_date = request.form.get('quote_date')
            date_approximation = request.form.get('date_approximation')
            tags_input = request.form.get('tags', '')

            if not quote_text:
                flash('Quote text is required', 'error')
                return redirect(url_for('new_quote'))

            # Handle tags - normalize (lowercase, trim)
            tags = []
            if tags_input:
                tags = [tag.strip().lower() for tag in tags_input.split(',') if tag.strip()]

            # Handle author selection/creation
            author_id = None

            if author_option == 'new':
                # Creating new author
                new_author_name = request.form.get('new_author_name', '').strip()
                new_author_description = request.form.get('new_author_description', '').strip()

                if not new_author_name:
                    flash('Author name is required', 'error')
                    return redirect(url_for('new_quote'))

                # Check if author already exists (case-insensitive)
                existing_author = supabase.table('cms_authors')\
                    .select('id')\
                    .ilike('name', new_author_name)\
                    .execute()

                if existing_author.data:
                    # Use existing author
                    author_id = existing_author.data[0]['id']
                    flash(f'Author "{new_author_name}" already exists, using existing author', 'info')
                else:
                    # Create new author
                    author_data = {
                        'name': new_author_name,
                        'description': new_author_description if new_author_description else None
                    }
                    author_result = supabase.table('cms_authors').insert(author_data).execute()
                    author_id = author_result.data[0]['id']
            else:
                # Using existing author
                author_id = author_option

            if not author_id:
                flash('Author is required', 'error')
                return redirect(url_for('new_quote'))

            # Generate auto-tags
            auto_tags = auto_tagger.generate_auto_tags(quote_text)

            # Create quote
            quote_data = {
                'quote_text': quote_text,
                'author_id': author_id,
                'source': source if source else None,
                'quote_date': quote_date if quote_date else None,
                'date_approximation': date_approximation if date_approximation else None,
                'tags': tags,
                'auto_tags': auto_tags,
                'removed_auto_tags': [],
                'created_by': session['user']['id']
            }

            supabase.table('cms_quotes').insert(quote_data).execute()

            # Log activity
            supabase.table('cms_activity_log').insert({
                'user_id': session['user']['id'],
                'action': 'quote_created',
                'details': f'Created quote: {quote_text[:50]}...'
            }).execute()

            flash('Quote created successfully', 'success')
            return redirect(url_for('quotes'))

        except Exception as e:
            flash(f'Error creating quote: {str(e)}', 'error')
            return redirect(url_for('new_quote'))

@app.route('/quotes/edit/<quote_id>', methods=['GET', 'POST'])
@admin_required
def edit_quote(quote_id):
    """Edit an existing quote"""
    if request.method == 'GET':
        try:
            # Load quote
            quote_result = supabase.table('cms_quotes')\
                .select('*, author:cms_authors(id, name)')\
                .eq('id', quote_id)\
                .execute()

            if not quote_result.data:
                flash('Quote not found', 'error')
                return redirect(url_for('quotes'))

            # Load all authors for dropdown
            authors_result = supabase.table('cms_authors')\
                .select('id, name')\
                .order('name')\
                .execute()

            quote = quote_result.data[0]
            # Convert tags array to comma-separated string for form
            if quote.get('tags'):
                quote['tags_string'] = ', '.join(quote['tags'])
            else:
                quote['tags_string'] = ''

            return render_template('quote_form.html', quote=quote, authors=authors_result.data)
        except Exception as e:
            flash(f'Error loading quote: {str(e)}', 'error')
            return redirect(url_for('quotes'))

    else:  # POST
        try:
            quote_text = request.form.get('quote_text')
            author_id = request.form.get('author_id')
            source = request.form.get('source')
            quote_date = request.form.get('quote_date')
            date_approximation = request.form.get('date_approximation')
            tags_input = request.form.get('tags', '')

            if not quote_text or not author_id:
                flash('Quote text and author are required', 'error')
                return redirect(url_for('edit_quote', quote_id=quote_id))

            # Handle tags - normalize
            tags = []
            if tags_input:
                tags = [tag.strip().lower() for tag in tags_input.split(',') if tag.strip()]

            # Get existing removed_auto_tags to respect user's choices
            existing_quote = supabase.table('cms_quotes')\
                .select('removed_auto_tags')\
                .eq('id', quote_id)\
                .execute()

            removed_auto_tags = (existing_quote.data[0].get('removed_auto_tags') or []) if existing_quote.data else []

            # Regenerate auto-tags (respecting removed tags)
            auto_tags = auto_tagger.generate_auto_tags(quote_text, removed_auto_tags)

            # Update quote
            update_data = {
                'quote_text': quote_text,
                'author_id': author_id,
                'source': source if source else None,
                'quote_date': quote_date if quote_date else None,
                'date_approximation': date_approximation if date_approximation else None,
                'tags': tags,
                'auto_tags': auto_tags
            }

            supabase.table('cms_quotes')\
                .update(update_data)\
                .eq('id', quote_id)\
                .execute()

            # Log activity
            supabase.table('cms_activity_log').insert({
                'user_id': session['user']['id'],
                'action': 'quote_updated',
                'details': f'Updated quote: {quote_text[:50]}...'
            }).execute()

            flash('Quote updated successfully', 'success')
            return redirect(url_for('quotes'))

        except Exception as e:
            flash(f'Error updating quote: {str(e)}', 'error')
            return redirect(url_for('edit_quote', quote_id=quote_id))

@app.route('/quotes/delete/<quote_id>', methods=['POST'])
@admin_required
def delete_quote(quote_id):
    """Delete a quote"""
    try:
        # Get quote info before deletion
        result = supabase.table('cms_quotes')\
            .select('quote_text')\
            .eq('id', quote_id)\
            .execute()

        if result.data:
            quote_text = result.data[0]['quote_text']

            # Delete quote and verify deletion
            delete_result = supabase.table('cms_quotes')\
                .delete()\
                .eq('id', quote_id)\
                .execute()

            # Verify the quote was actually deleted
            verify_result = supabase.table('cms_quotes')\
                .select('id')\
                .eq('id', quote_id)\
                .execute()

            if verify_result.data and len(verify_result.data) > 0:
                # Quote still exists - deletion failed
                flash('Error: Quote deletion failed. This may be due to database permissions. Please contact your administrator.', 'error')
                print(f"DEBUG: Quote {quote_id} deletion failed - quote still exists after delete operation")
            else:
                # Quote successfully deleted
                # Log activity
                try:
                    supabase.table('cms_activity_log').insert({
                        'user_id': session['user']['id'],
                        'action': 'quote_deleted',
                        'details': f'Deleted quote: {quote_text[:50]}...'
                    }).execute()
                except Exception as log_error:
                    print(f"Warning: Failed to log deletion: {log_error}")

                flash('Quote deleted successfully', 'success')
        else:
            flash('Quote not found', 'error')

    except Exception as e:
        flash(f'Error deleting quote: {str(e)}', 'error')
        print(f"DEBUG: Exception during quote deletion: {str(e)}")

    return redirect(url_for('quotes'))

@app.route('/quotes/<quote_id>/remove-auto-tag', methods=['POST'])
@admin_required
def remove_auto_tag(quote_id):
    """Remove an auto-tag from a quote (admin only)"""
    try:
        data = request.get_json()
        tag_to_remove = data.get('tag')

        if not tag_to_remove:
            return jsonify({'success': False, 'error': 'Tag is required'}), 400

        # Get current quote data
        quote_result = supabase.table('cms_quotes')\
            .select('auto_tags, removed_auto_tags')\
            .eq('id', quote_id)\
            .execute()

        if not quote_result.data:
            return jsonify({'success': False, 'error': 'Quote not found'}), 404

        quote = quote_result.data[0]
        current_auto_tags = quote.get('auto_tags') or []
        current_removed_tags = quote.get('removed_auto_tags') or []

        # Normalize tag (lowercase)
        tag_to_remove_lower = tag_to_remove.lower()

        # Check if tag exists in auto_tags
        if tag_to_remove_lower not in [t.lower() for t in current_auto_tags]:
            return jsonify({'success': False, 'error': 'Tag not found in auto_tags'}), 400

        # Remove from auto_tags
        new_auto_tags = [t for t in current_auto_tags if t.lower() != tag_to_remove_lower]

        # Add to removed_auto_tags if not already there
        if tag_to_remove_lower not in [t.lower() for t in current_removed_tags]:
            new_removed_tags = current_removed_tags + [tag_to_remove_lower]
        else:
            new_removed_tags = current_removed_tags

        # Update quote
        update_data = {
            'auto_tags': new_auto_tags,
            'removed_auto_tags': new_removed_tags
        }

        supabase.table('cms_quotes')\
            .update(update_data)\
            .eq('id', quote_id)\
            .execute()

        # Log activity
        supabase.table('cms_activity_log').insert({
            'user_id': session['user']['id'],
            'action': 'auto_tag_removed',
            'details': f'Removed auto-tag "{tag_to_remove}" from quote {quote_id}'
        }).execute()

        return jsonify({'success': True, 'message': 'Auto-tag removed successfully'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== AUTO-TAGGING ADMIN ROUTES ====================

@app.route('/quotes/admin/auto-tags')
@admin_required
def auto_tag_admin():
    """Admin page for managing auto-tagging"""
    try:
        # Get statistics
        all_quotes = supabase.table('cms_quotes')\
            .select('auto_tags')\
            .execute()

        stats = auto_tagger.get_tag_statistics(all_quotes.data)

        return render_template('auto_tag_admin.html', stats=stats)
    except Exception as e:
        flash(f'Error loading auto-tag admin: {str(e)}', 'error')
        return redirect(url_for('quotes'))

@app.route('/quotes/admin/reload-keywords', methods=['POST'])
@admin_required
def reload_keywords():
    """Reload keyword mappings from CSV file"""
    try:
        count = auto_tagger.reload_keyword_mappings()

        # Log activity
        supabase.table('cms_activity_log').insert({
            'user_id': session['user']['id'],
            'action': 'auto_tag_keywords_reloaded',
            'details': f'Reloaded {count} keyword mappings'
        }).execute()

        flash(f'Successfully reloaded {count} keyword mappings', 'success')
    except Exception as e:
        flash(f'Error reloading keywords: {str(e)}', 'error')

    return redirect(url_for('auto_tag_admin'))

@app.route('/quotes/admin/reprocess-all', methods=['POST'])
@admin_required
def reprocess_all_quotes():
    """Reprocess all quotes to regenerate auto-tags"""
    try:
        # Get all quotes
        all_quotes = supabase.table('cms_quotes')\
            .select('id, quote_text, removed_auto_tags')\
            .execute()

        processed_count = 0
        error_count = 0

        for quote in all_quotes.data:
            try:
                # Generate new auto-tags
                removed_tags = quote.get('removed_auto_tags') or []
                new_auto_tags = auto_tagger.generate_auto_tags(quote['quote_text'], removed_tags)

                # Update the quote
                supabase.table('cms_quotes')\
                    .update({'auto_tags': new_auto_tags})\
                    .eq('id', quote['id'])\
                    .execute()

                processed_count += 1
            except Exception as e:
                print(f"Error processing quote {quote['id']}: {e}")
                error_count += 1

        # Log activity
        supabase.table('cms_activity_log').insert({
            'user_id': session['user']['id'],
            'action': 'auto_tag_bulk_reprocess',
            'details': f'Reprocessed {processed_count} quotes ({error_count} errors)'
        }).execute()

        if error_count > 0:
            flash(f'Reprocessed {processed_count} quotes with {error_count} errors', 'warning')
        else:
            flash(f'Successfully reprocessed {processed_count} quotes', 'success')

    except Exception as e:
        flash(f'Error reprocessing quotes: {str(e)}', 'error')

    return redirect(url_for('auto_tag_admin'))

# ==================== AUTHOR ROUTES ====================

@app.route('/authors/<author_id>')
@login_required
def author_profile(author_id):
    """View author profile with all their quotes"""
    try:
        # Get author info
        author_result = supabase.table('cms_authors')\
            .select('*')\
            .eq('id', author_id)\
            .execute()

        if not author_result.data:
            flash('Author not found', 'error')
            return redirect(url_for('quotes'))

        # Get all quotes by this author
        quotes_result = supabase.table('cms_quotes')\
            .select('*')\
            .eq('author_id', author_id)\
            .order('created_at', desc=True)\
            .execute()

        return render_template('author_profile.html',
                             author=author_result.data[0],
                             quotes=quotes_result.data)
    except Exception as e:
        flash(f'Error loading author: {str(e)}', 'error')
        return redirect(url_for('quotes'))

@app.route('/authors/new', methods=['GET', 'POST'])
@admin_required
def new_author():
    """Create a new author"""
    if request.method == 'GET':
        return render_template('author_form.html', author=None)

    else:  # POST
        try:
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()

            if not name:
                flash('Author name is required', 'error')
                return redirect(url_for('new_author'))

            # Check if author already exists
            existing = supabase.table('cms_authors')\
                .select('id')\
                .ilike('name', name)\
                .execute()

            if existing.data:
                flash(f'Author "{name}" already exists', 'error')
                return redirect(url_for('new_author'))

            # Create author
            author_data = {
                'name': name,
                'description': description if description else None
            }

            result = supabase.table('cms_authors').insert(author_data).execute()

            # Log activity
            supabase.table('cms_activity_log').insert({
                'user_id': session['user']['id'],
                'action': 'author_created',
                'details': f'Created author: {name}'
            }).execute()

            flash('Author created successfully', 'success')
            return redirect(url_for('author_profile', author_id=result.data[0]['id']))

        except Exception as e:
            flash(f'Error creating author: {str(e)}', 'error')
            return redirect(url_for('new_author'))

@app.route('/authors/edit/<author_id>', methods=['GET', 'POST'])
@admin_required
def edit_author(author_id):
    """Edit an existing author"""
    if request.method == 'GET':
        try:
            result = supabase.table('cms_authors')\
                .select('*')\
                .eq('id', author_id)\
                .execute()

            if not result.data:
                flash('Author not found', 'error')
                return redirect(url_for('quotes'))

            return render_template('author_form.html', author=result.data[0])
        except Exception as e:
            flash(f'Error loading author: {str(e)}', 'error')
            return redirect(url_for('quotes'))

    else:  # POST
        try:
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()

            if not name:
                flash('Author name is required', 'error')
                return redirect(url_for('edit_author', author_id=author_id))

            # Check if another author with this name exists
            existing = supabase.table('cms_authors')\
                .select('id')\
                .ilike('name', name)\
                .neq('id', author_id)\
                .execute()

            if existing.data:
                flash(f'Another author with name "{name}" already exists', 'error')
                return redirect(url_for('edit_author', author_id=author_id))

            # Update author
            update_data = {
                'name': name,
                'description': description if description else None
            }

            supabase.table('cms_authors')\
                .update(update_data)\
                .eq('id', author_id)\
                .execute()

            # Log activity
            supabase.table('cms_activity_log').insert({
                'user_id': session['user']['id'],
                'action': 'author_updated',
                'details': f'Updated author: {name}'
            }).execute()

            flash('Author updated successfully', 'success')
            return redirect(url_for('author_profile', author_id=author_id))

        except Exception as e:
            flash(f'Error updating author: {str(e)}', 'error')
            return redirect(url_for('edit_author', author_id=author_id))

# ==================== API ENDPOINTS FOR CHROME EXTENSION ====================

# CORS decorator for API endpoints
def add_cors_headers(response):
    """Add CORS headers to response"""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

# API authentication decorator
def api_auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            response = jsonify({'error': 'Missing or invalid authorization header'})
            response.status_code = 401
            return add_cors_headers(response)

        token = auth_header.replace('Bearer ', '')

        # Validate token - it's just the user's session token
        # Check if it exists in our extension_tokens table or validate session
        try:
            # For simplicity, we'll store extension tokens in a simple dict in session
            # In production, you'd want to store these in a database table
            result = supabase.table('cms_extension_tokens')\
                .select('user_id')\
                .eq('token', token)\
                .single()\
                .execute()

            if not result.data:
                response = jsonify({'error': 'Invalid token'})
                response.status_code = 401
                return add_cors_headers(response)

            # Add user_id to request context
            request.user_id = result.data['user_id']

        except Exception as e:
            response = jsonify({'error': 'Token validation failed'})
            response.status_code = 401
            return add_cors_headers(response)

        return f(*args, **kwargs)
    return decorated

# Handle OPTIONS requests for CORS preflight
@app.route('/api/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    response = make_response('', 204)
    return add_cors_headers(response)

@app.route('/api/get-extension-token', methods=['GET'])
@login_required
def get_extension_token():
    """Generate and return an auth token for the Chrome extension"""
    try:
        # Generate a random token
        token = secrets.token_urlsafe(32)

        # Store token in database (you'll need to create this table)
        # For now, we'll try to insert, and if the table doesn't exist, we'll note it
        try:
            supabase.table('cms_extension_tokens').insert({
                'token': token,
                'user_id': session['user']['id'],
                'created_at': datetime.now().isoformat()
            }).execute()
        except Exception as e:
            # Table might not exist - create a simple in-memory solution for now
            print(f"Warning: Could not store token in database: {e}")
            # In this case, we'll just return the session-based approach
            token = f"session_{session['user']['id']}_{secrets.token_urlsafe(16)}"

        response = jsonify({
            'token': token,
            'user_id': session['user']['id'],
            'email': session['user']['email']
        })
        return add_cors_headers(response)

    except Exception as e:
        response = jsonify({'error': str(e)})
        response.status_code = 500
        return add_cors_headers(response)

@app.route('/api/validate-token', methods=['GET'])
def validate_token():
    """Validate an extension token"""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            response = jsonify({'valid': False, 'error': 'Missing authorization header'})
            return add_cors_headers(response)

        token = auth_header.replace('Bearer ', '')

        # Check if token exists in database
        try:
            result = supabase.table('cms_extension_tokens')\
                .select('user_id')\
                .eq('token', token)\
                .single()\
                .execute()

            if result.data:
                # Token exists - validation successful
                response = jsonify({
                    'valid': True,
                    'user_id': result.data['user_id']
                })
                return add_cors_headers(response)
        except Exception as e:
            # Log the error for debugging
            print(f"Token validation error: {e}")

        response = jsonify({'valid': False})
        return add_cors_headers(response)

    except Exception as e:
        print(f"Validation endpoint error: {e}")
        response = jsonify({'valid': False, 'error': str(e)})
        return add_cors_headers(response)

@app.route('/api/quote', methods=['POST'])
@api_auth_required
def api_create_quote():
    """Create a new quote via API"""
    try:
        data = request.get_json()

        # Validate required fields
        if not data.get('quote_text'):
            response = jsonify({'error': 'quote_text is required'})
            response.status_code = 400
            return add_cors_headers(response)

        # Handle author - either existing or new
        author_id = None

        if data.get('author_id'):
            author_id = data['author_id']
        elif data.get('author_name'):
            # Check if author exists
            existing_author = supabase.table('cms_authors')\
                .select('id')\
                .ilike('name', data['author_name'])\
                .execute()

            if existing_author.data:
                author_id = existing_author.data[0]['id']
            else:
                # Create new author
                new_author = supabase.table('cms_authors').insert({
                    'name': data['author_name']
                }).execute()
                author_id = new_author.data[0]['id']
        else:
            response = jsonify({'error': 'author_id or author_name is required'})
            response.status_code = 400
            return add_cors_headers(response)

        # Generate auto-tags
        auto_tags = auto_tagger.generate_auto_tags(data['quote_text'])

        # Create quote
        quote_data = {
            'quote_text': data['quote_text'],
            'author_id': author_id,
            'source': data.get('source'),
            'quote_date': data.get('quote_date'),
            'date_approximation': data.get('date_approximation'),
            'user_notes': data.get('user_notes'),
            'surrounding_context': data.get('surrounding_context'),
            'auto_tags': auto_tags,
            'removed_auto_tags': [],
            'created_by': request.user_id
        }

        result = supabase.table('cms_quotes').insert(quote_data).execute()

        # Log activity
        supabase.table('cms_activity_log').insert({
            'user_id': request.user_id,
            'action': 'quote_created_via_extension',
            'details': f'Created quote via extension: {data["quote_text"][:50]}...'
        }).execute()

        response = jsonify({
            'success': True,
            'quote_id': result.data[0]['id'],
            'message': 'Quote saved successfully'
        })
        return add_cors_headers(response)

    except Exception as e:
        response = jsonify({'error': str(e)})
        response.status_code = 500
        return add_cors_headers(response)

@app.route('/api/authors/search', methods=['GET'])
@api_auth_required
def api_search_authors():
    """Search for authors"""
    try:
        query = request.args.get('q', '').strip()

        if len(query) < 2:
            response = jsonify({'authors': []})
            return add_cors_headers(response)

        # Search authors
        result = supabase.table('cms_authors')\
            .select('id, name')\
            .ilike('name', f'%{query}%')\
            .order('name')\
            .limit(10)\
            .execute()

        response = jsonify({'authors': result.data})
        return add_cors_headers(response)

    except Exception as e:
        response = jsonify({'error': str(e)})
        response.status_code = 500
        return add_cors_headers(response)

@app.route('/api/quotes/recent', methods=['GET'])
@api_auth_required
def api_recent_quotes():
    """Get recent quotes for the current user"""
    try:
        # Get last 5 quotes by this user
        result = supabase.table('cms_quotes')\
            .select('id, quote_text, created_at, author:cms_authors(name)')\
            .eq('created_by', request.user_id)\
            .order('created_at', desc=True)\
            .limit(5)\
            .execute()

        # Format response
        quotes = []
        for quote in result.data:
            quotes.append({
                'id': quote['id'],
                'quote_text': quote['quote_text'],
                'author_name': quote['author']['name'] if quote.get('author') else 'Unknown',
                'created_at': quote['created_at']
            })

        response = jsonify({'quotes': quotes})
        return add_cors_headers(response)

    except Exception as e:
        response = jsonify({'error': str(e)})
        response.status_code = 500
        return add_cors_headers(response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
