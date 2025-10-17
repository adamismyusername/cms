from flask import Flask
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key')

@app.route('/')
def index():
    return "CMS is running on port 80 inside Docker!"

@app.route('/test')
def test():
    # Test that environment variables are loaded
    has_supabase = 'YES' if os.environ.get('SUPABASE_URL') else 'NO'
    has_key = 'YES' if os.environ.get('SUPABASE_ANON_KEY') else 'NO'
    return f"""
    <h1>Environment Check</h1>
    <p>SUPABASE_URL present: {has_supabase}</p>
    <p>SUPABASE_ANON_KEY present: {has_key}</p>
    <p>FLASK_ENV: {os.environ.get('FLASK_ENV', 'not set')}</p>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)