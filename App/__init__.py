from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import os
from dotenv import load_dotenv
import pyodbc
from flask_bcrypt import Bcrypt
import azure.cognitiveservices.speech as speech_sdk
import json
from authlib.integrations.flask_client import OAuth


def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.secret_key = os.urandom(24)
    bcrypt = Bcrypt(app)
    oauth = OAuth(app)

    # Google OAuth configuration
    oauth.register(
        name='google',
        client_id=os.getenv('GOOGLE_CLIENT_ID'),
        client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
        access_token_url='https://oauth2.googleapis.com/token',
        authorize_url='https://accounts.google.com/o/oauth2/auth',
        api_base_url='https://www.googleapis.com/oauth2/v2/',
        client_kwargs={'scope': 'openid email profile'},
        jwks_uri='https://www.googleapis.com/oauth2/v3/certs'
    )

    # Load environment variables
    load_dotenv()
    ai_key = os.getenv('SPEECH_KEY')
    ai_region = os.getenv('SPEECH_REGION')

    # Azure SQL Database connection details
    server = os.getenv('AZURE_SQL_SERVER')
    database = os.getenv('AZURE_SQL_DATABASE')
    username = os.getenv('AZURE_SQL_USERNAME')
    password = os.getenv('AZURE_SQL_PASSWORD')

    # Set up connection to Azure SQL Database
    conn_str = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}'
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    # Ensure users table exists
    cursor.execute('''
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='users' AND xtype='U')
        CREATE TABLE users (
            id INT PRIMARY KEY IDENTITY,
            username NVARCHAR(100) NOT NULL UNIQUE,
            password NVARCHAR(255) NOT NULL
        )
    ''')
    conn.commit()

    # Load configuration
    with open(os.path.join(os.path.dirname(__file__), 'config.json')) as config_file:
        config = json.load(config_file)
    languages = config['languages']

    # Speech and translation configurations
    translation_config = speech_sdk.translation.SpeechTranslationConfig(ai_key, ai_region)
    translation_config.speech_recognition_language = 'en-US'
    for lang_code in languages.keys():
        translation_config.add_target_language(lang_code)

    speech_config = speech_sdk.SpeechConfig(ai_key, ai_region)

    # Routes
    @app.route('/')
    @app.route('/home')
    def home():
        if 'username' not in session:
            return redirect('/login')
        return render_template('index.html', username=session['username'], languages=languages)

    @app.route('/signup', methods=['GET', 'POST'])
    def signup():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            cursor.execute("SELECT * FROM dbo.users WHERE username = ?", (username,))
            if cursor.fetchone():
                return render_template('signup.html', error="User already exists.")
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            cursor.execute("INSERT INTO dbo.users (username, password) VALUES (?, ?)", (username, hashed_password))
            conn.commit()
            return redirect('/login')
        return render_template('signup.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            cursor.execute("SELECT * FROM dbo.users WHERE username = ?", (username,))
            user = cursor.fetchone()
            if not user or not bcrypt.check_password_hash(user[2], password):
                return render_template('login.html', error="Invalid credentials.")
            session['username'] = username
            return redirect('/')
        return render_template('login.html', google_login_url=url_for('google_login'))

    @app.route('/logout')
    def logout():
        session.clear()
        return redirect('/login')

    @app.route('/login/google')
    def google_login():
        redirect_uri = url_for('google_callback', _external=True)
        return oauth.google.authorize_redirect(redirect_uri)

    @app.route('/login/callback')
    def google_callback():
        token = oauth.google.authorize_access_token()
        user_info = oauth.google.get('userinfo').json()
        email = user_info['email']
        cursor.execute("SELECT * FROM dbo.users WHERE username = ?", (email,))
        if not cursor.fetchone():
            hashed_password = bcrypt.generate_password_hash(os.urandom(24)).decode('utf-8')
            cursor.execute("INSERT INTO dbo.users (username, password) VALUES (?, ?)", (email, hashed_password))
            conn.commit()
        session['username'] = email
        return redirect('/')

    @app.route('/save_chat', methods=['POST'])
    def save_chat():
        if 'username' not in session:
            return jsonify({'error': 'User not logged in'}), 401
        username = session['username']
        data = request.get_json()
        cursor.execute(
            "INSERT INTO chat_history (username, original_text, translated_text, target_language) VALUES (?, ?, ?, ?)",
            (username, data['original_text'], data['translated_text'], data['target_language'])
        )
        conn.commit()
        return jsonify({'message': 'Chat saved successfully'})


    @app.route('/index')
    def index():
        if 'user' not in session:
            return redirect(url_for('login'))
        return render_template('index.html', languages=languages)
    
    @app.route('/get_chat_history', methods=['GET'])
    def get_chat_history():
        username = session.get('username')
        target_language = request.args.get('language')

        if not username:
            return jsonify({'error': 'User not logged in'}), 401

        cursor = conn.cursor()
        cursor.execute(
            "SELECT original_text, translated_text FROM chat_history WHERE username = ? AND target_language = ?",
            (username, target_language)
        )
        chats = cursor.fetchall()

        chat_html = ""
        for chat in chats:
            chat_html += f"""
            <div class="bubble left-bubble">
                <p class="chat-text">{chat.original_text}</p>
            </div>
            <div class="bubble right-bubble">
                <p class="chat-text">Translation: {chat.translated_text}</p>
            </div>
            """
        return chat_html


    @app.route('/clear_chat_history', methods=['POST'])
    def clear_chat_history():
        if 'username' not in session:
            return jsonify({'error': 'User not logged in'}), 401

        username = session['username']
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_history WHERE username = ?", (username,))
        conn.commit()
        return jsonify({'message': 'Chat history cleared successfully'})


    @app.route('/translate', methods=['POST'])
    def translate():
        if 'username' not in session:
            return jsonify({'error': 'User not logged in'}), 401

        username = session['username']
        target_language = request.form['language']

        if target_language not in languages:
            return jsonify({'error': 'Unsupported language'}), 400

        # Translate speech
        audio_config = speech_sdk.AudioConfig(use_default_microphone=True)
        translator = speech_sdk.translation.TranslationRecognizer(translation_config, audio_config=audio_config)
        result = translator.recognize_once_async().get()

        if result.reason == speech_sdk.ResultReason.TranslatedSpeech:
            original_text = result.text
            translation = result.translations[target_language]

            # Synthesize translation
            speech_config.speech_synthesis_voice_name = languages[target_language]['voice']
            speech_synthesizer = speech_sdk.SpeechSynthesizer(speech_config)
            speak = speech_synthesizer.speak_text_async(translation).get()

            if speak.reason == speech_sdk.ResultReason.SynthesizingAudioCompleted:
                # Save the chat history to the database
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO chat_history (username, original_text, translated_text, target_language) VALUES (?, ?, ?, ?)",
                        (username, original_text, translation, target_language)
                    )
                    conn.commit()
                except Exception as e:
                    return jsonify({'error': 'Database error', 'details': str(e)}), 500

                return jsonify({'text': original_text, 'translation': translation})
            else:
                return jsonify({'error': 'Error synthesizing audio'}), 500
        else:
            return jsonify({'error': 'Error recognizing speech'}), 500


    return app
