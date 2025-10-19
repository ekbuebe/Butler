import os
import requests
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI
from dotenv import load_dotenv

# Microsoft Graph
from integrations.ms_graph_helper import (
    get_access_token,
    get_mails,
    get_calendar,
    get_contacts,
    get_tasks
)

# Notion
from integrations.notion_helper import (
    get_databases,
    get_pages_in_database,
    create_page
)

# === ENV laden ===
load_dotenv()

app = Flask(__name__)

# === Clients & Keys ===
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH = os.getenv("TWILIO_AUTH")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

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

                os.system('ffmpeg -y -i voice.ogg -ar 44100 -ac 2 voice.wav')

                with open("voice.wav", "rb") as audio_file:
                    transcription = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file
                    )
                incoming_text = transcription.text
                os.remove("voice.ogg")
                os.remove("voice.wav")
                print("🗣️ Transkribiert:", incoming_text)
            else:
                return _twilio_response("❌ Fehler beim Abrufen der Sprachnachricht.")

        # Kein Text erkannt?
        if not incoming_text:
            return _twilio_response("Ich konnte nichts verstehen 🎧 – bitte sprich oder schreib nochmal.")

        lower_text = incoming_text.lower()

        # === Microsoft Graph Befehle ===
        if "mail" in lower_text or "nachricht" in lower_text:
            token = get_access_token()
            mails = get_mails(token)
            reply_text = "\n".join([f"📧 {m.get('subject', 'Ohne Betreff')}" for m in mails]) or "Keine Mails gefunden."

        elif "kalender" in lower_text or "termin" in lower_text:
            token = get_access_token()
            events = get_calendar(token)
            reply_text = "\n".join([f"📅 {e.get('subject', 'Ohne Titel')}" for e in events]) or "Keine Termine gefunden."

        elif "kontakt" in lower_text or "kontakte" in lower_text:
            token = get_access_token()
            contacts = get_contacts(token)
            reply_text = "\n".join([f"👤 {c.get('displayName', 'Unbekannt')}" for c in contacts]) or "Keine Kontakte gefunden."

        elif "aufgabe" in lower_text or "to-do" in lower_text:
            token = get_access_token()
            tasks = get_tasks(token)
            reply_text = "\n".join([f"📝 {t.get('displayName', 'Unbenannte Aufgabe')}" for t in tasks]) or "Keine Aufgaben gefunden."

        # === 🧠 Notion Befehle ===
        elif "notion" in lower_text:
            # Neue Notiz
            if "neue" in lower_text or "erstellen" in lower_text or "notiz" in lower_text:
                note_text = incoming_text.replace("notion", "").replace("neue", "").replace("erstellen", "").strip()
                try:
                    create_page(NOTION_DATABASE_ID, note_text)
                    reply_text = f"✅ Neue Notiz in Notion gespeichert:\n„{note_text}“"
                except Exception as e:
                    reply_text = f"❌ Fehler beim Erstellen der Notiz: {e}"

            # Notizen anzeigen
            elif "zeige" in lower_text or "liste" in lower_text or "notizen" in lower_text:
                try:
                    pages = get_pages_in_database(NOTION_DATABASE_ID)
                    if not pages:
                        reply_text = "📭 Keine Notizen gefunden."
                    else:
                        note_titles = []
                        for p in pages:
                            title = p["properties"].get("Name", {}).get("title", [])
                            title_text = title[0]["text"]["content"] if title else "Ohne Titel"
                            note_titles.append(f"📝 {title_text}")
                        reply_text = "\n".join(note_titles)
                except Exception as e:
                    reply_text = f"❌ Fehler beim Laden der Notizen: {e}"

            # Alle Datenbanken zeigen
            elif "datenbank" in lower_text:
                try:
                    dbs = get_databases()
                    reply_text = "\n".join([f"🗂️ {d['title'][0]['plain_text']}" for d in dbs if d.get('title')]) or "Keine Datenbanken gefunden."
                except Exception as e:
                    reply_text = f"❌ Fehler beim Abrufen der Datenbanken: {e}"

            else:
                reply_text = "🤔 Sag z. B. „Notion neue Notiz Einkaufsliste“ oder „Notion zeig meine Notizen“"

        # === 💬 GPT Smalltalk ===
        else:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": incoming_text}]
            )
            reply_text = response.choices[0].message.content.strip()

        # 📲 Antwort an WhatsApp
        return _twilio_response(reply_text)

    except Exception as e:
        print("💥 Fehler:", e)
        return _twilio_response("🚨 Unerwarteter Fehler. Bitte versuch es später erneut.")


# === Start ===
if __name__ == "__main__":
    print("🚀 Butler läuft auf Port 5000 ...")
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
