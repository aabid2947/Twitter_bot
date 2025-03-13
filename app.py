import os
import uuid
import threading
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename
from twitter_bot import TwitterBot
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

# Global dictionary to hold multiple TwitterBot instances
twitter_bots = {}

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
    # Build a list of active bots for display
    active_bots = [
        {"bot_id": bot.bot_id, "username": bot.username, "monitored_users": bot.user_ids}
        for bot in twitter_bots.values()
        if getattr(bot, "monitoring", False)
    ]
    monitoring_active = len(active_bots) > 0
    return render_template('index.html', monitoring_active=monitoring_active, active_bots=active_bots)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(url_for('index'))
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('index'))
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        session['user_ids_file'] = filepath

        # Get form values
        twitter_username = request.form.get('twitter_username')
        twitter_password = request.form.get('twitter_password')
        phone_number = request.form.get('phone_number')
        hashtags = request.form.get('hashtags')
        # Optionally, add monitoring settings from form (if available)
        # enable_monitoring = request.form.get('enable_monitoring') == 'on'
        # monitor_interval = int(request.form.get('monitor_interval', 300))
        
        session['twitter_username'] = twitter_username
        session['twitter_password'] = twitter_password
        session['phone_number'] = phone_number
        session['hashtags'] = hashtags
        # session['enable_monitoring'] = enable_monitoring
        # session['monitor_interval'] = monitor_interval

        # Use monitoring enabled by default
        enable_monitoring = session.get('enable_monitoring', True)
        monitor_interval = session.get('monitor_interval', 300)
        
        # Verify required info
        if not all([session.get('user_ids_file'), twitter_username, twitter_password, hashtags]):
            flash('Missing required information')
            return redirect(url_for('index'))
        
        # Load user IDs and hashtags from the uploaded file and form input
        user_ids = load_accounts_list(filepath)
        hashtag_list = [tag.strip() for tag in hashtags.split(',') if tag.strip()]
        
        try:
            # Create a new bot instance and assign the username for display
            new_bot = TwitterBot(twitter_username, twitter_password, phone_number)
            new_bot.username = twitter_username
            new_bot.user_ids = user_ids
            new_bot.hashtags = hashtag_list
            new_bot.results = []  # Ensure results attribute exists
            
            # Assign a unique ID to the bot
            new_bot.bot_id = str(uuid.uuid4())
            
            if enable_monitoring:
                # Start repost_tweets in a background thread with monitoring enabled.
                thread = threading.Thread(
                    target=new_bot.repost_tweets,
                    args=(user_ids, hashtag_list, True, monitor_interval, phone_number)
                )
                thread.daemon = True  # Ensure thread exits when the main process does.
                thread.start()
                twitter_bots[new_bot.bot_id] = new_bot
                flash(f"Bot started successfully with monitoring enabled. Bot ID: {new_bot.bot_id}")
            else:
                # If monitoring is disabled, run synchronously.
                results = new_bot.repost_tweets(user_ids, hashtag_list)
                flash("Bot started successfully.")
                twitter_bots[new_bot.bot_id] = new_bot
        except Exception as e:
            flash(f'Error: {str(e)}')
        
        # Build a list of all active bots for display
        active_bots = [
            {"bot_id": bot.bot_id, "username": bot.username, "monitored_users": bot.user_ids}
            for bot in twitter_bots.values() if getattr(bot, "monitoring", False)
        ]
        return render_template('index.html', monitoring_active=True, active_bots=active_bots)
    else:
        flash('File type not allowed. Please upload a .txt file.')
        return redirect(url_for('index'))

@app.route('/stop_monitoring')
def stop_monitoring():
    bot_id = request.args.get('bot_id')
    if bot_id and bot_id in twitter_bots:
        bot = twitter_bots[bot_id]
        if getattr(bot, "monitoring", False):
            bot.stop_monitoring()
            flash(f'Monitoring stopped for bot {bot_id}')
        else:
            flash(f'Bot {bot_id} is not currently monitoring')
    else:
        flash('No valid bot ID provided')
    return redirect(url_for('index'))

@app.route('/status')
def status():
    statuses = []
    for bot in twitter_bots.values():
        statuses.append({
            'bot_id': bot.bot_id,
            'monitoring_active': bot.monitoring,
            'result_count': len(bot.results) if hasattr(bot, 'results') else 0,
            'latest_results': bot.results[-10:] if hasattr(bot, 'results') and bot.results else []
        })
    return jsonify(statuses)

@app.route('/status_page')
def status_page():
    return render_template('status.html')

@app.route('/logout')
def logout_route():
    # Do not stop bots on logout; they will continue running.
    session.clear()
    flash("Logged out, but bots will continue running.")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
