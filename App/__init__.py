from flask import Flask, render_template, request, jsonify
import os
from dotenv import load_dotenv
import json
import azure.cognitiveservices.speech as speech_sdk


def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')

    # Load environment variables
    load_dotenv()
    ai_key = os.getenv('SPEECH_KEY')
    ai_region = os.getenv('SPEECH_REGION')

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
    def index():
        return render_template('index.html', languages=languages)

    @app.route('/translate', methods=['POST'])
    def translate():
        target_language = request.form['language']

        if target_language not in languages:
            return jsonify({'error': 'Unsupported language'}), 400

        # Translate speech
        audio_config = speech_sdk.AudioConfig(use_default_microphone=True)
        translator = speech_sdk.translation.TranslationRecognizer(translation_config, audio_config=audio_config)
        result = translator.recognize_once_async().get()

        if result.reason == speech_sdk.ResultReason.TranslatedSpeech:
            translation = result.translations[target_language]

            # Synthesize translation
            speech_config.speech_synthesis_voice_name = languages[target_language]['voice']
            speech_synthesizer = speech_sdk.SpeechSynthesizer(speech_config)
            speak = speech_synthesizer.speak_text_async(translation).get()

            if speak.reason == speech_sdk.ResultReason.SynthesizingAudioCompleted:
                od = result.text
                td = translation

                return jsonify({'text': od, 'translation': td})
            else:
                return jsonify({'error': 'Error synthesizing audio'}), 500
        else:
            return jsonify({'error': 'Error recognizing speech'}), 500

    return app