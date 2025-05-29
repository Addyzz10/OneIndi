import os
from flask import Flask, request, jsonify, render_template
import googletrans
import gtts
import playsound
import speech_recognition as sr
from datetime import datetime
import PyPDF2
import pytesseract
from PIL import Image
import logging
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled 


app = Flask(__name__, template_folder='templates', static_folder='static')
translator = googletrans.Translator()
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
logging.basicConfig(level=logging.DEBUG)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/translate_voice', methods=['POST'])
def translate_voice():
    recognizer = sr.Recognizer()
    data = request.get_json()
    from_lang = data['from_lang']
    to_lang = data['to_lang']
    translate_to_voice = data.get('translate_to_voice', True)
   
    try:
        with sr.Microphone() as source:
            print("Speak now")
            voice = recognizer.listen(source)
            listen = recognizer.recognize_google(voice, language=from_lang)
            logging.debug(f"Recognized speech: {listen}")

        translate = translator.translate(listen, dest=to_lang)
        logging.debug(f"Translated text: {translate.text.encode('utf-8')}")

        if translate_to_voice:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"translated_{timestamp}.mp3"
            converted_audio = gtts.gTTS(translate.text, lang=to_lang)
            converted_audio.save(filename)
            playsound.playsound(filename)
            os.remove(filename)
       
        return jsonify({'translated_text': translate.text})
    except Exception as e:
        logging.error(f"Error in voice translation: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/translate_text', methods=['POST'])
def translate_text():
    data = request.get_json()
    text = data['text']
    to_lang = data['to_lang']
    try:
        translate = translator.translate(text, dest=to_lang)
        return jsonify({'translated_text': translate.text})
    except Exception as e:
        logging.error(f"Error in text translation: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/text_to_speech', methods=['POST'])
def text_to_speech():
    data = request.get_json()
    text = data['text']
    to_lang = data['to_lang']
   
    try:
        translate = translator.translate(text, dest=to_lang)

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"text_to_speech_{timestamp}.mp3"
        converted_audio = gtts.gTTS(translate.text, lang=to_lang)
        converted_audio.save(filename)
        playsound.playsound(filename)
        os.remove(filename)
       
        return jsonify({'status': 'success'})
    except Exception as e:
        logging.error(f"Error in text-to-speech: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/file_translate', methods=['POST'])
def file_translate():
    file = request.files['file']
    from_lang = request.form['from_lang']
    to_lang = request.form['to_lang']
    
    logging.debug(f"Received file: {file.filename}")
    logging.debug(f"Translate from: {from_lang}, Translate to: {to_lang}")

    if file.filename.endswith('.txt'):
        try:
            text = file.read().decode('utf-8')
            logging.debug(f"Extracted text from .txt file: {text[:100]}")  # Log the first 100 characters
        except Exception as e:
            logging.error(f"Error reading .txt file: {e}")
            return jsonify({'error': 'Failed to read .txt file'}), 500
    elif file.filename.endswith('.pdf'):
        try:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ''
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text()
            logging.debug(f"Extracted text from .pdf file: {text[:100]}")  # Log the first 100 characters
        except Exception as e:
            logging.error(f"Error reading .pdf file: {e}")
            return jsonify({'error': 'Failed to read .pdf file'}), 500
    else:
        logging.error('Unsupported file type')
        return jsonify({'error': 'Unsupported file type'}), 400

    try:
        translate = translator.translate(text, dest=to_lang)
        logging.debug(f"Translated text: {translate.text[:100]}")  # Log the first 100 characters of the translation
        return jsonify({'translated_text': translate.text})
    except Exception as e:
        logging.error(f"Error translating text: {e}")
        return jsonify({'error': 'Translation failed'}), 500

@app.route('/image_translate', methods=['POST'])
def image_translate():
    file = request.files['file']
    from_lang = request.form['from_lang']
    to_lang = request.form['to_lang']

    if file and (file.filename.endswith('.jpg') or file.filename.endswith('.png') or file.filename.endswith('.jpeg')):
        try:
            image = Image.open(file)
            myconfig = r"--psm 6 --oem 3"
            text = pytesseract.image_to_string(image, config=myconfig)
            logging.debug(f"Extracted text: {text}")
            translate = translator.translate(text, dest=to_lang)
            logging.debug(f"Translated text: {translate.text}")
            return jsonify({'translated_text': translate.text})
        except Exception as e:
            logging.error(f"Error processing image: {e}")
            return jsonify({'error': 'Failed to process the image'}), 500
    else:
        logging.error('Unsupported file type or file not found')
        return jsonify({'error': 'Unsupported file type'}), 400

@app.route('/youtube_caption_translate', methods=['POST'])
def youtube_caption_translate():
    data = request.get_json()
    video_id = data['video_id']
    to_lang = data['to_lang']

    # Input Validation: Check if video_id is a valid YouTube video ID
    if not (video_id and len(video_id) == 11 and video_id.isalnum()):
        return jsonify({'error': 'Invalid YouTube video ID'}), 400 

    try:
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
        except NoTranscriptFound:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en-US']) 


        full_text = ' '.join([entry['text'] for entry in transcript])
        
        # Check for empty transcripts (after whitespace removal)
        if not full_text.strip():
            return jsonify({'error': 'No transcript content found for this video'}), 404

        translate = translator.translate(full_text, dest=to_lang)

        # Robust JSON serialization with default empty string if translation fails
        response_data = {
            'translated_text': translate.text if translate.text is not None else "",
        }
        logging.debug(f"JSON Response: {response_data}")  # Log the JSON response
        return jsonify(response_data)

    except NoTranscriptFound:
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            available_languages = [f"{t.language_code} ({t.language})" for t in transcript_list]
            return jsonify({'error': 'No English transcript found', 'available_languages': available_languages}), 404
        except Exception as e:
            return jsonify({'error': f'Failed to retrieve transcript information: {str(e)}'}), 500

    except TranscriptsDisabled:
        return jsonify({'error': 'Transcripts are disabled for this video'}), 404

    except Exception as e:
        logging.error(f"Error in YouTube caption translation: {e}, video_id: {video_id}, to_lang: {to_lang}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)