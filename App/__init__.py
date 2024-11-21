from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import os
from dotenv import load_dotenv
import pyodbc
from flask_bcrypt import Bcrypt
import azure.cognitiveservices.speech as speech_sdk
import json

def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.secret_key = os.urandom(24)
    bcrypt = Bcrypt(app)

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

    # Create users table if it doesn't exist (this can be run once during setup)
    cursor.execute('''
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='users' AND xtype='U')
        CREATE TABLE users (
            id INT PRIMARY KEY IDENTITY,
            username NVARCHAR(100) NOT NULL UNIQUE,
            password NVARCHAR(255) NOT NULL
        )
    ''')
    conn.commit()

    # Load supported languages and voices from configuration file
    with open(os.path.join(os.path.dirname(__file__), 'config.json')) as config_file:
        config = json.load(config_file)

    languages = config['languages']

    # Configure translation
    translation_config = speech_sdk.translation.SpeechTranslationConfig(ai_key, ai_region)
    translation_config.speech_recognition_language = 'en-US'
    for lang_code in languages.keys():
        translation_config.add_target_language(lang_code)

    # Configure speech
    speech_config = speech_sdk.SpeechConfig(ai_key, ai_region)

    @app.route('/')
    @app.route('/home')
    def home():
        if 'username' not in session:
            return redirect('/login')  # Redirect to login if user is not authenticated

        # Pass the languages dictionary to the template
        return render_template('index.html', username=session['username'], languages=languages)



    @app.route('/save_chat', methods=['POST'])
    def save_chat():
        if 'username' not in session:
            return jsonify({'error': 'User not logged in'}), 401

        username = session['username']
        data = request.get_json()
        original_text = data.get('original_text')
        translated_text = data.get('translated_text')

        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_history (username, original_text, translated_text) VALUES (?, ?, ?)",
            (username, original_text, translated_text)
        )
        conn.commit()
        return jsonify({'message': 'Chat saved successfully'})


    @app.route('/signup', methods=['GET', 'POST'])
    def signup():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']

            cursor = conn.cursor()
            # Check if the username already exists
            cursor.execute("SELECT * FROM dbo.users WHERE username = ?", (username,))
            user = cursor.fetchone()

            if user:
                return render_template('signup.html', error="User already exists. Please choose a different username.")

            # Insert new user
            cursor.execute("INSERT INTO dbo.users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            return redirect('/login')  # Redirect to login after successful signup

        return render_template('signup.html')



    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']

            cursor = conn.cursor()
            # Fetch user by username
            cursor.execute("SELECT * FROM dbo.users WHERE username = ?", (username,))
            user = cursor.fetchone()

            if not user:
                return render_template('login.html', error="No such user exists.")

            # Validate the password using bcrypt
            stored_hashed_password = user[2]  # Assuming the `password` column is the third column
            if bcrypt.check_password_hash(stored_hashed_password, password):
                session['username'] = username
                return redirect('/')  # Redirect to the index/home page
            else:
                return render_template('login.html', error="Incorrect password.")

        return render_template('login.html')


    @app.route('/logout')
    def logout():
        session.clear()
        return redirect('/login')


    @app.route('/index')
    def index():
        if 'user' not in session:
            return redirect(url_for('login'))
        return render_template('index.html', languages=languages)
    
    @app.route('/get_chat_history', methods=['GET'])
    def get_chat_history():
        username = session.get('username')
        if not username:
            return jsonify({'error': 'User not logged in'}), 401

        cursor = conn.cursor()
        cursor.execute("SELECT original_text, translated_text FROM chat_history WHERE username = ?", (username,))
        chats = cursor.fetchall()

        # Format the chat bubbles as HTML
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
