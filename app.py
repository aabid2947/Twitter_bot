import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename
from twitter_bot1 import TwitterBot
import chromedriver_autoinstaller

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'txt'}

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Install ChromeDriver
chromedriver_autoinstaller.install()

# Global bot instance for monitoring
twitter_bot = None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def load_accounts_list(file_path):
    accounts = []
    with open(file_path, mode='r', encoding='utf-8') as file:
        for line in file:
            account = line.strip()
            if account:
                accounts.append(account)
    return accounts

@app.route('/')
def index():
    monitoring_active = twitter_bot is not None and twitter_bot.monitoring
    return render_template('index.html', monitoring_active=monitoring_active)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        session['user_ids_file'] = filepath
        twitter_username = request.form.get('twitter_username')
        twitter_password = request.form.get('twitter_password')
        hashtags = request.form.get('hashtags')
        enable_monitoring = request.form.get('enable_monitoring') == 'on'
        monitor_interval = int(request.form.get('monitor_interval', 300))
        session['twitter_username'] = twitter_username
        session['twitter_password'] = twitter_password
        session['hashtags'] = hashtags
        session['enable_monitoring'] = enable_monitoring
        session['monitor_interval'] = monitor_interval
        return redirect(url_for('start_bot'))
    else:
        flash('File type not allowed. Please upload a .txt file.')
        return redirect(request.url)


@app.route('/start_bot')
def start_bot():
    # Check if all required information is available
    global twitter_bot
    user_ids_file = session.get('user_ids_file')
    twitter_username = session.get('twitter_username')
    twitter_password = session.get('twitter_password')
    phone_number = session.get('phone_number')
    hashtags = session.get('hashtags')
    enable_monitoring = session.get('enable_monitoring', False)
    monitor_interval = session.get('monitor_interval', 300)
    
    # Clear session data
    if not all([user_ids_file, twitter_username, twitter_password, hashtags]):
        flash('Missing required information')
        return redirect(url_for('index'))
    
    # Load user IDs and hashtags
    user_ids = load_accounts_list(user_ids_file)
    hashtag_list = [tag.strip() for tag in hashtags.split(',') if tag.strip()]
    
    # Start bot
    try:
        # Stop monitoring if already active
        if twitter_bot and twitter_bot.monitoring:
            twitter_bot.stop_monitoring()
        
        # Start bot
        twitter_bot = TwitterBot(twitter_username, twitter_password, phone_number)

        # Repost tweets
        results = twitter_bot.repost_tweets(
            user_ids, 
            hashtag_list, 
            start_monitoring=enable_monitoring,
            monitor_interval=monitor_interval
        )
        
        if enable_monitoring:
            flash('Bot started in monitoring mode. It will continue to run in the background.')
        return render_template('results.html', results=results, monitoring_active=enable_monitoring)
    except Exception as e:
        flash(f'Error: {str(e)}')
        return redirect(url_for('index'))

@app.route('/stop_monitoring')
def stop_monitoring():
    global twitter_bot
    if twitter_bot and twitter_bot.monitoring:
        twitter_bot.stop_monitoring()
        flash('Monitoring stopped successfully')
    else:
        flash('No active monitoring to stop')
    return redirect(url_for('index'))

@app.route('/status')
def status():
    global twitter_bot
    if twitter_bot:
        monitoring_active = twitter_bot.monitoring
        result_count = len(twitter_bot.results)
        latest_results = twitter_bot.results[-10:] if twitter_bot.results else []
        return jsonify({
            'monitoring_active': monitoring_active,
            'result_count': result_count,
            'latest_results': latest_results
        })
    else:
        return jsonify({
            'monitoring_active': False,
            'result_count': 0,
            'latest_results': []
        })

@app.route('/status_page')
def status_page():
    return render_template('status.html')

@app.route('/logout')
def logout_route():
    global twitter_bot
    if twitter_bot and twitter_bot.monitoring:
        twitter_bot.stop_monitoring()
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
