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

# OpenAI Client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Twilio Auth-Daten
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH = os.getenv("TWILIO_AUTH")

# --- HAUPT-WEBHOOK ---
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        num_media = int(request.values.get("NumMedia", 0))
        incoming_text = request.values.get("Body", "").strip()
        reply_text = ""

        # 🎧 Sprachdatei erhalten?
        if num_media > 0:
            media_url = request.values.get("MediaUrl0")
            content_type = request.values.get("MediaContentType0", "")
            print(f"🎙️ Sprachdatei empfangen: {media_url} ({content_type})")

            # Sprachdatei mit Twilio-Auth herunterladen
            audio_response = requests.get(media_url, auth=(TWILIO_SID, TWILIO_AUTH))
            if audio_response.status_code == 200:
                with open("voice.ogg", "wb") as f:
                    f.write(audio_response.content)
                print("✅ Sprachdatei erfolgreich heruntergeladen.")
            else:
                print(f"❌ Fehler beim Download: {audio_response.status_code}")
                resp = MessagingResponse()
                resp.message("Fehler beim Abrufen der Sprachnachricht 😕")
                return str(resp)

            # 🔊 In WAV konvertieren (Whisper bevorzugt .wav)
            conversion_result = os.system('ffmpeg -y -i voice.ogg -ar 44100 -ac 2 voice.wav')
            if conversion_result != 0 or not os.path.exists("voice.wav"):
                print("❌ Fehler bei der ffmpeg-Konvertierung.")
                resp = MessagingResponse()
                resp.message("Die Sprachnachricht konnte nicht verarbeitet werden 🎧.")
                return str(resp)

            # 🧠 Whisper Speech-to-Text
            try:
                with open("voice.wav", "rb") as audio_file:
                    transcription = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file
                    )
                incoming_text = transcription.text
                print("🗣️ Transkribierter Text:", incoming_text)
            except Exception as e:
                print("❌ Whisper-Fehler:", e)
                resp = MessagingResponse()
                resp.message("Die Sprachnachricht konnte nicht erkannt werden 🛠️.")
                return str(resp)
            finally:
                for f in ["voice.ogg", "voice.wav"]:
                    if os.path.exists(f):
                        os.remove(f)

        # Kein Text erkannt?
        if not incoming_text:
            reply_text = "Ich konnte nichts verstehen 🎧 – bitte sprich oder schreib nochmal."
        else:
            try:
                # 💬 GPT-Antwort
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": incoming_text}]
                )
                reply_text = response.choices[0].message.content.strip()
            except Exception as e:
                print("❌ GPT-Fehler:", e)
                reply_text = "😕 Es ist ein unerwarteter Fehler aufgetreten."

        # 📲 Antwort an WhatsApp zurücksenden
        resp = MessagingResponse()
        resp.message(reply_text)
        return str(resp)

    except Exception as e:
        print("💥 Allgemeiner Fehler:", e)
        resp = MessagingResponse()
        resp.message("🚨 Unerwarteter Serverfehler. Bitte versuch es später erneut.")
        return str(resp)


# --- START ---
if __name__ == "__main__":
    print("🚀 Butler läuft auf Port 5000 ...")
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
