import os
import requests
from flask import Flask, request, Response
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI
from dotenv import load_dotenv

# --- ENV-VARIABLEN LADEN ---
load_dotenv()

# --- INITIALISIERUNG ---
app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH = os.getenv("TWILIO_AUTH")


# --- HAUPT-WEBHOOK ---
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        num_media = int(request.values.get("NumMedia", 0))
        incoming_text = request.values.get("Body", "").strip()
        reply_text = ""

        # 📦 Sprachdatei prüfen
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
                print(f"❌ Fehler beim Herunterladen: {audio_response.status_code}")
                resp = MessagingResponse()
                resp.message("Fehler beim Abrufen der Sprachnachricht 😕")
                return Response(str(resp), mimetype="application/xml")

            # 🔊 Umwandeln in WAV
            conversion_result = os.system('ffmpeg -y -i voice.ogg -ar 44100 -ac 2 voice.wav')
            if conversion_result != 0 or not os.path.exists("voice.wav"):
                print("❌ Fehler bei der ffmpeg-Konvertierung.")
                resp = MessagingResponse()
                resp.message("Die Sprachnachricht konnte nicht verarbeitet werden 🎧.")
                return Response(str(resp), mimetype="application/xml")

            # 🧠 Whisper → Text
            with open("voice.wav", "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            incoming_text = transcription.text
            print("🗣️ Transkribierter Text:", incoming_text)

            # 🧹 Aufräumen
            for file in ["voice.ogg", "voice.wav"]:
                if os.path.exists(file):
                    os.remove(file)

        # 🧩 Wenn kein Text erkannt wurde
        if not incoming_text:
            reply_text = "Ich konnte nichts verstehen 🎧 – bitte sprich oder schreib noch einmal."
        else:
            # 💬 GPT-Antwort erzeugen
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": incoming_text}]
            )
            reply_text = response.choices[0].message.content.strip()

        # 📲 Twilio-Antwort senden (wichtig für WhatsApp!)
        resp = MessagingResponse()
        resp.message(reply_text)
        return Response(str(resp), mimetype="application/xml")

    except Exception as e:
        print("💥 Allgemeiner Fehler im Webhook:", e)
        resp = MessagingResponse()
        resp.message("🚨 Unerwarteter Serverfehler. Bitte versuch es später erneut.")
        return Response(str(resp), mimetype="application/xml")


# --- SERVER STARTEN (lokal & Render) ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Butler läuft auf Port {port} und wartet auf WhatsApp-Nachrichten ...")
    app.run(host="0.0.0.0", port=port)
