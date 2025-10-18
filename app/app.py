from flask import Flask, render_template, redirect, url_for, request, session, flash, send_from_directory
from functools import wraps
from supabase import create_client, Client
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timedelta
import secrets

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

        # Base query with author join
        query = supabase.table('cms_quotes')\
            .select('*, author:cms_authors!left(id, name)')

        # Apply filters
        if author_filter:
            query = query.eq('author_id', author_filter)
        if source_filter:
            query = query.eq('source', source_filter)
        if tags_filter:
            # Filter by tags - quotes must contain all selected tags
            for tag in tags_filter:
                query = query.contains('tags', [tag])

        # Execute query
        result = query.order('created_at', desc=True).execute()
        quotes_data = result.data

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

        # Get all unique tags for filter dropdown
        all_tags = set()
        for quote in supabase.table('cms_quotes').select('tags').execute().data:
            if quote.get('tags'):
                all_tags.update(quote['tags'])
        unique_tags = sorted(list(all_tags))

        return render_template('quotes.html',
                             quotes=quotes_data,
                             authors=authors_result.data,
                             sources=unique_sources,
                             tags=unique_tags,
                             selected_author=author_filter,
                             selected_source=source_filter,
                             selected_tags=tags_filter)
    except Exception as e:
        flash(f'Error loading quotes: {str(e)}', 'error')
        return render_template('quotes.html', quotes=[], authors=[], sources=[], tags=[])

@app.route('/quotes/search')
@login_required
def search_quotes():
    """Search quotes by text, author, source, or tags"""
    query = request.args.get('q', '')
    if query:
        try:
            # Search across quote_text, author name, source, and tags
            # Note: Supabase doesn't easily support cross-table text search in one query,
            # so we'll do multiple queries and combine results

            # Search in quote text, source
            quotes_result = supabase.table('cms_quotes')\
                .select('*, author:cms_authors(id, name)')\
                .or_(f"quote_text.ilike.%{query}%,source.ilike.%{query}%")\
                .order('created_at', desc=True)\
                .execute()

            # Search in author names
            authors_with_query = supabase.table('cms_authors')\
                .select('id')\
                .ilike('name', f'%{query}%')\
                .execute()

            # Get quotes by matching authors
            author_ids = [a['id'] for a in authors_with_query.data]
            author_quotes = []
            if author_ids:
                for author_id in author_ids:
                    aq_result = supabase.table('cms_quotes')\
                        .select('*, author:cms_authors(id, name)')\
                        .eq('author_id', author_id)\
                        .execute()
                    author_quotes.extend(aq_result.data)

            # Combine results (remove duplicates by id)
            all_quotes = quotes_result.data + author_quotes
            seen_ids = set()
            unique_quotes = []
            for quote in all_quotes:
                if quote['id'] not in seen_ids:
                    seen_ids.add(quote['id'])
                    unique_quotes.append(quote)

            # Also check tags
            all_quotes_for_tags = supabase.table('cms_quotes')\
                .select('*, author:cms_authors(id, name)')\
                .execute()

            for quote in all_quotes_for_tags.data:
                if quote['id'] not in seen_ids and quote.get('tags'):
                    # Check if query matches any tag
                    for tag in quote['tags']:
                        if query.lower() in tag.lower():
                            unique_quotes.append(quote)
                            seen_ids.add(quote['id'])
                            break

            return render_template('search.html', results=unique_quotes, query=query, content_type='quotes')
        except Exception as e:
            flash(f'Search error: {str(e)}', 'error')
            return render_template('search.html', results=[], query=query, content_type='quotes')
    return render_template('search.html', results=[], query='', content_type='quotes')

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

            # Create quote
            quote_data = {
                'quote_text': quote_text,
                'author_id': author_id,
                'source': source if source else None,
                'quote_date': quote_date if quote_date else None,
                'date_approximation': date_approximation if date_approximation else None,
                'tags': tags,
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

            # Update quote
            update_data = {
                'quote_text': quote_text,
                'author_id': author_id,
                'source': source if source else None,
                'quote_date': quote_date if quote_date else None,
                'date_approximation': date_approximation if date_approximation else None,
                'tags': tags
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

            # Delete quote
            supabase.table('cms_quotes')\
                .delete()\
                .eq('id', quote_id)\
                .execute()

            # Log activity
            supabase.table('cms_activity_log').insert({
                'user_id': session['user']['id'],
                'action': 'quote_deleted',
                'details': f'Deleted quote: {quote_text[:50]}...'
            }).execute()

            flash('Quote deleted successfully', 'success')
        else:
            flash('Quote not found', 'error')

    except Exception as e:
        flash(f'Error deleting quote: {str(e)}', 'error')

    return redirect(url_for('quotes'))

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
