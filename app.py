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

# === Hilfsfunktion für WhatsApp-Antwort ===
def _twilio_response(message: str):
    resp = MessagingResponse()
    resp.message(message)
    return str(resp)


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

                # In WAV konvertieren
                os.system('ffmpeg -y -i voice.ogg -ar 44100 -ac 2 voice.wav')

                # Transkription mit OpenAI Whisper
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

        # === Microsoft Graph Befehle ===
        if "mail" in lower_text or "nachricht" in lower_text:
            try:
                token = get_access_token()
                mails = get_mails(token)
                reply_text = "\n".join([f"📧 {m.get('subject', 'Ohne Betreff')}" for m in mails]) or "Keine Mails gefunden."
            except Exception as e:
                reply_text = f"❌ Fehler beim Abrufen der Mails: {e}"

        elif "kalender" in lower_text or "termin" in lower_text:
            try:
                token = get_access_token()
                events = get_calendar(token)
                reply_text = "\n".join([f"📅 {e.get('subject', 'Ohne Titel')}" for e in events]) or "Keine Termine gefunden."
            except Exception as e:
                reply_text = f"❌ Fehler beim Abrufen der Kalenderdaten: {e}"

        elif "kontakt" in lower_text or "kontakte" in lower_text:
            try:
                token = get_access_token()
                contacts = get_contacts(token)
                reply_text = "\n".join([f"👤 {c.get('displayName', 'Unbekannt')}" for c in contacts]) or "Keine Kontakte gefunden."
            except Exception as e:
                reply_text = f"❌ Fehler beim Abrufen der Kontakte: {e}"

        elif "aufgabe" in lower_text or "to-do" in lower_text:
            try:
                token = get_access_token()
                tasks = get_tasks(token)
                reply_text = "\n".join([f"📝 {t.get('displayName', 'Unbenannte Aufgabe')}" for t in tasks]) or "Keine Aufgaben gefunden."
            except Exception as e:
                reply_text = f"❌ Fehler beim Abrufen der Aufgaben: {e}"

        else:
            # 💬 GPT-Antwort für Chat
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": incoming_text}]
                )
                reply_text = response.choices[0].message.content.strip()
            except Exception as e:
                print("❌ GPT-Fehler:", e)
                reply_text = "😕 Es ist ein unerwarteter Fehler aufgetreten."

        # 📲 Antwort an WhatsApp senden
        return _twilio_response(reply_text)

    except Exception as e:
        print("💥 Allgemeiner Fehler:", e)
        return _twilio_response("🚨 Unerwarteter Serverfehler. Bitte versuch es später erneut.")


# === Start ===
if __name__ == "__main__":
    print("🚀 Butler läuft auf Port 5000 ...")
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
