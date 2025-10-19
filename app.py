import os
import requests
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI
from dotenv import load_dotenv
from integrations.ms_graph_helper import (
    get_access_token,
    get_mails,
    get_calendar,
    get_contacts,
    get_tasks
)

# === ENV laden ===
load_dotenv()

app = Flask(__name__)

# === Clients & Keys ===
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH = os.getenv("TWILIO_AUTH")

# === Haupt-Webhook ===
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        num_media = int(request.values.get("NumMedia", 0))
        incoming_text = request.values.get("Body", "").strip()
        reply_text = ""

        # 🎙️ Sprachnachricht erkannt
        if num_media > 0:
            media_url = request.values.get("MediaUrl0")
            audio_response = requests.get(media_url, auth=(TWILIO_SID, TWILIO_AUTH))

            if audio_response.status_code == 200:
                with open("voice.ogg", "wb") as f:
                    f.write(audio_response.content)

                os.system('ffmpeg -y -i voice.ogg -ar 44100 -ac 2 voice.wav')

                with open("voice.wav", "rb") as audio_file:
                    transcription = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file
                    )
                incoming_text = transcription.text
                print("🗣️ Transkribiert:", incoming_text)

                os.remove("voice.ogg")
                os.remove("voice.wav")
            else:
                return _twilio_response("❌ Fehler beim Abrufen der Sprachnachricht.")

        # 🧠 Kein Text?
        if not incoming_text:
            return _twilio_response("Ich konnte nichts verstehen 🎧 – bitte sprich oder schreib nochmal.")

        lower_text = incoming_text.lower()
        token = None

        # === Microsoft Graph Funktionen ===
        if "mail" in lower_text or "nachricht" in lower_text:
            token = get_access_token()
            mai
