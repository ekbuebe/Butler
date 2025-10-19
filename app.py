import os
import requests
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI
from dotenv import load_dotenv

# Microsoft Graph-Integration
from integrations.ms_graph_helper import (
    get_access_token,
    get_mails,
    get_calendar,
    get_contacts,
    get_tasks
)

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

            # Sprachdatei herunterladen
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

            # 🔊 Konvertieren in WAV
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
            lower_text = incoming_text.lower()
            token = None

            # 💼 Microsoft Graph-Kommandos
            if "mail" in lower_text or "nachricht" in lower_text:
                try:
                    token = get_access_token()
                    mails = get_mails(token)
                    if not mails:
                        reply_text = "📭 Keine neuen E-Mails gefunden."
                    else:
                        reply_text = "\n\n".join(
                            [f"✉️ {m.get('subject','(Kein Betreff)')} — von {m.get('from',{}).get('emailAddress',{}).get('address','Unbekannt')}" for m in mails]
                        )
                except Exception as e:
                    reply_text = f"❌ Fehler beim Abrufen der Mails: {e}"

            elif "kalender" in lower_text or "termin" in lower_text:
                try:
                    token = get_access_token()
                    events = get_calendar(token)
                    if not events:
                        reply_text = "📅 Keine bevorstehenden Termine gefunden."
                    else:
                        reply_text = "\n\n".join(
                            [f"📆 {e.get('subject','(Ohne Titel)')} — am {e.get('start',{}).get('dateTime','?')}" for e in events]
                        )
                except Exception as e:
                    reply_text = f"❌ Fehler beim Abrufen der Termine: {e}"

            elif "aufgabe" in lower_text or "to-do" in lower_text:
                try:
                    token = get_access_token()
                    tasks = get_tasks(token)
                    if not tasks:
                        reply_text = "✅ Keine offenen Aufgaben."
                    else:
                        reply_text = "\n".join([f"📝 {t.get('displayName','(Unbenannt)')}" for t in tasks])
                except Exception as e:
                    reply_text = f"❌ Fehler beim Abrufen der Aufgaben: {e}"

            elif "kontakt" in lower_text or "kontakte" in lower_text:
                try:
                    token = get_access_token()
                    contacts = get_contacts(token)
                    if not contacts:
                        reply_text = "📇 Keine gespeicherten Kontakte gefunden."
                    else:
                        reply_text = "\n".join([f"👤 {c.get('displayName','Unbekannt')}" for c in contacts])
                except Exception as e:
                    reply_text = f"❌ Fehler beim Abrufen der Kontakte: {e}"

            else:
                # 💬 GPT-Antwort für normale Chats
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
    print("🚀 Butler läuft ...")
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
