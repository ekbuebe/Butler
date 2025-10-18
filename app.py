import os
import threading
import time
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

# --- BACKGROUND VERARBEITUNG ---
def process_message(text, from_number, to_number):
    """GPT-Antwort im Hintergrund verarbeiten"""
    try:
        # 💬 GPT-Antwort generieren
        gpt_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": text}]
        )
        reply_text = gpt_response.choices[0].message.content.strip()

        # 🕒 kleine Pause, damit “tippt...” realistisch wirkt
        time.sleep(2)

        # ✉️ Finale Antwort senden
        requests.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json",
            auth=(TWILIO_SID, TWILIO_AUTH),
            data={"From": to_number, "To": from_number, "Body": reply_text}
        )
        print("✅ GPT-Antwort gesendet an:", from_number)

    except Exception as e:
        print("❌ Fehler bei GPT-Antwort:", e)


def process_audio(media_url, from_number, to_number):
    """Sprachnachricht laden, transkribieren und beantworten"""
    try:
        # 🔊 Sprachdatei laden
        audio_response = requests.get(media_url, auth=(TWILIO_SID, TWILIO_AUTH))
        with open("voice.ogg", "wb") as f:
            f.write(audio_response.content)

        # 🎧 Konvertieren in WAV
        subprocess.run(
            ['ffmpeg', '-y', '-i', 'voice.ogg', '-ar', '16000', '-ac', '1', '-b:a', '32k', 'voice.wav'],
            timeout=180, check=True
        )

        # 🧠 Whisper → Text
        with open("voice.wav", "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        text = transcription.text
        print("🗣️ Transkribierter Text:", text)

        # 💬 Sende kurz „Butler tippt...“
        requests.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json",
            auth=(TWILIO_SID, TWILIO_AUTH),
            data={"From": to_number, "To": from_number, "Body": "💬 Butler tippt gerade..."}
        )

        # GPT im Hintergrund
        threading.Thread(target=process_message, args=(text, from_number, to_number)).start()

        # 🧹 Aufräumen
        for f in ["voice.ogg", "voice.wav"]:
            if os.path.exists(f):
                os.remove(f)

    except Exception as e:
        print("❌ Fehler in process_audio:", e)


# --- HAUPT-WEBHOOK ---
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        from_number = request.values.get("From", "")
        to_number = request.values.get("To", "")
        num_media = int(request.values.get("NumMedia", 0))
        incoming_text = request.values.get("Body", "").strip()

        # 🎙️ Sprachnachricht
        if num_media > 0:
            media_url = request.values.get("MediaUrl0")
            print(f"🎙️ Sprachdatei empfangen: {media_url}")
            resp = MessagingResponse()
            resp.message("Ich verarbeite deine Sprachnachricht 🎧... Einen Moment bitte ⏳")

            # Hintergrund-Thread
            threading.Thread(target=process_audio, args=(media_url, from_number, to_number)).start()
            return Response(str(resp), mimetype="application/xml")

        # ✉️ Textnachricht
        if incoming_text:
            # Sofortige “tippt”-Nachricht senden
            requests.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json",
                auth=(TWILIO_SID, TWILIO_AUTH),
                data={"From": to_number, "To": from_number, "Body": "💬 Butler tippt gerade..."}
            )

            # GPT-Verarbeitung im Hintergrund
            threading.Thread(target=process_message, args=(incoming_text, from_number, to_number)).start()

            # Schnellantwort an Twilio (damit Webhook sofort schließt)
            resp = MessagingResponse()
            resp.message("✅ Nachricht empfangen – einen Moment...")
            return Response(str(resp), mimetype="application/xml")

        # Wenn weder Text noch Audio
        resp = MessagingResponse()
        resp.message("Ich konnte nichts verstehen 🎧 – bitte sprich oder schreib noch einmal.")
        return Response(str(resp), mimetype="application/xml")

    except Exception as e:
        print("💥 Allgemeiner Fehler:", e)
        resp = MessagingResponse()
        resp.message("🚨 Fehler – bitte versuch es erneut.")
        return Response(str(resp), mimetype="application/xml")


# --- START ---
if __name__ == "__main__":
    print("🚀 Butler läuft auf Port 5000 ...")
    app.run(host="0.0.0.0", port=5000)
