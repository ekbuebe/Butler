import os
import threading
import requests
import subprocess
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

# --- BACKGROUND VERARBEITUNG DER SPRACHNACHRICHT ---
def process_audio(media_url, from_number, to_number):
    try:
        # 🔊 Sprachdatei laden
        audio_response = requests.get(media_url, auth=(TWILIO_SID, TWILIO_AUTH))
        with open("voice.ogg", "wb") as f:
            f.write(audio_response.content)

        # 🎧 In WAV konvertieren (Mono + 16kHz = perfekt für Whisper)
        subprocess.run(
            ['ffmpeg', '-y', '-i', 'voice.ogg', '-ar', '16000', '-ac', '1', '-b:a', '32k', 'voice.wav'],
            timeout=120, check=True
        )

        # 🧠 OpenAI Whisper → Text
        with open("voice.wav", "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        text = transcription.text
        print("🗣️ Transkribierter Text:", text)

        # 💬 GPT antwortet auf das Transkript
        gpt_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": text}]
        )
        reply_text = gpt_response.choices[0].message.content.strip()

        # 📨 Nachricht über Twilio REST API zurücksenden
        requests.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json",
            auth=(TWILIO_SID, TWILIO_AUTH),
            data={
                "From": to_number,  # 🔥 automatisch Twilio-Nummer
                "To": from_number,  # Nutzer, der die Sprachnachricht gesendet hat
                "Body": reply_text
            }
        )
        print("✅ Antwort gesendet an:", from_number)

        # 🧹 Aufräumen
        for f in ["voice.ogg", "voice.wav"]:
            if os.path.exists(f):
                os.remove(f)

    except Exception as e:
        print("❌ Fehler in Background-Verarbeitung:", e)


# --- HAUPT-WEBHOOK ---
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        from_number = request.values.get("From", "")
        to_number = request.values.get("To", "")
        num_media = int(request.values.get("NumMedia", 0))
        incoming_text = request.values.get("Body", "").strip()

        if num_media > 0:
            media_url = request.values.get("MediaUrl0")
            print(f"🎙️ Sprachdatei empfangen von {from_number} an {to_number}: {media_url}")

            # Sofortige Zwischenantwort, damit Twilio nicht abbricht
            resp = MessagingResponse()
            resp.message("Ich transkribiere deine Sprachnachricht 🎧... Einen Moment bitte ⏳")

            # Hintergrund-Thread starten
            threading.Thread(target=process_audio, args=(media_url, from_number, to_number)).start()

            return Response(str(resp), mimetype="application/xml")

        # 📝 Wenn Textnachricht
        if incoming_text:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": incoming_text}]
            )
            reply_text = response.choices[0].message.content.strip()
        else:
            reply_text = "Ich konnte nichts verstehen 🎧 – bitte sprich oder schreib noch einmal."

        # Antwort sofort senden
        resp = MessagingResponse()
        resp.message(reply_text)
        return Response(str(resp), mimetype="application/xml")

    except Exception as e:
        print("💥 Allgemeiner Fehler:", e)
        resp = MessagingResponse()
        resp.message("🚨 Ein Fehler ist aufgetreten. Bitte versuch es erneut.")
        return Response(str(resp), mimetype="application/xml")


# --- START ---
if __name__ == "__main__":
    print("🚀 Butler läuft auf Port 5000 ...")
    app.run(host="0.0.0.0", port=5000)
