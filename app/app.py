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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
