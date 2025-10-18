import os
import requests
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI
from dotenv import load_dotenv

# --- ENV-VARIABLEN LADEN ---
load_dotenv()

# --- INITIALISIERUNG ---
app = Flask(__name__)
client = OpenAI(api_key=os.getenv(OPENAI_API_KEY))

TWILIO_SID = os.getenv(TWILIO_SID)
TWILIO_AUTH = os.getenv(TWILIO_AUTH)

# --- HAUPT-WEBHOOK ---
@app.route(webhook, methods=[POST])
def webhook()
    try
        num_media = int(request.values.get(NumMedia, 0))
        incoming_text = request.values.get(Body, ).strip()
        reply_text = 

        # 📦 Prüfen, ob Audio gesendet wurde
        if num_media  0
            media_url = request.values.get(MediaUrl0)
            content_type = request.values.get(MediaContentType0, )
            print(f🎙️ Sprachdatei empfangen {media_url} ({content_type}))

            # Sprachdatei mit Twilio-Auth herunterladen
            audio_response = requests.get(media_url, auth=(TWILIO_SID, TWILIO_AUTH))
            if audio_response.status_code == 200
                with open(voice.ogg, wb) as f
                    f.write(audio_response.content)
                print(✅ Sprachdatei erfolgreich heruntergeladen.)
            else
                print(f❌ Fehler beim Herunterladen der Datei {audio_response.status_code})
                resp = MessagingResponse()
                resp.message(Fehler beim Abrufen der Sprachnachricht 😕)
                return str(resp)

            # 🔊 In WAV umwandeln (Whisper versteht .wav am besten)
            conversion_result = os.system('ffmpeg -y -i voice.ogg -ar 44100 -ac 2 voice.wav')
            if conversion_result != 0 or not os.path.exists(voice.wav)
                print(❌ Fehler bei der ffmpeg-Konvertierung.)
                resp = MessagingResponse()
                resp.message(Die Sprachnachricht konnte nicht verarbeitet werden 🎧.)
                return str(resp)

            # 🧠 Whisper → Text
            with open(voice.wav, rb) as audio_file
                transcription = client.audio.transcriptions.create(
                    model=whisper-1,
                    file=audio_file
                )
            incoming_text = transcription.text
            print(🗣️ Transkribierter Text, incoming_text)

            # 🧹 Aufräumen
            for file in [voice.ogg, voice.wav]()
